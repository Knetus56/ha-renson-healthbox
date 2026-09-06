"""The Renson Healthbox integration."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from pyhealthbox3.healthbox3 import Healthbox3

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, MANUFACTURER, PLATFORMS
from .coordinator import HealthboxConfigEntry, HealthboxDataUpdateCoordinator
from .services import async_setup_services

# This integration is config-entry only (no YAML configuration), which
# hassfest requires stating explicitly whenever a component defines
# async_setup - otherwise it assumes YAML config is possible and expects it.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Set up the Healthbox integration.

    Services are registered here (once, for the whole integration's
    lifetime) rather than in async_setup_entry, so unloading a single
    Healthbox config entry never removes them for any other Healthbox
    that is still configured.
    """
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: HealthboxConfigEntry) -> bool:
    """Set up Renson Healthbox from a config entry."""
    api_key = entry.data.get(CONF_API_KEY)
    api = Healthbox3(
        host=entry.data[CONF_HOST],
        api_key=api_key,
        session=async_get_clientsession(hass),
    )
    if api_key:
        await api.async_enable_advanced_api_features()

    scan_interval_seconds = entry.options.get(
        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds()
    )
    coordinator = HealthboxDataUpdateCoordinator(
        hass=hass,
        config_entry=entry,
        api=api,
        update_interval=timedelta(seconds=scan_interval_seconds),
    )
    await coordinator.async_config_entry_first_refresh()

    # Register the hub device up front (rather than letting the sensor
    # platform's DeviceInfo create it implicitly) so room devices below can
    # link to it via via_device_id, the current (non-deprecated) API - it
    # needs the hub's actual registry id, which only exists once the device
    # itself has been created.
    hub_device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Healthbox {api.serial}",
        manufacturer=MANUFACTURER,
        model=api.description,
        hw_version=api.warranty_number,
        sw_version=api.firmware_version,
    )
    coordinator.hub_device_id = hub_device.id

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HealthboxConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: HealthboxConfigEntry) -> None:
    """Reload a config entry when its options change (e.g. scan_interval)."""
    await hass.config_entries.async_reload(entry.entry_id)
