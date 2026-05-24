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
    CONF_MAPPING_OIL,
    CONF_MODIFIER_OIL,
    CONF_MAPPING_DTC,
    CONF_MODIFIER_DTC,
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
        key="totalDistance",
        name="Total Distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        modifier="*0.001",
    ),
    Fmc130SensorDescription(
        key=81,
        name="Vehicle Speed",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
    ),
    Fmc130SensorDescription(
        key=115,
        name="Engine Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        modifier="*0.1",
    ),
    Fmc130SensorDescription(
        key=200,
        name="Sleep Mode",
    ),
    Fmc130SensorDescription(
        key=866,
        name="Vehicle Range",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
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
        (CONF_MAPPING_RPM, CONF_MODIFIER_RPM, "RPM", "rpm"),
        (CONF_MAPPING_FUEL, CONF_MODIFIER_FUEL, "Fuel Level", "l"),
        (CONF_MAPPING_DTC, CONF_MODIFIER_DTC, "DTC Codes", None),
    ]
    
    for map_key, mod_key, name, unit in mappings:
        io_id = parse_int_value(options.get(map_key, DEFAULT_MAPPINGS[map_key]))
        modifier = options.get(mod_key, DEFAULT_MODIFIERS[mod_key])
        
        if io_id is not None:
            dynamic_sensors.append(Fmc130SensorDescription(
                key=io_id,
                name=name,
                native_unit_of_measurement=unit,
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
            raw = pos.get(self.entity_description.key)

        if raw is None:
            return None

        if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
            try:
                return dt_util.parse_datetime(str(raw))
            except (ValueError, TypeError):
                return None

        val = apply_modifier(raw, self.entity_description.modifier)
        
        return val
