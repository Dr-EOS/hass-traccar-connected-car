from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.const import UnitOfLength, UnitOfSpeed, UnitOfElectricPotential
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_MAPPING_RPM,
    CONF_MAPPING_FUEL,
    CONF_MAPPING_OIL,
    CONF_MAPPING_DTC,
    DEFAULT_MAPPINGS,
)

@dataclass(frozen=True, kw_only=True)
class Fmc130SensorDescription(SensorEntityDescription):
    """Class describing FMC130 sensor entities."""
    factor: float = 1.0

SENSORS: list[Fmc130SensorDescription] = [
    Fmc130SensorDescription(
        key="odometer",
        name="Odometer",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        factor=0.001,
    ),
    Fmc130SensorDescription(
        key="totalDistance",
        name="Total Distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        factor=0.001,
    ),
    Fmc130SensorDescription(
        key="power",
        name="Power",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    Fmc130SensorDescription(
        key="speed",
        name="Speed",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
    ),
    Fmc130SensorDescription(
        key="sat",
        name="Satellites",
        native_unit_of_measurement="sat",
    ),
]

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    devices = coordinator.data["devices"]
    positions = coordinator.data["positions"]

    options = entry.options
    
    dynamic_sensors = list(SENSORS)
    dynamic_sensors.extend([
        Fmc130SensorDescription(
            key=options.get(CONF_MAPPING_RPM, DEFAULT_MAPPINGS[CONF_MAPPING_RPM]),
            name="RPM",
            native_unit_of_measurement="rpm"
        ),
        Fmc130SensorDescription(
            key=options.get(CONF_MAPPING_FUEL, DEFAULT_MAPPINGS[CONF_MAPPING_FUEL]),
            name="Fuel Level",
            native_unit_of_measurement="%"
        ),
        Fmc130SensorDescription(
            key=options.get(CONF_MAPPING_OIL, DEFAULT_MAPPINGS[CONF_MAPPING_OIL]),
            name="Oil Level"
        ),
        Fmc130SensorDescription(
            key=options.get(CONF_MAPPING_DTC, DEFAULT_MAPPINGS[CONF_MAPPING_DTC]),
            name="DTC Codes"
        )
    ])

    entities = []

    for dev in devices:
        # Check if we have data for this device
        if dev["id"] not in positions:
            continue

        for desc in dynamic_sensors:
            entities.append(Fmc130Sensor(coordinator, dev, desc))
        
        # Add Log Sensor for each device
        entities.append(Fmc130LogSensor(coordinator, dev, data.get("server")))

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

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._device["id"])},
            name=self._device["name"],
            manufacturer="Teltonika",
            model=self._device.get("model", "FMC130"),
        )

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
        self._attr_unique_id = f"{DOMAIN}_{device['id']}_{description.key}"
        # No need to set _attr_name or _attr_native_unit_of_measurement manually 
        # as SensorEntity handles it via entity_description

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._device["id"])},
            name=self._device["name"],
            manufacturer="Teltonika",
            model=self._device.get("model", "FMC130"),
        )

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
            
        pos = self.coordinator.data["positions"].get(self._device["id"])
        if not pos:
            return None

        attrs = pos.get("attributes", {})
        raw = attrs.get(self.entity_description.key)

        # Fallback for speed
        if raw is None and self.entity_description.key == "speed":
            raw = pos.get("speed")

        if raw is None:
            return None

        try:
            return raw * self.entity_description.factor
        except (TypeError, ValueError):
            return raw
