"""Local reward ledger with serialized, durable updates."""

import asyncio
from copy import deepcopy
from datetime import timedelta
import logging

from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import restore_state
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CHILDREN, DEFAULT_BEDTIME, DEFAULT_DINNER, DOMAIN, STORAGE_KEY, STICKERS, TASKS,
)

_LOGGER = logging.getLogger(__name__)


def routine_date():
    """Use Home Assistant's local calendar date, with a 4 am boundary."""
    now = dt_util.now()
    return (now.date() - timedelta(days=now.hour < 4)).isoformat()


def empty_data():
    return {
        "dinner_time": DEFAULT_DINNER,
        "bedtime_time": DEFAULT_BEDTIME,
        "children": {
            child: {"total": 0, "month": "", "stickers": {}, "task_dates": {}}
            for child in CHILDREN
        },
    }


def reconcile(data, day):
    """Apply earned/withdrawn credit once and retain the selected emoji."""
    for child in data["children"].values():
        if child["month"] != day[:7]:
            child["month"] = day[:7]
            child["stickers"] = {}
        previous = child["stickers"].get(day, {})
        earned = all(child["task_dates"].get(task) == day for task in TASKS)
        child["total"] = max(0, child["total"] + int(earned) - int(previous.get("earned", False)))
        if earned or previous:
            child["stickers"][day] = {
                "emoji": previous.get("emoji", "⭐"), "earned": earned,
            }


class BedtimeCoordinator(DataUpdateCoordinator):
    """Store confirmed actions before publishing their new state to the UI."""

    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry)
        self.entry = entry
        self.store = Store(hass, 1, STORAGE_KEY)
        self.lock = asyncio.Lock()

    async def async_initialize(self):
        data = await self.store.async_load()
        if data is None:
            data = self._import_legacy()
        reconcile(data, routine_date())
        # Persist migration before removing any obsolete registry entries.
        await self.store.async_save(data)
        self.async_set_updated_data(data)

    def _import_legacy(self):
        """Import restored YAML entities once; leave HA's old storage intact."""
        saved = restore_state.async_get(self.hass).last_states

        def state(entity_id):
            stored = saved.get(entity_id)
            current = self.hass.states.get(entity_id)
            if current and not current.attributes.get("restored") and current.state not in ("unknown", "unavailable"):
                return current
            return stored.state if stored else current

        data = empty_data()
        for child_id, child in data["children"].items():
            old = state(f"sensor.bedtime_{child_id}")
            if old is None:
                continue
            try:
                child["total"] = max(0, int(old.state))
            except ValueError as err:
                raise ServiceValidationError(
                    f"Cannot import unavailable progress for {child_id}; restore a Home Assistant backup first."
                ) from err
            attrs = old.attributes
            child["month"] = attrs.get("month", "")
            child["stickers"] = deepcopy(dict(attrs.get("stickers", {})))
            for task in TASKS:
                helper = state(f"input_datetime.bedtime_{child_id}_{task}")
                if helper and helper.state not in ("unknown", "unavailable"):
                    child["task_dates"][task] = helper.state
                elif attrs.get("tasks", {}).get(task):
                    child["task_dates"][task] = attrs.get("routine_date", "")
        for name in ("dinner_time", "bedtime_time"):
            old = state(f"input_datetime.bedtime_{name}")
            if old and dt_util.parse_time(old.state) is not None:
                data[name] = old.state
        return data

    @property
    def phase(self):
        clock = dt_util.now().strftime("%H:%M:%S")
        dinner, bedtime = self.data["dinner_time"], self.data["bedtime_time"]
        if not "04:00:00" <= dinner < bedtime <= "23:59:59":
            return "invalid_schedule"
        if clock < "04:00:00" or clock >= bedtime:
            return "bedtime"
        return "dinner" if clock >= dinner else "daytime"

    def child_attributes(self, child_id):
        child = self.data["children"][child_id]
        day = routine_date()
        tasks = {task: child["task_dates"].get(task) == day for task in TASKS}
        names = self.entry.options or self.entry.data
        return {
            "routine_date": day,
            "month": day[:7],
            "tasks": tasks,
            "completed": sum(tasks.values()),
            "stickers": child["stickers"] if child["month"] == day[:7] else {},
            "child_name": names.get(f"{child_id}_name", child_id.replace("_", " ").title()),
        }

    async def _commit(self, data):
        await self.store.async_save(data)
        self.async_set_updated_data(data)

    async def async_tick(self, _now=None):
        async with self.lock:
            data = deepcopy(self.data)
            reconcile(data, routine_date())
            if data != self.data:
                await self._commit(data)
            else:
                # Phase and routine-date attributes can change without storage changes.
                self.async_update_listeners()

    async def async_command(self, operation, child_id, day, **values):
        async with self.lock:
            if child_id not in CHILDREN or day != routine_date():
                raise ServiceValidationError("This action belongs to an invalid child or an old routine day. Refresh the dashboard.")
            data = deepcopy(self.data)
            reconcile(data, day)
            child = data["children"][child_id]
            if operation == "task":
                task, completed = values.get("task"), values.get("completed")
                if task not in TASKS or type(completed) is not bool:
                    raise ServiceValidationError("Invalid task or completion value.")
                child["task_dates"][task] = day if completed else "1970-01-01"
                reconcile(data, day)
            elif operation == "sticker":
                sticker = values.get("sticker")
                record = child["stickers"].get(day, {})
                if sticker not in STICKERS or not record.get("earned"):
                    raise ServiceValidationError("Finish all three tasks and choose a supported sticker.")
                record["emoji"] = sticker
            else:
                raise ServiceValidationError("Invalid operation.")
            await self._commit(data)

    async def async_set_time(self, name, value):
        async with self.lock:
            data = deepcopy(self.data)
            data[name] = value.strftime("%H:%M:%S")
            await self._commit(data)
