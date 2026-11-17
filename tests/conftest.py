"""Fixtures for Plate Recognizer tests."""
from __future__ import annotations

import sys
from unittest.mock import patch
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.platerecognizer.const import (
    CLOUD_READ_URL,
    CLOUD_USAGE_URL,
    DOMAIN,
    OPT_CAMERA,
    OPT_TOKEN,
)

if sys.platform == "win32":
    try:
        import pytest_socket
        def _win_disable_socket(allow_unix_socket=False):
            pass
        pytest_socket.disable_socket = _win_disable_socket
    except ImportError:
        pass


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in all tests."""
    yield


@pytest.fixture(autouse=True)
def mock_usage_api(aioclient_mock):
    """Mock Plate Recognizer usage API endpoint."""
    aioclient_mock.get(
        CLOUD_USAGE_URL,
        json={
            "total_calls": 2500,
            "usage": {"calls": 120},
            "resets_on": "2026-12-01T00:00:00",
        },
    )
    aioclient_mock.post(
        CLOUD_READ_URL,
        json={
            "results": [
                {
                    "plate": "WXY1234",
                    "score": 0.95,
                    "region": {"code": "my"},
                    "vehicle": {"type": "Sedan"},
                    "box": {"xmin": 100, "ymin": 100, "xmax": 200, "ymax": 150},
                }
            ]
        },
    )
    return aioclient_mock


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Front Door",
        data={
            OPT_CAMERA: "camera.front_door",
            OPT_TOKEN: "mock_token_123",
        },
        entry_id="test_platerecognizer_entry",
        unique_id="camera.front_door",
        version=2,
    )


@pytest.fixture(autouse=True)
async def cleanup_entries(hass):
    """Ensure any loaded config entries are unloaded after each test."""
    yield
    for entry in list(hass.config_entries.async_entries()):
        if entry.state.loaded:
            await hass.config_entries.async_unload(entry.entry_id)
