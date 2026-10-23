"""Routine status and per-child reward sensors."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CHILDREN, DOMAIN, TITLE
from .coordinator import routine_date


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([
        BedtimeSensor(entry.runtime_data, child) for child in ("routine", *CHILDREN)
    ])


class BedtimeSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, child):
        super().__init__(coordinator)
        self.child = child
        self.entity_id = f"sensor.bedtime_{child}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{child}"
        self._attr_name = f"Bedtime {child.replace('_', ' ').title()}"
        self._attr_icon = "mdi:star-face" if child == "routine" else "mdi:sticker-emoji"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.entry.entry_id)}, "name": TITLE,
        }

    @property
    def native_value(self):
        if self.child == "routine":
            return self.coordinator.phase
        return self.coordinator.data["children"][self.child]["total"]

    @property
    def extra_state_attributes(self):
        if self.child == "routine":
            return {
                "routine_date": routine_date(),
                "dinner_time": self.coordinator.data["dinner_time"],
                "bedtime_time": self.coordinator.data["bedtime_time"],
            }
        return self.coordinator.child_attributes(self.child)
