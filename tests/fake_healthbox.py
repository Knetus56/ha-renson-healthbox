"""A fake pyhealthbox3.Healthbox3 for integration tests.

Used instead of patching individual attributes on the real class (which are
shared class-wide and would leak between config entries in a multi-entry
test), and instead of mocking only `async_get_data` (which leaves any other
call - including a coordinator's own periodic refresh outside the test's
immediate `await` - hitting a real socket). Each call to the patched
constructor gets its own independent fake instance with its own data and
already-mocked async methods, so nothing here ever reaches the network.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

from pyhealthbox3.models import Healthbox3FanDataObject, Healthbox3WIFIConnectionDataObject


class FakeHealthbox3:
    """Stand-in for pyhealthbox3.healthbox3.Healthbox3."""

    def __init__(self, host: str, api_key: str | None = None, session=None) -> None:
        self.host = host
        self.api_key = api_key
        self.serial = host.replace(".", "_")
        self.description = "Healthbox 3"
        self.warranty_number = "W"
        self.firmware_version = "1.0"
        self.error_count = 0
        self.global_aqi = 1.0
        self.advanced_api_enabled = bool(api_key)
        self.rooms: list = []
        self.wifi = Healthbox3WIFIConnectionDataObject()
        self.fan = Healthbox3FanDataObject()

        self.async_get_data = AsyncMock(return_value=None)
        self.async_enable_advanced_api_features = AsyncMock(return_value=None)
        self.async_validate_connectivity = AsyncMock(return_value=None)
        self.async_start_room_boost = AsyncMock(return_value=None)
        self.async_stop_room_boost = AsyncMock(return_value=None)
        self.async_change_room_profile = AsyncMock(return_value=None)
        self.close = AsyncMock(return_value=None)


class FakeHealthbox3Factory:
    """Callable that builds one FakeHealthbox3 per host and remembers it."""

    def __init__(self) -> None:
        self.instances: dict[str, FakeHealthbox3] = {}

    def __call__(self, host: str, api_key: str | None = None, session=None) -> FakeHealthbox3:
        fake = FakeHealthbox3(host, api_key, session)
        self.instances[host] = fake
        return fake


def make_room(room_id: int, name: str):
    """Build a bare Healthbox3Room with just enough set to be usable."""
    from pyhealthbox3.models import Healthbox3Room, Healthbox3RoomBoost

    room = object.__new__(Healthbox3Room)
    room.room_id = room_id
    room.name = name
    room.type = "bathroom"
    room.room_type = "bathroom"
    room.enabled_sensors = []
    room._advanced_features = False
    room._parameters = {}
    room._actuator = []
    room._profile = "health"
    room.boost = Healthbox3RoomBoost()
    return room
