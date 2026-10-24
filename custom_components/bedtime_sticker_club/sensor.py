"""Routine status and per-child reward sensors."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CHILDREN, DOMAIN, TITLE
from .coordinator import routine_date


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    async_add_entities([
        BedtimeSensor(coordinator, "routine"),
        *[
            BedtimeSensor(coordinator, child, routine)
            for child in coordinator.profile_ids()
            for routine in ("bedtime", "morning")
        ],
    ])

    def child_added(child):
        async_add_entities([
            BedtimeSensor(coordinator, child, routine)
            for routine in ("bedtime", "morning")
        ])

    coordinator._async_child_added = child_added


class BedtimeSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, child, routine="bedtime"):
        super().__init__(coordinator)
        self.child = child
        self.routine = routine
        suffix = "" if child == "routine" or routine == "bedtime" else "_morning"
        self.entity_id = f"sensor.bedtime_{child}{suffix}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{child}{suffix}"
        self._attr_name = (
            "Bedtime routine" if child == "routine"
            else f"{routine.title()} {coordinator.data['profiles'][child]['name']}"
        )
        self._attr_icon = "mdi:star-face" if child == "routine" else "mdi:sticker-emoji"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.entry.entry_id)}, "name": TITLE,
        }

    @property
    def native_value(self):
        if self.child == "routine":
            return self.coordinator.phase
        child = self.coordinator.data["children"][self.child]
        return child["total"] if self.routine == "bedtime" else child["morning_total"]

    @property
    def extra_state_attributes(self):
        if self.child == "routine":
            return {
                "routine_date": routine_date(),
                "dinner_time": self.coordinator.data["dinner_time"],
                "bedtime_time": self.coordinator.data["bedtime_time"],
                "active_routine": self.coordinator.active_routine,
                "routine_switch_time": self.coordinator.data["routine_switch_time"],
            }
        return self.coordinator.child_attributes(self.child, self.routine)
