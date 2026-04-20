# FMC130 + Traccar + Home Assistant - Custom Integration (`fmc130_traccar`)

This documentation describes the creation of a custom Home Assistant integration to connect a Teltonika FMC130 (with CAN control) via a Traccar server.  
The goal is to make CAN bus telemetry and remote commands fully available in Home Assistant.

---

## 1. Motivation

The official "Traccar Server" Home Assistant integration is minimalist. It provides:

- GPS position  
- Speed  
- Basic attributes  

It does not provide:

- CAN bus data (doors, locks, fuel level, oil level, RPM, DTCs...)  
- FMC130 IO elements  
- Remote commands (Lock, Unlock, Horn, Lights, Engine Start/Stop)  
- Dynamic sensors  
- Vehicle control  

Since the FMC130 provides extensive vehicle data via CAN control, a custom integration is necessary.

---

## 2. Integration Architecture

The integration consists of:
```
custom_components/fmc130_traccar/
├── __init__.py
├── manifest.json
├── config_flow.py
├── const.py
├── api.py
├── sensor.py
├── binary_sensor.py
├── device_tracker.py
└── services.yaml
```

### Data Flow
Teltonika FMC130 → Proxy/TLS → Traccar Server → Home Assistant Integration

The integration uses the Traccar API:

- `/api/devices`
- `/api/positions`
- `/api/commands/send`

---

## 3. Current Features

The integration currently provides the following entities:

### Sensors
- Odometer (km)  
- Total Distance (km)  
- Power (V)  
- Speed (km/h)  
- Satellites  

### Binary Sensors
- Motion  
- Ignition  

### Device Tracker
- GPS tracking (Latitude / Longitude) for the Home Assistant Map
- Battery Level

These values are sourced from `position.attributes`.

---

## 4. Installation

1. Create folder:
`config/custom_components/fmc130_traccar/`

2. Copy all files from this repository into the folder.

3. Restart Home Assistant.

4. Add integration:

**Settings → Devices & Services → Add Integration → "FMC130 Traccar Car Control"**

5. Enter Traccar server credentials.

---

## 5. Integration Files

The following files are located in the `custom_components/fmc130_traccar/` folder:

- [manifest.json](custom_components/fmc130_traccar/manifest.json)
- [const.py](custom_components/fmc130_traccar/const.py)
- [api.py](custom_components/fmc130_traccar/api.py)
- [__init__.py](custom_components/fmc130_traccar/__init__.py)
- [sensor.py](custom_components/fmc130_traccar/sensor.py)
- [binary_sensor.py](custom_components/fmc130_traccar/binary_sensor.py)
- [device_tracker.py](custom_components/fmc130_traccar/device_tracker.py)
- [services.yaml](custom_components/fmc130_traccar/services.yaml)

---

## 6. Next Steps

### CAN Bus Expansion
Once a sample position JSON with active CAN control is available, the following entities will be added:
- Doors (Front Left, Front Right, Rear Left, Rear Right)
- Locks
- Window Status
- Fuel Level
- Oil Level
- RPM
- DTC Error List
- Handbrake
- Light Status

### Remote Commands
Via Traccar:
- setio
- outputControl
- custom

The following HA services will be implemented:
- car.lock
- car.unlock
- car.horn
- car.flash_lights
- car.engine_start
- car.engine_stop
- car.dtc_reset

---

## 7. Conclusion
This integration forms the basis for a complete vehicle integration in Home Assistant:
- CAN bus telemetry
- Remote commands
- Dynamic sensors
- Clean Device Registry integration
- Extensibility for future IO elements

It is intentionally designed to be modular to support any Teltonika devices and CAN adapters in the future.
