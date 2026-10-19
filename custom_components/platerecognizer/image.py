"""Image entity showing the last scanned frame with plates outlined."""

from __future__ import annotations

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PlateRecognizerConfigEntry
from .entity import PlateRecognizerEntity
from .scanner import PlateScanner


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlateRecognizerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([LastFrameImage(hass, entry.runtime_data)])


class LastFrameImage(PlateRecognizerEntity, ImageEntity):
    """Annotated copy of the frame used for the latest scan."""

    _attr_content_type = "image/jpeg"

    def __init__(self, hass: HomeAssistant, scanner: PlateScanner) -> None:
        ImageEntity.__init__(self, hass)
        PlateRecognizerEntity.__init__(self, scanner, "last_frame")

    def _handle_scan(self) -> None:
        self._attr_image_last_updated = self.scanner.result.scanned_at
        self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        return self.scanner.result.frame
