"""Config flow for the Renson Healthbox integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from pyhealthbox3.healthbox3 import (
    Healthbox3,
    Healthbox3ApiClientAuthenticationError,
    Healthbox3ApiClientCommunicationError,
    Healthbox3ApiClientError,
)

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)


async def _validate_connection(hass: HomeAssistant, host: str, api_key: str | None) -> None:
    """Validate that we can talk to a Healthbox at `host`.

    Uses HA's shared client session (never one we create and forget to
    close) and raises one of the pyhealthbox3 client errors on failure.
    """
    client = Healthbox3(host=host, api_key=api_key, session=async_get_clientsession(hass))
    if api_key:
        await client.async_enable_advanced_api_features()
    else:
        await client.async_validate_connectivity()


class HealthboxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Renson Healthbox."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry) -> OptionsFlow:
        """Create the options flow."""
        return HealthboxOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            api_key = user_input.get(CONF_API_KEY) or None
            LOGGER.debug(
                "Validating user-submitted Healthbox at %s (api_key %s)",
                host,
                "provided" if api_key else "not provided",
            )
            try:
                await _validate_connection(self.hass, host, api_key)
            except Healthbox3ApiClientAuthenticationError as exception:
                LOGGER.warning("Healthbox authentication failed: %s", exception)
                errors["base"] = "auth"
            except Healthbox3ApiClientCommunicationError as exception:
                LOGGER.warning("Could not reach Healthbox at %s: %s", host, exception)
                errors["base"] = "connection"
            except Healthbox3ApiClientError as exception:
                LOGGER.exception("Unexpected error validating Healthbox: %s", exception)
                errors["base"] = "unknown"
            else:
                LOGGER.debug("Healthbox at %s validated OK, creating entry", host)
                await self.async_set_unique_id(f"{DOMAIN}_{host}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=host,
                    data={CONF_HOST: host, CONF_API_KEY: api_key},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default=(user_input or {}).get(CONF_HOST)
                    ): selector.TextSelector(),
                    vol.Optional(CONF_API_KEY): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD),
                    ),
                }
            ),
            errors=errors,
        )


class HealthboxOptionsFlowHandler(OptionsFlow):
    """Options flow for a Healthbox config entry.

    `entry.data` stays the single source of truth for connection identity
    (host, api_key); `entry.options` only ever holds behaviour tuning
    (scan_interval). Neither is ever written before the new values have
    actually been validated against the device.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        current_data = self.config_entry.data
        current_options = self.config_entry.options

        if user_input is not None:
            api_key = user_input.get(CONF_API_KEY) or None
            scan_interval = user_input[CONF_SCAN_INTERVAL]
            LOGGER.debug(
                "Validating updated options for %s (scan_interval=%s)",
                current_data[CONF_HOST],
                scan_interval,
            )
            try:
                await _validate_connection(self.hass, current_data[CONF_HOST], api_key)
            except Healthbox3ApiClientAuthenticationError as exception:
                LOGGER.warning("Healthbox authentication failed: %s", exception)
                errors["base"] = "auth"
            except Healthbox3ApiClientCommunicationError as exception:
                LOGGER.warning("Could not reach Healthbox: %s", exception)
                errors["base"] = "connection"
            except Healthbox3ApiClientError as exception:
                LOGGER.exception("Unexpected error validating Healthbox: %s", exception)
                errors["base"] = "unknown"
            else:
                LOGGER.debug("Options for %s validated OK, saving", current_data[CONF_HOST])
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**current_data, CONF_API_KEY: api_key},
                )
                return self.async_create_entry(
                    title="", data={CONF_SCAN_INTERVAL: scan_interval}
                )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_API_KEY,
                        description={"suggested_value": current_data.get(CONF_API_KEY, "")},
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD),
                    ),
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=current_options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds()
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=5,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    ),
                }
            ),
            errors=errors,
        )
