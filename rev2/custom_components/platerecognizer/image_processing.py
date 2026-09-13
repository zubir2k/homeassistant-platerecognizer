"""Image processing platform for Plate Recognizer."""
from __future__ import annotations

import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp

from homeassistant.components.image_processing import ImageProcessingEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.dt import utcnow

from .const import (
    API_URL_CLOUD,
    ATTR_CALLS_REMAINING,
    ATTR_CONFIDENCE,
    ATTR_LAST_DETECTION,
    ATTR_MMC,
    ATTR_ORIENTATION,
    ATTR_PLATE,
    ATTR_PLATES_DETECTED,
    ATTR_REGION,
    ATTR_STATISTICS,
    ATTR_VEHICLE_TYPE,
    ATTR_WATCHED_PLATES,
    CONF_ALWAYS_SAVE_LATEST,
    CONF_API_TOKEN,
    CONF_CAMERA_ENTITY,
    CONF_DETECTION_RULE,
    CONF_MMC,
    CONF_ON_PREMISE,
    CONF_REGION_MODE,
    CONF_REGIONS,
    CONF_SAVE_FILE_FOLDER,
    CONF_SAVE_TIMESTAMPED,
    CONF_SERVER,
    CONF_WATCHED_PLATES,
    DEFAULT_ALWAYS_SAVE_LATEST,
    DEFAULT_DETECTION_RULE,
    DEFAULT_MMC,
    DEFAULT_ON_PREMISE,
    DEFAULT_REGION_MODE,
    DEFAULT_SAVE_TIMESTAMPED,
    DEFAULT_SERVER,
    DOMAIN,
    EVENT_VEHICLE_DETECTED,
)

_LOGGER = logging.getLogger(__name__)


def _parse_list_option(value: Any) -> list[str]:
    """Accept either a list or a comma-separated string from the options flow."""
    if isinstance(value, list):
        return [v.strip().lower() for v in value if v.strip()]
    if isinstance(value, str):
        return [v.strip().lower() for v in value.split(",") if v.strip()]
    return []


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Plate Recognizer image processing entity from config entry."""
    config = {**entry.data, **entry.options}
    entity = PlateRecognizerEntity(hass, entry.entry_id, config)
    async_add_entities([entity], update_before_add=False)


class PlateRecognizerEntity(ImageProcessingEntity):
    """Plate Recognizer image processing entity."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        config: dict[str, Any],
    ) -> None:
        """Initialise the entity."""
        self.hass = hass
        self._entry_id = entry_id

        # --- Required by ImageProcessingEntity ---
        self._attr_camera_entity: str = config[CONF_CAMERA_ENTITY]

        # Credentials / server
        self._api_token: str = config.get(CONF_API_TOKEN, "")
        self._on_premise: bool = config.get(CONF_ON_PREMISE, DEFAULT_ON_PREMISE)
        self._server: str = config.get(CONF_SERVER, DEFAULT_SERVER).rstrip("/")

        # Detection options
        self._regions: list[str] = _parse_list_option(config.get(CONF_REGIONS, []))
        self._watched_plates: list[str] = _parse_list_option(config.get(CONF_WATCHED_PLATES, []))
        self._detection_rule: str = config.get(CONF_DETECTION_RULE, DEFAULT_DETECTION_RULE)
        self._region_mode: str = config.get(CONF_REGION_MODE, DEFAULT_REGION_MODE)
        self._mmc: bool = config.get(CONF_MMC, DEFAULT_MMC)

        # File saving
        self._save_folder: str = config.get(CONF_SAVE_FILE_FOLDER, "")
        self._save_timestamped: bool = config.get(CONF_SAVE_TIMESTAMPED, DEFAULT_SAVE_TIMESTAMPED)
        self._always_save_latest: bool = config.get(CONF_ALWAYS_SAVE_LATEST, DEFAULT_ALWAYS_SAVE_LATEST)

        # State
        self._plates: list[dict[str, Any]] = []
        self._watched_plate_status: dict[str, bool] = {p: False for p in self._watched_plates}
        self._statistics: dict[str, Any] = {}
        self._last_detection: str | None = None

        # Derive a stable name from the camera entity ID
        camera_slug = self._attr_camera_entity.replace("camera.", "")
        self._attr_name = f"Plate Recognizer {camera_slug}"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}"

    # ------------------------------------------------------------------ #
    # ImageProcessingEntity required properties                             #
    # ------------------------------------------------------------------ #

    @property
    def camera_entity(self) -> str:
        """Return the source camera entity_id (required by ImageProcessingEntity)."""
        return self._attr_camera_entity

    @property
    def confidence(self) -> float | None:
        """Return confidence of the top result, or None."""
        if self._plates:
            return self._plates[0].get(ATTR_CONFIDENCE)
        return None

    # ------------------------------------------------------------------ #
    # State & attributes                                                    #
    # ------------------------------------------------------------------ #

    @property
    def state(self) -> int:
        """Number of plates found in the last scan."""
        return len(self._plates)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            ATTR_PLATES_DETECTED: self._plates,
            ATTR_STATISTICS: self._statistics,
        }
        if self._last_detection:
            attrs[ATTR_LAST_DETECTION] = self._last_detection
        if self._watched_plates:
            attrs[ATTR_WATCHED_PLATES] = self._watched_plate_status
        return attrs

    # ------------------------------------------------------------------ #
    # Core processing                                                        #
    # ------------------------------------------------------------------ #

    @property
    def _api_url(self) -> str:
        if self._on_premise:
            return f"{self._server}/v1/plate-reader/"
        return API_URL_CLOUD

    @property
    def _auth_headers(self) -> dict[str, str]:
        if self._on_premise:
            return {}
        return {"Authorization": f"Token {self._api_token}"}

    async def async_process_image(self, image: bytes) -> None:
        """Receive raw image bytes from HA, send to Plate Recognizer API."""
        session = async_get_clientsession(self.hass)

        data = aiohttp.FormData()
        data.add_field(
            "upload",
            io.BytesIO(image),
            filename="image.jpg",
            content_type="image/jpeg",
        )

        for region in self._regions:
            data.add_field("regions", region)

        if self._mmc:
            data.add_field("mmc", "true")

        config_parts: list[str] = []
        if self._detection_rule and self._detection_rule != "none":
            config_parts.append(f'"detection_rule":"{self._detection_rule}"')
        if self._region_mode and self._region_mode != "none":
            config_parts.append(f'"region":"{self._region_mode}"')
        if config_parts:
            data.add_field("config", "{" + ",".join(config_parts) + "}")

        try:
            async with session.post(
                self._api_url,
                headers=self._auth_headers,
                data=data,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status not in (200, 201):
                    _LOGGER.error(
                        "Plate Recognizer API error HTTP %s: %s",
                        resp.status,
                        await resp.text(),
                    )
                    return
                payload = await resp.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Connection error calling Plate Recognizer: %s", err)
            return

        self._handle_response(payload, image)

    # ------------------------------------------------------------------ #
    # Response handling                                                     #
    # ------------------------------------------------------------------ #

    def _handle_response(self, payload: dict[str, Any], image: bytes) -> None:
        """Parse the API response and update entity state."""
        results: list[dict] = payload.get("results", [])
        usage: dict = payload.get("usage", {})

        self._plates = []
        detected_plates: list[str] = []

        for vehicle in results:
            # Pick the highest-confidence candidate
            candidates = vehicle.get("candidates", [])
            if candidates:
                best = max(candidates, key=lambda c: c.get("score", 0))
                plate_str = best.get("plate", vehicle.get("plate", "")).upper()
                confidence = best.get("score", vehicle.get("score", 0.0))
            else:
                plate_str = vehicle.get("plate", "").upper()
                confidence = vehicle.get("score", 0.0)

            region_code = vehicle.get("region", {}).get("code", "unknown")
            vehicle_type = vehicle.get("vehicle", {}).get("type", "unknown")

            plate_info: dict[str, Any] = {
                ATTR_PLATE: plate_str,
                ATTR_CONFIDENCE: round(confidence, 3),
                ATTR_REGION: region_code,
                ATTR_VEHICLE_TYPE: vehicle_type,
            }

            if self._mmc:
                vdata = vehicle.get("vehicle", {})
                try:
                    plate_info[ATTR_ORIENTATION] = (
                        vdata.get("orientation", [{}])[0].get("orientation", "unknown")
                    )
                    plate_info[ATTR_MMC] = {
                        "make": vdata.get("make", [{}])[0].get("name", "unknown"),
                        "model": vdata.get("model", [{}])[0].get("name", "unknown"),
                        "color": vdata.get("color", [{}])[0].get("name", "unknown"),
                    }
                except (IndexError, KeyError, TypeError):
                    pass

            self._plates.append(plate_info)
            detected_plates.append(plate_str)

            self.hass.bus.fire(
                EVENT_VEHICLE_DETECTED,
                {"entity_id": self.entity_id, **plate_info},
            )

        # Fuzzy match watched plates
        if self._watched_plates:
            self._watched_plate_status = {
                wp: any(self._fuzzy_match(wp, dp) for dp in detected_plates)
                for wp in self._watched_plates
            }

        # Usage stats
        if usage:
            max_calls = usage.get("max_calls", usage.get("total_calls", 0))
            calls_used = usage.get("calls", 0)
            self._statistics = {
                ATTR_CALLS_REMAINING: max_calls - calls_used,
                "calls_used": calls_used,
                "max_calls": max_calls,
            }

        if results:
            self._last_detection = utcnow().isoformat()

        # Optional image saving (sync write — acceptable for occasional saves)
        if self._save_folder and (results or self._always_save_latest):
            self.hass.async_create_task(self._async_save_image(image, bool(results)))

    # ------------------------------------------------------------------ #
    # Helpers                                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _fuzzy_match(watched: str, detected: str, tolerance: int = 2) -> bool:
        """Return True if plates are within `tolerance` character differences."""
        w, d = watched.lower(), detected.lower()
        if w == d:
            return True
        if abs(len(w) - len(d)) > tolerance:
            return False
        mismatches = sum(c1 != c2 for c1, c2 in zip(w, d)) + abs(len(w) - len(d))
        return mismatches <= tolerance

    async def _async_save_image(self, image: bytes, had_detections: bool) -> None:
        """Save processed image to disk (runs in executor to avoid blocking)."""
        folder = Path(self._save_folder)
        try:
            await self.hass.async_add_executor_job(folder.mkdir, True, True)
        except OSError as err:
            _LOGGER.error("Cannot create save folder %s: %s", folder, err)
            return

        camera_slug = self._attr_camera_entity.replace("camera.", "").replace(".", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        def _write(path: Path, data: bytes) -> None:
            path.write_bytes(data)

        if self._always_save_latest:
            await self.hass.async_add_executor_job(
                _write, folder / f"{camera_slug}_latest.jpg", image
            )

        if self._save_timestamped and had_detections:
            await self.hass.async_add_executor_job(
                _write, folder / f"{camera_slug}_{timestamp}.jpg", image
            )