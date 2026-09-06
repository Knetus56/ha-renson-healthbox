"""Sensor platform for the Renson Healthbox integration."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from pyhealthbox3.healthbox3 import Healthbox3
from pyhealthbox3.models import Healthbox3Room

from .const import LOGGER
from .coordinator import HealthboxConfigEntry, HealthboxDataUpdateCoordinator
from .entity import (
    HealthboxHubDescriptionMixin,
    HealthboxHubEntity,
    HealthboxRoomDescriptionMixin,
    HealthboxRoomEntity,
    room_field,
)

try:
    # HA 2026.7+: CONCENTRATION_PARTS_PER_MILLION is deprecated (removed in
    # 2027.8) in favour of the unit-less UnitOfRatio enum.
    from homeassistant.const import UnitOfRatio

    _PARTS_PER_MILLION = UnitOfRatio.PARTS_PER_MILLION
except ImportError:  # HA < 2026.7
    from homeassistant.const import CONCENTRATION_PARTS_PER_MILLION as _PARTS_PER_MILLION


@dataclass(frozen=True, kw_only=True)
class HealthboxHubEntityDescription(SensorEntityDescription, HealthboxHubDescriptionMixin):
    """Describes a Healthbox hub-level sensor."""


@dataclass(frozen=True, kw_only=True)
class HealthboxRoomEntityDescription(SensorEntityDescription, HealthboxRoomDescriptionMixin):
    """Describes a Healthbox room sensor."""


def _hub_sensor_descriptions(api: Healthbox3) -> list[HealthboxHubEntityDescription]:
    """Build the hub-level sensor descriptions currently supported by `api`.

    Called on every coordinator refresh so a value that only starts being
    reported later (e.g. WiFi SSID after a reconnect) gets its entity added
    without requiring a reload, instead of only being considered at startup.
    """
    descriptions = [
        HealthboxHubEntityDescription(
            key="global_aqi",
            name="Global Air Quality Index",
            device_class=SensorDeviceClass.AQI,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=0,
            value_fn=lambda x: x.global_aqi,
        ),
        HealthboxHubEntityDescription(
            key="error_count",
            name="Error Count",
            icon="mdi:alert-outline",
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            suggested_display_precision=0,
            value_fn=lambda x: x.error_count,
        ),
    ]

    if api.wifi.status is not None:
        descriptions.append(
            HealthboxHubEntityDescription(
                key="wifi_status",
                name="WiFi Status",
                icon="mdi:wifi",
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda x: x.wifi.status,
            )
        )
    if api.wifi.internet_connection is not None:
        descriptions.append(
            HealthboxHubEntityDescription(
                key="wifi_internet_connection",
                name="WiFi Internet Connection",
                icon="mdi:web",
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda x: x.wifi.internet_connection,
            )
        )
    if api.wifi.ssid is not None:
        descriptions.append(
            HealthboxHubEntityDescription(
                key="wifi_ssid",
                name="WiFi SSID",
                icon="mdi:wifi-settings",
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda x: x.wifi.ssid,
            )
        )
    if api.fan.voltage is not None:
        descriptions.append(
            HealthboxHubEntityDescription(
                key="fan_voltage",
                name="Fan Voltage",
                icon="mdi:sine-wave",
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                device_class=SensorDeviceClass.VOLTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=0,
                value_fn=lambda x: x.fan.voltage,
            )
        )
    if api.fan.pressure is not None:
        descriptions.append(
            HealthboxHubEntityDescription(
                key="fan_pressure",
                name="Fan Pressure",
                icon="mdi:arrow-collapse-vertical",
                native_unit_of_measurement=UnitOfPressure.PA,
                device_class=SensorDeviceClass.PRESSURE,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=0,
                value_fn=lambda x: x.fan.pressure,
            )
        )
    if api.fan.flow is not None:
        descriptions.append(
            HealthboxHubEntityDescription(
                key="fan_flow",
                name="Fan Flow",
                icon="mdi:wind-power",
                native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
                device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=0,
                value_fn=lambda x: x.fan.flow,
            )
        )
    if api.fan.power is not None:
        descriptions.append(
            HealthboxHubEntityDescription(
                key="fan_power",
                name="Fan Power",
                icon="mdi:flash",
                native_unit_of_measurement=UnitOfPower.WATT,
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=0,
                value_fn=lambda x: x.fan.power,
            )
        )
    if api.fan.rpm is not None:
        descriptions.append(
            HealthboxHubEntityDescription(
                key="fan_rpm",
                name="Fan RPM",
                icon="mdi:fan",
                native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=0,
                value_fn=lambda x: x.fan.rpm,
            )
        )

    return descriptions


def _room_sensor_descriptions(room: Healthbox3Room) -> list[HealthboxRoomEntityDescription]:
    """Build the sensor descriptions currently supported by one room.

    Only the sensor modules actually installed in a given room show up here
    (e.g. one room may report CO2, another VOC, another neither) — called
    every refresh so a module that starts reporting later still gets added.
    """
    descriptions: list[HealthboxRoomEntityDescription] = []

    if room_field(room, lambda r: r.indoor_temperature) is not None:
        descriptions.append(
            HealthboxRoomEntityDescription(
                key="temperature",
                name="Temperature",
                native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                device_class=SensorDeviceClass.TEMPERATURE,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=1,
                value_fn=lambda r: r.indoor_temperature,
            )
        )
    if room_field(room, lambda r: r.indoor_humidity) is not None:
        descriptions.append(
            HealthboxRoomEntityDescription(
                key="humidity",
                name="Humidity",
                native_unit_of_measurement=PERCENTAGE,
                device_class=SensorDeviceClass.HUMIDITY,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=0,
                value_fn=lambda r: r.indoor_humidity,
            )
        )
    if room_field(room, lambda r: r.indoor_co2_concentration) is not None:
        descriptions.append(
            HealthboxRoomEntityDescription(
                key="co2_concentration",
                name="CO2 Concentration",
                icon="mdi:molecule-co2",
                native_unit_of_measurement=_PARTS_PER_MILLION,
                device_class=SensorDeviceClass.CO2,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=0,
                value_fn=lambda r: r.indoor_co2_concentration,
            )
        )
    if room_field(room, lambda r: r.indoor_voc_ppm) is not None:
        descriptions.append(
            HealthboxRoomEntityDescription(
                key="volatile_organic_compounds",
                name="Volatile Organic Compounds",
                native_unit_of_measurement=_PARTS_PER_MILLION,
                device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=0,
                value_fn=lambda r: r.indoor_voc_ppm,
            )
        )
    if room_field(room, lambda r: r.indoor_aqi) is not None:
        descriptions.append(
            HealthboxRoomEntityDescription(
                key="air_quality_index",
                name="Air Quality Index",
                device_class=SensorDeviceClass.AQI,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=0,
                value_fn=lambda r: r.indoor_aqi,
            )
        )
    if room_field(room, lambda r: r.airflow_ventilation_rate) is not None:
        descriptions.append(
            HealthboxRoomEntityDescription(
                key="airflow_ventilation_rate",
                name="Airflow Ventilation Rate",
                icon="mdi:fan",
                native_unit_of_measurement=PERCENTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=0,
                value_fn=lambda r: (
                    r.airflow_ventilation_rate * 100
                    if r.airflow_ventilation_rate is not None
                    else None
                ),
            )
        )
    # Room profile (Eco/Health/Intense) is a select.py entity, not a
    # read-only sensor - it's both readable and settable.

    # room.boost always exists on a Healthbox3Room (the library defaults it
    # rather than leaving it None), so these are always created; individual
    # fields simply read back None until a real boost value is available.
    descriptions.append(
        HealthboxRoomEntityDescription(
            key="boost_level",
            name="Boost Level",
            icon="mdi:fan",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=0,
            value_fn=lambda r: r.boost.level,
        )
    )
    descriptions.append(
        HealthboxRoomEntityDescription(
            key="boost_remaining",
            name="Boost Remaining",
            icon="mdi:clock-time-five-outline",
            native_unit_of_measurement=UnitOfTime.SECONDS,
            device_class=SensorDeviceClass.DURATION,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=0,
            value_fn=lambda r: r.boost.remaining,
        )
    )

    return descriptions


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HealthboxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Healthbox sensors, and keep adding new ones as they appear."""
    coordinator = entry.runtime_data
    known_hub_keys: set[str] = set()
    known_room_keys: dict[int, set[str]] = {}

    @callback
    def _add_new_entities() -> None:
        new_entities: list[SensorEntity] = []

        for description in _hub_sensor_descriptions(coordinator.api):
            if description.key not in known_hub_keys:
                known_hub_keys.add(description.key)
                new_entities.append(HealthboxHubSensor(coordinator, description))

        for room in coordinator.api.rooms:
            seen = known_room_keys.setdefault(room.room_id, set())
            for description in _room_sensor_descriptions(room):
                if description.key not in seen:
                    seen.add(description.key)
                    new_entities.append(HealthboxRoomSensor(coordinator, description, room))

        if new_entities:
            LOGGER.debug(
                "Adding %s new Healthbox sensor(s): %s",
                len(new_entities),
                [e.entity_description.key for e in new_entities],
            )
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class HealthboxHubSensor(HealthboxHubEntity, SensorEntity):
    """A sensor describing the Healthbox device itself."""

    entity_description: HealthboxHubEntityDescription

    def __init__(
        self,
        coordinator: HealthboxDataUpdateCoordinator,
        description: HealthboxHubEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        SensorEntity.__init__(self)
        HealthboxHubEntity.__init__(self, coordinator, description)

    @property
    def native_value(self):
        """Return the current value."""
        return self._safe_value()


class HealthboxRoomSensor(HealthboxRoomEntity, SensorEntity):
    """A sensor describing one Healthbox room."""

    entity_description: HealthboxRoomEntityDescription

    def __init__(
        self,
        coordinator: HealthboxDataUpdateCoordinator,
        description: HealthboxRoomEntityDescription,
        room: Healthbox3Room,
    ) -> None:
        """Initialize the sensor."""
        SensorEntity.__init__(self)
        HealthboxRoomEntity.__init__(self, coordinator, description, room)

    @property
    def native_value(self):
        """Return the current value."""
        return self._safe_value()
