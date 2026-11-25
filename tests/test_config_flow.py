"""Test config flow for Plate Recognizer."""
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from platerecognizer import CLOUD_USAGE_URL

from custom_components.platerecognizer.const import (
    DOMAIN,
    OPT_CAMERA,
    OPT_TOKEN,
)


async def test_flow_user_success(hass: HomeAssistant) -> None:
    """Test successful user step creating an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            OPT_CAMERA: "camera.front_door",
            OPT_TOKEN: "valid_token",
        },
    )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "camera.front_door"
    assert result2["data"][OPT_CAMERA] == "camera.front_door"
    assert result2["data"][OPT_TOKEN] == "valid_token"


async def test_flow_duplicate_abort(hass: HomeAssistant, mock_config_entry) -> None:
    """Test duplicate configuration aborts."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            OPT_CAMERA: "camera.front_door",
            OPT_TOKEN: "valid_token",
        },
    )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_flow_invalid_auth(hass: HomeAssistant, aioclient_mock) -> None:
    """Test invalid token error."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(CLOUD_USAGE_URL, status=401)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            OPT_CAMERA: "camera.front_door",
            OPT_TOKEN: "bad_token",
        },
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_flow_cannot_connect(hass: HomeAssistant, aioclient_mock) -> None:
    """Test network or server failure error."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(CLOUD_USAGE_URL, status=500)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            OPT_CAMERA: "camera.front_door",
            OPT_TOKEN: "token",
        },
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_reauth_flow(hass: HomeAssistant, mock_config_entry, aioclient_mock) -> None:
    """Test reauthentication flow updates token."""
    mock_config_entry.add_to_hass(hass)
    aioclient_mock.clear_requests()
    aioclient_mock.get(CLOUD_USAGE_URL, status=200)

    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            OPT_TOKEN: "new_valid_token",
        },
    )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert mock_config_entry.data[OPT_TOKEN] == "new_valid_token"
