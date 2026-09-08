"""Image entity for Plate Recognizer — serves the last annotated frame."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import utcnow

from .const import CONF_CAMERA_ENTITY, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    config = {**entry.data, **entry.options}
    camera_slug = config[CONF_CAMERA_ENTITY].replace("camera.", "")

    entity = PlateRecognizerImageEntity(hass, entry.entry_id, camera_slug)

    # Store reference so image_processing can push frames to it directly
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][f"image_entity_{entry.entry_id}"] = entity

    async_add_entities([entity], update_before_add=False)


class PlateRecognizerImageEntity(ImageEntity):
    """Last annotated image frame — updated on every scan."""

    _attr_should_poll = False
    _attr_content_type = "image/jpeg"
    _attr_icon = "mdi:car-search"

    def __init__(self, hass: HomeAssistant, entry_id: str, camera_slug: str) -> None:
        super().__init__(hass)
        self._image_bytes: bytes | None = None
        self._vehicles: list[dict[str, Any]] = []
        # standardized name: platerecognizer_<camera>_image
        self._attr_name = f"platerecognizer_{camera_slug}_image"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_image"

    def update_image(self, image_bytes: bytes, vehicles: list[dict[str, Any]] | None = None) -> None:
        """Called by image_processing entity after each scan."""
        self._image_bytes = image_bytes
        self._vehicles = vehicles or []
        self._attr_image_last_updated = utcnow()
        self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        return self._image_bytes

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose detected plates as attributes on the image entity."""
        return {"vehicles": self._vehicles}
