"""DataUpdateCoordinator for the Renson Healthbox integration."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from pyhealthbox3.healthbox3 import (
    Healthbox3,
    Healthbox3ApiClientAuthenticationError,
    Healthbox3ApiClientError,
)

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER

type HealthboxConfigEntry = ConfigEntry[HealthboxDataUpdateCoordinator]


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class HealthboxDataUpdateCoordinator(DataUpdateCoordinator[None]):
    """Coordinator to fetch data from a single Healthbox 3 device.

    The device has no push mechanism, so this polls `api.async_get_data()`
    and entities read straight off `coordinator.api` afterwards, matching
    the pattern used by pyhealthbox3's own data model.
    """

    config_entry: HealthboxConfigEntry
    # Set right after the hub device is registered in async_setup_entry -
    # room entities need it to link to the hub via via_device_id.
    hub_device_id: str

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: HealthboxConfigEntry,
        api: Healthbox3,
        update_interval: timedelta = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        super().__init__(
            hass=hass,
            logger=LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN} - {config_entry.data.get('host')}",
            update_interval=update_interval,
        )

    async def change_room_profile(self, room_id: int, profile_name: str) -> None:
        """Change a room's ventilation profile, then refresh state."""
        LOGGER.debug("Room %s: changing profile to %s", room_id, profile_name)
        try:
            await self.api.async_change_room_profile(room_id=room_id, profile_name=profile_name)
        except Healthbox3ApiClientError:
            LOGGER.error("Room %s: failed to change profile to %s", room_id, profile_name)
            raise
        await self.async_request_refresh()

    async def start_room_boost(self, room_id: int, boost_level: int, boost_timeout: int) -> None:
        """Start boosting a room's fan, then refresh state."""
        LOGGER.debug(
            "Room %s: starting boost at %s%% for %s seconds", room_id, boost_level, boost_timeout
        )
        try:
            await self.api.async_start_room_boost(
                room_id=room_id, boost_level=boost_level, boost_timeout=boost_timeout
            )
        except Healthbox3ApiClientError:
            LOGGER.error("Room %s: failed to start boost", room_id)
            raise
        await self.async_request_refresh()

    async def stop_room_boost(self, room_id: int) -> None:
        """Stop boosting a room's fan, then refresh state."""
        LOGGER.debug("Room %s: stopping boost", room_id)
        try:
            await self.api.async_stop_room_boost(room_id=room_id)
        except Healthbox3ApiClientError:
            LOGGER.error("Room %s: failed to stop boost", room_id)
            raise
        await self.async_request_refresh()

    async def _async_update_data(self) -> None:
        """Fetch the latest data from the Healthbox device."""
        try:
            await self.api.async_get_data()
        except Healthbox3ApiClientAuthenticationError as exception:
            LOGGER.debug("Auth failed talking to %s: %s", self.api.host, exception)
            raise ConfigEntryAuthFailed(
                "Healthbox rejected the configured API key"
            ) from exception
        except Healthbox3ApiClientError as exception:
            LOGGER.debug("Update failed talking to %s: %s", self.api.host, exception)
            raise UpdateFailed(
                f"Error communicating with Healthbox at {self.api.host}: {exception}"
            ) from exception
        else:
            LOGGER.debug(
                "Update OK for %s: global_aqi=%s error_count=%s rooms=%s",
                self.api.host,
                self.api.global_aqi,
                self.api.error_count,
                len(self.api.rooms),
            )
