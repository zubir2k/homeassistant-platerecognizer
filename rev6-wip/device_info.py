"""Shared device info for Plate Recognizer entities."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def build_device_info(entry_id: str, camera_entity: str) -> DeviceInfo:
    """Return a DeviceInfo that groups all entities for one camera under one device."""
    camera_slug = camera_entity.replace("camera.", "")
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name=f"Plate Recognizer ({camera_slug})",
        manufacturer="Plate Recognizer",
        model="Snapshot Cloud",
        entry_type="service",
        configuration_url="https://app.platerecognizer.com",
    )
