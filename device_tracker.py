"""Device tracker platform for FMC130."""
from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import Fmc130ConfigEntry
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Fmc130ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the FMC130 device trackers."""
    coordinator = entry.runtime_data.coordinator
    devices = coordinator.data["devices"]

    entities = [
        Fmc130DeviceTracker(coordinator, dev)
        for dev in devices
    ]

    async_add_entities(entities)


class Fmc130DeviceTracker(CoordinatorEntity, TrackerEntity):
    """FMC130 Device Tracker."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        coordinator: Any,
        device: dict[str, Any],
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"{DOMAIN}_{device['id']}_tracker"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device["id"])},
            name=self._device["name"],
            manufacturer="Teltonika",
            model=self._device.get("model", "FMC130"),
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not self.coordinator.data:
            return False
        return self._device["id"] in self.coordinator.data.get("positions", {})

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        if not self.coordinator.data or "positions" not in self.coordinator.data:
            return None
        pos = self.coordinator.data["positions"].get(self._device["id"])
        if pos and "latitude" in pos:
            return pos["latitude"]
        return None

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        if not self.coordinator.data or "positions" not in self.coordinator.data:
            return None
        pos = self.coordinator.data["positions"].get(self._device["id"])
        if pos and "longitude" in pos:
            return pos["longitude"]
        return None

    @property
    def battery_level(self) -> int | None:
        """Return the battery level of the device."""
        if not self.coordinator.data or "positions" not in self.coordinator.data:
            return None
        pos = self.coordinator.data["positions"].get(self._device["id"])
        if pos and "attributes" in pos and "batteryLevel" in pos["attributes"]:
            return pos["attributes"]["batteryLevel"]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return device specific state attributes."""
        if not self.coordinator.data or "positions" not in self.coordinator.data:
            return {}
        pos = self.coordinator.data["positions"].get(self._device["id"])
        if not pos:
            return {}

        attrs = {
            "altitude": pos.get("altitude"),
            "speed": pos.get("speed"),
            "satellites": pos.get("sat"),
        }
        
        # Add all other attributes
        if "attributes" in pos:
            attrs.update(pos["attributes"])
            
        return attrs
