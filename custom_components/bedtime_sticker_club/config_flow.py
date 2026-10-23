"""UI setup and options for Bedtime Sticker Club."""

import probatio as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import CHILDREN, DOMAIN, TITLE


def name_schema(values):
    return vol.Schema({
        vol.Required(f"{child}_name", default=values.get(f"{child}_name", f"Kid {i}")):
            vol.All(str, vol.Length(min=1, max=40))
        for i, child in enumerate(CHILDREN, 1)
    })


class BedtimeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if self.hass.services.has_service("script", "bedtime_set_task"):
            return self.async_abort(reason="legacy_package_active")
        if user_input is not None:
            return self.async_create_entry(title=TITLE, data=user_input)
        return self.async_show_form(step_id="user", data_schema=name_schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BedtimeOptionsFlow()


class BedtimeOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=name_schema(self.config_entry.options or self.config_entry.data),
        )
