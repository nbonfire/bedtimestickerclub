"""Exercise the shipped YAML using Home Assistant's real template engine.

Run in the pinned HA image; see README.md. No live HA instance is modified.
"""

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

import yaml
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, template
from homeassistant.util import dt as dt_util

PACKAGE = yaml.safe_load(
    (Path(__file__).resolve().parents[1] / "packages/bedtime.yaml").read_text()
)
ZONE = ZoneInfo("America/New_York")


class RewardTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = TemporaryDirectory()
        self.hass = HomeAssistant(self.directory.name)
        self.hass.config.time_zone = "America/New_York"
        dt_util.set_default_time_zone(ZONE)
        self.now = datetime(2026, 10, 15, 19, 0, tzinfo=ZONE)
        self.hass.states.async_set("input_boolean.bedtime_initialized", "on")
        self.hass.states.async_set("input_datetime.bedtime_dinner_time", "18:00:00")
        self.hass.states.async_set("input_datetime.bedtime_bedtime_time", "19:00:00")
        for kid in (1, 2, 3):
            for task in ("plate", "teeth", "outfit"):
                self.set_task(task, "1970-01-01", kid)

    async def asyncTearDown(self):
        await self.hass.async_stop()
        self.directory.cleanup()

    def set_task(self, task, date="2026-10-15", kid=1):
        self.hass.states.async_set(f"input_datetime.bedtime_kid_{kid}_{task}", date)

    def render(self, kid=1, event=None):
        group = PACKAGE["template"][kid]
        variables = cv.SCRIPT_VARIABLES_SCHEMA(group["variables"])
        trigger = {"platform": "state"}
        if event is not None:
            trigger = {"platform": "event", "event": SimpleNamespace(data=event)}
        with patch.object(dt_util, "now", return_value=self.now):
            values = variables.async_render(self.hass, {"trigger": trigger})
            permitted = template.Template(
                group["conditions"][0]["value_template"], self.hass
            ).async_render(values)
            entity = f"sensor.bedtime_kid_{kid}"
            if permitted:
                sensor = group["sensor"][0]
                attrs = {
                    key: template.Template(value, self.hass).async_render(values)
                    for key, value in sensor["attributes"].items()
                }
                total = template.Template(sensor["state"], self.hass).async_render(values)
                self.hass.states.async_set(entity, total, attrs)
            return self.hass.states.get(entity)

    def finish(self, kid=1, date="2026-10-15"):
        for task in ("plate", "teeth", "outfit"):
            self.set_task(task, date, kid)
            state = self.render(kid)
        return state

    def choose(self, sticker="🚀", **overrides):
        event = dict(child_id="kid_1", routine_date="2026-10-15", sticker=sticker)
        event.update(overrides)
        return self.render(event=event)

    def test_first_day_and_independent_children(self):
        self.assertEqual(self.render().state, "0")
        self.set_task("plate")
        state = self.render()
        self.assertEqual(state.attributes["completed"], 1)
        self.assertEqual(state.state, "0")
        self.assertEqual(self.finish().state, "1")
        self.assertEqual(self.render(2).attributes["completed"], 0)
        self.assertEqual(self.render(3).state, "0")
        self.assertEqual(self.finish(2).state, "1")

    def test_duplicate_events_and_emoji_changes_do_not_add_credit(self):
        self.finish()
        for _ in range(5):
            self.assertEqual(self.render().state, "1")
            self.assertEqual(self.choose().state, "1")
        state = self.choose("🦖")
        self.assertEqual(state.attributes["stickers"]["2026-10-15"], {"emoji": "🦖", "earned": True})

    def test_undo_withdraws_credit_and_recompletion_remembers_emoji(self):
        self.finish()
        self.choose()
        self.set_task("teeth", "1970-01-01")
        state = self.render()
        self.assertEqual(state.state, "0")
        self.assertEqual(state.attributes["stickers"]["2026-10-15"], {"emoji": "🚀", "earned": False})
        self.set_task("teeth")
        state = self.render()
        self.assertEqual(state.state, "1")
        self.assertEqual(state.attributes["stickers"]["2026-10-15"]["emoji"], "🚀")

    def test_picker_rejects_incomplete_stale_invalid_and_other_child_events(self):
        self.render()
        self.assertEqual(self.choose().attributes["stickers"], {})
        self.finish()
        for event in ({"routine_date": "2026-10-14"}, {"child_id": "kid_2"}, {"sticker": "<script>"}):
            self.assertEqual(self.choose(**event).attributes["stickers"]["2026-10-15"]["emoji"], "⭐")

    def test_midnight_keeps_evening_and_four_am_resets_without_losing_credit(self):
        self.finish()
        self.choose()
        self.now = datetime(2026, 10, 16, 0, 30, tzinfo=ZONE)
        self.assertEqual(self.render().attributes["completed"], 3)
        self.assertEqual(self.render().attributes["routine_date"], "2026-10-15")
        self.now = datetime(2026, 10, 16, 4, 0, tzinfo=ZONE)
        state = self.render()
        self.assertEqual(state.attributes["completed"], 0)
        self.assertEqual(state.state, "1")
        self.assertEqual(state.attributes["stickers"]["2026-10-15"]["emoji"], "🚀")

    def test_downtime_skips_days_without_carrying_checks(self):
        self.finish()
        self.now = datetime(2026, 10, 20, 19, 0, tzinfo=ZONE)
        state = self.render()
        self.assertEqual(state.state, "1")
        self.assertEqual(state.attributes["completed"], 0)
        self.assertEqual(self.finish(date="2026-10-20").state, "2")

    def test_month_and_year_rollover_preserve_lifetime_total(self):
        self.finish()
        self.now = datetime(2026, 11, 1, 3, 59, tzinfo=ZONE)
        self.assertEqual(self.render().attributes["month"], "2026-10")
        self.now = datetime(2026, 11, 1, 4, 0, tzinfo=ZONE)
        state = self.render()
        self.assertEqual(state.attributes["stickers"], {})
        self.assertEqual(state.state, "1")
        self.assertEqual(self.finish(date="2026-11-01").state, "2")
        self.now = datetime(2027, 1, 1, 4, 0, tzinfo=ZONE)
        self.assertEqual(self.render().attributes["month"], "2027-01")
        self.assertEqual(self.render().state, "2")

    def test_dst_uses_wall_clock_boundary(self):
        for month, day in ((3, 8), (11, 1)):
            for hour in (1, 3, 4):
                for fold in (0, 1):
                    self.now = datetime(2026, month, day, hour, 0, tzinfo=ZONE, fold=fold)
                    state = self.render()
                    expected = self.now.date()
                    if hour < 4:
                        from datetime import timedelta
                        expected -= timedelta(days=1)
                    self.assertEqual(state.attributes["routine_date"], expected.isoformat())

    def test_unavailable_helper_does_not_withdraw_reward(self):
        self.finish()
        self.choose()
        self.set_task("teeth", "unavailable")
        state = self.render()
        self.assertEqual(state.state, "1")
        self.assertTrue(state.attributes["stickers"]["2026-10-15"]["earned"])
        self.set_task("teeth")
        self.assertEqual(self.render().state, "1")

    def test_uninitialized_helpers_cannot_award_false_stickers(self):
        self.hass.states.async_set("input_boolean.bedtime_initialized", "off")
        for task in ("plate", "teeth", "outfit"):
            self.set_task(task)
        self.assertIsNone(self.render())

    def test_phase_highlights_and_invalid_schedule(self):
        source = PACKAGE["template"][0]["sensor"][0]["state"]
        for hour, expected in ((3, "bedtime"), (4, "daytime"), (17, "daytime"), (18, "dinner"), (19, "bedtime")):
            with patch.object(dt_util, "now", return_value=self.now.replace(hour=hour)):
                self.assertEqual(template.Template(source, self.hass).async_render(), expected)
        self.hass.states.async_set("input_datetime.bedtime_dinner_time", "20:00:00")
        self.assertEqual(template.Template(source, self.hass).async_render(), "invalid_schedule")


if __name__ == "__main__":
    unittest.main()
