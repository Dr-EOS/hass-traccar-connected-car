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
from .utils import parse_int_value, apply_modifier

@dataclass(frozen=True, kw_only=True)
class Fmc130BinarySensorDescription(BinarySensorEntityDescription):
    """Class describing FMC130 binary sensor entities."""
    modifier: str | None = None

BINARY_SENSORS: list[Fmc130BinarySensorDescription] = []

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up binary sensor platform."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator

    devices = coordinator.data["devices"]
    positions = coordinator.data["positions"]

    options = entry.options

    dynamic_sensors = list(BINARY_SENSORS)
    
    # Doors
    door_mappings = [
        (CONF_MAPPING_DOOR_FL, CONF_MODIFIER_DOOR_FL, "Door Front Left"),
        (CONF_MAPPING_DOOR_FR, CONF_MODIFIER_DOOR_FR, "Door Front Right"),
        (CONF_MAPPING_DOOR_RL, CONF_MODIFIER_DOOR_RL, "Door Rear Left"),
        (CONF_MAPPING_DOOR_RR, CONF_MODIFIER_DOOR_RR, "Door Rear Right"),
    ]
    
    for map_key, mod_key, name in door_mappings:
        io_id = parse_int_value(options.get(map_key, DEFAULT_MAPPINGS[map_key]))
        modifier = options.get(mod_key, DEFAULT_MODIFIERS[mod_key])
        
        if io_id is not None:
            dynamic_sensors.append(Fmc130BinarySensorDescription(
                key=io_id,
                modifier=modifier,
                name=name,
                device_class=BinarySensorDeviceClass.DOOR
            ))
    
    # Other bitmask/numeric sensors
    other_mappings = [
        (CONF_MAPPING_LOCKED, CONF_MODIFIER_LOCKED, "Locked", BinarySensorDeviceClass.LOCK),
        (CONF_MAPPING_WINDOWS, CONF_MODIFIER_WINDOWS, "Windows", BinarySensorDeviceClass.WINDOW),
        (CONF_MAPPING_HANDBRAKE, CONF_MODIFIER_HANDBRAKE, "Handbrake", None),
        (CONF_MAPPING_LIGHTS, CONF_MODIFIER_LIGHTS, "Lights", BinarySensorDeviceClass.LIGHT),
        (CONF_MAPPING_OIL, CONF_MODIFIER_OIL, "Oil Level Indicator", BinarySensorDeviceClass.PROBLEM),
        (CONF_MAPPING_TRUNK, CONF_MODIFIER_TRUNK, "Trunk Door Open", BinarySensorDeviceClass.DOOR),
        (CONF_MAPPING_ENGINE_COVER, CONF_MODIFIER_ENGINE_COVER, "Engine Cover Open", BinarySensorDeviceClass.DOOR),
        (CONF_MAPPING_CHECK_ENGINE, CONF_MODIFIER_CHECK_ENGINE, "Check Engine Indicator", BinarySensorDeviceClass.PROBLEM),
        (CONF_MAPPING_COOLANT_LEVEL, CONF_MODIFIER_COOLANT_LEVEL, "Coolant liquid level Indicator", BinarySensorDeviceClass.PROBLEM),
        (CONF_MAPPING_BATTERY_CHARGE, CONF_MODIFIER_BATTERY_CHARGE, "Battery Not Charging Indicator", BinarySensorDeviceClass.BATTERY),
        (CONF_MAPPING_WARNING, CONF_MODIFIER_WARNING, "Warning Indicator", BinarySensorDeviceClass.PROBLEM),
        (CONF_MAPPING_LOW_TIRE, CONF_MODIFIER_LOW_TIRE, "Low Tire Pressure Indicator", BinarySensorDeviceClass.PROBLEM),
        (CONF_MAPPING_WEAR_BRAKE, CONF_MODIFIER_WEAR_BRAKE, "Wear Of Brake Pads Indicator", BinarySensorDeviceClass.PROBLEM),
        (CONF_MAPPING_LOW_FUEL, CONF_MODIFIER_LOW_FUEL, "Low Fuel Level Indicator", BinarySensorDeviceClass.PROBLEM),
        (CONF_MAPPING_MAINTENANCE, CONF_MODIFIER_MAINTENANCE, "Maintenence required Indicator", BinarySensorDeviceClass.PROBLEM),
        (CONF_MAPPING_LOW_COOLANT, CONF_MODIFIER_LOW_COOLANT, "Low Coolant Level Indicator", BinarySensorDeviceClass.PROBLEM),
        (CONF_MAPPING_IGNITION, CONF_MODIFIER_IGNITION, "Ignition", BinarySensorDeviceClass.POWER),
        (CONF_MAPPING_MOTION, CONF_MODIFIER_MOTION, "Motion", BinarySensorDeviceClass.MOTION),
    ]
    
    for map_key, mod_key, name, dev_class in other_mappings:
        io_id = parse_int_value(options.get(map_key, DEFAULT_MAPPINGS[map_key]))
        modifier = options.get(mod_key, DEFAULT_MODIFIERS[mod_key])
        
        if io_id is not None:
            dynamic_sensors.append(Fmc130BinarySensorDescription(
                key=io_id,
                modifier=modifier,
                name=name,
                device_class=dev_class
            ))

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
        
        # Unique ID based on IMEI, key (IO ID), and modifier (to distinguish multi-entity IOs)
        uid = f"{DOMAIN}_{device['id']}_{description.key}"
        if description.modifier is not None:
            uid += f"_{description.modifier}"
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
    def available(self) -> bool:
        """Return True if entity is available."""
        if not self.coordinator.data:
            return False
        return self._device["id"] in self.coordinator.data.get("positions", {})

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

        # Apply modifier
        val = apply_modifier(raw, self.entity_description.modifier)

        # Home Assistant LOCK device class: ON = Unlocked, OFF = Locked
        state = bool(val)
        if self.entity_description.device_class == BinarySensorDeviceClass.LOCK:
            # If modifier is a bitmask, we check if all bits are set
            if self.entity_description.modifier and self.entity_description.modifier.startswith("&"):
                mask = parse_int_value(self.entity_description.modifier[1:])
                if mask is not None:
                    is_locked = (int(raw) & mask) == mask
                    state = not is_locked
            else:
                state = not bool(val)

        return state
