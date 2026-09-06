"""Diagnostics support for the Renson Healthbox integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from .coordinator import HealthboxConfigEntry

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: HealthboxConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    api = coordinator.api

    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "entry_options": dict(entry.options),
        "device": {
            "serial": api.serial,
            "description": api.description,
            "warranty_number": api.warranty_number,
            "firmware_version": api.firmware_version,
            "advanced_api_enabled": api.advanced_api_enabled,
            "global_aqi": api.global_aqi,
            "error_count": api.error_count,
        },
        "wifi": vars(api.wifi),
        "fan": vars(api.fan),
        "rooms": [
            {
                "room_id": room.room_id,
                "name": room.name,
                "type": room.room_type,
                "enabled_sensors": room.enabled_sensors,
                "profile_name": _safe(lambda: room.profile_name),
                "indoor_temperature": _safe(lambda: room.indoor_temperature),
                "indoor_humidity": _safe(lambda: room.indoor_humidity),
                "indoor_co2_concentration": _safe(lambda: room.indoor_co2_concentration),
                "indoor_voc_ppm": _safe(lambda: room.indoor_voc_ppm),
                "indoor_aqi": _safe(lambda: room.indoor_aqi),
                "airflow_ventilation_rate": _safe(lambda: room.airflow_ventilation_rate),
                "boost": vars(room.boost),
            }
            for room in api.rooms
        ],
    }


def _safe(getter):
    """Evaluate a possibly-raising pyhealthbox3 property for diagnostics."""
    try:
        return getter()
    except (AttributeError, TypeError, KeyError, IndexError) as err:
        return f"<error: {err}>"
