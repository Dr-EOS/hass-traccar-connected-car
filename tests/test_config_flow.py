"""Test fmc130_traccar config flow."""
from unittest.mock import patch
import pytest

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.fmc130_traccar.const import (
    DOMAIN,
    CONF_IMEI,
    CONF_DEVICE_NAME,
    CONF_LISTENER_PORT,
    CONF_TLS_MODE,
    TLS_MODE_NONE,
)

@pytest.mark.asyncio
async def test_user_flow_success(hass: HomeAssistant) -> None:
    """Test successful user flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.fmc130_traccar.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_DEVICE_NAME: "My Car",
                CONF_IMEI: "123456789012345",
                CONF_LISTENER_PORT: 5027,
                CONF_TLS_MODE: TLS_MODE_NONE,
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "Teltonika My Car"
        assert result["data"][CONF_IMEI] == "123456789012345"
        assert result["data"][CONF_LISTENER_PORT] == 5027

        await hass.async_block_till_done()
        assert len(mock_setup_entry.mock_calls) == 1

@pytest.mark.asyncio
async def test_user_flow_invalid_imei(hass: HomeAssistant) -> None:
    """Test flow with invalid IMEI."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_DEVICE_NAME: "My Car",
            CONF_IMEI: "short",
            CONF_LISTENER_PORT: 5027,
            CONF_TLS_MODE: TLS_MODE_NONE,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_IMEI: "invalid_imei"}
