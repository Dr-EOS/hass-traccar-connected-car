from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_IMEI,
    CONF_DEVICE_NAME,
    CONF_LISTENER_PORT,
    CONF_TLS_MODE,
    CONF_SSL_CERT,
    CONF_SSL_KEY,
    TLS_MODE_NONE,
    TLS_MODE_HA,
    TLS_MODE_CUSTOM,
    DEFAULT_LISTENER_PORT,
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

from homeassistant.helpers import selector

_LOGGER = logging.getLogger(__name__)

USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_NAME): str,
        vol.Required(CONF_IMEI): str,
        vol.Required(CONF_LISTENER_PORT, default=DEFAULT_LISTENER_PORT): int,
        vol.Required(CONF_TLS_MODE, default=TLS_MODE_HA): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value=TLS_MODE_NONE, label="Disabled (Plain TCP)"),
                    selector.SelectOptionDict(value=TLS_MODE_HA, label="Use Home Assistant Certificates"),
                    selector.SelectOptionDict(value=TLS_MODE_CUSTOM, label="Use Custom Certificates"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
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
            # Basic validation
            if not user_input[CONF_IMEI].isdigit() or len(user_input[CONF_IMEI]) < 10:
                errors[CONF_IMEI] = "invalid_imei"
            
            if not errors:
                return self.async_create_entry(
                    title=f"Teltonika {user_input[CONF_DEVICE_NAME]}", 
                    data=user_input
                )

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
