"""Diagnostics support for FMC130 Traccar."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import REDACTED
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_PASSWORD, CONF_TOKEN, CONF_USERNAME

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    server = data.get("server")

    # Redact sensitive info
    config = {**entry.data}
    for key in (CONF_PASSWORD, CONF_TOKEN, CONF_USERNAME):
        if key in config:
            config[key] = REDACTED

    diagnostics_data = {
        "config": config,
        "coordinator_data": coordinator.data,
        "server_info": {
            "active": server is not None,
            "port": entry.data.get("listener_port"),
            "tls_enabled": entry.data.get("tls_enabled"),
            "connections": getattr(server, "_connections", {}),
        } if server else "Not Running",
    }

    return diagnostics_data
