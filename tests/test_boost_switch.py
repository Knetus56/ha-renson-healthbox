"""The boost switch reads/writes through the number.py setting entities.

Turning it on must use whatever level/timeout are currently configured
(not just the defaults), and its state must reflect the device's actual
boost.enabled rather than anything we track ourselves - so it naturally
flips back off once the device's own timeout elapses and the next poll
picks that up.
"""
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.healthbox.const import DOMAIN

from .fake_healthbox import FakeHealthbox3Factory, make_room


async def _setup(hass, factory):
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4", "api_key": None})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    room = make_room(1, "Cuisine")
    factory.instances["1.2.3.4"].rooms = [room]
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    return entry, room


async def test_boost_numbers_have_sane_defaults(hass):
    """Fresh install: numbers default to 100% / 60 minutes."""
    factory = FakeHealthbox3Factory()
    with patch("custom_components.healthbox.Healthbox3", side_effect=factory):
        await _setup(hass, factory)

        level = hass.states.get("number.healthbox_cuisine_boost_level")
        timeout = hass.states.get("number.healthbox_cuisine_boost_timeout")
        assert level.state == "100"
        assert timeout.state == "60"


async def test_turning_on_the_switch_uses_the_configured_level_and_timeout(hass):
    """Changing the numbers, then flipping the switch, must use the new values."""
    factory = FakeHealthbox3Factory()
    with patch("custom_components.healthbox.Healthbox3", side_effect=factory):
        entry, room = await _setup(hass, factory)

        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.healthbox_cuisine_boost_level", "value": 150},
            blocking=True,
        )
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.healthbox_cuisine_boost_timeout", "value": 30},
            blocking=True,
        )

        switch_state = hass.states.get("switch.healthbox_cuisine_boost")
        assert switch_state is not None
        assert switch_state.state == "off"

        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.healthbox_cuisine_boost"},
            blocking=True,
        )

    factory.instances["1.2.3.4"].async_start_room_boost.assert_called_once_with(
        room_id=1, boost_level=150, boost_timeout=30 * 60
    )


async def test_switch_reflects_real_device_state(hass):
    """is_on must come from the device's boost.enabled, not our own tracking."""
    factory = FakeHealthbox3Factory()
    with patch("custom_components.healthbox.Healthbox3", side_effect=factory):
        entry, room = await _setup(hass, factory)

        room.boost.enabled = True
        await entry.runtime_data.async_refresh()
        await hass.async_block_till_done()
        assert hass.states.get("switch.healthbox_cuisine_boost").state == "on"

        # Simulate the device's own timeout elapsing between two polls.
        room.boost.enabled = False
        await entry.runtime_data.async_refresh()
        await hass.async_block_till_done()
        assert hass.states.get("switch.healthbox_cuisine_boost").state == "off"

        await hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": "switch.healthbox_cuisine_boost"},
            blocking=True,
        )

    factory.instances["1.2.3.4"].async_stop_room_boost.assert_called_once_with(room_id=1)
