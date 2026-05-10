from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN, 
    CONF_IMEI,
    CONF_DEVICE_NAME,
    CONF_LISTENER_PORT,
    CONF_TLS_MODE,
    CONF_SSL_CERT,
    CONF_SSL_KEY,
    TLS_MODE_NONE,
)
from .listener import TeltonikaServer

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "device_tracker"]

@dataclass
class Fmc130RuntimeData:
    """Runtime data for FMC130."""
    coordinator: DataUpdateCoordinator
    server: TeltonikaServer

type Fmc130ConfigEntry = ConfigEntry[Fmc130RuntimeData]

async def async_setup_entry(hass: HomeAssistant, entry: Fmc130ConfigEntry):
    """Set up FMC130 from a config entry."""
    
    # State storage for push data
    entry_data = {
        "devices": [{
            "id": entry.entry_id,
            "name": entry.data[CONF_DEVICE_NAME],
            "uniqueId": entry.data[CONF_IMEI],
            "model": "FMC130"
        }],
        "positions": {
            entry.entry_id: {"deviceId": entry.entry_id, "attributes": {}}
        }
    }

    async def async_update_data():
        """No polling, just return current state."""
        return entry_data

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"fmc130_{entry.data[CONF_DEVICE_NAME]}",
        update_method=async_update_data,
        update_interval=None,
    )

    await coordinator.async_config_entry_first_refresh()

    async def handle_car_service(call):
        """Handle the car services."""
        device_id = call.data.get("device_id")
        service = call.service
        _LOGGER.info("Car service %s called for device %s", service, device_id)
        # In a real implementation, this would send a command to the Teltonika device.
        # For now, we log the command and update the log sensor.
        server._log_event(f"Service command sent: {service}")

    for service in ["lock", "unlock", "horn", "flash_lights", "engine_start", "engine_stop", "dtc_reset"]:
        hass.services.async_register(DOMAIN, service, handle_car_service)

    @callback
    def handle_direct_telemetry(imei, data):
        """Handle data pushed from the Teltonika listener."""
        if imei != entry.data[CONF_IMEI]:
            return

        dev_id = entry.entry_id
        
        # Merge into positions
        if dev_id not in entry_data["positions"]:
            entry_data["positions"][dev_id] = {"deviceId": dev_id, "attributes": {}}
        
        # Extract location if present
        if "latitude" in data:
            entry_data["positions"][dev_id]["latitude"] = data.pop("latitude")
        if "longitude" in data:
            entry_data["positions"][dev_id]["longitude"] = data.pop("longitude")
            
        entry_data["positions"][dev_id]["attributes"].update(data)
        entry_data["positions"][dev_id]["fixTime"] = dt_util.utcnow().isoformat()
        
        coordinator.async_set_updated_data(entry_data)

    # Start Direct Listener
    server = TeltonikaServer(hass, handle_direct_telemetry)
    tls_config = {
        "mode": entry.data.get(CONF_TLS_MODE, TLS_MODE_NONE),
        "cert": entry.data.get(CONF_SSL_CERT),
        "key": entry.data.get(CONF_SSL_KEY),
    }
    await server.async_start(entry.data.get(CONF_LISTENER_PORT, 5027), tls_config)

    entry.runtime_data = Fmc130RuntimeData(
        coordinator=coordinator,
        server=server,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: Fmc130ConfigEntry):
    """Unload a config entry."""
    await entry.runtime_data.server.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
