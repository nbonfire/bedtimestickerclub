"""Set up Bedtime Sticker Club from Home Assistant's integration UI."""

from copy import deepcopy
from datetime import timedelta
from pathlib import Path

import probatio as vol

from homeassistant.components import frontend
from homeassistant.components import websocket_api
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.dashboard import LovelaceYAML
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryError, HomeAssistantError
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.event import async_track_time_interval

from .avatar import ChildAvatarView
from .const import DASHBOARD_URL, DOMAIN, ROUTINES, STICKERS, TITLE
from .coordinator import BedtimeCoordinator

PLATFORMS = [Platform.SENSOR, Platform.TIME]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
FRONTEND_URL = f"/{DOMAIN}/static/bedtime-sticker-club.js"


def require_parent_admin(connection):
    """Require an authenticated Home Assistant administrator for parent actions."""
    if not connection.user.is_admin:
        raise HomeAssistantError("Parent Controls are available to Home Assistant administrators.")


async def async_handle_parent_action(hass, connection, entry_id, action, data):
    """Authorize and dispatch a Parent Controls request."""
    require_parent_admin(connection)
    coordinator = hass.data[DOMAIN].get(entry_id) if entry_id else next(
        iter(hass.data[DOMAIN].values()), None,
    )
    if coordinator is None:
        raise ServiceValidationError("Bedtime Sticker Club is not loaded.")
    return await coordinator.async_parent_control(action, **data)


async def async_setup(hass, config: ConfigType):
    """Register the native cards and the administrator-only Parent Controls API."""
    from homeassistant.components.http import StaticPathConfig

    hass.data.setdefault(DOMAIN, {})
    await hass.http.async_register_static_paths([
        StaticPathConfig(
            FRONTEND_URL,
            str(Path(__file__).parent / "frontend/bedtime-sticker-club.js"),
            cache_headers=False,
        )
    ])
    frontend.add_extra_js_url(hass, FRONTEND_URL)
    hass.http.register_view(ChildAvatarView)

    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/admin",
        vol.Optional("entry_id"): cv.string,
        vol.Required("action"): cv.string,
        vol.Optional("data", default={}): dict,
    })
    @websocket_api.async_response
    async def parent_controls(hass, connection, message):
        result = await async_handle_parent_action(
            hass, connection, message.get("entry_id"),
            message["action"], message["data"],
        )
        connection.send_result(message["id"], result or {})

    websocket_api.async_register_command(hass, parent_controls)
    return True


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
    hass.data[DOMAIN][entry.entry_id] = coordinator

    registry = er.async_get(hass)
    for key in ("routine", *coordinator.profile_ids()):
        entity_id = f"sensor.bedtime_{key}"
        existing = registry.async_get(entity_id)
        if existing and existing.platform == "template" and existing.unique_id == f"bedtime_{key}":
            registry.async_remove(entity_id)
        elif existing and existing.platform != DOMAIN:
            raise ConfigEntryError(f"The entity ID {entity_id} is already in use")
        if key != "routine":
            morning_entity_id = f"sensor.bedtime_{key}_morning"
            morning_entry = registry.async_get(morning_entity_id)
            if morning_entry and morning_entry.platform != DOMAIN:
                raise ConfigEntryError(f"The entity ID {morning_entity_id} is already in use")

    coordinator.dashboard = register_dashboard(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(async_track_time_interval(
        hass, coordinator.async_tick, timedelta(minutes=1), name=DOMAIN,
    ))

    async def options_updated(hass, updated_entry):
        data = deepcopy(coordinator.data)
        changed = False
        for child_id, profile in data["profiles"].items():
            key = f"{child_id}_name"
            if key in updated_entry.options and profile["name"] != updated_entry.options[key]:
                profile["name"] = coordinator._valid_name(updated_entry.options[key])
                changed = True
        if changed:
            await coordinator._commit(data)
        else:
            coordinator.async_update_listeners()

    entry.async_on_unload(entry.add_update_listener(options_updated))

    async def set_task(call):
        values = call.data
        await coordinator.async_command(
            "task", values["child_id"], values["routine_date"],
            task=values["task"], completed=values["completed"],
            routine=values.get("routine", "bedtime"),
        )

    async def choose_sticker(call):
        values = call.data
        await coordinator.async_command(
            "sticker", values["child_id"], values["routine_date"],
            sticker=values["sticker"],
            routine=values.get("routine", "bedtime"),
        )

    async def set_avatar(call):
        values = call.data
        await coordinator.async_set_avatar(values["child_id"], values["avatar"])

    common = {
        vol.Required("child_id"): cv.string,
        vol.Required("routine_date"): cv.string,
    }
    hass.services.async_register(DOMAIN, "set_task", set_task, schema=vol.Schema({
        **common, vol.Required("task"): cv.string, vol.Required("completed"): bool,
        vol.Optional("routine", default="bedtime"): vol.In(ROUTINES),
    }))
    hass.services.async_register(DOMAIN, "choose_sticker", choose_sticker, schema=vol.Schema({
        **common, vol.Required("sticker"): vol.In(STICKERS),
        vol.Optional("routine", default="bedtime"): vol.In(ROUTINES),
    }))
    hass.services.async_register(DOMAIN, "set_avatar", set_avatar, schema=vol.Schema({
        vol.Required("child_id"): cv.string,
        vol.Required("avatar"): cv.string,
    }))
    return True


async def async_unload_entry(hass, entry):
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    for service in ("set_task", "choose_sticker", "set_avatar"):
        hass.services.async_remove(DOMAIN, service)
    dashboard = entry.runtime_data.dashboard
    lovelace = hass.data[LOVELACE_DATA]
    if dashboard is not None and lovelace.dashboards.get(DASHBOARD_URL) is dashboard:
        lovelace.dashboards.pop(DASHBOARD_URL)
        frontend.async_remove_panel(hass, DASHBOARD_URL)
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
