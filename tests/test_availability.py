"""Control entities (switch, number, select) must go unavailable, not
crash or keep stale state, when their room disappears from the API - the
same guarantee HealthboxRoomEntity.available already gives sensors.
"""
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.healthbox.const import DOMAIN

from .fake_healthbox import FakeHealthbox3Factory, make_room


async def test_control_entities_go_unavailable_when_room_disappears(hass):
    """A room removed from api.rooms must not leave stale/crashing entities."""
    factory = FakeHealthbox3Factory()
    with patch("custom_components.healthbox.Healthbox3", side_effect=factory):
        entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4", "api_key": None})
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        factory.instances["1.2.3.4"].rooms = [make_room(1, "Cuisine")]
        await entry.runtime_data.async_refresh()
        await hass.async_block_till_done()

        for entity_id in (
            "switch.healthbox_cuisine_boost",
            "number.healthbox_cuisine_boost_level",
            "number.healthbox_cuisine_boost_timeout",
            "select.healthbox_cuisine_profile",
        ):
            state = hass.states.get(entity_id)
            assert state is not None, f"{entity_id} was never created"
            assert state.state != "unavailable", f"{entity_id} should be available"

        # The room is gone (e.g. reconfigured on the device, or a transient
        # API hiccup) - the next poll no longer reports it at all.
        factory.instances["1.2.3.4"].rooms = []
        await entry.runtime_data.async_refresh()
        await hass.async_block_till_done()

        for entity_id in (
            "switch.healthbox_cuisine_boost",
            "number.healthbox_cuisine_boost_level",
            "number.healthbox_cuisine_boost_timeout",
            "select.healthbox_cuisine_profile",
        ):
            assert hass.states.get(entity_id).state == "unavailable", entity_id
