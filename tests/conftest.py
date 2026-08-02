from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")

"""Fixtures for fmc130_traccar tests."""



from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

pytest_plugins = ["pytest_homeassistant_custom_component"]

def pytest_configure(config):
    config.addinivalue_line("filterwarnings", "ignore::pytest.PytestRemovedIn9Warning")
    config.addinivalue_line("filterwarnings", "ignore::DeprecationWarning")



from custom_components.fmc130_traccar.const import (
    DOMAIN,
    CONF_IMEI,
    CONF_DEVICE_NAME,
    CONF_LISTENER_PORT,
    CONF_TLS_MODE,
    TLS_MODE_NONE,
)












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
def mock_config_entry() -> MockConfigEntry:
    """Create mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="FMC130 Test",
        data={
            CONF_DEVICE_NAME: "Test Vehicle",
            CONF_IMEI: "123456789012345",
            CONF_LISTENER_PORT: 5027,
            CONF_TLS_MODE: TLS_MODE_NONE,
        },
        unique_id="test-fmc130",
    )
