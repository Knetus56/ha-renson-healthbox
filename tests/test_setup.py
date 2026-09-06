"""End-to-end smoke test: does the integration actually set up under real HA?"""
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.healthbox.const import DOMAIN

from .fake_healthbox import FakeHealthbox3Factory


async def test_setup_entry_creates_expected_entities(hass):
    """A config entry should load and create hub entities."""
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4", "api_key": None})
    entry.add_to_hass(hass)

    with patch("custom_components.healthbox.Healthbox3", side_effect=FakeHealthbox3Factory()):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state.value == "loaded"
        assert hass.services.has_service(DOMAIN, "start_room_boost")
        assert hass.services.has_service(DOMAIN, "stop_room_boost")
        assert hass.services.has_service(DOMAIN, "change_room_profile")

        global_aqi = hass.states.get("sensor.healthbox_1_2_3_4_global_air_quality_index")
        assert global_aqi is not None
        assert global_aqi.state == "1.0"

        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
