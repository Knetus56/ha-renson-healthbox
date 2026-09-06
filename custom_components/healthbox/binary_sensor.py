"""Binary sensor platform for the Renson Healthbox integration."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from pyhealthbox3.models import Healthbox3Room

from .const import LOGGER
from .coordinator import HealthboxConfigEntry, HealthboxDataUpdateCoordinator
from .entity import HealthboxRoomDescriptionMixin, HealthboxRoomEntity


@dataclass(frozen=True, kw_only=True)
class HealthboxRoomEntityDescription(BinarySensorEntityDescription, HealthboxRoomDescriptionMixin):
    """Describes a Healthbox room binary sensor."""


def _room_binary_sensor_descriptions(
    room: Healthbox3Room,
) -> list[HealthboxRoomEntityDescription]:
    """Build the binary sensor descriptions for one room.

    room.boost always exists on a Healthbox3Room, so the boost status
    entity is always created; it just reads back "off" until a real
    boost is running.
    """
    return [
        HealthboxRoomEntityDescription(
            key="boost_status",
            name="Boost Status",
            icon="mdi:fan-plus",
            value_fn=lambda r: bool(r.boost.enabled),
        ),
    ]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HealthboxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Healthbox binary sensors, adding new ones as rooms appear."""
    coordinator = entry.runtime_data
    known_room_keys: dict[int, set[str]] = {}

    @callback
    def _add_new_entities() -> None:
        new_entities: list[BinarySensorEntity] = []

        for room in coordinator.api.rooms:
            seen = known_room_keys.setdefault(room.room_id, set())
            for description in _room_binary_sensor_descriptions(room):
                if description.key not in seen:
                    seen.add(description.key)
                    new_entities.append(
                        HealthboxRoomBinarySensor(coordinator, description, room)
                    )

        if new_entities:
            LOGGER.debug(
                "Adding %s new Healthbox binary sensor(s): %s",
                len(new_entities),
                [e.entity_description.key for e in new_entities],
            )
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class HealthboxRoomBinarySensor(HealthboxRoomEntity, BinarySensorEntity):
    """A binary sensor describing one Healthbox room."""

    entity_description: HealthboxRoomEntityDescription

    def __init__(
        self,
        coordinator: HealthboxDataUpdateCoordinator,
        description: HealthboxRoomEntityDescription,
        room: Healthbox3Room,
    ) -> None:
        """Initialize the binary sensor."""
        BinarySensorEntity.__init__(self)
        HealthboxRoomEntity.__init__(self, coordinator, description, room)

    @property
    def is_on(self) -> bool | None:
        """Return true if the boost is currently running."""
        return self._safe_value()
