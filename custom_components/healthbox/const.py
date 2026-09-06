"""Constants for the Renson Healthbox integration."""
from __future__ import annotations

from datetime import timedelta
from logging import Logger, getLogger

from homeassistant.const import Platform

LOGGER: Logger = getLogger(__package__)

DOMAIN = "healthbox"
NAME = "Renson Healthbox"
MANUFACTURER = "Renson"
MODEL_ROOM = "Healthbox Room"

PLATFORMS = [Platform.SENSOR, Platform.SELECT, Platform.NUMBER, Platform.SWITCH]

# Config entry keys.
# CONF_HOST / CONF_API_KEY live in entry.data (connection identity).
# CONF_SCAN_INTERVAL lives in entry.options (polling behaviour, user-tunable).
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 3600

# Services are registered once for the whole integration (see __init__.py),
# never per config entry, so unloading one Healthbox does not remove the
# services for every other configured Healthbox.
SERVICE_START_ROOM_BOOST = "start_room_boost"
SERVICE_STOP_ROOM_BOOST = "stop_room_boost"
SERVICE_CHANGE_ROOM_PROFILE = "change_room_profile"

ATTR_BOOST_LEVEL = "boost_level"
ATTR_BOOST_TIMEOUT = "boost_timeout"
ATTR_PROFILE_NAME = "profile_name"

ROOM_PROFILES = ["Eco", "Health", "Intense"]

# Boost level (%) and timeout (minutes) ranges, shared between the
# start_room_boost service schema and the number.py entities that hold the
# level/timeout to use the next time a room's boost switch is turned on.
MIN_BOOST_LEVEL = 10
MAX_BOOST_LEVEL = 200
DEFAULT_BOOST_LEVEL = 100
MIN_BOOST_TIMEOUT = 5
MAX_BOOST_TIMEOUT = 720
DEFAULT_BOOST_TIMEOUT = 60

# Device identifiers: the hub device is (DOMAIN, entry.entry_id); a room
# device is (DOMAIN, f"{entry.entry_id}{ROOM_IDENTIFIER_SEP}{room_id}").
# This lets a service call resolve a target device back to its room without
# guessing from a display name.
ROOM_IDENTIFIER_SEP = "_room_"
