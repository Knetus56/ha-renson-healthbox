"""Services for the Renson Healthbox integration.

Registered once for the whole integration (from `async_setup`), never per
config entry — a service call resolves its target `device_id` back to
whichever loaded Healthbox config entry actually owns that device. This is
what lets unloading one Healthbox leave the services in place for every
other one still configured, instead of removing them integration-wide.
"""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .const import (
    ATTR_BOOST_LEVEL,
    ATTR_BOOST_TIMEOUT,
    ATTR_PROFILE_NAME,
    DOMAIN,
    ROOM_PROFILES,
    SERVICE_CHANGE_ROOM_PROFILE,
    SERVICE_START_ROOM_BOOST,
    SERVICE_STOP_ROOM_BOOST,
)
from .coordinator import HealthboxDataUpdateCoordinator
from .entity import room_id_from_identifier

_DEVICE_ID_SCHEMA = {vol.Required(cv.CONF_DEVICE_ID): cv.string}

_START_ROOM_BOOST_SCHEMA = vol.Schema(
    {
        **_DEVICE_ID_SCHEMA,
        vol.Required(ATTR_BOOST_LEVEL): vol.All(int, vol.Range(min=10, max=200)),
        vol.Required(ATTR_BOOST_TIMEOUT): vol.All(int, vol.Range(min=5, max=720)),
    }
)
_STOP_ROOM_BOOST_SCHEMA = vol.Schema(_DEVICE_ID_SCHEMA)
_CHANGE_ROOM_PROFILE_SCHEMA = vol.Schema(
    {
        **_DEVICE_ID_SCHEMA,
        vol.Required(ATTR_PROFILE_NAME): vol.In(ROOM_PROFILES),
    }
)


def _resolve_room(hass: HomeAssistant, device_id: str) -> tuple[HealthboxDataUpdateCoordinator, int]:
    """Resolve a target device_id to the coordinator and room_id it belongs to."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        raise ServiceValidationError(f"Unknown device: {device_id}")

    for identifier in device.identifiers:
        room_id = room_id_from_identifier(identifier)
        if room_id is None:
            continue
        for entry_id in device.config_entries:
            entry = hass.config_entries.async_get_entry(entry_id)
            if entry is not None and entry.domain == DOMAIN and entry.state is ConfigEntryState.LOADED:
                return entry.runtime_data, room_id

    raise ServiceValidationError(f"Device {device_id} is not a Healthbox room")


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the Healthbox services (once, for the whole integration)."""

    async def start_room_boost(call: ServiceCall) -> None:
        coordinator, room_id = _resolve_room(hass, call.data[cv.CONF_DEVICE_ID])
        await coordinator.start_room_boost(
            room_id=room_id,
            boost_level=call.data[ATTR_BOOST_LEVEL],
            boost_timeout=call.data[ATTR_BOOST_TIMEOUT] * 60,
        )

    async def stop_room_boost(call: ServiceCall) -> None:
        coordinator, room_id = _resolve_room(hass, call.data[cv.CONF_DEVICE_ID])
        await coordinator.stop_room_boost(room_id=room_id)

    async def change_room_profile(call: ServiceCall) -> None:
        coordinator, room_id = _resolve_room(hass, call.data[cv.CONF_DEVICE_ID])
        await coordinator.change_room_profile(
            room_id=room_id, profile_name=call.data[ATTR_PROFILE_NAME]
        )

    if hass.services.has_service(DOMAIN, SERVICE_START_ROOM_BOOST):
        return

    hass.services.async_register(
        DOMAIN, SERVICE_START_ROOM_BOOST, start_room_boost, _START_ROOM_BOOST_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_STOP_ROOM_BOOST, stop_room_boost, _STOP_ROOM_BOOST_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CHANGE_ROOM_PROFILE, change_room_profile, _CHANGE_ROOM_PROFILE_SCHEMA
    )
