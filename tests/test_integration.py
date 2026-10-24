"""Native ledger tests using Home Assistant's real storage and config entries."""

import asyncio
from io import BytesIO
from copy import deepcopy
from datetime import datetime, time, timedelta
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import MappingProxyType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from aiohttp import web
from PIL import Image
from homeassistant.components import frontend
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import ConfigEntryError, HomeAssistantError, ServiceValidationError
from homeassistant.helpers import restore_state
from homeassistant.util import dt as dt_util

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.bedtime_sticker_club import (
    async_handle_parent_action,
    register_dashboard,
    require_parent_admin,
)
from custom_components.bedtime_sticker_club.avatar import ChildAvatarView
from custom_components.bedtime_sticker_club.const import DOMAIN, ROUTINES, TASKS
from custom_components.bedtime_sticker_club.coordinator import BedtimeCoordinator, routine_date

ZONE = ZoneInfo("America/New_York")


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = TemporaryDirectory()
        self.hass = HomeAssistant(self.directory.name)
        self.hass.config.time_zone = "America/New_York"
        dt_util.set_default_time_zone(ZONE)
        self.now = datetime(2026, 10, 15, 19, tzinfo=ZONE)
        self.clock = patch.object(dt_util, "now", side_effect=lambda: self.now)
        self.clock.start()
        self.entry = ConfigEntry(
            domain=DOMAIN, title="Bedtime Sticker Club", version=1, minor_version=1,
            source="user", unique_id=DOMAIN, data={"kid_1_name": "Alex"}, options={},
            discovery_keys=MappingProxyType({}), subentries_data=None,
        )
        self.coordinator = BedtimeCoordinator(self.hass, self.entry)
        await self.coordinator.async_initialize()

    async def asyncTearDown(self):
        self.clock.stop()
        await self.coordinator.async_shutdown()
        await self.hass.async_stop()
        self.directory.cleanup()

    async def task(self, task, completed=True, child="kid_1", day=None, routine="bedtime"):
        await self.coordinator.async_command(
            "task", child, day or routine_date(), task=task, completed=completed, routine=routine,
        )

    async def finish(self, child="kid_1"):
        for task in TASKS:
            await self.task(task, child=child)

    async def finish_routine(self, routine, child="kid_1"):
        for task in self.coordinator.tasks_for(child, routine):
            await self.task(task["id"], child=child, routine=routine)

    def child(self, child="kid_1"):
        return self.coordinator.data["children"][child]

    async def test_parent_api_requires_home_assistant_administrator(self):
        admin_connection = SimpleNamespace(user=SimpleNamespace(is_admin=True))
        child_connection = SimpleNamespace(user=SimpleNamespace(is_admin=False))
        require_parent_admin(admin_connection)
        with self.assertRaises(HomeAssistantError):
            require_parent_admin(child_connection)
        self.hass.data.setdefault(DOMAIN, {})[self.entry.entry_id] = self.coordinator
        request = {"action": "profile_create", "data": {"name": "Taylor"}}
        with self.assertRaises(HomeAssistantError):
            await async_handle_parent_action(
                self.hass, child_connection, self.entry.entry_id,
                request["action"], request["data"],
            )
        profile_id = await async_handle_parent_action(
            self.hass, admin_connection, self.entry.entry_id,
            request["action"], request["data"],
        )
        self.assertEqual(self.coordinator.data["profiles"][profile_id]["name"], "Taylor")

    async def test_independent_progress_and_duplicate_awards(self):
        await self.finish()
        await asyncio.gather(*(self.task("outfit") for _ in range(10)))
        self.assertEqual(self.child()["total"], 1)
        self.assertEqual(self.child("kid_2")["total"], 0)
        self.assertEqual(self.coordinator.child_attributes("kid_1")["child_name"], "Alex")

    async def test_sticker_undo_and_recompletion(self):
        await self.finish()
        await self.coordinator.async_command("sticker", "kid_1", routine_date(), sticker="🚀")
        await self.task("teeth", False)
        self.assertEqual(self.child()["total"], 0)
        await self.task("teeth")
        self.assertEqual(self.child()["total"], 1)
        self.assertEqual(self.child()["stickers"][routine_date()], {"emoji": "🚀", "earned": True})

    async def test_rejects_stale_invalid_and_incomplete_requests(self):
        invalid = [
            ("task", "kid_1", "2026-10-14", {"task": "plate", "completed": True}),
            ("task", "kid_4", routine_date(), {"task": "plate", "completed": True}),
            ("task", "kid_1", routine_date(), {"task": "bad", "completed": True}),
            ("task", "kid_1", routine_date(), {"task": "plate", "completed": "false"}),
            ("sticker", "kid_1", routine_date(), {"sticker": "🚀"}),
        ]
        before = deepcopy(self.coordinator.data)
        for operation, child, day, values in invalid:
            with self.assertRaises(ServiceValidationError):
                await self.coordinator.async_command(operation, child, day, **values)
        self.assertEqual(self.coordinator.data, before)
        await self.finish()
        with self.assertRaises(ServiceValidationError):
            await self.coordinator.async_command("sticker", "kid_1", routine_date(), sticker="<script>")

    async def test_midnight_four_am_and_missed_days(self):
        await self.finish()
        self.now = datetime(2026, 10, 16, 0, 30, tzinfo=ZONE)
        await self.coordinator.async_tick()
        self.assertEqual(self.coordinator.child_attributes("kid_1")["completed"], 3)
        self.now = datetime(2026, 10, 16, 4, tzinfo=ZONE)
        await self.coordinator.async_tick()
        self.assertEqual(self.coordinator.child_attributes("kid_1")["completed"], 0)
        self.assertEqual(self.child()["total"], 1)
        self.now = datetime(2026, 10, 20, 19, tzinfo=ZONE)
        await self.finish()
        self.assertEqual(self.child()["total"], 2)

    async def test_morning_and_bedtime_rewards_are_separate(self):
        self.assertEqual(tuple(ROUTINES), ("bedtime", "morning"))
        self.now = datetime(2026, 10, 17, 7, tzinfo=ZONE)
        self.assertEqual(self.coordinator.active_routine, "morning")
        self.assertEqual(
            [task["label"] for task in self.coordinator.tasks_for("kid_1", "morning")],
            ["Get dressed", "Eat breakfast", "Brush teeth", "Pack the school bag"],
        )
        await self.finish_routine("morning")
        self.assertEqual(self.child()["morning_total"], 1)
        self.assertEqual(self.child()["total"], 0)
        await self.coordinator.async_command(
            "sticker", "kid_1", routine_date(), routine="morning", sticker="🌈",
        )
        self.assertEqual(self.child()["morning_stickers"][routine_date()]["emoji"], "🌈")
        self.assertEqual(self.child()["stickers"], {})
        await self.finish()
        self.assertEqual(self.child()["total"], 1)
        self.assertEqual(self.child()["morning_total"], 1)

    async def test_parent_can_correct_a_morning_reward_without_changing_bedtime(self):
        await self.coordinator.async_parent_control(
            "set_reward", child_id="kid_1", routine="morning",
            routine_date=routine_date(), earned=True, sticker="🌈",
        )
        self.assertEqual(self.child()["morning_total"], 1)
        self.assertEqual(self.child()["total"], 0)
        await self.coordinator.async_parent_control(
            "correct_task", child_id="kid_1", routine="morning",
            routine_date=routine_date(), task="get_dressed", completed=True,
        )
        self.assertEqual(self.child()["morning_total"], 0)
        self.assertEqual(self.child()["total"], 0)

    async def test_auto_switch_is_configurable_and_manual_actions_stay_daily(self):
        self.now = datetime(2026, 10, 15, 11, 59, tzinfo=ZONE)
        self.assertEqual(self.coordinator.active_routine, "morning")
        old_day = routine_date()
        self.now = self.now.replace(hour=12)
        self.assertEqual(self.coordinator.active_routine, "bedtime")
        self.assertEqual(routine_date(), old_day)
        await self.coordinator.async_parent_control(
            "schedule", schedule={"routine_switch_time": "08:00:00"},
        )
        self.assertEqual(self.coordinator.active_routine, "bedtime")

    async def test_month_year_and_dst_boundaries(self):
        await self.finish()
        self.now = datetime(2026, 11, 1, 3, 59, tzinfo=ZONE)
        self.assertEqual(routine_date(), "2026-10-31")
        self.now = self.now.replace(hour=4)
        await self.coordinator.async_tick()
        self.assertEqual(self.child()["stickers"], {})
        self.assertEqual(self.child()["total"], 1)
        self.now = datetime(2027, 1, 1, 4, tzinfo=ZONE)
        await self.coordinator.async_tick()
        self.assertEqual(self.child()["month"], "2027-01")
        for month, day, expected in ((3, 8, "2026-03-07"), (11, 1, "2026-10-31")):
            for fold in (0, 1):
                self.now = datetime(2026, month, day, 1, fold=fold, tzinfo=ZONE)
                self.assertEqual(routine_date(), expected)

    async def test_schedule_and_invalid_order(self):
        self.assertEqual(self.coordinator.phase, "bedtime")
        self.now = self.now.replace(hour=18)
        self.assertEqual(self.coordinator.phase, "dinner")
        await self.coordinator.async_set_time("dinner_time", time(20))
        self.assertEqual(self.coordinator.phase, "invalid_schedule")
        await self.finish()
        self.assertEqual(self.child()["total"], 1)

    async def test_progress_and_schedule_survive_storage_reload(self):
        await self.finish()
        await self.coordinator.async_command("sticker", "kid_1", routine_date(), sticker="🚀")
        await self.coordinator.async_set_time("bedtime_time", time(20, 15))
        loaded = BedtimeCoordinator(self.hass, self.entry)
        await loaded.async_initialize()
        self.assertEqual(loaded.data, self.coordinator.data)
        await loaded.async_shutdown()

    async def test_failed_save_does_not_publish_or_commit_progress(self):
        before = deepcopy(self.coordinator.data)
        with patch.object(self.coordinator.store, "async_save", new=AsyncMock(side_effect=OSError("disk full"))):
            with self.assertRaises(OSError):
                await self.task("plate")
        self.assertEqual(self.coordinator.data, before)

    async def test_imports_legacy_stickers_totals_dates_and_schedule_once(self):
        await self.coordinator.store.async_remove()
        restore = restore_state.async_get(self.hass)
        old = State("sensor.bedtime_kid_1", "42", {
            "month": "2026-10", "routine_date": routine_date(),
            "tasks": dict.fromkeys(TASKS, True),
            "stickers": {routine_date(): {"emoji": "🚀", "earned": True}},
        })
        restore.last_states[old.entity_id] = SimpleNamespace(state=old)
        dinner = State("input_datetime.bedtime_dinner_time", "17:30:00")
        restore.last_states[dinner.entity_id] = SimpleNamespace(state=dinner)
        await self.coordinator.async_initialize()
        self.assertEqual(self.child()["total"], 42)
        self.assertEqual(self.coordinator.child_attributes("kid_1")["completed"], 3)
        self.assertEqual(self.coordinator.data["dinner_time"], "17:30:00")
        await self.task("teeth", False)
        await self.coordinator.async_initialize()
        self.assertEqual(self.child()["total"], 41)
        # Do not leave fake restore objects for HA shutdown to serialize.
        restore.last_states.clear()

    async def test_schema_one_data_migrates_without_changing_bedtime_totals(self):
        legacy = {
            "schema_version": 1,
            "dinner_time": "17:45:00",
            "bedtime_time": "20:00:00",
            "children": {
                "kid_1": {
                    "total": 12, "month": "2026-10",
                    "stickers": {"2026-10-15": {"emoji": "🚀", "earned": True}},
                    "task_dates": {"plate": "2026-10-15"},
                },
            },
        }
        upgraded = self.coordinator._upgrade(legacy)
        self.assertEqual(upgraded["schema_version"], 3)
        self.assertEqual(upgraded["children"]["kid_1"]["total"], 12)
        self.assertEqual(upgraded["children"]["kid_1"]["stickers"]["2026-10-15"]["emoji"], "🚀")
        self.assertEqual(upgraded["profiles"]["kid_1"]["name"], "Alex")
        self.assertEqual(upgraded["children"]["kid_1"]["morning_total"], 0)
        self.assertEqual(upgraded["default_morning_tasks"], self.coordinator.data["default_morning_tasks"])

    async def test_registers_dashboard_and_preserves_existing_copy(self):
        self.hass.data[LOVELACE_DATA] = SimpleNamespace(dashboards={})
        dashboard = register_dashboard(self.hass)
        data = await dashboard.async_load(False)
        self.assertEqual([v["path"] for v in data["views"]], ["tonight", "parents"])
        self.assertIsNone(register_dashboard(self.hass))
        self.assertIs(self.hass.data[LOVELACE_DATA].dashboards["bedtime-club"], dashboard)

    async def test_creates_archives_orders_and_restores_children(self):
        await self.coordinator.async_parent_control("profile_create", name="Robin")
        profile_id = self.coordinator.profile_ids()[-1]
        self.assertTrue(profile_id.startswith("child_"))
        self.assertEqual(self.coordinator.child_attributes(profile_id)["child_name"], "Robin")
        await self.coordinator.async_parent_control("profile_move", child_id=profile_id, position=0)
        self.assertEqual(self.coordinator.profile_ids()[0], profile_id)
        await self.coordinator.async_parent_control("profile_archive", child_id=profile_id)
        self.assertNotIn(profile_id, self.coordinator.profile_ids(active=True))
        with self.assertRaises(ServiceValidationError):
            await self.task("plate", child=profile_id)
        await self.coordinator.async_parent_control("profile_restore", child_id=profile_id)
        self.assertIn(profile_id, self.coordinator.profile_ids(active=True))

    async def test_task_defaults_preserve_custom_lists_and_can_be_reset(self):
        custom = [
            {"id": "read", "label": "Read together", "icon": "📚"},
            {"id": "pack", "label": "Pack a bag", "icon": "🎒"},
        ]
        await self.coordinator.async_parent_control(
            "child_tasks", child_id="kid_1", tasks=custom, effective_day="today",
        )
        new_default = deepcopy(self.coordinator.data["default_tasks"])
        new_default.append({"id": "shoes", "label": "Find shoes", "icon": "👟"})
        await self.coordinator.async_parent_control(
            "default_tasks", child_id="", tasks=new_default, effective_day="today",
        )
        self.assertEqual(self.coordinator.tasks_for("kid_1"), custom)
        self.assertEqual(self.coordinator.tasks_for("kid_2"), new_default)
        await self.coordinator.async_parent_control(
            "child_tasks", child_id="kid_1", tasks=None, effective_day="tomorrow",
        )
        self.assertEqual(self.coordinator.tasks_for("kid_1"), custom)
        self.now += timedelta(days=1)
        await self.coordinator.async_tick()
        self.assertEqual(self.coordinator.tasks_for("kid_1"), new_default)

    async def test_parent_overrides_hold_until_a_real_task_change(self):
        day = routine_date()
        await self.coordinator.async_parent_control(
            "set_reward", child_id="kid_1", routine_date=day, earned=True, sticker="🚀",
        )
        self.assertEqual(self.child()["total"], 1)
        await self.task("plate", completed=False)
        self.assertEqual(self.child()["total"], 1)
        await self.task("plate", completed=True)
        self.assertEqual(self.child()["total"], 0)
        await self.task("teeth")
        await self.task("outfit")
        self.assertEqual(self.child()["total"], 1)

    async def test_admin_corrections_reject_future_and_previous_month(self):
        with self.assertRaises(ServiceValidationError):
            await self.coordinator.async_parent_control(
                "set_reward", child_id="kid_1", routine_date="2026-11-01",
                earned=True, sticker="⭐",
            )
        with self.assertRaises(ServiceValidationError):
            await self.coordinator.async_parent_control(
                "set_reward", child_id="kid_1", routine_date="2026-09-30",
                earned=True, sticker="⭐",
            )
        self.assertEqual(self.child()["total"], 0)

    async def test_authenticated_avatar_upload_is_normalized_and_persisted(self):
        self.hass.data.setdefault(DOMAIN, {})[self.entry.entry_id] = self.coordinator
        payload = BytesIO()
        Image.new("RGB", (256, 128), "orange").save(payload, format="PNG")
        request = SimpleNamespace(
            app={"hass": self.hass},
            content_type="image/png",
            content_length=len(payload.getvalue()),
            content=SimpleNamespace(read=AsyncMock(return_value=payload.getvalue())),
        )
        view = ChildAvatarView()
        response = await view.post(request, "kid_1")
        image_name = json.loads(response.body)["avatar_image"]
        self.assertTrue(ChildAvatarView.requires_auth)
        self.assertTrue(image_name.startswith("kid_1-"))
        stored_path = Path(self.hass.config.path(DOMAIN, "avatars", image_name))
        with Image.open(stored_path) as image:
            self.assertEqual((image.format, image.size), ("WEBP", (512, 512)))
        self.assertEqual(self.coordinator.data["profiles"]["kid_1"]["avatar_image"], image_name)

        bad_request = SimpleNamespace(
            app={"hass": self.hass},
            content_type="image/png",
            content_length=len(b"not an image"),
            content=SimpleNamespace(read=AsyncMock(return_value=b"not an image")),
        )
        with self.assertRaises(web.HTTPBadRequest) as raised:
            await view.post(bad_request, "kid_1")
        self.assertEqual(getattr(raised.exception, "status", None), 400)
        self.assertTrue(stored_path.is_file())

    async def test_refuses_to_overwrite_unrelated_panel(self):
        self.hass.data[LOVELACE_DATA] = SimpleNamespace(dashboards={})
        frontend.async_register_built_in_panel(self.hass, "map", frontend_url_path="bedtime-club")
        with self.assertRaises(ConfigEntryError):
            register_dashboard(self.hass)


if __name__ == "__main__":
    unittest.main()
