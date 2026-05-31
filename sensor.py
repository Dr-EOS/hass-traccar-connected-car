from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
)
from homeassistant.const import UnitOfLength, UnitOfSpeed, UnitOfElectricPotential, UnitOfTemperature
from homeassistant.util import dt as dt_util
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_MAPPING_RPM,
    CONF_MODIFIER_RPM,
    CONF_MAPPING_FUEL,
    CONF_MODIFIER_FUEL,
    CONF_MAPPING_DTC,
    CONF_MODIFIER_DTC,
    CONF_MAPPING_VOLTAGE,
    CONF_MODIFIER_VOLTAGE,
    CONF_MAPPING_SPEED,
    CONF_MODIFIER_SPEED,
    CONF_MAPPING_MILEAGE,
    CONF_MODIFIER_MILEAGE,
    CONF_MAPPING_ENGINE_TEMP,
    CONF_MODIFIER_ENGINE_TEMP,
    CONF_MAPPING_SLEEP_MODE,
    CONF_MODIFIER_SLEEP_MODE,
    CONF_MAPPING_VEHICLE_RANGE,
    CONF_MODIFIER_VEHICLE_RANGE,
    DEFAULT_MAPPINGS,
    DEFAULT_MODIFIERS,
)
from .utils import parse_int_value, apply_modifier

@dataclass(frozen=True, kw_only=True)
class Fmc130SensorDescription(SensorEntityDescription):
    """Class describing FMC130 sensor entities."""
    modifier: str | None = None

SENSORS: list[Fmc130SensorDescription] = [
    Fmc130SensorDescription(
        key="sat",
        name="Satellites",
        native_unit_of_measurement="sat",
    ),
    Fmc130SensorDescription(
        key="fixTime",
        name="Last Update",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
]

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensor platform."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator

    devices = coordinator.data["devices"]
    positions = coordinator.data["positions"]

    options = entry.options
    
    dynamic_sensors = list(SENSORS)
    
    mappings = [
        (CONF_MAPPING_RPM, CONF_MODIFIER_RPM, "RPM", "rpm", None),
        (CONF_MAPPING_FUEL, CONF_MODIFIER_FUEL, "Fuel Level", "l", None),
        (CONF_MAPPING_DTC, CONF_MODIFIER_DTC, "DTC Codes", None, None),
        (CONF_MAPPING_VOLTAGE, CONF_MODIFIER_VOLTAGE, "External Voltage", UnitOfElectricPotential.VOLT, None),
        (CONF_MAPPING_SPEED, CONF_MODIFIER_SPEED, "Vehicle Speed", UnitOfSpeed.KILOMETERS_PER_HOUR, None),
        (CONF_MAPPING_MILEAGE, CONF_MODIFIER_MILEAGE, "Total Mileage", UnitOfLength.KILOMETERS, None),
        (CONF_MAPPING_ENGINE_TEMP, CONF_MODIFIER_ENGINE_TEMP, "Engine Temperature", UnitOfTemperature.CELSIUS, None),
        (CONF_MAPPING_SLEEP_MODE, CONF_MODIFIER_SLEEP_MODE, "Sleep Mode", None, None),
        (CONF_MAPPING_VEHICLE_RANGE, CONF_MODIFIER_VEHICLE_RANGE, "Vehicle Range", UnitOfLength.KILOMETERS, None),
    ]
    
    for map_key, mod_key, name, unit, dev_class in mappings:
        io_id = parse_int_value(options.get(map_key, DEFAULT_MAPPINGS[map_key]))
        modifier = options.get(mod_key, DEFAULT_MODIFIERS[mod_key])
        
        if io_id is not None:
            dynamic_sensors.append(Fmc130SensorDescription(
                key=io_id,
                name=name,
                native_unit_of_measurement=unit,
                device_class=dev_class,
                modifier=modifier
            ))

    entities = []

    for dev in devices:
        if dev["id"] not in positions:
            continue

        for desc in dynamic_sensors:
            entities.append(Fmc130Sensor(coordinator, dev, desc))
        
        # Add Log Sensor for each device
        entities.append(Fmc130LogSensor(coordinator, dev, runtime_data.server))

    async_add_entities(entities)

class Fmc130LogSensor(CoordinatorEntity, SensorEntity):
    """Sensor that displays recent protocol logs."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:format-list-bulleted"

    def __init__(self, coordinator, device, server):
        super().__init__(coordinator)
        self._device = device
        self._server = server
        self._attr_unique_id = f"{DOMAIN}_{device['id']}_logs"
        self._attr_name = "Logs"

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._server.async_add_update_callback(self.async_write_ha_state)
        )

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
        return True

    @property
    def native_value(self) -> str | None:
        """Return the last log entry."""
        if self._server and self._server.events:
            return self._server.events[0]["event"]
        return "No events"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return all recent events."""
        if self._server:
            return {"recent_events": self._server.events}
        return {}

class Fmc130Sensor(CoordinatorEntity, SensorEntity):
    """FMC130 sensor entity."""
    
    _attr_has_entity_name = True
    entity_description: Fmc130SensorDescription

    def __init__(self, coordinator, device, description):
        super().__init__(coordinator)
        self._device = device
        self.entity_description = description
        
        # Unique ID based on IMEI and key (IO ID)
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
    def available(self) -> bool:
        """Return True if entity is available."""
        if not self.coordinator.data:
            return False
        return self._device["id"] in self.coordinator.data.get("positions", {})

    @property
    def native_value(self) -> StateType | dt_util.dt.datetime:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
            
        pos = self.coordinator.data["positions"].get(self._device["id"])
        if not pos:
            return None

        attrs = pos.get("attributes", {})
        raw = attrs.get(self.entity_description.key)
        
        if raw is None:
            raw = attrs.get(str(self.entity_description.key))

        if raw is None:
            raw = pos.get(self.entity_description.key)
            
        if raw is None:
            raw = pos.get(str(self.entity_description.key))

        fallback_map = {
            66: "power",
            "66": "power",
            67: "battery",
            "67": "battery",
            81: "speed",
            "81": "speed",
            87: "totalDistance",
            "87": "totalDistance",
            113: "batteryLevel",
            "113": "batteryLevel",
        }

        is_fallback = False
        if raw is None:
            fallback_name = fallback_map.get(self.entity_description.key)
            if fallback_name:
                raw = pos.get(fallback_name)
                if raw is None:
                    raw = attrs.get(fallback_name)
                if raw is not None:
                    is_fallback = True

        if raw is None:
            return None

        if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
            try:
                return dt_util.parse_datetime(str(raw))
            except (ValueError, TypeError):
                return None

        if is_fallback and self.entity_description.key in [66, "66", 67, "67"]:
            val = raw
        else:
            val = apply_modifier(raw, self.entity_description.modifier)
        
        return val
