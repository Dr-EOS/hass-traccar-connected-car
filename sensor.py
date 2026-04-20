"""FMC130 Traccar Sensor Platform.

Generated with ha-integration@aurora-smart-home v1.0.0
https://github.com/tonylofgren/aurora-smart-home
"""

from __future__ import annotations

from collections.abc import Callable
import contextlib
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfElectricPotential, UnitOfLength, UnitOfSpeed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import Fmc130TraccarConfigEntry
from .const import (
    CONF_MAPPING_DTC,
    CONF_MAPPING_FUEL,
    CONF_MAPPING_OIL,
    CONF_MAPPING_RPM,
    DEFAULT_MAPPINGS,
    DOMAIN,
)


@dataclass(frozen=True, kw_only=True)
class Fmc130SensorEntityDescription(SensorEntityDescription):
    """Class describing FMC130 sensor entities."""

    value_fn: Callable[[Any], StateType] | None = None
    factor: float = 1.0


SENSORS: tuple[Fmc130SensorEntityDescription, ...] = (
    Fmc130SensorEntityDescription(
        key="odometer",
        name="Odometer",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        factor=0.001,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    Fmc130SensorEntityDescription(
        key="totalDistance",
        name="Total Distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        factor=0.001,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    Fmc130SensorEntityDescription(
        key="power",
        name="Power",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    Fmc130SensorEntityDescription(
        key="speed",
        name="Speed",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    Fmc130SensorEntityDescription(
        key="sat",
        name="Satellites",
        native_unit_of_measurement="sat",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Fmc130TraccarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the FMC130 sensors."""
    coordinator = entry.runtime_data.coordinator

    devices = coordinator.data["devices"]

    options = entry.options

    dynamic_sensors = list(SENSORS)
    dynamic_sensors.extend(
        [
            Fmc130SensorEntityDescription(
                key=options.get(CONF_MAPPING_RPM, DEFAULT_MAPPINGS[CONF_MAPPING_RPM]),
                name="RPM",
                native_unit_of_measurement="rpm",
                state_class=SensorStateClass.MEASUREMENT,
            ),
            Fmc130SensorEntityDescription(
                key=options.get(CONF_MAPPING_FUEL, DEFAULT_MAPPINGS[CONF_MAPPING_FUEL]),
                name="Fuel Level",
                native_unit_of_measurement="%",
                state_class=SensorStateClass.MEASUREMENT,
            ),
            Fmc130SensorEntityDescription(
                key=options.get(CONF_MAPPING_OIL, DEFAULT_MAPPINGS[CONF_MAPPING_OIL]),
                name="Oil Level",
                state_class=SensorStateClass.MEASUREMENT,
            ),
            Fmc130SensorEntityDescription(
                key=options.get(CONF_MAPPING_DTC, DEFAULT_MAPPINGS[CONF_MAPPING_DTC]),
                name="DTC Codes",
            ),
        ]
    )

    entities = [
        Fmc130Sensor(coordinator, dev, desc)
        for dev in devices
        for desc in dynamic_sensors
    ]

    async_add_entities(entities)


class Fmc130Sensor(CoordinatorEntity, SensorEntity):
    """Representation of an FMC130 sensor."""

    _attr_has_entity_name = True
    entity_description: Fmc130SensorEntityDescription

    def __init__(
        self,
        coordinator: Any,
        device: dict[str, Any],
        description: Fmc130SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device = device
        self.entity_description = description
        # Ensure unique_id is unique even if mappings overlap
        self._attr_unique_id = f"{DOMAIN}_{device['id']}_{description.name.lower().replace(' ', '_')}_{description.key}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(device["id"]))},
            name=device["name"],
            manufacturer="Teltonika",
            model=device.get("model", "FMC130"),
        )

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if not self.coordinator.data or "positions" not in self.coordinator.data:
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

        with contextlib.suppress(TypeError, ValueError):
            # Handle potential string values from Traccar
            return float(raw) * self.entity_description.factor
        return raw
