from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass, BinarySensorEntityDescription
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
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

@dataclass(frozen=True, kw_only=True)
class Fmc130BinarySensorDescription(BinarySensorEntityDescription):
    """Class describing FMC130 binary sensor entities."""

BINARY_SENSORS: list[Fmc130BinarySensorDescription] = [
    Fmc130BinarySensorDescription(
        key="motion", 
        name="Motion", 
        device_class=BinarySensorDeviceClass.MOTION
    ),
    Fmc130BinarySensorDescription(
        key="ignition", 
        name="Ignition", 
        device_class=BinarySensorDeviceClass.POWER
    ),
]

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    devices = coordinator.data["devices"]
    positions = coordinator.data["positions"]

    options = entry.options

    dynamic_sensors = list(BINARY_SENSORS)
    dynamic_sensors.extend([
        Fmc130BinarySensorDescription(
            key=options.get(CONF_MAPPING_DOOR_FL, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_FL]),
            name="Door Front Left",
            device_class=BinarySensorDeviceClass.DOOR
        ),
        Fmc130BinarySensorDescription(
            key=options.get(CONF_MAPPING_DOOR_FR, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_FR]),
            name="Door Front Right",
            device_class=BinarySensorDeviceClass.DOOR
        ),
        Fmc130BinarySensorDescription(
            key=options.get(CONF_MAPPING_DOOR_RL, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_RL]),
            name="Door Rear Left",
            device_class=BinarySensorDeviceClass.DOOR
        ),
        Fmc130BinarySensorDescription(
            key=options.get(CONF_MAPPING_DOOR_RR, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_RR]),
            name="Door Rear Right",
            device_class=BinarySensorDeviceClass.DOOR
        ),
        Fmc130BinarySensorDescription(
            key=options.get(CONF_MAPPING_LOCKED, DEFAULT_MAPPINGS[CONF_MAPPING_LOCKED]),
            name="Locked",
            device_class=BinarySensorDeviceClass.LOCK
        ),
        Fmc130BinarySensorDescription(
            key=options.get(CONF_MAPPING_WINDOWS, DEFAULT_MAPPINGS[CONF_MAPPING_WINDOWS]),
            name="Windows",
            device_class=BinarySensorDeviceClass.WINDOW
        ),
        Fmc130BinarySensorDescription(
            key=options.get(CONF_MAPPING_HANDBRAKE, DEFAULT_MAPPINGS[CONF_MAPPING_HANDBRAKE]),
            name="Handbrake"
        ),
        Fmc130BinarySensorDescription(
            key=options.get(CONF_MAPPING_LIGHTS, DEFAULT_MAPPINGS[CONF_MAPPING_LIGHTS]),
            name="Lights",
            device_class=BinarySensorDeviceClass.LIGHT
        )
    ])

    entities = []

    for dev in devices:
        if dev["id"] not in positions:
            continue

        for desc in dynamic_sensors:
            entities.append(Fmc130BinarySensor(coordinator, dev, desc))

    async_add_entities(entities)

class Fmc130BinarySensor(CoordinatorEntity, BinarySensorEntity):
    """FMC130 binary sensor entity."""
    
    _attr_has_entity_name = True
    entity_description: Fmc130BinarySensorDescription

    def __init__(self, coordinator, device, description):
        super().__init__(coordinator)
        self._device = device
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{device['id']}_{description.key}"

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._device["id"])},
            name=self._device["name"],
            manufacturer="Teltonika",
            model=self._device.get("model", "FMC130"),
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return None

        pos = self.coordinator.data["positions"].get(self._device["id"])
        if not pos:
            return None

        attrs = pos.get("attributes", {})
        raw = attrs.get(self.entity_description.key)

        if raw is None:
            return None

        return bool(raw)
