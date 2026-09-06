"""Base entities shared by the Healthbox sensor and binary_sensor platforms."""
from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from pyhealthbox3.healthbox3 import Healthbox3
from pyhealthbox3.models import Healthbox3Room

from .const import DOMAIN, LOGGER, MANUFACTURER, MODEL_ROOM, ROOM_IDENTIFIER_SEP
from .coordinator import HealthboxConfigEntry, HealthboxDataUpdateCoordinator

# via_device_id (an actual device registry id) replaces the older via_device
# (a domain, identifier tuple HA had to resolve itself) - but older cores'
# DeviceRegistry.async_get_or_create() raises TypeError on the unknown
# kwarg rather than ignoring it, so detect support instead of assuming it.
_SUPPORTS_VIA_DEVICE_ID = "via_device_id" in inspect.signature(
    dr.DeviceRegistry.async_get_or_create
).parameters


@dataclass(frozen=True, kw_only=True)
class HealthboxHubDescriptionMixin:
    """Mixin for descriptions of a sensor attached to the Healthbox device itself.

    Each platform (sensor, binary_sensor) combines this with its own
    `*EntityDescription` base class, since those carry different,
    platform-specific fields (device_class, state_class, ...).
    """

    value_fn: Callable[[Any], Any]


@dataclass(frozen=True, kw_only=True)
class HealthboxRoomDescriptionMixin:
    """Mixin for descriptions of a sensor attached to one Healthbox room."""

    value_fn: Callable[[Healthbox3Room], Any]


def room_field(room: Healthbox3Room, getter: Callable[[Healthbox3Room], Any]) -> Any:
    """Read a possibly-raising room property, treating errors as "not yet available".

    Shared by sensor.py, binary_sensor.py and select.py's description
    generators to decide whether a given sensor module is currently
    present on a room (pyhealthbox3 properties can raise instead of
    returning None, e.g. a profile name that is briefly missing upstream).
    """
    try:
        return getter(room)
    except (AttributeError, TypeError, KeyError, IndexError):
        return None


def room_device_identifier(config_entry_id: str, room_id: int) -> tuple[str, str]:
    """Build the device_registry identifier for a room device.

    Kept as a single helper so __init__.py's service handlers and the
    entity platforms always agree on the format (and so it can be parsed
    back into a room_id for the boost/profile services).
    """
    return (DOMAIN, f"{config_entry_id}{ROOM_IDENTIFIER_SEP}{room_id}")


def room_id_from_identifier(identifier: tuple[str, str]) -> int | None:
    """Extract a room_id from a device identifier, or None if it's not one."""
    domain, value = identifier
    if domain != DOMAIN or ROOM_IDENTIFIER_SEP not in value:
        return None
    try:
        return int(value.rsplit(ROOM_IDENTIFIER_SEP, 1)[-1])
    except ValueError:
        return None


class HealthboxHubEntity(CoordinatorEntity[HealthboxDataUpdateCoordinator]):
    """Base entity for sensors describing the Healthbox device itself."""

    _attr_has_entity_name = True
    entity_description: HealthboxHubDescriptionMixin

    def __init__(
        self,
        coordinator: HealthboxDataUpdateCoordinator,
        description: HealthboxHubDescriptionMixin,
    ) -> None:
        """Initialize the hub entity."""
        super().__init__(coordinator)
        self.entity_description = description
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=f"Healthbox {coordinator.api.serial}",
            manufacturer=MANUFACTURER,
            model=coordinator.api.description,
            hw_version=coordinator.api.warranty_number,
            sw_version=coordinator.api.firmware_version,
        )

    def _safe_value(self) -> Any:
        """Evaluate value_fn, tolerating a device that momentarily has no data.

        pyhealthbox3's own model properties can raise (e.g. a profile name
        that is briefly None upstream) instead of always returning None, and
        a value_fn can do arithmetic on a field that just went missing. Treat
        either as "temporarily unavailable" rather than crashing the update.
        """
        try:
            return self.entity_description.value_fn(self.coordinator.api)
        except (AttributeError, TypeError, KeyError, IndexError) as err:
            self.coordinator.logger.debug(
                "Healthbox entity %s could not read a value this cycle: %s",
                self.entity_id,
                err,
            )
            return None


class HealthboxRoomEntity(CoordinatorEntity[HealthboxDataUpdateCoordinator]):
    """Base entity for sensors describing a single Healthbox room."""

    _attr_has_entity_name = True
    entity_description: HealthboxRoomDescriptionMixin

    def __init__(
        self,
        coordinator: HealthboxDataUpdateCoordinator,
        description: HealthboxRoomDescriptionMixin,
        room: Healthbox3Room,
    ) -> None:
        """Initialize the room entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._room_id = room.room_id
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_room_{room.room_id}_{description.key}"
        via = (
            {"via_device_id": coordinator.hub_device_id}
            if _SUPPORTS_VIA_DEVICE_ID
            else {"via_device": (DOMAIN, entry_id)}
        )
        self._attr_device_info = DeviceInfo(
            identifiers={room_device_identifier(entry_id, room.room_id)},
            name=f"Healthbox {room.name}",
            manufacturer=MANUFACTURER,
            model=MODEL_ROOM,
            **via,
        )

    @property
    def _room(self) -> Healthbox3Room | None:
        """Look up this entity's room in the latest coordinator data.

        Rooms are re-fetched (not mutated in place) on every poll, so the
        object from __init__ goes stale; always look the current one up by
        id (via the coordinator's rooms_by_id, rebuilt once per poll)
        instead of caching a reference to it.
        """
        return self.coordinator.rooms_by_id.get(self._room_id)

    @property
    def available(self) -> bool:
        """Room devices can disappear from the API without an entry reload."""
        return super().available and self._room is not None

    def _safe_value(self) -> Any:
        """Evaluate value_fn for the current room, tolerating missing data.

        See HealthboxHubEntity._safe_value for why this is needed: a
        value_fn can raise on a field that just went missing upstream.
        """
        room = self._room
        if room is None:
            return None
        try:
            return self.entity_description.value_fn(room)
        except (AttributeError, TypeError, KeyError, IndexError) as err:
            self.coordinator.logger.debug(
                "Healthbox entity %s could not read a value this cycle: %s",
                self.entity_id,
                err,
            )
            return None


def async_setup_hub_entities(
    entry: HealthboxConfigEntry,
    async_add_entities: AddEntitiesCallback,
    description_fn: Callable[[Healthbox3], list[EntityDescription]],
    entity_cls: type[HealthboxHubEntity],
    label: str,
) -> None:
    """Wire up dynamic discovery for a platform's hub-level entities.

    Shared by every platform with hub entities (currently just sensor.py):
    calls `description_fn(coordinator.api)` on setup and on every
    coordinator refresh, creating `entity_cls(coordinator, description)`
    for any key not seen before. Never removes entities for a key that
    stops appearing - see HealthboxRoomEntity.available for why that's the
    room-level equivalent's approach too.
    """
    coordinator = entry.runtime_data
    known_keys: set[str] = set()

    @callback
    def _add_new_entities() -> None:
        new_entities = []
        for description in description_fn(coordinator.api):
            if description.key not in known_keys:
                known_keys.add(description.key)
                new_entities.append(entity_cls(coordinator, description))

        if new_entities:
            LOGGER.debug(
                "Adding %s new Healthbox %s: %s",
                len(new_entities),
                label,
                [e.entity_description.key for e in new_entities],
            )
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


def async_setup_room_entities(
    entry: HealthboxConfigEntry,
    async_add_entities: AddEntitiesCallback,
    description_fn: Callable[[Healthbox3Room], list[EntityDescription]],
    entity_cls: type[HealthboxRoomEntity],
    label: str,
) -> None:
    """Wire up dynamic discovery for a platform's per-room entities.

    Shared by sensor.py, select.py, switch.py and number.py: calls
    `description_fn(room)` for every room on setup and on every coordinator
    refresh, creating `entity_cls(coordinator, description, room)` for any
    (room, key) pair not seen before. A description_fn that always returns
    the same fixed list (e.g. number.py's two boost settings) works too -
    it just means every key is "discovered" the first time its room is.
    """
    coordinator = entry.runtime_data
    known_keys: dict[int, set[str]] = {}

    @callback
    def _add_new_entities() -> None:
        new_entities = []
        for room in coordinator.api.rooms:
            seen = known_keys.setdefault(room.room_id, set())
            for description in description_fn(room):
                if description.key not in seen:
                    seen.add(description.key)
                    new_entities.append(entity_cls(coordinator, description, room))

        if new_entities:
            LOGGER.debug(
                "Adding %s new Healthbox %s: %s",
                len(new_entities),
                label,
                [e.entity_description.key for e in new_entities],
            )
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))
