"""Persistent reminder times editable from the parent dashboard."""

from homeassistant.components.time import TimeEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, TITLE


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([
        BedtimeTime(entry.runtime_data, name) for name in ("dinner_time", "bedtime_time")
    ])


class BedtimeTime(CoordinatorEntity, TimeEntity):
    def __init__(self, coordinator, name):
        super().__init__(coordinator)
        self.key = name
        self.entity_id = f"time.bedtime_{name}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{name}"
        self._attr_name = f"Bedtime {name.replace('_', ' ')}"
        self._attr_icon = "mdi:clock-outline"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.entry.entry_id)}, "name": TITLE,
        }

    @property
    def native_value(self):
        return dt_util.parse_time(self.coordinator.data[self.key])

    async def async_set_value(self, value):
        raise HomeAssistantError("Change bedtime schedules in Parent Controls.")
