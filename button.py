"""Refresh button for FMC130 Traccar."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    devices = coordinator.data["devices"]

    async_add_entities(
        [Fmc130RefreshButton(coordinator, device) for device in devices]
    )

class Fmc130RefreshButton(ButtonEntity):
    """Button to request a data refresh."""

    _attr_has_entity_name = True
    _attr_translation_key = "refresh"

    def __init__(self, coordinator, device) -> None:
        """Initialize the button."""
        self._coordinator = coordinator
        self._device = device
        self._attr_unique_id = f"{DOMAIN}_{device['id']}_refresh"
        self._attr_name = f"{device['name']} Refresh"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device["id"])},
            name=self._device["name"],
            manufacturer="Teltonika",
            model=self._device.get("model", "FMC130"),
        )

    async def async_press(self) -> None:
        """Press the button."""
        await self._coordinator.async_request_refresh()
