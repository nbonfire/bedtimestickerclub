"""Local reward ledger with serialized, durable updates."""

import asyncio
from copy import deepcopy
from datetime import timedelta
import logging
import re
from uuid import uuid4

from homeassistant.exceptions import ServiceValidationError, Unauthorized
from homeassistant.helpers import restore_state
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CHILDREN, DEFAULT_BEDTIME, DEFAULT_DINNER, DEFAULT_MORNING_TASKS,
    DEFAULT_SWITCH_TIME, DEFAULT_TASKS, DOMAIN, PROFILE_COLORS, ROUTINES,
    STORAGE_KEY, STICKERS, TASKS,
)

_LOGGER = logging.getLogger(__name__)


def routine_date():
    """Use Home Assistant's local calendar date, with a 4 am boundary."""
    now = dt_util.now()
    return (now.date() - timedelta(days=now.hour < 4)).isoformat()


def task_defaults_key(routine):
    """Return the persisted shared-task key, retaining the legacy bedtime key."""
    return "default_tasks" if routine == "bedtime" else "default_morning_tasks"


def empty_data():
    return {
        "schema_version": 3,
        "dinner_time": DEFAULT_DINNER,
        "bedtime_time": DEFAULT_BEDTIME,
        "routine_switch_time": DEFAULT_SWITCH_TIME,
        "default_tasks": deepcopy(DEFAULT_TASKS),
        "default_morning_tasks": deepcopy(DEFAULT_MORNING_TASKS),
        "profiles": {},
        "children": {
            child: {
                "total": 0, "morning_total": 0, "month": "", "stickers": {},
                "morning_stickers": {}, "task_dates": {}, "morning_task_dates": {},
                "days": {}, "task_overrides": {"bedtime": None, "morning": None},
            }
            for child in CHILDREN
        },
    }


def reconcile(data, day):
    """Reconcile today's snapshot and retain only current-month details."""
    for child_id, child in data["children"].items():
        if child["month"] != day[:7]:
            child["month"] = day[:7]
        child["days"] = {
            saved_day: record
            for saved_day, record in child["days"].items()
            if saved_day[:7] == day[:7]
        }
        child["stickers"] = {
            saved_day: sticker
            for saved_day, sticker in child["stickers"].items()
            if saved_day[:7] == day[:7]
        }
        child["morning_stickers"] = {
            saved_day: sticker
            for saved_day, sticker in child["morning_stickers"].items()
            if saved_day[:7] == day[:7]
        }
        profile = data["profiles"][child_id]
        daily = child["days"].setdefault(day, {"tasks": {}, "rewards": {}})
        daily.setdefault("tasks", {})
        daily.setdefault("rewards", {})
        for routine in ROUTINES:
            required_key = "required_tasks" if routine == "bedtime" else "morning_required_tasks"
            dates_key = "task_dates" if routine == "bedtime" else "morning_task_dates"
            stickers_key = "stickers" if routine == "bedtime" else "morning_stickers"
            required = daily.setdefault(
                required_key,
                profile.get("task_overrides", {}).get(routine)
                or data[task_defaults_key(routine)],
            )
            task_state = daily["tasks"].setdefault(routine, {
                task["id"]: child[dates_key].get(task["id"]) == day
                for task in required
            })
            legacy = child[stickers_key].get(day)
            reward = daily["rewards"].setdefault(routine, {
                **(deepcopy(legacy) if legacy else {"emoji": "⭐", "earned": False}),
                "override": None,
            })
            earned = (
                bool(reward["override"])
                if reward.get("override") is not None
                else bool(required) and all(task_state.get(task["id"], False) for task in required)
            )
            was_earned = bool(reward.get("earned"))
            reward["earned"] = earned
            total_key = "total" if routine == "bedtime" else "morning_total"
            child[total_key] = max(0, child[total_key] + int(earned) - int(was_earned))
            if earned or legacy or reward.get("override") is not None:
                reward["emoji"] = reward.get("emoji", "⭐")
                child[stickers_key][day] = {"emoji": reward["emoji"], "earned": earned}


def install_task_snapshot(data, child_id, day, task_list, routine="bedtime"):
    """Apply an effective task list to one dated routine snapshot."""
    child = data["children"][child_id]
    daily = child["days"].setdefault(day, {"tasks": {}, "rewards": {}})
    daily.setdefault("tasks", {})
    daily.setdefault("rewards", {})
    required_key = "required_tasks" if routine == "bedtime" else "morning_required_tasks"
    dates_key = "task_dates" if routine == "bedtime" else "morning_task_dates"
    stickers_key = "stickers" if routine == "bedtime" else "morning_stickers"
    previous = daily.get(required_key, data[task_defaults_key(routine)])
    state = daily["tasks"].setdefault(routine, {
        task["id"]: child[dates_key].get(task["id"]) == day
        for task in previous
    })
    daily["tasks"][routine] = {
        task["id"]: state.get(task["id"], False) for task in task_list
    }
    changed = task_list != previous
    daily[required_key] = deepcopy(task_list)
    legacy = child[stickers_key].get(day)
    reward = daily["rewards"].setdefault(routine, {
        **(deepcopy(legacy) if legacy else {"emoji": "⭐", "earned": False}),
        "override": None,
    })
    if changed:
        reward["override"] = None
    BedtimeCoordinator._recalculate(data, child, day, routine, reward)
    if day == routine_date():
        ids = {task["id"] for task in task_list}
        for task_id in set(child[dates_key]) - ids:
            child[dates_key].pop(task_id, None)
        for task_id, done in daily["tasks"][routine].items():
            if not done:
                child[dates_key][task_id] = "1970-01-01"
            else:
                child[dates_key][task_id] = day


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
        data = self._upgrade(data)
        reconcile(data, routine_date())
        # Persist migration before removing any obsolete registry entries.
        await self.store.async_save(data)
        self.async_set_updated_data(data)

    def _upgrade(self, data):
        """Apply idempotent ledger migrations and fill profile defaults."""
        if data.get("schema_version", 1) > 3:
            raise ServiceValidationError("The saved sticker data was created by a newer integration version.")
        data.setdefault("schema_version", 3)
        data.setdefault("dinner_time", DEFAULT_DINNER)
        data.setdefault("bedtime_time", DEFAULT_BEDTIME)
        data.setdefault("routine_switch_time", DEFAULT_SWITCH_TIME)
        data.setdefault("default_tasks", deepcopy(DEFAULT_TASKS))
        data.setdefault("default_morning_tasks", deepcopy(DEFAULT_MORNING_TASKS))
        data.setdefault("scheduled_tasks", {})
        data.setdefault("profiles", {})
        names = self.entry.options or self.entry.data
        for index, child_id in enumerate(CHILDREN, 1):
            data["profiles"].setdefault(child_id, self._new_profile(
                child_id, names.get(f"{child_id}_name", f"Kid {index}"), index - 1,
            ))
        data.setdefault("children", {})
        for child_id in data["profiles"]:
            data["children"].setdefault(child_id, {
                "total": 0, "morning_total": 0, "month": "", "stickers": {},
                "task_dates": {}, "morning_task_dates": {}, "morning_stickers": {},
                "days": {}, "task_overrides": {"bedtime": None, "morning": None},
            })
        for child_id, child in data["children"].items():
            child.setdefault("total", 0)
            child.setdefault("morning_total", 0)
            child.setdefault("month", "")
            child.setdefault("stickers", {})
            child.setdefault("task_dates", {})
            child.setdefault("morning_task_dates", {})
            child.setdefault("morning_stickers", {})
            child.setdefault("days", {})
            child.setdefault("task_overrides", {"bedtime": None})
            profile = data["profiles"].setdefault(
                child_id,
                self._new_profile(child_id, child_id.replace("_", " ").title(), len(data["profiles"])),
            )
            profile.setdefault("name", child_id.replace("_", " ").title())
            profile.setdefault("avatar", "🙂")
            profile.setdefault("accent", "#7541bf")
            profile.setdefault("tint", "#f0e6ff")
            profile.setdefault("size", "standard")
            profile.setdefault("active", True)
            profile.setdefault("order", len(data["profiles"]) - 1)
            child["task_overrides"].setdefault("bedtime", None)
            child["task_overrides"].setdefault("morning", None)
            for day, sticker in child["stickers"].items():
                record = child["days"].setdefault(day, {"tasks": {}, "rewards": {}})
                record["rewards"].setdefault("bedtime", deepcopy(sticker))
                # An earned legacy sticker proves that all three original tasks
                # were complete; withdrawn records do not prove which was done.
                if sticker.get("earned") and "bedtime" not in record["tasks"]:
                    record["tasks"]["bedtime"] = dict.fromkeys(TASKS, True)
        data["schema_version"] = 3
        return data

    @staticmethod
    def _new_profile(child_id, name, order):
        accent, tint = PROFILE_COLORS.get(child_id, ("#7541bf", "#f0e6ff"))
        avatar = {"kid_1": "🦊", "kid_2": "🦖", "kid_3": "🦄"}.get(child_id, "🙂")
        return {
            "id": child_id, "name": name, "avatar": avatar, "accent": accent,
            "tint": tint, "size": "standard", "active": True, "order": order,
            "task_overrides": {"bedtime": None, "morning": None},
        }

    def profile_ids(self, *, active=None):
        profiles = sorted(self.data["profiles"].values(), key=lambda item: item["order"])
        if active is not None:
            profiles = [profile for profile in profiles if profile["active"] is active]
        return [profile["id"] for profile in profiles]

    def tasks_for(self, child_id, routine="bedtime"):
        today = routine_date()
        daily = self.data["children"][child_id]["days"].get(today, {})
        snapshot = daily.get(
            "required_tasks" if routine == "bedtime" else "morning_required_tasks"
        )
        if snapshot is not None:
            return deepcopy(snapshot)
        profile = self.data["profiles"][child_id]
        override = profile.get("task_overrides", {}).get(routine)
        return deepcopy(override if override is not None else self.data[task_defaults_key(routine)])

    @staticmethod
    def profile_ids_from(profiles):
        return [item["id"] for item in sorted(profiles.values(), key=lambda entry: entry["order"])]

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
        data["schema_version"] = 3
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

    @property
    def active_routine(self):
        clock = dt_util.now().strftime("%H:%M:%S")
        return "morning" if "04:00:00" <= clock < self.data["routine_switch_time"] else "bedtime"

    def child_attributes(self, child_id, routine="bedtime"):
        child = self.data["children"][child_id]
        profile = self.data["profiles"][child_id]
        day = routine_date()
        dates_key = "task_dates" if routine == "bedtime" else "morning_task_dates"
        stickers_key = "stickers" if routine == "bedtime" else "morning_stickers"
        tasks = {
            task["id"]: child[dates_key].get(task["id"]) == day
            for task in self.tasks_for(child_id, routine)
        }
        daily = child["days"].get(day, {})
        return {
            "routine_date": day,
            "month": day[:7],
            "routine": routine,
            "tasks": tasks,
            "task_definitions": self.tasks_for(child_id, routine),
            "completed": sum(tasks.values()),
            "stickers": child[stickers_key] if child["month"] == day[:7] else {},
            "child_name": profile["name"],
            "child_id": child_id,
            "integration_entry_id": self.entry.entry_id,
            "avatar": profile["avatar"],
            "accent": profile["accent"],
            "tint": profile["tint"],
            "card_size": profile["size"],
            "archived": not profile["active"],
            "display_order": profile["order"],
            "earned": daily.get("rewards", {}).get(routine, {}).get("earned", False),
            "lifetime_total": child["total"] if routine == "bedtime" else child["morning_total"],
        }

    async def _commit(self, data):
        await self.store.async_save(data)
        self.async_set_updated_data(data)

    async def async_tick(self, _now=None):
        async with self.lock:
            data = deepcopy(self.data)
            today = routine_date()
            for effective_day in sorted(day for day in data["scheduled_tasks"] if day <= today):
                for update in data["scheduled_tasks"].pop(effective_day):
                    install_task_snapshot(
                        data, update["child_id"], effective_day,
                        update["tasks"], update.get("routine", "bedtime"),
                    )
            reconcile(data, today)
            if data != self.data:
                await self._commit(data)
            else:
                # Phase and routine-date attributes can change without storage changes.
                self.async_update_listeners()

    async def async_command(self, operation, child_id, day, **values):
        async with self.lock:
            if child_id not in self.data["profiles"] or not self.data["profiles"][child_id]["active"] or day != routine_date():
                raise ServiceValidationError("This action belongs to an invalid child or an old routine day. Refresh the dashboard.")
            data = deepcopy(self.data)
            reconcile(data, day)
            child = data["children"][child_id]
            profile = data["profiles"][child_id]
            routine = values.get("routine", "bedtime")
            if routine not in ROUTINES:
                raise ServiceValidationError("Choose the morning or bedtime routine.")
            if operation == "task":
                task, completed = values.get("task"), values.get("completed")
                allowed_tasks = {item["id"] for item in self.tasks_for(child_id, routine)}
                if task not in allowed_tasks or type(completed) is not bool:
                    raise ServiceValidationError("Invalid task or completion value.")
                dates_key = "task_dates" if routine == "bedtime" else "morning_task_dates"
                was_completed = child[dates_key].get(task) == day
                child[dates_key][task] = day if completed else "1970-01-01"
                reconcile(data, day)
                daily = self._day_record(child, day, profile, routine)
                task_state = daily["tasks"].setdefault(routine, {})
                task_state[task] = completed
                reward = daily["rewards"].setdefault(routine, {
                    "emoji": "⭐", "earned": False, "override": None,
                })
                if was_completed != completed:
                    reward["override"] = None
                self._recalculate(data, child, day, routine, reward)
            elif operation == "sticker":
                sticker = values.get("sticker")
                daily = self._day_record(child, day, profile, routine)
                record = daily["rewards"].get(routine, {})
                if sticker not in STICKERS or not record.get("earned"):
                    raise ServiceValidationError("Finish this routine's tasks and choose a supported sticker.")
                record["emoji"] = sticker
                stickers_key = "stickers" if routine == "bedtime" else "morning_stickers"
                child[stickers_key][day] = {"emoji": sticker, "earned": record["earned"]}
            else:
                raise ServiceValidationError("Invalid operation.")
            await self._commit(data)

    @staticmethod
    def _day_record(child, day, profile=None, routine="bedtime"):
        """Return a dated snapshot, seeding known legacy sticker records."""
        record = child["days"].setdefault(day, {"tasks": {}, "rewards": {}})
        record.setdefault("tasks", {})
        record.setdefault("rewards", {})
        stickers_key = "stickers" if routine == "bedtime" else "morning_stickers"
        dates_key = "task_dates" if routine == "bedtime" else "morning_task_dates"
        required_key = "required_tasks" if routine == "bedtime" else "morning_required_tasks"
        legacy = child[stickers_key].get(day)
        reward = record["rewards"].setdefault(routine, {
            **(deepcopy(legacy) if legacy else {"emoji": "⭐", "earned": False}),
            "override": None,
        })
        if "override" not in reward:
            reward["override"] = None
        if routine not in record["tasks"]:
            record["tasks"][routine] = {}
            if profile and legacy and legacy.get("earned"):
                record["tasks"][routine] = dict.fromkeys(TASKS, True)
        fallback = DEFAULT_TASKS if routine == "bedtime" else DEFAULT_MORNING_TASKS
        record.setdefault(required_key, deepcopy(fallback))
        return record

    @staticmethod
    def _recalculate(data, child, day, routine, reward):
        previous = bool(reward.get("earned"))
        if reward.get("override") is not None:
            earned = bool(reward["override"])
        else:
            tasks = child["days"][day]["tasks"].get(routine, {})
            required_key = "required_tasks" if routine == "bedtime" else "morning_required_tasks"
            fallback = DEFAULT_TASKS if routine == "bedtime" else DEFAULT_MORNING_TASKS
            required = child["days"][day].get(required_key, fallback)
            earned = bool(required) and all(tasks.get(item["id"], False) for item in required)
        reward["earned"] = earned
        total_key = "total" if routine == "bedtime" else "morning_total"
        child[total_key] = max(0, child[total_key] + int(earned) - int(previous))
        stickers_key = "stickers" if routine == "bedtime" else "morning_stickers"
        child[stickers_key][day] = {"emoji": reward.get("emoji", "⭐"), "earned": earned}

    @staticmethod
    def _validate_task_list(tasks):
        if not isinstance(tasks, list) or not 1 <= len(tasks) <= 20:
            raise ServiceValidationError("A checklist must contain between 1 and 20 tasks.")
        ids = set()
        clean = []
        for item in tasks:
            if not isinstance(item, dict):
                raise ServiceValidationError("Each task must have an ID and label.")
            task_id = item.get("id")
            label = item.get("label")
            icon = item.get("icon", "✓")
            if not isinstance(task_id, str) or not re.fullmatch(r"[a-z0-9_]{1,48}", task_id):
                raise ServiceValidationError("Task IDs must contain only lowercase letters, numbers, and underscores.")
            if task_id in ids:
                raise ServiceValidationError("Task IDs must be unique.")
            if not isinstance(label, str) or not label.strip() or len(label) > 60:
                raise ServiceValidationError("Task labels must contain 1 to 60 characters.")
            if not isinstance(icon, str) or not 1 <= len(icon) <= 16:
                raise ServiceValidationError("Task icons must contain 1 to 16 characters.")
            ids.add(task_id)
            clean.append({"id": task_id, "label": label.strip(), "icon": icon})
        return clean

    async def async_parent_control(self, action, **values):
        """Apply an administrator-authorized parent-panel action."""
        async with self.lock:
            data = deepcopy(self.data)
            profiles, children = data["profiles"], data["children"]
            child_id = values.get("child_id")
            callback = None
            today = routine_date()
            if action == "read":
                return {
                    "profiles": sorted(profiles.values(), key=lambda item: item["order"]),
                    "default_tasks": deepcopy(data["default_tasks"]),
                    "default_morning_tasks": deepcopy(data["default_morning_tasks"]),
                    "schedule": {
                        key: data[key]
                        for key in ("dinner_time", "bedtime_time", "routine_switch_time")
                    },
                    "today": today,
                    "days": {
                        child_key: deepcopy(child["days"])
                        for child_key, child in children.items()
                    },
                }
            if action == "profile_create":
                name = self._valid_name(values.get("name"))
                child_id = f"child_{uuid4().hex[:12]}"
                while child_id in profiles:
                    child_id = f"child_{uuid4().hex[:12]}"
                profiles[child_id] = self._new_profile(child_id, name, len(profiles))
                children[child_id] = {
                    "total": 0, "morning_total": 0, "month": today[:7],
                    "stickers": {}, "morning_stickers": {},
                    "task_dates": {}, "morning_task_dates": {}, "days": {},
                    "task_overrides": {"bedtime": None, "morning": None},
                }
                callback = getattr(self, "_async_child_added", None)
            elif action not in ("default_tasks", "schedule") and child_id not in profiles:
                raise ServiceValidationError("Choose an existing child profile.")
            elif action == "profile_update":
                profile = profiles[child_id]
                name = values.get("name", profile["name"])
                accent = values.get("accent", profile["accent"])
                tint = values.get("tint", profile["tint"])
                size = values.get("size", profile["size"])
                profile.update(
                    name=self._valid_name(name),
                    accent=self._valid_color(accent),
                    tint=self._valid_color(tint),
                )
                if size not in ("compact", "standard", "large"):
                    raise ServiceValidationError("Choose a supported card size.")
                profile["size"] = size
            elif action in ("profile_archive", "profile_restore"):
                profiles[child_id]["active"] = action == "profile_restore"
                ordered = self.profile_ids_from(profiles)
                for position, item in enumerate(ordered):
                    profiles[item]["order"] = position
            elif action == "profile_move":
                ordered = self.profile_ids_from(profiles)
                try:
                    current = ordered.index(child_id)
                except ValueError as err:
                    raise ServiceValidationError("Choose an existing child profile.") from err
                destination = values.get("position")
                if type(destination) is not int or not 0 <= destination < len(ordered):
                    raise ServiceValidationError("Choose a valid display position.")
                ordered.insert(destination, ordered.pop(current))
                for position, item in enumerate(ordered):
                    profiles[item]["order"] = position
            elif action == "default_tasks":
                routine = values.get("routine", "bedtime")
                if routine not in ROUTINES:
                    raise ServiceValidationError("Choose the morning or bedtime routine.")
                default_key = task_defaults_key(routine)
                data[default_key] = self._validate_task_list(values.get("tasks"))
                await self._apply_task_list_change(
                    data, "", data[default_key], values.get("effective_day", "tomorrow"), today, routine,
                )
            elif action == "child_tasks":
                routine = values.get("routine", "bedtime")
                if routine not in ROUTINES:
                    raise ServiceValidationError("Choose the morning or bedtime routine.")
                effective = values.get("effective_day", "tomorrow")
                override = values.get("tasks")
                profiles[child_id]["task_overrides"][routine] = (
                    None if override is None else self._validate_task_list(override)
                )
                chosen = profiles[child_id]["task_overrides"][routine] or data[task_defaults_key(routine)]
                await self._apply_task_list_change(data, child_id, chosen, effective, today, routine)
            elif action == "correct_task":
                day, task_id, completed = values.get("routine_date"), values.get("task"), values.get("completed")
                routine = values.get("routine", "bedtime")
                if routine not in ROUTINES:
                    raise ServiceValidationError("Choose the morning or bedtime routine.")
                self._validate_correction_day(day, today)
                task_ids = {item["id"] for item in self.tasks_for_profile(data, child_id, routine)}
                if task_id not in task_ids or type(completed) is not bool:
                    raise ServiceValidationError("Choose a current routine task and completion value.")
                child = children[child_id]
                daily = self._day_record(child, day, profiles[child_id], routine)
                required_key = "required_tasks" if routine == "bedtime" else "morning_required_tasks"
                dates_key = "task_dates" if routine == "bedtime" else "morning_task_dates"
                daily[required_key] = self.tasks_for_profile(data, child_id, routine)
                task_state = daily["tasks"].setdefault(routine, {})
                changed = task_state.get(task_id, False) is not completed
                task_state[task_id] = completed
                reward = daily["rewards"][routine]
                if changed:
                    reward["override"] = None
                self._recalculate(data, child, day, routine, reward)
                if day == today:
                    child[dates_key][task_id] = day if completed else "1970-01-01"
            elif action == "set_reward":
                day, earned = values.get("routine_date"), values.get("earned")
                routine = values.get("routine", "bedtime")
                sticker = values.get("sticker", "⭐")
                if routine not in ROUTINES:
                    raise ServiceValidationError("Choose the morning or bedtime routine.")
                self._validate_correction_day(day, today)
                if type(earned) is not bool or sticker not in STICKERS:
                    raise ServiceValidationError("Choose a valid sticker and earned state.")
                child = children[child_id]
                daily = self._day_record(child, day, profiles[child_id], routine)
                reward = daily["rewards"][routine]
                reward["emoji"], reward["override"] = sticker, earned
                self._recalculate(data, child, day, routine, reward)
            elif action == "schedule":
                schedule = values.get("schedule")
                if not isinstance(schedule, dict):
                    raise ServiceValidationError("Provide the reminder times.")
                for key in ("dinner_time", "bedtime_time", "routine_switch_time"):
                    if key in schedule:
                        parsed = dt_util.parse_time(schedule[key])
                        if parsed is None:
                            raise ServiceValidationError("Enter valid local reminder times.")
                        data[key] = parsed.strftime("%H:%M:%S")
            elif action == "read":
                return {
                    "profiles": sorted(profiles.values(), key=lambda item: item["order"]),
                    "default_tasks": deepcopy(data["default_tasks"]),
                    "default_morning_tasks": deepcopy(data["default_morning_tasks"]),
                    "schedule": {
                        key: data[key]
                        for key in ("dinner_time", "bedtime_time", "routine_switch_time")
                    },
                    "today": today,
                    "days": {
                        child_key: deepcopy(child["days"])
                        for child_key, child in children.items()
                    },
                }
            elif action == "set_avatar":
                avatar = values.get("avatar")
                if not isinstance(avatar, str) or not 1 <= len(avatar) <= 16:
                    raise ServiceValidationError("Choose a valid emoji avatar.")
                profiles[child_id]["avatar"] = avatar
            else:
                raise ServiceValidationError("Unknown Parent Controls action.")
            await self._commit(data)
        if action == "profile_create" and callback:
            callback(child_id)
        if action == "profile_create":
            return child_id

    @staticmethod
    def tasks_for_profile(data, child_id, routine="bedtime"):
        profile = data["profiles"][child_id]
        return deepcopy(
            profile.get("task_overrides", {}).get(routine)
            or data[task_defaults_key(routine)]
        )

    async def _apply_task_list_change(self, data, child_id, task_list, effective_day, today, routine="bedtime"):
        if effective_day not in ("today", "tomorrow"):
            raise ServiceValidationError("Apply checklist changes today or tomorrow.")
        targets = [child_id] if child_id else [
            key for key in data["children"]
            if data["profiles"][key].get("task_overrides", {}).get(routine) is None
        ]
        apply_day = today if effective_day == "today" else (
            dt_util.parse_date(today) + timedelta(days=1)
        ).isoformat()
        if effective_day == "tomorrow":
            pending = data.setdefault("scheduled_tasks", {})
            updates = pending.setdefault(apply_day, [])
            for target in targets:
                if target in data["children"]:
                    updates[:] = [item for item in updates if item["child_id"] != target]
                    updates.append({"child_id": target, "tasks": deepcopy(task_list), "routine": routine})
            return
        for target in targets:
            if target not in data["children"]:
                continue
            install_task_snapshot(data, target, apply_day, task_list, routine)

    @staticmethod
    def _validate_correction_day(day, today):
        if (
            not isinstance(day, str)
            or dt_util.parse_date(day) is None
            or day > today
            or day[:7] != today[:7]
        ):
            raise ServiceValidationError("Corrections are limited to dates in the current routine month.")

    @staticmethod
    def _valid_name(value):
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > 40:
            raise ServiceValidationError("Names must contain 1 to 40 characters.")
        return value.strip()

    @staticmethod
    def _valid_color(value):
        if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise ServiceValidationError("Choose a valid six-digit color.")
        return value


    async def async_set_time(self, name, value):
        async with self.lock:
            data = deepcopy(self.data)
            data[name] = value.strftime("%H:%M:%S")
            await self._commit(data)

    async def async_set_avatar(self, child_id, avatar):
        async with self.lock:
            if child_id not in self.data["profiles"] or not self.data["profiles"][child_id]["active"]:
                raise ServiceValidationError("Choose an active child profile.")
            if not isinstance(avatar, str) or not 1 <= len(avatar) <= 16:
                raise ServiceValidationError("Choose a valid emoji avatar.")
            data = deepcopy(self.data)
            data["profiles"][child_id]["avatar"] = avatar
            await self._commit(data)
