"""Image entity for Plate Recognizer — serves the last processed frame."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import utcnow

from .const import CONF_CAMERA_ENTITY, CONF_ON_PREMISE, DEFAULT_ON_PREMISE, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    config = {**entry.data, **entry.options}
    camera_slug = config[CONF_CAMERA_ENTITY].replace("camera.", "")
    on_premise = config.get(CONF_ON_PREMISE, DEFAULT_ON_PREMISE)

    entity = PlateRecognizerImageEntity(hass, entry.entry_id, camera_slug, on_premise)

    # Store reference so image_processing entity can push frames directly
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][f"image_entity_{entry.entry_id}"] = entity

    async_add_entities([entity], update_before_add=False)


class PlateRecognizerImageEntity(ImageEntity):
    """Last processed image frame from Plate Recognizer."""

    _attr_should_poll = False
    _attr_content_type = "image/jpeg"
    _attr_icon = "mdi:car-search"
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry_id: str, camera_slug: str, on_premise: bool) -> None:
        super().__init__(hass)
        self._entry_id = entry_id
        self._image_bytes: bytes | None = None
        self._attr_name = f"platerecognizer_{camera_slug}"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_image"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=f"Plate Recognizer ({camera_slug})",
            manufacturer="Plate Recognizer",
            model="Snapshot Cloud" if not on_premise else "On-Premise SDK",
            entry_type="service",
            configuration_url="https://app.platerecognizer.com",
        )

    def update_image(self, image_bytes: bytes) -> None:
        """Called by image_processing entity after each scan."""
        self._image_bytes = image_bytes
        self._attr_image_last_updated = utcnow()
        self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        return self._image_bytes
