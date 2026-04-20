"""FMC130 Traccar Binary Sensor Platform.

Generated with ha-integration@aurora-smart-home v1.0.0
https://github.com/tonylofgren/aurora-smart-home
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import Fmc130TraccarConfigEntry
from .const import (
    CONF_MAPPING_DOOR_FL,
    CONF_MAPPING_DOOR_FR,
    CONF_MAPPING_DOOR_RL,
    CONF_MAPPING_DOOR_RR,
    CONF_MAPPING_HANDBRAKE,
    CONF_MAPPING_LIGHTS,
    CONF_MAPPING_LOCKED,
    CONF_MAPPING_WINDOWS,
    DEFAULT_MAPPINGS,
    DOMAIN,
)

BINARY_SENSORS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="motion",
        name="Motion",
        device_class=BinarySensorDeviceClass.MOTION,
    ),
    BinarySensorEntityDescription(
        key="ignition",
        name="Ignition",
        device_class=BinarySensorDeviceClass.POWER,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Fmc130TraccarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the FMC130 binary sensors."""
    coordinator = entry.runtime_data.coordinator

    devices = coordinator.data["devices"]

    options = entry.options

    dynamic_sensors = list(BINARY_SENSORS)
    dynamic_sensors.extend(
        [
            BinarySensorEntityDescription(
                key=options.get(
                    CONF_MAPPING_DOOR_FL, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_FL]
                ),
                name="Door Front Left",
                device_class=BinarySensorDeviceClass.DOOR,
            ),
            BinarySensorEntityDescription(
                key=options.get(
                    CONF_MAPPING_DOOR_FR, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_FR]
                ),
                name="Door Front Right",
                device_class=BinarySensorDeviceClass.DOOR,
            ),
            BinarySensorEntityDescription(
                key=options.get(
                    CONF_MAPPING_DOOR_RL, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_RL]
                ),
                name="Door Rear Left",
                device_class=BinarySensorDeviceClass.DOOR,
            ),
            BinarySensorEntityDescription(
                key=options.get(
                    CONF_MAPPING_DOOR_RR, DEFAULT_MAPPINGS[CONF_MAPPING_DOOR_RR]
                ),
                name="Door Rear Right",
                device_class=BinarySensorDeviceClass.DOOR,
            ),
            BinarySensorEntityDescription(
                key=options.get(
                    CONF_MAPPING_LOCKED, DEFAULT_MAPPINGS[CONF_MAPPING_LOCKED]
                ),
                name="Locked",
                device_class=BinarySensorDeviceClass.LOCK,
            ),
            BinarySensorEntityDescription(
                key=options.get(
                    CONF_MAPPING_WINDOWS, DEFAULT_MAPPINGS[CONF_MAPPING_WINDOWS]
                ),
                name="Windows",
                device_class=BinarySensorDeviceClass.WINDOW,
            ),
            BinarySensorEntityDescription(
                key=options.get(
                    CONF_MAPPING_HANDBRAKE, DEFAULT_MAPPINGS[CONF_MAPPING_HANDBRAKE]
                ),
                name="Handbrake",
            ),
            BinarySensorEntityDescription(
                key=options.get(
                    CONF_MAPPING_LIGHTS, DEFAULT_MAPPINGS[CONF_MAPPING_LIGHTS]
                ),
                name="Lights",
                device_class=BinarySensorDeviceClass.LIGHT,
            ),
        ]
    )

    entities = [
        Fmc130BinarySensor(coordinator, dev, desc)
        for dev in devices
        for desc in dynamic_sensors
    ]

    async_add_entities(entities)


class Fmc130BinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of an FMC130 binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Any,
        device: dict[str, Any],
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
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
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data or "positions" not in self.coordinator.data:
            return None

        pos = self.coordinator.data["positions"].get(self._device["id"])
        if not pos:
            return None

        attrs = pos.get("attributes", {})
        raw = attrs.get(self.entity_description.key)

        if raw is None:
            return None

        return bool(raw)
