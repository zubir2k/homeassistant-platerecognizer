"""Shared base for Plate Recognizer entities."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .scanner import PlateScanner


class PlateRecognizerEntity(Entity):
    """One device per configured camera; entities update after every scan."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, scanner: PlateScanner, key: str) -> None:
        self.scanner = scanner
        self._attr_unique_id = f"{scanner.entry_id}_{key}"
        self._attr_translation_key = key
        camera_state = scanner.hass.states.get(scanner.camera)
        camera_name = camera_state.name if camera_state else scanner.camera.split(".", 1)[-1]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, scanner.entry_id)},
            name=f"Plate Recognizer {camera_name}",
            manufacturer="Plate Recognizer",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://app.platerecognizer.com/",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.scanner.add_listener(self._handle_scan))

    def _handle_scan(self) -> None:
        self.async_write_ha_state()
