"""Regression tests for the config/options flow bugs found in the original.

The original OptionsFlowHandler wrote the new API key to entry.data BEFORE
validating it, swallowed the auth exception, and always returned success -
an invalid key was silently accepted. These tests pin the fixed behaviour.
"""
from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.healthbox.const import CONF_SCAN_INTERVAL, DOMAIN
from pyhealthbox3.healthbox3 import Healthbox3ApiClientAuthenticationError


async def test_user_flow_rejects_invalid_api_key(hass):
    """An auth failure during setup must show an error, not create an entry."""
    with patch(
        "custom_components.healthbox.config_flow.Healthbox3.async_enable_advanced_api_features",
        new=AsyncMock(side_effect=Healthbox3ApiClientAuthenticationError),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_HOST: "1.2.3.4", CONF_API_KEY: "bad-key"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "auth"}
    assert not hass.config_entries.async_entries(DOMAIN)


async def test_options_flow_rejects_invalid_api_key_without_saving(hass):
    """Options flow must validate before writing entry.data, and show an error.

    This is the concrete original bug: it used to `async_update_entry`
    first, swallow the auth exception, and unconditionally return success.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "1.2.3.4", CONF_API_KEY: "good-key"},
        options={CONF_SCAN_INTERVAL: 30},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.healthbox.config_flow.Healthbox3.async_enable_advanced_api_features",
        new=AsyncMock(side_effect=Healthbox3ApiClientAuthenticationError),
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_API_KEY: "bad-key", CONF_SCAN_INTERVAL: 30},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "auth"}
    # entry.data must be untouched - the bad key was never written.
    assert entry.data[CONF_API_KEY] == "good-key"


async def test_options_flow_saves_scan_interval_on_success(hass):
    """A valid options submission updates data and options as designed."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "1.2.3.4", CONF_API_KEY: "good-key"},
        options={CONF_SCAN_INTERVAL: 30},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.healthbox.config_flow.Healthbox3.async_enable_advanced_api_features",
        new=AsyncMock(),
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_API_KEY: "good-key", CONF_SCAN_INTERVAL: 60},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_API_KEY] == "good-key"
    assert entry.options[CONF_SCAN_INTERVAL] == 60
