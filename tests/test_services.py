"""Regression test for the original multi-entry services bug.

The original registered start_room_boost/stop_room_boost/change_room_profile
in async_setup_entry and removed them ALL in async_unload_entry - so
unloading one Healthbox deleted the services for every other Healthbox
still configured. Services are now registered once in async_setup and
resolve their target device to the right entry, so this must not happen.
"""
from unittest.mock import patch

from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.healthbox.const import DOMAIN

from .fake_healthbox import FakeHealthbox3Factory, make_room


async def test_unloading_one_entry_keeps_services_for_the_other(hass):
    """Unloading Healthbox A must not remove the services Healthbox B relies on."""
    factory = FakeHealthbox3Factory()

    with patch("custom_components.healthbox.Healthbox3", side_effect=factory):
        entry_a = MockConfigEntry(
            domain=DOMAIN, entry_id="entry_a", data={"host": "1.1.1.1", "api_key": None}
        )
        entry_a.add_to_hass(hass)
        entry_b = MockConfigEntry(
            domain=DOMAIN, entry_id="entry_b", data={"host": "2.2.2.2", "api_key": None}
        )
        entry_b.add_to_hass(hass)

        # The very first async_setup() call for the domain bootstraps the
        # "healthbox" component, which loads every config entry already
        # registered for it - both entry_a and entry_b end up loaded here,
        # matching how Home Assistant actually starts up multiple entries.
        assert await hass.config_entries.async_setup(entry_a.entry_id)
        await hass.async_block_till_done()
        assert entry_b.state.value == "loaded"

        factory.instances["1.1.1.1"].rooms = [make_room(1, "Cuisine")]
        await entry_a.runtime_data.async_request_refresh()
        factory.instances["2.2.2.2"].rooms = [make_room(1, "SDB")]
        await entry_b.runtime_data.async_request_refresh()
        await hass.async_block_till_done()

        assert hass.services.has_service(DOMAIN, "start_room_boost")

        await hass.config_entries.async_unload(entry_a.entry_id)
        await hass.async_block_till_done()

        assert hass.services.has_service(
            DOMAIN, "start_room_boost"
        ), "Unloading one Healthbox must not remove services for the other"

        device = next(
            d
            for d in dr.async_get(hass).devices.values()
            if entry_b.entry_id in d.config_entries and "SDB" in (d.name or "")
        )

        await hass.services.async_call(
            DOMAIN,
            "start_room_boost",
            {"device_id": device.id, "boost_level": 100, "boost_timeout": 30},
            blocking=True,
        )

    factory.instances["2.2.2.2"].async_start_room_boost.assert_called_once_with(
        room_id=1, boost_level=100, boost_timeout=1800
    )
    # The unloaded entry's fake was never touched by the service call.
    factory.instances["1.1.1.1"].async_start_room_boost.assert_not_called()
