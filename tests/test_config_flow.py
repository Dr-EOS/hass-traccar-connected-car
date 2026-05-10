"""Test fmc130_traccar config flow."""
from unittest.mock import AsyncMock, patch
import pytest

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.fmc130_traccar.const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_USE_SSL,
    CONF_LISTENER_PORT,
)
from custom_components.fmc130_traccar.api import TraccarApiError

@pytest.mark.asyncio
async def test_user_flow_success(hass: HomeAssistant, mock_traccar_client: AsyncMock) -> None:
    """Test successful user flow."""
    with patch(
        "custom_components.fmc130_traccar.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "traccar.example.com",
                CONF_PORT: 8082,
                "username": "test-user",
                "password": "test-password",
                CONF_USE_SSL: True,
                "enable_direct_listener": True,
                CONF_LISTENER_PORT: 5027,
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "FMC130 traccar.example.com"
        assert result["data"][CONF_HOST] == "traccar.example.com"
        assert result["data"]["enable_direct_listener"] is True
        await hass.async_block_till_done()
        assert len(mock_setup_entry.mock_calls) == 1

@pytest.mark.asyncio
async def test_user_flow_cannot_connect(hass: HomeAssistant, mock_traccar_client: AsyncMock) -> None:
    """Test flow when connection fails."""
    mock_traccar_client.get_devices.side_effect = TraccarApiError("Cannot connect")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "wrong-host",
            CONF_PORT: 8082,
            "username": "user",
            "password": "pass",
            CONF_USE_SSL: True,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
