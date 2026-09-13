"""Plate Recognizer integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import discovery
from homeassistant.helpers import entity_registry as er

from .const import CONF_CAMERA_ENTITY, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Plate Recognizer from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {**entry.data, **entry.options}

    # image_processing is a legacy platform — must use discovery
    hass.async_create_task(
        discovery.async_load_platform(
            hass,
            "image_processing",
            DOMAIN,
            {"entry_id": entry.entry_id},
            {},
        )
    )

    # sensor + image platforms via config entry
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "image"])

    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await hass.config_entries.async_unload_platforms(entry, ["sensor", "image"])

    # Remove the image_processing entity immediately so it doesn't
    # linger in the state machine after the integration is deleted
    config = hass.data[DOMAIN].get(entry.entry_id, {})
    camera_slug = config.get(CONF_CAMERA_ENTITY, "").replace("camera.", "")
    entity_id = f"image_processing.platerecognizer_{camera_slug}"

    if hass.states.get(entity_id):
        hass.states.async_remove(entity_id)
        _LOGGER.debug("Removed state: %s", entity_id)

    registry = er.async_get(hass)
    if registry.async_get(entity_id):
        registry.async_remove(entity_id)
        _LOGGER.debug("Removed registry entry: %s", entity_id)

    hass.data[DOMAIN].pop(entry.entry_id, None)
    hass.data[DOMAIN].pop(f"image_entity_{entry.entry_id}", None)

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload on options change."""
    await hass.config_entries.async_reload(entry.entry_id)
