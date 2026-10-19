"""Sensors: last plate read and remaining API calls."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PlateRecognizerConfigEntry
from .entity import PlateRecognizerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlateRecognizerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    scanner = entry.runtime_data
    entities: list[SensorEntity] = [LastPlateSensor(scanner, "last_plate")]
    if not scanner.is_local:
        entities.append(RemainingCallsSensor(scanner, "remaining_calls"))
    async_add_entities(entities)


class LastPlateSensor(PlateRecognizerEntity, SensorEntity):
    """Best plate from the latest scan; every read is in the attributes."""

    _attr_icon = "mdi:car-search"

    @property
    def native_value(self) -> str | None:
        reads = self.scanner.result.reads
        return reads[0]["plate"] if reads else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        result = self.scanner.result
        attrs: dict[str, Any] = {
            "plates_found": len(result.reads),
            "reads": result.reads,
            "scanned_at": result.scanned_at.isoformat() if result.scanned_at else None,
        }
        if result.watchlist:
            attrs["watchlist"] = result.watchlist
        return attrs


class RemainingCallsSensor(PlateRecognizerEntity, SensorEntity):
    """Cloud API calls left this billing month."""

    _attr_icon = "mdi:counter"
    _attr_native_unit_of_measurement = "calls"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        return self.scanner.usage.get("remaining")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        usage = self.scanner.usage
        return {k: usage.get(k) for k in ("allowance", "used", "resets_on")}
