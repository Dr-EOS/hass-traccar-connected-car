from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN, 
    CONF_HOST, 
    CONF_PORT, 
    CONF_USERNAME, 
    CONF_PASSWORD, 
    CONF_USE_SSL, 
    CONF_TOKEN,
    CONF_LISTENER_PORT,
    CONF_TLS_ENABLED,
    CONF_SSL_CERT,
    CONF_SSL_KEY
)
from .api import TraccarClient, TraccarApiError
from .listener import TeltonikaServer

from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    use_ssl = entry.data[CONF_USE_SSL]
    token = entry.data.get(CONF_TOKEN)

    session = async_get_clientsession(hass)
    client = TraccarClient(
        host, 
        port, 
        username, 
        password, 
        use_ssl, 
        token, 
        session=session,
        verify_ssl=entry.data.get("verify_ssl", True)
    )

    # State storage for push data
    hass.data.setdefault(DOMAIN, {})
    entry_data = {
        "devices": [],
        "positions": {},
        "direct_data": {}
    }

    async def async_update_data():
        """Polling fallback (if needed) or initial load."""
        try:
            devices = await client.get_devices()
            positions = await client.get_positions()
        except TraccarApiError as err:
            _LOGGER.warning("Traccar polling failed: %s", err)
            # If direct listener is active, we might ignore this
            return entry_data

        pos_by_device = {p["deviceId"]: p for p in positions}
        entry_data["devices"] = devices
        entry_data["positions"] = pos_by_device
        return entry_data

    # If direct listener is enabled, we might disable polling or use a long interval
    update_interval = timedelta(seconds=10)
    if entry.data.get("enable_direct_listener"):
         # For direct push, we can either disable polling or use it as background sync
         # User wants to be independent, but we might still need Traccar for historical/API purposes
         pass

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="fmc130_traccar",
        update_method=async_update_data,
        update_interval=update_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    @callback
    def handle_direct_telemetry(imei, data):
        """Handle data pushed from the Teltonika listener."""
        _LOGGER.debug("Direct telemetry for %s: %s", imei, data)
        # Update entry_data and refresh coordinator
        # In a real implementation, we'd find the device matching the IMEI
        for device in entry_data["devices"]:
            if device.get("uniqueId") == imei:
                dev_id = device["id"]
                # Merge into positions
                if dev_id not in entry_data["positions"]:
                    entry_data["positions"][dev_id] = {"deviceId": dev_id, "attributes": {}}
                
                entry_data["positions"][dev_id]["attributes"].update(data)
                # Update timestamp
                from homeassistant.util import dt as dt_util
                entry_data["positions"][dev_id]["fixTime"] = dt_util.utcnow().isoformat()
                
                coordinator.async_set_updated_data(entry_data)
                break

    # Start Direct Listener
    server = None
    if entry.data.get("enable_direct_listener"):
        server = TeltonikaServer(hass, handle_direct_telemetry)
        tls_config = {
            "enabled": entry.data.get(CONF_TLS_ENABLED, False),
            "cert": entry.data.get(CONF_SSL_CERT),
            "key": entry.data.get(CONF_SSL_KEY),
        }
        await server.async_start(entry.data.get(CONF_LISTENER_PORT, 5027), tls_config)

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "server": server,
    }

    import homeassistant.helpers.device_registry as dr
    device_registry = dr.async_get(hass)

    async def handle_remote_command(call):
        device_id = call.data.get("device_id")
        if not device_id:
            return
            
        device = device_registry.async_get(device_id)
        if not device:
            _LOGGER.error("Device %s not found", device_id)
            return

        traccar_device_id = None
        for identifier in device.identifiers:
            if identifier[0] == DOMAIN:
                traccar_device_id = identifier[1]
                break

        if not traccar_device_id:
            _LOGGER.error("Traccar device ID not found for device %s", device_id)
            return

        # If direct listener is active, we should try sending via direct socket if possible
        # For now we stick to Traccar API as fallback/primary for commands
        # TODO: Implement direct binary command sending
        
        command_map = {
            "lock": "custom",
            "unlock": "custom",
            "horn": "custom",
            "flash_lights": "custom",
            "engine_start": "engineResume",
            "engine_stop": "engineStop",
            "dtc_reset": "custom",
        }
        
        command_type = command_map.get(call.service)
        if not command_type:
            _LOGGER.error("Unknown command %s", call.service)
            return

        try:
            if command_type == "custom":
                payload = {
                    "type": "custom", 
                    "attributes": {"data": f"placeholder_for_{call.service}"}
                }
            else:
                payload = {"type": command_type}
            await client.send_command(traccar_device_id, payload)
        except Exception as err:
            _LOGGER.error("Failed to send command %s: %s", call.service, err)

    services = ["lock", "unlock", "horn", "flash_lights", "engine_start", "engine_stop", "dtc_reset"]
    for service in services:
        hass.services.async_register(DOMAIN, service, handle_remote_command)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    data = hass.data[DOMAIN].get(entry.entry_id)
    if data and data.get("server"):
        await data["server"].async_stop()
        
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
