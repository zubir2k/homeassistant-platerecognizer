"""Plate Recognizer integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import (
    DOMAIN,
    OPT_COUNTRIES,
    OPT_LOCAL_SDK,
    OPT_MATCH_COUNTRY_FORMAT,
    OPT_PLATE_IN_VEHICLE_ONLY,
    OPT_SDK_URL,
    OPT_SNAPSHOT_DIR,
    OPT_SNAPSHOT_EVERY_SCAN,
    OPT_SNAPSHOT_KEEP_HISTORY,
    OPT_VEHICLE_DETAILS,
    OPT_WATCHLIST,
)
from .scanner import PlateScanner

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.IMAGE, Platform.SENSOR]

type PlateRecognizerConfigEntry = ConfigEntry[PlateScanner]


async def async_setup_entry(hass: HomeAssistant, entry: PlateRecognizerConfigEntry) -> bool:
    """Set up one camera from a config entry."""
    scanner = PlateScanner(hass, entry.entry_id, {**entry.data, **entry.options})
    await scanner.async_refresh_usage()
    entry.runtime_data = scanner
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PlateRecognizerConfigEntry) -> bool:
    """Unload a config entry. Home Assistant owns the entity registry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: PlateRecognizerConfigEntry) -> None:
    """Apply new options by reloading; entities keep their registry entries."""
    await hass.config_entries.async_reload(entry.entry_id)


# Version 1 (v2.x) stored options under older key names.
_V1_RENAMES = {
    "on_premise": OPT_LOCAL_SDK,
    "server": OPT_SDK_URL,
    "regions": OPT_COUNTRIES,
    "watched_plates": OPT_WATCHLIST,
    "mmc": OPT_VEHICLE_DETAILS,
    "save_file_folder": OPT_SNAPSHOT_DIR,
    "save_timestamped_file": OPT_SNAPSHOT_KEEP_HISTORY,
    "always_save_latest_file": OPT_SNAPSHOT_EVERY_SCAN,
}
_V1_STRICT = {"detection_rule": OPT_PLATE_IN_VEHICLE_ONLY, "region_mode": OPT_MATCH_COUNTRY_FORMAT}


def _upgrade_v1(values: dict) -> dict:
    out: dict = {}
    for key, value in values.items():
        if key in _V1_STRICT:
            out[_V1_STRICT[key]] = value == "strict"
        else:
            out[_V1_RENAMES.get(key, key)] = value
    return out


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Move v2.x entries to the current storage layout."""
    if entry.version > 2:
        return False
    if entry.version == 1:
        hass.config_entries.async_update_entry(
            entry,
            data=_upgrade_v1(dict(entry.data)),
            options=_upgrade_v1(dict(entry.options)),
            version=2,
        )
        await _async_move_v1_entities(hass, entry)
        _LOGGER.info("Migrated Plate Recognizer entry %s to version 2", entry.entry_id)
    return True


async def _async_move_v1_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Keep users' entity customisations across the v2 -> v3 upgrade."""
    old_prefix = f"{DOMAIN}_{entry.entry_id}"
    new_ids = {
        f"{old_prefix}_stats": f"{entry.entry_id}_remaining_calls",
        f"{old_prefix}_image": f"{entry.entry_id}_last_frame",
    }

    @callback
    def _rename(reg_entry: er.RegistryEntry) -> dict | None:
        if reg_entry.unique_id in new_ids:
            return {"new_unique_id": new_ids[reg_entry.unique_id]}
        return None

    await er.async_migrate_entries(hass, entry.entry_id, _rename)

    # v2 created a legacy image_processing entity outside the config entry.
    # That platform is gone in v3, so drop its leftover registry entry once.
    registry = er.async_get(hass)
    if old := registry.async_get_entity_id("image_processing", DOMAIN, old_prefix):
        registry.async_remove(old)
