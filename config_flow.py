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

_LOGGER = logging.getLogger(__name__)

def get_user_data_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the user data schema with optional defaults."""
    if defaults is None:
        defaults = {}
    
    return vol.Schema(
        {
            vol.Required(
                CONF_DEVICE_NAME, 
                default=defaults.get(CONF_DEVICE_NAME, "")
            ): selector.TextSelector(),
            vol.Required(
                CONF_IMEI, 
                default=defaults.get(CONF_IMEI, "")
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
                )
            ),
        }
    )

def get_tls_data_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the TLS data schema with optional defaults."""
    if defaults is None:
        defaults = {}
    
    return vol.Schema(
        {
            vol.Required(
                CONF_SSL_CERT,
                default=defaults.get(CONF_SSL_CERT, "")
            ): selector.TextSelector(),
            vol.Required(
                CONF_SSL_KEY,
                default=defaults.get(CONF_SSL_KEY, "")
            ): selector.TextSelector(),
        }
    )

class Fmc130TraccarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._user_data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            # Basic validation
            if not user_input[CONF_IMEI].isdigit() or len(user_input[CONF_IMEI]) < 10:
                errors[CONF_IMEI] = "invalid_imei"
            
            if not errors:
                self._user_data = user_input
                if user_input[CONF_TLS_MODE] == TLS_MODE_CUSTOM:
                    return await self.async_step_tls()
                
                await self.async_set_unique_id(user_input[CONF_IMEI])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Teltonika {user_input[CONF_DEVICE_NAME]}", 
                    data=self._user_data
                )

        return self.async_show_form(
            step_id="user", data_schema=get_user_data_schema(), errors=errors
        )

    async def async_step_tls(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle TLS custom step."""
        if user_input is not None:
            self._user_data.update(user_input)
            await self.async_set_unique_id(self._user_data[CONF_IMEI])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Teltonika {self._user_data[CONF_DEVICE_NAME]}", 
                data=self._user_data
            )

        return self.async_show_form(
            step_id="tls", data_schema=get_tls_data_schema(self._user_data)
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle reconfiguration."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            # Basic validation
            if not user_input[CONF_IMEI].isdigit() or len(user_input[CONF_IMEI]) < 10:
                errors[CONF_IMEI] = "invalid_imei"
            
            if not errors:
                self._user_data = user_input
                if user_input[CONF_TLS_MODE] == TLS_MODE_CUSTOM:
                    return await self.async_step_reconfigure_tls()
                
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

    async def async_step_reconfigure_tls(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle TLS custom step during reconfiguration."""
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            self._user_data.update(user_input)
            if self._user_data[CONF_IMEI] != entry.unique_id:
                await self.async_set_unique_id(self._user_data[CONF_IMEI])
                self._abort_if_unique_id_configured()
            
            return self.async_update_reload_and_abort(
                entry,
                data_updates=self._user_data,
            )

        return self.async_show_form(
            step_id="reconfigure_tls", data_schema=get_tls_data_schema(entry.data)
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return Fmc130TraccarOptionsFlow(config_entry)


class Fmc130TraccarOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._connection_data: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["connection", "mapping"],
        )

    async def async_step_connection(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage connection settings."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # Basic validation
            if not user_input[CONF_IMEI].isdigit() or len(user_input[CONF_IMEI]) < 10:
                errors[CONF_IMEI] = "invalid_imei"
            
            if not errors:
                self._connection_data = user_input
                if user_input[CONF_TLS_MODE] == TLS_MODE_CUSTOM:
                    return await self.async_step_connection_tls()
                
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

    async def async_step_connection_tls(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage custom TLS settings in options flow."""
        if user_input is not None:
            self._connection_data.update(user_input)
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
            step_id="connection_tls", data_schema=get_tls_data_schema(self.config_entry.data)
        )
