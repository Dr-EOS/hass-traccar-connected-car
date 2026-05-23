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
    CONF_DEBUG_MODE,
    TLS_MODE_NONE,
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
from .listener import TeltonikaServer
from .utils import parse_int_value

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "device_tracker"]

@dataclass
class Fmc130RuntimeData:
    """Runtime data for FMC130."""
    coordinator: DataUpdateCoordinator
    server: TeltonikaServer
    port: int

type Fmc130ConfigEntry = ConfigEntry[Fmc130RuntimeData]

async def async_setup_entry(hass: HomeAssistant, entry: Fmc130ConfigEntry):
    """Set up FMC130 from a config entry."""
    
    # Initialize domain data
    hass.data.setdefault(DOMAIN, {"servers": {}})

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

    # Prepare IO tracking info
    io_modifiers = {}
    for map_key, mod_key in [
        (CONF_MAPPING_RPM, CONF_MODIFIER_RPM),
        (CONF_MAPPING_FUEL, CONF_MODIFIER_FUEL),
        (CONF_MAPPING_OIL, CONF_MODIFIER_OIL),
        (CONF_MAPPING_DTC, CONF_MODIFIER_DTC),
        (CONF_MAPPING_DOOR_FL, CONF_MODIFIER_DOOR_FL),
        (CONF_MAPPING_DOOR_FR, CONF_MODIFIER_DOOR_FR),
        (CONF_MAPPING_DOOR_RL, CONF_MODIFIER_DOOR_RL),
        (CONF_MAPPING_DOOR_RR, CONF_MODIFIER_DOOR_RR),
        (CONF_MAPPING_LOCKED, CONF_MODIFIER_LOCKED),
        (CONF_MAPPING_WINDOWS, CONF_MODIFIER_WINDOWS),
        (CONF_MAPPING_HANDBRAKE, CONF_MODIFIER_HANDBRAKE),
        (CONF_MAPPING_LIGHTS, CONF_MODIFIER_LIGHTS),
    ]:
        map_val = entry.options.get(map_key, DEFAULT_MAPPINGS.get(map_key))
        io_id = parse_int_value(map_val)
        if io_id is not None:
            modifier = entry.options.get(mod_key, DEFAULT_MODIFIERS.get(mod_key))
            io_modifiers.setdefault(io_id, []).append(modifier)
    
    # Standard modifiers
    io_modifiers.setdefault(16, ["*0.001"]) # Odometer
    io_modifiers.setdefault(87, ["*0.001"]) # Total Mileage
    io_modifiers.setdefault(66, ["*0.001"]) # External Voltage
    io_modifiers.setdefault(67, ["*0.001"]) # Battery Voltage

    @callback
    def handle_direct_telemetry(imei, data):
        """Handle data pushed from the Teltonika listener."""
        dev_id = entry.entry_id
        
        # Merge into positions
        if dev_id not in entry_data["positions"]:
            entry_data["positions"][dev_id] = {"deviceId": dev_id, "attributes": {}}
        
        pos = entry_data["positions"][dev_id]

        # IO Tracking (before data is popped)
        if server.is_debug(imei):
            from .utils import apply_modifier
            for key, val in data.items():
                if isinstance(key, int):
                    modifiers = io_modifiers.get(key, [None])
                    for mod in modifiers:
                        converted = apply_modifier(val, mod)
                        msg = f"IO TRACKING [{imei}]: ID={key}, Raw={val}, Modifier={mod or 'None'}, Val={converted}"
                        server._log_event(msg)
                        _LOGGER.info(msg)
        
        # Extract location and common GPS fields if present
        for field in ["latitude", "longitude", "altitude", "angle", "sat", "speed"]:
            if field in data:
                pos[field] = data.pop(field)
            
        pos["attributes"].update(data)
        pos["fixTime"] = dt_util.utcnow().isoformat()
        
        coordinator.async_set_updated_data(entry_data)

    # Start or Get Direct Listener
    port = entry.data.get(CONF_LISTENER_PORT, 5027)
    if port not in hass.data[DOMAIN]["servers"]:
        server = TeltonikaServer(hass)
        tls_config = {
            "mode": entry.data.get(CONF_TLS_MODE, TLS_MODE_NONE),
            "cert": entry.data.get(CONF_SSL_CERT),
            "key": entry.data.get(CONF_SSL_KEY),
        }
        await server.async_start(port, tls_config)
        hass.data[DOMAIN]["servers"][port] = {
            "instance": server,
            "devices": set()
        }
    
    server_info = hass.data[DOMAIN]["servers"][port]
    server = server_info["instance"]
    server_info["devices"].add(entry.entry_id)
    
    # Set debug mode for this device
    imei = entry.data[CONF_IMEI]
    server.set_debug(imei, entry.data.get(CONF_DEBUG_MODE, False))
    
    # Register mapped IO IDs for unknown IO tracking
    mapping_keys = [
        CONF_MAPPING_RPM, CONF_MAPPING_FUEL, CONF_MAPPING_OIL, CONF_MAPPING_DTC,
        CONF_MAPPING_DOOR_FL, CONF_MAPPING_DOOR_FR, CONF_MAPPING_DOOR_RL, CONF_MAPPING_DOOR_RR,
        CONF_MAPPING_LOCKED, CONF_MAPPING_WINDOWS, CONF_MAPPING_HANDBRAKE, CONF_MAPPING_LIGHTS
    ]
    mapped_ids = set()
    for key in mapping_keys:
        val = entry.options.get(key, DEFAULT_MAPPINGS.get(key))
        io_id = parse_int_value(val)
        if io_id is not None:
            mapped_ids.add(io_id)
    server.set_mappings(imei, mapped_ids)
    
    # Register this device's callback
    unsub_data = server.async_add_data_callback(imei, handle_direct_telemetry)
    entry.async_on_unload(unsub_data)

    entry.runtime_data = Fmc130RuntimeData(
        coordinator=coordinator,
        server=server,
        port=port,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    # Register services once
    _async_setup_services(hass)
    
    return True

@callback
def _async_setup_services(hass: HomeAssistant):
    """Register services for the domain."""
    if hass.services.has_service(DOMAIN, "lock"):
        return

    async def handle_car_service(call):
        """Handle the car services."""
        device_id = call.data.get("device_id")
        service = call.service
        
        from homeassistant.helpers import device_registry as dr
        device_reg = dr.async_get(hass)
        device = device_reg.async_get(device_id)
        
        if not device:
            _LOGGER.error("Device %s not found", device_id)
            return
            
        # Find the config entry for this device
        entry_id = next(iter(device.config_entries), None)
        if not entry_id:
            _LOGGER.error("Device %s has no config entries", device_id)
            return
            
        entry = hass.config_entries.async_get_entry(entry_id)
        if not entry or entry.domain != DOMAIN:
            _LOGGER.error("Device %s does not belong to %s", device_id, DOMAIN)
            return

        runtime_data: Fmc130RuntimeData = entry.runtime_data
        server = runtime_data.server
        imei = entry.data[CONF_IMEI]

        _LOGGER.info("Car service %s called for device %s (IMEI: %s)", service, device_id, imei)
        
        # Mapping services to Teltonika GPRS commands
        command = None
        if service == "lock":
            command = "can_control lock"
        elif service == "unlock":
            command = "can_control unlock"
        elif service == "horn":
            command = "can_control horn"
        elif service == "flash_lights":
            command = "can_control flash"
        elif service == "engine_start":
            command = "setparam 404:1"
        elif service == "engine_stop":
            command = "setparam 404:0"
        elif service == "dtc_reset":
            command = "can_control dtc_reset"

        if command:
            success = server.send_command(imei, command)
            if success:
                server._log_event(f"Service command sent: {service} ({command})")
            else:
                _LOGGER.warning("Failed to send command %s: Device not connected", service)
                server._log_event(f"Service command FAILED: {service} (Device offline)")
        else:
            server._log_event(f"Service command not implemented: {service}")

    for service in ["lock", "unlock", "horn", "flash_lights", "engine_start", "engine_stop", "dtc_reset"]:
        hass.services.async_register(DOMAIN, service, handle_car_service)

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: Fmc130ConfigEntry):
    """Unload a config entry."""
    port = entry.runtime_data.port
    
    if port in hass.data[DOMAIN]["servers"]:
        server_info = hass.data[DOMAIN]["servers"][port]
        server_info["devices"].remove(entry.entry_id)
        
        # If last device for this server, stop it
        if not server_info["devices"]:
            await server_info["instance"].async_stop()
            del hass.data[DOMAIN]["servers"][port]

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
