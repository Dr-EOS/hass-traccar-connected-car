"""FMC130 Traccar Car Control Integration.

Generated with ha-integration@aurora-smart-home v1.0.0
https://github.com/tonylofgren/aurora-smart-home
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_TOKEN,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TraccarApiError, TraccarClient
from .const import CONF_USE_SSL, CONF_VERIFY_SSL, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.DEVICE_TRACKER]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass
class Fmc130TraccarData:
    """Runtime data for FMC130 Traccar."""

    client: TraccarClient
    coordinator: DataUpdateCoordinator[dict[str, Any]]


type Fmc130TraccarConfigEntry = ConfigEntry[Fmc130TraccarData]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the FMC130 Traccar component."""
    hass.data.setdefault(DOMAIN, {})
    await async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: Fmc130TraccarConfigEntry) -> bool:
    """Set up FMC130 Traccar from a config entry."""
    host = entry.options.get(CONF_HOST, entry.data[CONF_HOST])
    port = entry.options.get(CONF_PORT, entry.data[CONF_PORT])
    username = entry.options.get(CONF_USERNAME, entry.data.get(CONF_USERNAME))
    password = entry.options.get(CONF_PASSWORD, entry.data.get(CONF_PASSWORD))
    use_ssl = entry.options.get(CONF_USE_SSL, entry.data[CONF_USE_SSL])
    token = entry.options.get(CONF_TOKEN, entry.data.get(CONF_TOKEN))
    verify_ssl = entry.options.get(CONF_VERIFY_SSL, entry.data.get(CONF_VERIFY_SSL, True))

    session = async_get_clientsession(hass)
    client = TraccarClient(
        host,
        port,
        username,
        password,
        use_ssl,
        token,
        session=session,
        verify_ssl=verify_ssl,
    )

    async def async_update_data() -> dict[str, Any]:
        """Fetch data from Traccar."""
        try:
            devices = await client.get_devices()
            positions = await client.get_positions()
        except TraccarApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

        pos_by_device = {p["deviceId"]: p for p in positions}
        return {"devices": devices, "positions": pos_by_device}

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=10),
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = Fmc130TraccarData(
        client=client,
        coordinator=coordinator,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True


async def update_listener(hass: HomeAssistant, entry: Fmc130TraccarConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: Fmc130TraccarConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for FMC130 Traccar."""
    if "services_registered" in hass.data[DOMAIN]:
        return

    async def handle_remote_command(call: ServiceCall) -> None:
        """Handle remote commands."""
        device_id = call.data.get("device_id")
        if not device_id:
            # Also check target if device_id not in data
            device_ids = call.data.get("device_id") # Should be handled by target usually
            # In HA, target is handled automatically if defined in services.yaml
            # but we need to extract it from call.data.device_id or similar.
            pass

        if not device_id:
            return

        dev_reg = dr.async_get(hass)
        device = dev_reg.async_get(device_id)
        if not device:
            _LOGGER.error("Device %s not found", device_id)
            return

        # Find the config entry for this device
        traccar_entry: Fmc130TraccarConfigEntry | None = None
        for eid in device.config_entries:
            cfg_entry = hass.config_entries.async_get_entry(eid)
            if cfg_entry and cfg_entry.domain == DOMAIN:
                traccar_entry = cfg_entry # type: ignore[assignment]
                break

        if not traccar_entry or not hasattr(traccar_entry, "runtime_data"):
            _LOGGER.error("No config entry found for device %s", device_id)
            return

        client = traccar_entry.runtime_data.client

        traccar_device_id = None
        for identifier in device.identifiers:
            if identifier[0] == DOMAIN:
                try:
                    traccar_device_id = int(identifier[1])
                except (ValueError, TypeError):
                    traccar_device_id = identifier[1]
                break

        if traccar_device_id is None:
            _LOGGER.error("Traccar device ID not found for device %s", device_id)
            return

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
                # For now using a placeholder payload for custom commands
                payload = {
                    "type": "custom",
                    "attributes": {"data": f"placeholder_for_{call.service}"},
                }
            else:
                payload = {"type": command_type}
            await client.send_command(traccar_device_id, payload)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Failed to send command %s: %s", call.service, err)

    services = [
        "lock",
        "unlock",
        "horn",
        "flash_lights",
        "engine_start",
        "engine_stop",
        "dtc_reset",
    ]
    for service in services:
        hass.services.async_register(DOMAIN, service, handle_remote_command)

    hass.data[DOMAIN]["services_registered"] = True
