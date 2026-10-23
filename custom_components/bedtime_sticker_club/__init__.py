"""Set up Bedtime Sticker Club from Home Assistant's integration UI."""

from datetime import timedelta
from pathlib import Path

import probatio as vol

from homeassistant.components import frontend
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.dashboard import LovelaceYAML
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.event import async_track_time_interval

from .const import CHILDREN, DASHBOARD_URL, DOMAIN, STICKERS, TASKS, TITLE
from .coordinator import BedtimeCoordinator

PLATFORMS = [Platform.SENSOR, Platform.TIME]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def register_dashboard(hass):
    """Register a bundled dashboard, respecting an existing personal copy."""
    lovelace = hass.data[LOVELACE_DATA]
    if DASHBOARD_URL in lovelace.dashboards:
        return None
    if frontend.async_panel_exists(hass, DASHBOARD_URL):
        raise ConfigEntryError(f"The sidebar path {DASHBOARD_URL} is already in use")
    dashboard = LovelaceYAML(hass, DASHBOARD_URL, {
        "mode": "yaml", "title": TITLE, "icon": "mdi:star-face",
        "show_in_sidebar": True, "require_admin": False,
        "filename": str(Path(__file__).parent / "dashboard.yaml"),
    })
    frontend.async_register_built_in_panel(
        hass, "lovelace", sidebar_title=TITLE, sidebar_icon="mdi:star-face",
        frontend_url_path=DASHBOARD_URL, config={"mode": "yaml"},
    )
    lovelace.dashboards[DASHBOARD_URL] = dashboard
    return dashboard


async def async_setup_entry(hass, entry):
    if hass.services.has_service("script", "bedtime_set_task"):
        raise ConfigEntryError("Remove the old Bedtime YAML package and restart Home Assistant before adding this integration.")
    coordinator = BedtimeCoordinator(hass, entry)
    await coordinator.async_initialize()
    entry.runtime_data = coordinator

    registry = er.async_get(hass)
    for key in ("routine", *CHILDREN):
        entity_id = f"sensor.bedtime_{key}"
        existing = registry.async_get(entity_id)
        if existing and existing.platform == "template" and existing.unique_id == f"bedtime_{key}":
            registry.async_remove(entity_id)
        elif existing and existing.platform != DOMAIN:
            raise ConfigEntryError(f"The entity ID {entity_id} is already in use")

    coordinator.dashboard = register_dashboard(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(async_track_time_interval(
        hass, coordinator.async_tick, timedelta(minutes=1), name=DOMAIN,
    ))

    async def options_updated(hass, updated_entry):
        coordinator.async_update_listeners()

    entry.async_on_unload(entry.add_update_listener(options_updated))

    async def set_task(call):
        values = call.data
        await coordinator.async_command(
            "task", values["child_id"], values["routine_date"],
            task=values["task"], completed=values["completed"],
        )

    async def choose_sticker(call):
        values = call.data
        await coordinator.async_command(
            "sticker", values["child_id"], values["routine_date"],
            sticker=values["sticker"],
        )

    common = {
        vol.Required("child_id"): vol.In(CHILDREN),
        vol.Required("routine_date"): cv.string,
    }
    hass.services.async_register(DOMAIN, "set_task", set_task, schema=vol.Schema({
        **common, vol.Required("task"): vol.In(TASKS), vol.Required("completed"): bool,
    }))
    hass.services.async_register(DOMAIN, "choose_sticker", choose_sticker, schema=vol.Schema({
        **common, vol.Required("sticker"): vol.In(STICKERS),
    }))
    return True


async def async_unload_entry(hass, entry):
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    for service in ("set_task", "choose_sticker"):
        hass.services.async_remove(DOMAIN, service)
    dashboard = entry.runtime_data.dashboard
    lovelace = hass.data[LOVELACE_DATA]
    if dashboard is not None and lovelace.dashboards.get(DASHBOARD_URL) is dashboard:
        lovelace.dashboards.pop(DASHBOARD_URL)
        frontend.async_remove_panel(hass, DASHBOARD_URL)
    return True
