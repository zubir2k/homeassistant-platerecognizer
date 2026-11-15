"""Diagnostics support for Plate Recognizer."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_TOKEN
from homeassistant.core import HomeAssistant

from . import PlateRecognizerConfigEntry
from .const import OPT_TOKEN

TO_REDACT = {OPT_TOKEN, CONF_TOKEN, CONF_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PlateRecognizerConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    scanner = entry.runtime_data
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "scanner": {
            "camera": scanner.camera,
            "is_local": scanner.is_local,
            "watchlist_count": len(scanner.watchlist),
            "usage": scanner.usage,
            "last_scan": {
                "reads_count": len(scanner.result.reads),
                "scanned_at": (
                    scanner.result.scanned_at.isoformat()
                    if scanner.result.scanned_at
                    else None
                ),
            },
        },
    }
