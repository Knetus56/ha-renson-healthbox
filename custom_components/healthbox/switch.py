"""Switch platform for the Renson Healthbox integration.

Replaces a plain "boost status" binary sensor: is_on reflects the room's
actual boost state from the device (so it flips back off by itself once
the device's own boost timeout elapses and the next poll picks that up),
and turning it on/off starts/stops the boost - using whatever level and
timeout are currently set in this room's number.py entities.
"""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from pyhealthbox3.models import Healthbox3Room

from .coordinator import HealthboxConfigEntry, HealthboxDataUpdateCoordinator
from .entity import HealthboxRoomDescriptionMixin, HealthboxRoomEntity, async_setup_room_entities


@dataclass(frozen=True, kw_only=True)
class HealthboxRoomSwitchEntityDescription(SwitchEntityDescription, HealthboxRoomDescriptionMixin):
    """Describes a Healthbox room switch."""


def _room_switch_descriptions(room: Healthbox3Room) -> list[HealthboxRoomSwitchEntityDescription]:
    """Build the switch descriptions for one room.

    room.boost always exists on a Healthbox3Room, so the boost switch is
    always created; it just reads back "off" until a real boost is running.
    """
    return [
        HealthboxRoomSwitchEntityDescription(
            key="boost",
            name="Boost",
            icon="mdi:fan-plus",
            value_fn=lambda r: bool(r.boost.enabled),
        ),
    ]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HealthboxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Healthbox switches, adding new ones as rooms appear."""
    async_setup_room_entities(
        entry,
        async_add_entities,
        _room_switch_descriptions,
        HealthboxRoomBoostSwitch,
        "switch(es)",
    )


class HealthboxRoomBoostSwitch(HealthboxRoomEntity, SwitchEntity):
    """A switch to start/stop a room's boost, reflecting its actual state."""

    entity_description: HealthboxRoomSwitchEntityDescription

    def __init__(
        self,
        coordinator: HealthboxDataUpdateCoordinator,
        description: HealthboxRoomSwitchEntityDescription,
        room: Healthbox3Room,
    ) -> None:
        """Initialize the switch."""
        SwitchEntity.__init__(self)
        HealthboxRoomEntity.__init__(self, coordinator, description, room)

    @property
    def is_on(self) -> bool | None:
        """Return true if the boost is currently running on the device."""
        return self._safe_value()

    async def async_turn_on(self, **kwargs) -> None:
        """Start the boost using this room's currently configured level/timeout."""
        settings = self.coordinator.get_boost_settings(self._room_id)
        await self.coordinator.start_room_boost(
            room_id=self._room_id,
            boost_level=round(settings["level"]),
            boost_timeout=round(settings["timeout"]) * 60,
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Stop the boost."""
        await self.coordinator.stop_room_boost(room_id=self._room_id)
