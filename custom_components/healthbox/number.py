"""Number platform for the Renson Healthbox integration.

Holds the boost level (%) and timeout (minutes) to use the *next* time a
room's boost switch (switch.py) is turned on. The device itself has no
notion of a "configured but not started" boost - these values only exist
as Home Assistant state, so they're restored across restarts via
RestoreNumber rather than read from the API.
"""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntityDescription,
    NumberMode,
    RestoreNumber,
)
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from pyhealthbox3.models import Healthbox3Room

from .const import (
    DEFAULT_BOOST_LEVEL,
    DEFAULT_BOOST_TIMEOUT,
    LOGGER,
    MAX_BOOST_LEVEL,
    MAX_BOOST_TIMEOUT,
    MIN_BOOST_LEVEL,
    MIN_BOOST_TIMEOUT,
)
from .coordinator import HealthboxConfigEntry, HealthboxDataUpdateCoordinator
from .entity import HealthboxRoomEntity


@dataclass(frozen=True, kw_only=True)
class HealthboxBoostSettingDescription(NumberEntityDescription):
    """Describes a boost-configuration number.

    `field` is the key this number occupies in
    HealthboxDataUpdateCoordinator.get_boost_settings()'s dict.
    """

    field: str
    default_value: float


BOOST_LEVEL_DESCRIPTION = HealthboxBoostSettingDescription(
    key="boost_level_setting",
    name="Boost Level",
    icon="mdi:fan",
    native_min_value=MIN_BOOST_LEVEL,
    native_max_value=MAX_BOOST_LEVEL,
    native_step=5,
    native_unit_of_measurement=PERCENTAGE,
    mode=NumberMode.SLIDER,
    field="level",
    default_value=DEFAULT_BOOST_LEVEL,
)
BOOST_TIMEOUT_DESCRIPTION = HealthboxBoostSettingDescription(
    key="boost_timeout_setting",
    name="Boost Timeout",
    icon="mdi:clock-time-five-outline",
    native_min_value=MIN_BOOST_TIMEOUT,
    native_max_value=MAX_BOOST_TIMEOUT,
    native_step=1,
    native_unit_of_measurement=UnitOfTime.MINUTES,
    mode=NumberMode.BOX,
    field="timeout",
    default_value=DEFAULT_BOOST_TIMEOUT,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HealthboxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Healthbox boost-setting numbers, adding new ones as rooms appear."""
    coordinator = entry.runtime_data
    known_room_ids: set[int] = set()

    @callback
    def _add_new_entities() -> None:
        new_entities: list[HealthboxRoomBoostNumber] = []

        for room in coordinator.api.rooms:
            if room.room_id not in known_room_ids:
                known_room_ids.add(room.room_id)
                new_entities.append(
                    HealthboxRoomBoostNumber(coordinator, BOOST_LEVEL_DESCRIPTION, room)
                )
                new_entities.append(
                    HealthboxRoomBoostNumber(coordinator, BOOST_TIMEOUT_DESCRIPTION, room)
                )

        if new_entities:
            LOGGER.debug(
                "Adding %s new Healthbox boost-setting number(s): %s",
                len(new_entities),
                [e.entity_description.key for e in new_entities],
            )
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class HealthboxRoomBoostNumber(HealthboxRoomEntity, RestoreNumber):
    """A number holding the boost level or timeout to use next for a room."""

    entity_description: HealthboxBoostSettingDescription

    def __init__(
        self,
        coordinator: HealthboxDataUpdateCoordinator,
        description: HealthboxBoostSettingDescription,
        room: Healthbox3Room,
    ) -> None:
        """Initialize the number."""
        RestoreNumber.__init__(self)
        HealthboxRoomEntity.__init__(self, coordinator, description, room)
        self._attr_native_value = description.default_value

    async def async_added_to_hass(self) -> None:
        """Restore the last set value, and seed the coordinator's shared settings."""
        await super().async_added_to_hass()
        last_data = await self.async_get_last_number_data()
        if last_data is not None and last_data.native_value is not None:
            self._attr_native_value = last_data.native_value
        self.coordinator.get_boost_settings(self._room_id)[
            self.entity_description.field
        ] = self._attr_native_value

    @property
    def native_value(self) -> float | None:
        """Return the currently configured value."""
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Update the value, both locally and in the coordinator's shared settings."""
        LOGGER.debug(
            "Room %s: boost %s set to %s",
            self._room_id,
            self.entity_description.field,
            value,
        )
        self._attr_native_value = value
        self.coordinator.get_boost_settings(self._room_id)[self.entity_description.field] = value
        self.async_write_ha_state()
