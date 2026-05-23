from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_IMEI,
    CONF_DEVICE_NAME,
    CONF_LISTENER_PORT,
    CONF_TLS_MODE,
    CONF_SSL_CERT,
    CONF_SSL_KEY,
    CONF_DEBUG_MODE,
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
    CONF_MODIFIER_RPM,
    CONF_MODIFIER_FUEL,
    CONF_MODIFIER_OIL,
    CONF_MODIFIER_DTC,
    CONF_MODIFIER_DOOR_FL,
    CONF_MODIFIER_DOOR_FR,
    CONF_MODIFIER_DOOR_RL,
    CONF_MODIFIER_DOOR_RR,
    CONF_MODIFIER_LOCKED,
    CONF_MODIFIER_WINDOWS,
    CONF_MODIFIER_HANDBRAKE,
    CONF_MODIFIER_LIGHTS,
    DEFAULT_MAPPINGS,
    DEFAULT_MODIFIERS,
)

_LOGGER = logging.getLogger(__name__)

def get_user_data_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the user data schema with optional defaults."""
    if defaults is None:
        defaults = {}
    
    schema = {
        vol.Required(
            CONF_DEVICE_NAME, 
            default=str(defaults.get(CONF_DEVICE_NAME, ""))
        ): selector.TextSelector(),
        vol.Required(
            CONF_IMEI, 
            default=str(defaults.get(CONF_IMEI, ""))
        ): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)),
        vol.Required(
            CONF_LISTENER_PORT, 
            default=defaults.get(CONF_LISTENER_PORT, DEFAULT_LISTENER_PORT)
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=65535, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_TLS_MODE, 
            default=defaults.get(CONF_TLS_MODE, TLS_MODE_HA)
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value=TLS_MODE_NONE, label="Disabled (Plain TCP)"),
                    selector.SelectOptionDict(value=TLS_MODE_HA, label="Use Home Assistant Certificates"),
                    selector.SelectOptionDict(value=TLS_MODE_CUSTOM, label="Use Custom Certificates"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="tls_mode"
            )
        ),
        vol.Optional(
            CONF_SSL_CERT,
            default=defaults.get(CONF_SSL_CERT, "")
        ): selector.TextSelector(),
        vol.Optional(
            CONF_SSL_KEY,
            default=defaults.get(CONF_SSL_KEY, "")
        ): selector.TextSelector(),
        vol.Optional(
            CONF_DEBUG_MODE,
            default=defaults.get(CONF_DEBUG_MODE, False)
        ): selector.BooleanSelector(),
    }

    return vol.Schema(schema)

class Fmc130TraccarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._user_data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            # Basic validation
            if not user_input[CONF_IMEI].isdigit() or len(user_input[CONF_IMEI]) != 15:
                errors[CONF_IMEI] = "invalid_imei"
            
            if not errors:
                self._user_data = user_input
                await self.async_set_unique_id(user_input[CONF_IMEI])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Teltonika {user_input[CONF_DEVICE_NAME]}", 
                    data=self._user_data
                )

        return self.async_show_form(
            step_id="user", data_schema=get_user_data_schema(), errors=errors
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle reconfiguration."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            # Basic validation
            if not user_input[CONF_IMEI].isdigit() or len(user_input[CONF_IMEI]) != 15:
                errors[CONF_IMEI] = "invalid_imei"
            
            if not errors:
                self._user_data = user_input
                if user_input[CONF_IMEI] != entry.unique_id:
                    await self.async_set_unique_id(user_input[CONF_IMEI])
                    self._abort_if_unique_id_configured()
                
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=self._user_data,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=get_user_data_schema(entry.data),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return Fmc130TraccarOptionsFlow()


class Fmc130TraccarOptionsFlow(config_entries.OptionsFlow):
    def __init__(self) -> None:
        """Initialize options flow."""
        self._connection_data: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            if user_input["section"] == "connection":
                return await self.async_step_connection()
            return await self.async_step_mapping()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("section", default="connection"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value="connection", label="Connection Settings"),
                                selector.SelectOptionDict(value="mapping", label="Data Mapping"),
                            ],
                            mode=selector.SelectSelectorMode.LIST,
                            translation_key="section"
                        )
                    )
                }
            ),
        )

    async def async_step_connection(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage connection settings."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # Basic validation
            if not user_input[CONF_IMEI].isdigit() or len(user_input[CONF_IMEI]) != 15:
                errors[CONF_IMEI] = "invalid_imei"
            
            if not errors:
                self._connection_data = user_input
                # Update entry data and unique_id if needed
                updates: dict[str, Any] = {
                    "data": {**self.config_entry.data, **self._connection_data}
                }
                if self._connection_data[CONF_IMEI] != self.config_entry.unique_id:
                    updates["unique_id"] = self._connection_data[CONF_IMEI]
                
                self.hass.config_entries.async_update_entry(
                    self.config_entry, **updates
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="connection",
            data_schema=get_user_data_schema(self.config_entry.data),
            errors=errors,
        )

    async def async_step_mapping(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage data mapping."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="mapping",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_MAPPING_RPM,
                        default=str(options.get(CONF_MAPPING_RPM, DEFAULT_MAPPINGS[CONF_MAPPING_RPM])),
                    ): selector.TextSelector(),
                    vol.Optional(
                        CONF_MODIFIER_RPM,
                        default=str(options.get(CONF_MODIFIER_RPM, DEFAULT_MODIFIERS[CONF_MODIFIER_RPM])),
                    ): selector.TextSelector(),
                    
                    vol.Optional(
                        CONF_MAPPING_FUEL,
                        default=str(options.get(CONF_MAPPING_FUEL, DEFAULT_MAPPINGS[CONF_MAPPING_FUEL])),
                    ): selector.TextSelector(),
                    vol.Optional(
                        CONF_MODIFIER_FUEL,
                        default=str(options.get(CONF_MODIFIER_FUEL, DEFAULT_MODIFIERS[CONF_MODIFIER_FUEL])),
                    ): selector.TextSelector(),
                    
                    vol.Optional(
                        CONF_MAPPING_OIL,
                        default=str(options.get(CONF_MAPPING_OIL, DEFAULT_MAPPINGS[CONF_MAPPING_OIL])),
                    ): selector.TextSelector(),
                    vol.Optional(
                        CONF_MODIFIER_OIL,
                        default=str(options.get(CONF_MODIFIER_OIL, DEFAULT_MODIFIERS[CONF_MODIFIER_OIL])),
                    ): selector.TextSelector(),
                    
                    vol.Optional(
                        CONF_MAPPING_DTC,
                        default=str(options.get(CONF_MAPPING_DTC, DEFAULT_MAPPINGS[CONF_MAPPING_DTC])),
                    ): selector.TextSelector(),
                    vol.Optional(
                        CONF_MODIFIER_DTC,
                        default=str(options.get(CONF_MODIFIER_DTC, DEFAULT_MODIFIERS[CONF_MODIFIER_DTC])),
                    ): selector.TextSelector(),
                    
                    vol.Optional(
                        CONF_MAPPING_DOOR_FL,
                        default=str(options.get(CONF_MAPPING_DOOR_FL, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_FL])),
                    ): selector.TextSelector(),
                    vol.Optional(
                        CONF_MODIFIER_DOOR_FL,
                        default=str(options.get(CONF_MODIFIER_DOOR_FL, DEFAULT_MODIFIERS[CONF_MODIFIER_DOOR_FL])),
                    ): selector.TextSelector(),
                    
                    vol.Optional(
                        CONF_MAPPING_DOOR_FR,
                        default=str(options.get(CONF_MAPPING_DOOR_FR, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_FR])),
                    ): selector.TextSelector(),
                    vol.Optional(
                        CONF_MODIFIER_DOOR_FR,
                        default=str(options.get(CONF_MODIFIER_DOOR_FR, DEFAULT_MODIFIERS[CONF_MODIFIER_DOOR_FR])),
                    ): selector.TextSelector(),
                    
                    vol.Optional(
                        CONF_MAPPING_DOOR_RL,
                        default=str(options.get(CONF_MAPPING_DOOR_RL, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_RL])),
                    ): selector.TextSelector(),
                    vol.Optional(
                        CONF_MODIFIER_DOOR_RL,
                        default=str(options.get(CONF_MODIFIER_DOOR_RL, DEFAULT_MODIFIERS[CONF_MODIFIER_DOOR_RL])),
                    ): selector.TextSelector(),
                    
                    vol.Optional(
                        CONF_MAPPING_DOOR_RR,
                        default=str(options.get(CONF_MAPPING_DOOR_RR, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_RR])),
                    ): selector.TextSelector(),
                    vol.Optional(
                        CONF_MODIFIER_DOOR_RR,
                        default=str(options.get(CONF_MODIFIER_DOOR_RR, DEFAULT_MODIFIERS[CONF_MODIFIER_DOOR_RR])),
                    ): selector.TextSelector(),
                    
                    vol.Optional(
                        CONF_MAPPING_LOCKED,
                        default=str(options.get(CONF_MAPPING_LOCKED, DEFAULT_MAPPINGS[CONF_MAPPING_LOCKED])),
                    ): selector.TextSelector(),
                    vol.Optional(
                        CONF_MODIFIER_LOCKED,
                        default=str(options.get(CONF_MODIFIER_LOCKED, DEFAULT_MODIFIERS[CONF_MODIFIER_LOCKED])),
                    ): selector.TextSelector(),
                    
                    vol.Optional(
                        CONF_MAPPING_WINDOWS,
                        default=str(options.get(CONF_MAPPING_WINDOWS, DEFAULT_MAPPINGS[CONF_MAPPING_WINDOWS])),
                    ): selector.TextSelector(),
                    vol.Optional(
                        CONF_MODIFIER_WINDOWS,
                        default=str(options.get(CONF_MODIFIER_WINDOWS, DEFAULT_MODIFIERS[CONF_MODIFIER_WINDOWS])),
                    ): selector.TextSelector(),
                    
                    vol.Optional(
                        CONF_MAPPING_HANDBRAKE,
                        default=str(options.get(CONF_MAPPING_HANDBRAKE, DEFAULT_MAPPINGS[CONF_MAPPING_HANDBRAKE])),
                    ): selector.TextSelector(),
                    vol.Optional(
                        CONF_MODIFIER_HANDBRAKE,
                        default=str(options.get(CONF_MODIFIER_HANDBRAKE, DEFAULT_MODIFIERS[CONF_MODIFIER_HANDBRAKE])),
                    ): selector.TextSelector(),
                    
                    vol.Optional(
                        CONF_MAPPING_LIGHTS,
                        default=str(options.get(CONF_MAPPING_LIGHTS, DEFAULT_MAPPINGS[CONF_MAPPING_LIGHTS])),
                    ): selector.TextSelector(),
                    vol.Optional(
                        CONF_MODIFIER_LIGHTS,
                        default=str(options.get(CONF_MODIFIER_LIGHTS, DEFAULT_MODIFIERS[CONF_MODIFIER_LIGHTS])),
                    ): selector.TextSelector(),
                }
            ),
        )
