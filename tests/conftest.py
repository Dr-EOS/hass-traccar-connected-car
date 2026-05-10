"""Fixtures for fmc130_traccar tests."""
from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fmc130_traccar.const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_USE_SSL,
    CONF_LISTENER_PORT,
    CONF_TLS_ENABLED,
)

@pytest.fixture(autouse=True)
def mock_aiohttp_client_session() -> Generator[AsyncMock, None, None]:
    """Mock aiohttp client session."""
    with patch(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession",
        return_value=AsyncMock(),
    ) as mock:
        yield mock

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""
    yield

@pytest.fixture(autouse=True)
def mock_teltonika_server() -> Generator[AsyncMock, None, None]:
    """Mock TeltonikaServer to avoid real sockets."""
    with patch(
        "custom_components.fmc130_traccar.listener.TeltonikaServer.async_start",
        autospec=True,
    ) as mock:
        yield mock

@pytest.fixture
def mock_traccar_client() -> Generator[AsyncMock, None, None]:
    """Create mock Traccar API client."""
    with patch(
        "custom_components.fmc130_traccar.api.TraccarClient",
        autospec=True,
    ) as mock:
        client = mock.return_value
        client.get_devices.return_value = [
            {"id": 1, "name": "Test Vehicle", "uniqueId": "123456789012345"}
        ]
        client.get_positions.return_value = [
            {
                "deviceId": 1,
                "attributes": {"power": 12.5, "ignition": True, "motion": False},
                "speed": 50,
                "fixTime": "2026-05-10T12:00:00Z"
            }
        ]
        # Patch in multiple locations where it might have been imported
        with patch("custom_components.fmc130_traccar.config_flow.TraccarClient", new=mock), \
             patch("custom_components.fmc130_traccar.TraccarClient", new=mock):
            yield client

@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="FMC130 Test",
        data={
            CONF_HOST: "traccar.example.com",
            CONF_PORT: 8082,
            CONF_USE_SSL: True,
            "enable_direct_listener": True,
            CONF_LISTENER_PORT: 5027,
            CONF_TLS_ENABLED: False,
        },
        unique_id="test-fmc130",
    )
