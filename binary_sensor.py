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
    bitmask: int | None = None

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
    """Set up binary sensor platform."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator

    devices = coordinator.data["devices"]
    positions = coordinator.data["positions"]

    options = entry.options

    dynamic_sensors = list(BINARY_SENSORS)
    
    # Doors (Bitmask on configured IO ID)
    door_id = options.get(CONF_MAPPING_DOOR_FL, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_FL])
    dynamic_sensors.extend([
        Fmc130BinarySensorDescription(
            key=door_id,
            bitmask=0x01,
            name="Door Front Left",
            device_class=BinarySensorDeviceClass.DOOR
        ),
        Fmc130BinarySensorDescription(
            key=door_id,
            bitmask=0x02,
            name="Door Front Right",
            device_class=BinarySensorDeviceClass.DOOR
        ),
        Fmc130BinarySensorDescription(
            key=door_id,
            bitmask=0x04,
            name="Door Rear Left",
            device_class=BinarySensorDeviceClass.DOOR
        ),
        Fmc130BinarySensorDescription(
            key=door_id,
            bitmask=0x08,
            name="Door Rear Right",
            device_class=BinarySensorDeviceClass.DOOR
        ),
    ])
    
    # Other bitmask/numeric sensors
    dynamic_sensors.extend([
        Fmc130BinarySensorDescription(
            key=options.get(CONF_MAPPING_LOCKED, DEFAULT_MAPPINGS[CONF_MAPPING_LOCKED]),
            bitmask=0x1E,
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
        
        # Unique ID based on IMEI, key (IO ID), and bitmask (if any)
        uid = f"{DOMAIN}_{device['id']}_{description.key}"
        if description.bitmask is not None:
            uid += f"_{description.bitmask}"
        self._attr_unique_id = uid

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
            raw = pos.get(self.entity_description.key)

        if raw is None:
            return None

        # Apply bitmask if defined
        if self.entity_description.bitmask is not None:
            try:
                # For "Locked" sensor, we check if all bits in mask are 1
                if self.entity_description.device_class == BinarySensorDeviceClass.LOCK:
                    val = (int(raw) & self.entity_description.bitmask) == self.entity_description.bitmask
                else:
                    val = bool(int(raw) & self.entity_description.bitmask)
            except (ValueError, TypeError):
                val = bool(raw)
        else:
            val = bool(raw)

        # Home Assistant LOCK device class: ON = Unlocked, OFF = Locked
        if self.entity_description.device_class == BinarySensorDeviceClass.LOCK:
            return not val

        return val
