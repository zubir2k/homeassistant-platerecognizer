"""Button that triggers a scan of the camera."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PlateRecognizerConfigEntry
from .entity import PlateRecognizerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlateRecognizerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([ScanButton(entry.runtime_data, "scan")])


class ScanButton(PlateRecognizerEntity, ButtonEntity):
    """Press (or call button.press) to read plates from the current frame."""

    async def async_press(self) -> None:
        await self.scanner.async_scan()
