"""Select platform for the Renson Healthbox integration.

Room profile (Eco/Health/Intense) is both readable and settable, which
makes it a select entity rather than a read-only sensor plus a service -
the value shows up directly on the entity and can be changed from its
dropdown, same as any other select in Home Assistant.
"""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from pyhealthbox3.models import Healthbox3Room

from .const import ROOM_PROFILES
from .coordinator import HealthboxConfigEntry, HealthboxDataUpdateCoordinator
from .entity import (
    HealthboxRoomDescriptionMixin,
    HealthboxRoomEntity,
    async_setup_room_entities,
    room_field,
)


@dataclass(frozen=True, kw_only=True)
class HealthboxRoomSelectEntityDescription(SelectEntityDescription, HealthboxRoomDescriptionMixin):
    """Describes a Healthbox room select."""


def _room_select_descriptions(room: Healthbox3Room) -> list[HealthboxRoomSelectEntityDescription]:
    """Build the select descriptions currently supported by one room."""
    if room_field(room, lambda r: r.profile_name) is None:
        return []
    return [
        HealthboxRoomSelectEntityDescription(
            key="profile",
            name="Profile",
            icon="mdi:account-box",
            options=ROOM_PROFILES,
            value_fn=lambda r: r.profile_name,
        )
    ]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HealthboxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Healthbox selects, adding new ones as rooms appear."""
    async_setup_room_entities(
        entry, async_add_entities, _room_select_descriptions, HealthboxRoomSelect, "select(s)"
    )


class HealthboxRoomSelect(HealthboxRoomEntity, SelectEntity):
    """A select describing one Healthbox room's settable field."""

    entity_description: HealthboxRoomSelectEntityDescription

    def __init__(
        self,
        coordinator: HealthboxDataUpdateCoordinator,
        description: HealthboxRoomSelectEntityDescription,
        room: Healthbox3Room,
    ) -> None:
        """Initialize the select."""
        SelectEntity.__init__(self)
        HealthboxRoomEntity.__init__(self, coordinator, description, room)

    @property
    def current_option(self) -> str | None:
        """Return the room's current profile."""
        return self._safe_value()

    async def async_select_option(self, option: str) -> None:
        """Change the room's profile."""
        await self.coordinator.change_room_profile(room_id=self._room_id, profile_name=option)
