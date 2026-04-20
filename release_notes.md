# Release Notes: FMC130 Traccar Car Control

## v1.1.0

### Added Features
- **Device Tracker Platform**: Added `device_tracker.py` to automatically report latitude, longitude, and battery level from the Traccar server. Vehicles now appear automatically on the Home Assistant map.

### Bug Fixes
- **Options Flow 500 Error**: Fixed an issue where opening the integration options resulted in a 500 Internal Server Error. This was caused by recent Home Assistant Core architectural changes making `config_entry` a read-only property in `OptionsFlow`.

## v1.0.0

### Added Features
- Initial release of the `fmc130_traccar` integration.
- Setup `sensor` platform: Odometer, Total Distance, Power, Speed, and Satellites.
- Setup `binary_sensor` platform: Motion and Ignition.
- Service registry setup for remote commands (lock, unlock, horn, flash_lights, engine_start, engine_stop, dtc_reset).
- UI Configuration flow for adding the Traccar server credentials.
