"""Auto-created sensors for each watched plate and API statistics."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_API_TOKEN,
    CONF_CAMERA_ENTITY,
    CONF_ON_PREMISE,
    CONF_WATCHED_PLATES,
    DEFAULT_ON_PREMISE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _parse_list_option(value: Any) -> list[str]:
    if isinstance(value, list):
        return [v.strip().upper() for v in value if v.strip()]
    if isinstance(value, str):
        return [v.strip().upper() for v in value.split(",") if v.strip()]
    return []


def _build_device_info(entry_id: str, camera_slug: str, on_premise: bool) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name=f"Plate Recognizer ({camera_slug})",
        manufacturer="Plate Recognizer",
        model="Snapshot Cloud" if not on_premise else "On-Premise SDK",
        entry_type="service",
        configuration_url="https://app.platerecognizer.com",
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    config = {**entry.data, **entry.options}
    camera_entity = config[CONF_CAMERA_ENTITY]
    camera_slug = camera_entity.replace("camera.", "")
    on_premise = config.get(CONF_ON_PREMISE, DEFAULT_ON_PREMISE)
    image_entity_id = f"image_processing.platerecognizer_{camera_slug}"
    api_token = config.get(CONF_API_TOKEN, "")
    token_suffix = api_token[-8:] if api_token else entry.entry_id[:8]

    watched_plates = _parse_list_option(config.get(CONF_WATCHED_PLATES, []))
    device_info = _build_device_info(entry.entry_id, camera_slug, on_premise)

    entities: list[SensorEntity] = []

    # One sensor per watched plate — sensor.platerecognizer_<camera>_<plate>
    for plate in watched_plates:
        entities.append(
            WatchedPlateSensor(
                hass=hass,
                entry_id=entry.entry_id,
                plate=plate,
                camera_slug=camera_slug,
                image_entity_id=image_entity_id,
                device_info=device_info,
            )
        )

    # One stats sensor per API token — deduped across entries sharing same token
    token_key = f"stats_sensor_{token_suffix}"
    if token_key not in hass.data.get(DOMAIN, {}):
        hass.data.setdefault(DOMAIN, {})[token_key] = True
        entities.append(
            StatisticsSensor(
                hass=hass,
                entry_id=entry.entry_id,
                image_entity_id=image_entity_id,
                token_suffix=token_suffix,
                device_info=device_info,
            )
        )

    async_add_entities(entities, update_before_add=False)


class WatchedPlateSensor(SensorEntity):
    """True/False sensor for a single watched plate, scoped to a camera."""

    _attr_should_poll = False
    _attr_icon = "mdi:car-search"
    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        plate: str,
        camera_slug: str,
        image_entity_id: str,
        device_info: DeviceInfo,
    ) -> None:
        self.hass = hass
        self._plate = plate
        self._image_entity_id = image_entity_id
        self._attr_name = f"platerecognizer_{camera_slug}_{plate.lower()}"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{plate.lower()}"
        self._attr_device_info = device_info
        self._attr_native_value: bool | None = None

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._image_entity_id], self._handle_state_change
            )
        )

    @callback
    def _handle_state_change(self, event: Any) -> None:
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        watched = new_state.attributes.get("watched_plates", {})
        self._attr_native_value = watched.get(self._plate.lower(), False)
        self.async_write_ha_state()

    @property
    def state(self) -> str:
        if self._attr_native_value is None:
            return "unknown"
        return "true" if self._attr_native_value else "false"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"plate": self._plate, "source": self._image_entity_id}


class StatisticsSensor(SensorEntity):
    """Shared API statistics sensor — one per Plate Recognizer account/token."""

    _attr_should_poll = False
    _attr_icon = "mdi:chart-bar"
    _attr_native_unit_of_measurement = "calls"
    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        image_entity_id: str,
        token_suffix: str,
        device_info: DeviceInfo,
    ) -> None:
        self.hass = hass
        self._image_entity_id = image_entity_id
        self._attr_name = "platerecognizer_stats"
        self._attr_unique_id = f"{DOMAIN}_stats_{token_suffix}"
        self._attr_device_info = device_info
        self._attr_native_value: int | None = None
        self._stats: dict[str, Any] = {}

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._image_entity_id], self._handle_state_change
            )
        )

    @callback
    def _handle_state_change(self, event: Any) -> None:
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        stats = new_state.attributes.get("statistics", {})
        self._stats = stats
        self._attr_native_value = stats.get("calls_remaining")
        self.async_write_ha_state()

    @property
    def state(self) -> int | str:
        return self._attr_native_value if self._attr_native_value is not None else "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "total_calls": self._stats.get("total_calls"),
            "calls_used": self._stats.get("calls_used"),
            "calls_remaining": self._stats.get("calls_remaining"),
            "month": self._stats.get("month"),
            "year": self._stats.get("year"),
            "resets_on": self._stats.get("resets_on"),
        }
