from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_USE_SSL,
    CONF_TOKEN,
    CONF_VERIFY_SSL,
    CONF_LISTENER_PORT,
    CONF_TLS_ENABLED,
    CONF_SSL_CERT,
    CONF_SSL_KEY,
    DEFAULT_PORT,
    DEFAULT_LISTENER_PORT,
    DEFAULT_USE_SSL,
    CONF_MAPPING_RPM,
    CONF_MAPPING_FUEL,
    CONF_MAPPING_OIL,
    CONF_MAPPING_DTC,
    CONF_MAPPING_DOOR_FL,
    CONF_MAPPING_DOOR_FR,
    CONF_MAPPING_DOOR_RL,
    CONF_MAPPING_DOOR_RR,
    CONF_MAPPING_LOCKED,
    CONF_MAPPING_WINDOWS,
    CONF_MAPPING_HANDBRAKE,
    CONF_MAPPING_LIGHTS,
    DEFAULT_MAPPINGS,
)
from .api import TraccarClient, TraccarApiError

from homeassistant.helpers import selector

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
        vol.Separator(),
        vol.Required("enable_direct_listener", default=False): bool,
        vol.Optional(CONF_LISTENER_PORT, default=DEFAULT_LISTENER_PORT): int,
        vol.Optional(CONF_TLS_ENABLED, default=False): bool,
        vol.Optional(CONF_SSL_CERT): str,
        vol.Optional(CONF_SSL_KEY): str,
    }
)

def OPTIONS_SCHEMA(options: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(CONF_MAPPING_RPM, default=options.get(CONF_MAPPING_RPM, DEFAULT_MAPPINGS[CONF_MAPPING_RPM])): str,
            vol.Optional(CONF_MAPPING_FUEL, default=options.get(CONF_MAPPING_FUEL, DEFAULT_MAPPINGS[CONF_MAPPING_FUEL])): str,
            vol.Optional(CONF_MAPPING_OIL, default=options.get(CONF_MAPPING_OIL, DEFAULT_MAPPINGS[CONF_MAPPING_OIL])): str,
            vol.Optional(CONF_MAPPING_DTC, default=options.get(CONF_MAPPING_DTC, DEFAULT_MAPPINGS[CONF_MAPPING_DTC])): str,
            vol.Optional(CONF_MAPPING_DOOR_FL, default=options.get(CONF_MAPPING_DOOR_FL, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_FL])): str,
            vol.Optional(CONF_MAPPING_DOOR_FR, default=options.get(CONF_MAPPING_DOOR_FR, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_FR])): str,
            vol.Optional(CONF_MAPPING_DOOR_RL, default=options.get(CONF_MAPPING_DOOR_RL, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_RL])): str,
            vol.Optional(CONF_MAPPING_DOOR_RR, default=options.get(CONF_MAPPING_DOOR_RR, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_RR])): str,
            vol.Optional(CONF_MAPPING_LOCKED, default=options.get(CONF_MAPPING_LOCKED, DEFAULT_MAPPINGS[CONF_MAPPING_LOCKED])): str,
            vol.Optional(CONF_MAPPING_WINDOWS, default=options.get(CONF_MAPPING_WINDOWS, DEFAULT_MAPPINGS[CONF_MAPPING_WINDOWS])): str,
            vol.Optional(CONF_MAPPING_HANDBRAKE, default=options.get(CONF_MAPPING_HANDBRAKE, DEFAULT_MAPPINGS[CONF_MAPPING_HANDBRAKE])): str,
            vol.Optional(CONF_MAPPING_LIGHTS, default=options.get(CONF_MAPPING_LIGHTS, DEFAULT_MAPPINGS[CONF_MAPPING_LIGHTS])): str,
        }
    )

class Fmc130TraccarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_TOKEN) and not (user_input.get(CONF_USERNAME) and user_input.get(CONF_PASSWORD)):
                 errors["base"] = "missing_auth"
            
            if not errors:
                from homeassistant.helpers.aiohttp_client import async_get_clientsession
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
                    return self.async_create_entry(title=f"FMC130 {user_input[CONF_HOST]}", data=user_input)
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
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return Fmc130TraccarOptionsFlow(config_entry)


class Fmc130TraccarOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=OPTIONS_SCHEMA(self.config_entry.options),
        )
