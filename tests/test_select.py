"""The room profile is a select entity (readable + settable), not a
read-only sensor plus a service-only action."""
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.healthbox.const import DOMAIN

from .fake_healthbox import FakeHealthbox3Factory, make_room


async def test_profile_select_reads_and_sets_the_room_profile(hass):
    """The select shows the current profile and can change it."""
    factory = FakeHealthbox3Factory()

    with patch("custom_components.healthbox.Healthbox3", side_effect=factory):
        entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4", "api_key": None})
        entry.add_to_hass(hass)

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        factory.instances["1.2.3.4"].rooms = [make_room(1, "Cuisine")]
        await entry.runtime_data.async_request_refresh()
        await hass.async_block_till_done()

        state = hass.states.get("select.healthbox_cuisine_profile")
        assert state is not None
        assert state.state == "Health"
        assert state.attributes["options"] == ["Eco", "Health", "Intense"]
        # No read-only duplicate left behind.
        assert hass.states.get("sensor.healthbox_cuisine_profile") is None

        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": "select.healthbox_cuisine_profile", "option": "Intense"},
            blocking=True,
        )

    factory.instances["1.2.3.4"].async_change_room_profile.assert_called_once_with(
        room_id=1, profile_name="Intense"
    )
