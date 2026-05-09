from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity
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

@dataclass
class Fmc130SensorDescription:
    key: str
    name: str
    unit: str | None = None
    factor: float = 1.0

SENSORS = [
    Fmc130SensorDescription("odometer", "Odometer", UnitOfLength.KILOMETERS, 0.001),
    Fmc130SensorDescription("totalDistance", "Total Distance", UnitOfLength.KILOMETERS, 0.001),
    Fmc130SensorDescription("power", "Power", UnitOfElectricPotential.VOLT),
    Fmc130SensorDescription("speed", "Speed", UnitOfSpeed.KILOMETERS_PER_HOUR),
    Fmc130SensorDescription("sat", "Satellites", "sat"),
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
            unit="rpm"
        ),
        Fmc130SensorDescription(
            key=options.get(CONF_MAPPING_FUEL, DEFAULT_MAPPINGS[CONF_MAPPING_FUEL]),
            name="Fuel Level",
            unit="%"
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
        if dev["id"] not in positions:
            continue

        for desc in dynamic_sensors:
            entities.append(Fmc130Sensor(coordinator, dev, desc))

    async_add_entities(entities)

class Fmc130Sensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, device, description):
        super().__init__(coordinator)
        self._device = device
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{device['id']}_{description.key}"
        self._attr_name = f"{device['name']} {description.name}"
        self._attr_native_unit_of_measurement = description.unit

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

        if raw is None and self.entity_description.key == "speed":
            raw = pos.get("speed")

        if raw is None:
            return None

        try:
            return raw * self.entity_description.factor
        except (TypeError, ValueError):
            return raw
