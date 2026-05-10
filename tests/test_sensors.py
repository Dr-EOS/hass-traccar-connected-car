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
    
    # The callback is stored in the server instance
    server.callback_fn("123456789012345", {"power": 13.8, "ignition": 1})
    
    await hass.async_block_till_done()

    # Check if state updated immediately
    state = hass.states.get("sensor.test_vehicle_power")
    assert state.state == "13.8"
    
    binary_state = hass.states.get("binary_sensor.test_vehicle_ignition")
    assert binary_state.state == STATE_ON

    # Check Log Sensor
    log_state = hass.states.get("sensor.test_vehicle_logs")
    assert log_state is not None
    assert log_state.state == "Push Update Test"
    assert "recent_events" in log_state.attributes
