"""Test fmc130_traccar entities."""
from unittest.mock import patch
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.const import STATE_ON, STATE_OFF

from custom_components.fmc130_traccar.const import DOMAIN

@pytest.mark.asyncio
async def test_sensors(hass: HomeAssistant, mock_config_entry) -> None:
    """Test sensor states and push updates."""
    mock_config_entry.add_to_hass(hass)
    
    # Patch the server start to avoid real socket
    with patch("custom_components.fmc130_traccar.listener.TeltonikaServer.async_start"):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Initial state should be unknown as we haven't received data yet
    # but we did fetch initial data in __init__ (mocked via DataUpdateCoordinator method)
    # Actually in our new __init__, positions start empty.
    
    state = hass.states.get("sensor.test_vehicle_power")
    assert state is not None
    assert state.state == "unknown"

    # Simulate a push update from the listener
    runtime_data = hass.config_entries.async_get_entry(mock_config_entry.entry_id).runtime_data
    server = runtime_data.server
    
    # Log the event BEFORE triggering the callback
    server._log_event("Push Update Test")
    
    # The callback is now IMEI specific
    callback = server._data_callbacks["123456789012345"]
    callback("123456789012345", {
        "power": 13.8, 
        "ignition": 1,
        "speed": 85,
        "sat": 12,
        "latitude": 52.5200,
        "longitude": 13.4050,
        "altitude": 150
    })
    
    await hass.async_block_till_done()

    # Check if state updated immediately
    state = hass.states.get("sensor.test_vehicle_power")
    assert state.state == "13.8"
    
    state = hass.states.get("sensor.test_vehicle_speed")
    assert state.state == "85"
    
    state = hass.states.get("sensor.test_vehicle_satellites")
    assert state.state == "12"

    # Check Last Update sensor
    update_state = hass.states.get("sensor.test_vehicle_last_update")
    assert update_state is not None
    assert update_state.state != "unknown"
    
    binary_state = hass.states.get("binary_sensor.test_vehicle_ignition")
    assert binary_state.state == STATE_ON

    # Check Device Tracker
    tracker_state = hass.states.get("device_tracker.test_vehicle")
    assert tracker_state is not None
    assert tracker_state.attributes["latitude"] == 52.5200
    assert tracker_state.attributes["longitude"] == 13.4050
    assert tracker_state.attributes["altitude"] == 150
    assert tracker_state.attributes["speed"] == 85
    assert tracker_state.attributes["satellites"] == 12

    # Check Log Sensor
    log_state = hass.states.get("sensor.test_vehicle_logs")
    assert log_state is not None
    assert log_state.state == "Push Update Test"
    assert "recent_events" in log_state.attributes

    # Test Locked bitmask (IO ID 321, mask 0x1E)
    # 0x1E = 30 decimal
    callback("123456789012345", {321: 30}) # All bits set -> Locked
    await hass.async_block_till_done()
    lock_state = hass.states.get("binary_sensor.test_vehicle_locked")
    assert lock_state.state == STATE_OFF # Locked

    callback("123456789012345", {321: 0}) # No bits set -> Unlocked
    await hass.async_block_till_done()
    lock_state = hass.states.get("binary_sensor.test_vehicle_locked")
    assert lock_state.state == STATE_ON # Unlocked

    callback("123456789012345", {321: 2}) # Only some bits set -> Unlocked
    await hass.async_block_till_done()
    lock_state = hass.states.get("binary_sensor.test_vehicle_locked")
    assert lock_state.state == STATE_ON # Unlocked

    # Test scaling modifier (*0.001 for totalDistance)
    callback("123456789012345", {"totalDistance": 1234567}) # 1234567 meters -> 1234.567 km
    await hass.async_block_till_done()
    odo_state = hass.states.get("sensor.test_vehicle_total_distance")
    assert odo_state.state == "1234.567"
