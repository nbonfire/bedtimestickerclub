"""Exercise the actual Add integration flow, entities, services, and unload."""

from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from homeassistant import bootstrap, loader
from homeassistant.core import HomeAssistant, State
from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er, restore_state
from homeassistant.util import dt as dt_util

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "bedtime_sticker_club"


class SetupTests(unittest.IsolatedAsyncioTestCase):
    async def test_add_integration_services_options_and_unload(self):
        with TemporaryDirectory() as directory:
            shutil.copytree(ROOT / "custom_components", Path(directory) / "custom_components")
            hass = HomeAssistant(directory)
            loader.async_setup(hass)
            try:
                await bootstrap.async_from_config_dict({
                    "homeassistant": {"time_zone": "America/New_York"},
                    "frontend": {}, "lovelace": {},
                }, hass)
                await hass.async_start()
                # A disabled legacy template can leave an unavailable placeholder;
                # migration must prefer the real saved state and reuse its ID.
                registry = er.async_get(hass)
                registry.async_get_or_create(
                    "sensor", "template", "bedtime_kid_3",
                    suggested_object_id="bedtime_kid_3",
                )
                legacy = State("sensor.bedtime_kid_3", "7", {
                    "month": "2026-10", "stickers": {}, "tasks": {},
                })
                restore_state.async_get(hass).last_states[legacy.entity_id] = restore_state.StoredState(
                    legacy, None, dt_util.utcnow(),
                )
                hass.states.async_set(legacy.entity_id, "unavailable", {"restored": True})
                hass.services.async_register("script", "bedtime_set_task", lambda call: None)
                blocked = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
                self.assertEqual(blocked["reason"], "legacy_package_active")
                hass.services.async_remove("script", "bedtime_set_task")
                result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
                self.assertEqual(result["type"], "form")
                result = await hass.config_entries.flow.async_configure(result["flow_id"], {
                    "kid_1_name": "Alex", "kid_2_name": "Sam", "kid_3_name": "Charlie",
                })
                self.assertEqual(result["type"], "create_entry")
                await hass.async_block_till_done()
                entry = result["result"]
                if entry.state == ConfigEntryState.NOT_LOADED:
                    self.assertTrue(await hass.config_entries.async_setup(entry.entry_id))
                    await hass.async_block_till_done()
                self.assertEqual(entry.state, ConfigEntryState.LOADED)
                self.assertTrue(frontend.async_panel_exists(hass, "bedtime-club"))
                self.assertEqual(hass.states.get("sensor.bedtime_kid_3").state, "7")
                self.assertEqual(registry.async_get("sensor.bedtime_kid_3").platform, DOMAIN)
                for entity in ("sensor.bedtime_routine", "sensor.bedtime_kid_1", "sensor.bedtime_kid_2", "sensor.bedtime_kid_3", "time.bedtime_dinner_time", "time.bedtime_bedtime_time"):
                    self.assertIsNotNone(hass.states.get(entity), entity)
                day = hass.states.get("sensor.bedtime_routine").attributes["routine_date"]
                for task in ("plate", "teeth", "outfit"):
                    await hass.services.async_call(DOMAIN, "set_task", {
                        "child_id": "kid_1", "routine_date": day,
                        "task": task, "completed": True,
                    }, blocking=True)
                await hass.services.async_call(DOMAIN, "choose_sticker", {
                    "child_id": "kid_1", "routine_date": day, "sticker": "🚀",
                }, blocking=True)
                self.assertEqual(hass.states.get("sensor.bedtime_kid_1").state, "1")
                self.assertEqual(hass.states.get("sensor.bedtime_kid_1").attributes["stickers"][day]["emoji"], "🚀")
                # Entity-targeted writes are closed; schedule changes go through
                # the administrator-only Parent Controls websocket.
                from homeassistant.exceptions import HomeAssistantError
                with self.assertRaises(HomeAssistantError):
                    await hass.services.async_call("time", "set_value", {
                        "entity_id": "time.bedtime_dinner_time", "time": "17:30:00",
                    }, blocking=True)
                self.assertEqual(hass.states.get("time.bedtime_dinner_time").state, "18:00:00")
                await entry.runtime_data.async_parent_control(
                    "schedule", schedule={"dinner_time": "17:30:00"},
                )
                self.assertEqual(hass.states.get("time.bedtime_dinner_time").state, "17:30:00")
                duplicate = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
                self.assertEqual(duplicate["reason"], "already_configured")
                options = await hass.config_entries.options.async_init(entry.entry_id)
                await hass.config_entries.options.async_configure(options["flow_id"], {
                    "kid_1_name": "Robin", "kid_2_name": "Sam", "kid_3_name": "Charlie",
                })
                await hass.async_block_till_done()
                self.assertEqual(hass.states.get("sensor.bedtime_kid_1").attributes["child_name"], "Robin")
                self.assertTrue(await hass.config_entries.async_unload(entry.entry_id))
                self.assertFalse(hass.services.has_service(DOMAIN, "set_task"))
                self.assertFalse(frontend.async_panel_exists(hass, "bedtime-club"))
                self.assertTrue(await hass.config_entries.async_setup(entry.entry_id))
                self.assertEqual(hass.states.get("sensor.bedtime_kid_1").state, "1")
            finally:
                await hass.async_stop()
