<<<<<<< HEAD
"""Sensor for API statistics — one per camera/entry."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_CAMERA_ENTITY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    config = {**entry.data, **entry.options}
    camera_slug = config[CONF_CAMERA_ENTITY].replace("camera.", "")
    image_entity_id = f"image_processing.platerecognizer_{camera_slug}"

    async_add_entities(
        [StatisticsSensor(hass, entry.entry_id, camera_slug, image_entity_id)],
        update_before_add=False,
    )


class StatisticsSensor(SensorEntity):
    """API usage sensor per camera — calls remaining as state, full stats as attributes."""

    _attr_should_poll = False
    _attr_icon = "mdi:chart-bar"
    _attr_native_unit_of_measurement = "calls"

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        camera_slug: str,
        image_entity_id: str,
    ) -> None:
        self.hass = hass
        self._image_entity_id = image_entity_id
        # platerecognizer_<camera>_stats
        self._attr_name = f"platerecognizer_{camera_slug}_stats"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_stats"
        self._calls_remaining: int | None = None
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
        self._calls_remaining = stats.get("calls_remaining")
        self.async_write_ha_state()

    @property
    def state(self) -> int | str:
        return self._calls_remaining if self._calls_remaining is not None else "unknown"

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
=======
"""Sensor for API statistics — one per camera/entry."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_CAMERA_ENTITY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    config = {**entry.data, **entry.options}
    camera_slug = config[CONF_CAMERA_ENTITY].replace("camera.", "")
    image_entity_id = f"image_processing.platerecognizer_{camera_slug}"

    async_add_entities(
        [StatisticsSensor(hass, entry.entry_id, camera_slug, image_entity_id)],
        update_before_add=False,
    )


class StatisticsSensor(SensorEntity):
    """API usage sensor per camera — calls remaining as state, full stats as attributes."""

    _attr_should_poll = False
    _attr_icon = "mdi:chart-bar"
    _attr_native_unit_of_measurement = "calls"

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        camera_slug: str,
        image_entity_id: str,
    ) -> None:
        self.hass = hass
        self._image_entity_id = image_entity_id
        # platerecognizer_<camera>_stats
        self._attr_name = f"platerecognizer_{camera_slug}_stats"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_stats"
        self._calls_remaining: int | None = None
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
        self._calls_remaining = stats.get("calls_remaining")
        self.async_write_ha_state()

    @property
    def state(self) -> int | str:
        return self._calls_remaining if self._calls_remaining is not None else "unknown"

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
>>>>>>> 6d11309c36a402dcef785300801a53539221bb28
