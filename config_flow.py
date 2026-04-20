"""Config flow for FMC130 Traccar Car Control integration.

Generated with ha-integration@aurora-smart-home v1.0.0
https://github.com/tonylofgren/aurora-smart-home
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_TOKEN,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import Fmc130TraccarConfigEntry
from .api import TraccarApiError, TraccarClient
from .const import (
    CONF_MAPPING_DOOR_FL,
    CONF_MAPPING_DOOR_FR,
    CONF_MAPPING_DOOR_RL,
    CONF_MAPPING_DOOR_RR,
    CONF_MAPPING_DTC,
    CONF_MAPPING_FUEL,
    CONF_MAPPING_HANDBRAKE,
    CONF_MAPPING_LIGHTS,
    CONF_MAPPING_LOCKED,
    CONF_MAPPING_OIL,
    CONF_MAPPING_RPM,
    CONF_MAPPING_WINDOWS,
    CONF_USE_SSL,
    CONF_VERIFY_SSL,
    DEFAULT_MAPPINGS,
    DEFAULT_PORT,
    DEFAULT_USE_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_TOKEN): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
        vol.Required(CONF_USE_SSL, default=DEFAULT_USE_SSL): bool,
        vol.Required(CONF_VERIFY_SSL, default=True): bool,
    }
)


def OPTIONS_SCHEMA(options: dict[str, Any]) -> vol.Schema:
    """Return options schema."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_MAPPING_RPM,
                default=options.get(
                    CONF_MAPPING_RPM, DEFAULT_MAPPINGS[CONF_MAPPING_RPM]
                ),
            ): str,
            vol.Optional(
                CONF_MAPPING_FUEL,
                default=options.get(
                    CONF_MAPPING_FUEL, DEFAULT_MAPPINGS[CONF_MAPPING_FUEL]
                ),
            ): str,
            vol.Optional(
                CONF_MAPPING_OIL,
                default=options.get(
                    CONF_MAPPING_OIL, DEFAULT_MAPPINGS[CONF_MAPPING_OIL]
                ),
            ): str,
            vol.Optional(
                CONF_MAPPING_DTC,
                default=options.get(
                    CONF_MAPPING_DTC, DEFAULT_MAPPINGS[CONF_MAPPING_DTC]
                ),
            ): str,
            vol.Optional(
                CONF_MAPPING_DOOR_FL,
                default=options.get(
                    CONF_MAPPING_DOOR_FL, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_FL]
                ),
            ): str,
            vol.Optional(
                CONF_MAPPING_DOOR_FR,
                default=options.get(
                    CONF_MAPPING_DOOR_FR, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_FR]
                ),
            ): str,
            vol.Optional(
                CONF_MAPPING_DOOR_RL,
                default=options.get(
                    CONF_MAPPING_DOOR_RL, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_RL]
                ),
            ): str,
            vol.Optional(
                CONF_MAPPING_DOOR_RR,
                default=options.get(
                    CONF_MAPPING_DOOR_RR, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_RR]
                ),
            ): str,
            vol.Optional(
                CONF_MAPPING_LOCKED,
                default=options.get(
                    CONF_MAPPING_LOCKED, DEFAULT_MAPPINGS[CONF_MAPPING_LOCKED]
                ),
            ): str,
            vol.Optional(
                CONF_MAPPING_WINDOWS,
                default=options.get(
                    CONF_MAPPING_WINDOWS, DEFAULT_MAPPINGS[CONF_MAPPING_WINDOWS]
                ),
            ): str,
            vol.Optional(
                CONF_MAPPING_HANDBRAKE,
                default=options.get(
                    CONF_MAPPING_HANDBRAKE, DEFAULT_MAPPINGS[CONF_MAPPING_HANDBRAKE]
                ),
            ): str,
            vol.Optional(
                CONF_MAPPING_LIGHTS,
                default=options.get(
                    CONF_MAPPING_LIGHTS, DEFAULT_MAPPINGS[CONF_MAPPING_LIGHTS]
                ),
            ): str,
        }
    )


class Fmc130TraccarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FMC130 Traccar Car Control."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}_{user_input[CONF_PORT]}"
            )
            self._abort_if_unique_id_configured()

            if not user_input.get(CONF_TOKEN) and not (
                user_input.get(CONF_USERNAME) and user_input.get(CONF_PASSWORD)
            ):
                errors["base"] = "missing_auth"

            if not errors:
                session = async_get_clientsession(self.hass)
                client = TraccarClient(
                    user_input[CONF_HOST],
                    user_input[CONF_PORT],
                    user_input.get(CONF_USERNAME),
                    user_input.get(CONF_PASSWORD),
                    user_input[CONF_USE_SSL],
                    user_input.get(CONF_TOKEN),
                    session=session,
                    verify_ssl=user_input.get(CONF_VERIFY_SSL, True),
                )
                try:
                    await client.get_devices()
                    return self.async_create_entry(
                        title=f"FMC130 {user_input[CONF_HOST]}", data=user_input
                    )
                except TraccarApiError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected exception")
                    errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: Fmc130TraccarConfigEntry,
    ) -> Fmc130TraccarOptionsFlow:
        """Get the options flow for this handler."""
        return Fmc130TraccarOptionsFlow()


class Fmc130TraccarOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for FMC130 Traccar."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=OPTIONS_SCHEMA(self.config_entry.options),
        )
