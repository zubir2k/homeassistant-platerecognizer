<<<<<<< HEAD
"""Image processing platform for Plate Recognizer."""
from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Any

import aiohttp

from homeassistant.components.image_processing import ImageProcessingEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.dt import utcnow

from .const import (
    API_URL_CLOUD,
    API_URL_STATISTICS,
    ATTR_BOX_X_CENTRE,
    ATTR_BOX_Y_CENTRE,
    ATTR_CALLS_REMAINING,
    ATTR_CONFIDENCE,
    ATTR_MMC,
    ATTR_ORIENTATION,
    ATTR_PLATE,
    ATTR_REGION_CODE,
    ATTR_VEHICLE_TYPE,
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
    if isinstance(value, list):
        return [v.strip().lower() for v in value if v.strip()]
    if isinstance(value, str):
        return [v.strip().lower() for v in value.split(",") if v.strip()]
    return []


def _annotate_image(image: bytes, results: list[dict]) -> bytes:
    """Draw bounding boxes and plate labels onto image using PIL."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.open(io.BytesIO(image)).convert("RGB")
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24
            )
        except Exception:
            font = ImageFont.load_default()

        for r in results:
            box = r.get("box", {})
            xmin, ymin = box.get("xmin", 0), box.get("ymin", 0)
            xmax, ymax = box.get("xmax", 0), box.get("ymax", 0)
            plate = r.get("plate", "").upper()
            score = r.get("score", 0)

            # Bounding box — thicker line
            draw.rectangle([xmin, ymin, xmax, ymax], outline="red", width=4)

            # Label background + text above box
            label = f"{plate} {score:.0%}"
            bbox = draw.textbbox((xmin, ymin - 28), label, font=font)
            draw.rectangle(bbox, fill="red")
            draw.text((xmin, ymin - 28), label, fill="white", font=font)

        out = io.BytesIO()
        img.save(out, format="JPEG", quality=90)
        return out.getvalue()
    except ImportError:
        _LOGGER.debug("PIL not available — returning unannotated image")
        return image
    except Exception as err:
        _LOGGER.warning("Image annotation failed: %s", err)
        return image


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up via platform discovery (legacy image_processing style)."""
    if discovery_info is None:
        return
    entry_id = discovery_info["entry_id"]
    cfg = hass.data[DOMAIN][entry_id]
    entity = PlateRecognizerEntity(hass, entry_id, cfg)
    async_add_entities([entity], update_before_add=False)


class PlateRecognizerEntity(ImageProcessingEntity):
    """Plate Recognizer image processing entity."""

    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry_id: str, config: dict[str, Any]) -> None:
        self.hass = hass
        self._entry_id = entry_id

        self._attr_camera_entity: str = config[CONF_CAMERA_ENTITY]
        self._api_token: str = config.get(CONF_API_TOKEN, "")
        self._on_premise: bool = config.get(CONF_ON_PREMISE, DEFAULT_ON_PREMISE)
        self._server: str = config.get(CONF_SERVER, DEFAULT_SERVER).rstrip("/")

        self._regions: list[str] = _parse_list_option(config.get(CONF_REGIONS, []))
        self._watched_plates: list[str] = _parse_list_option(config.get(CONF_WATCHED_PLATES, []))
        self._detection_rule: str = config.get(CONF_DETECTION_RULE, DEFAULT_DETECTION_RULE)
        self._region_mode: str = config.get(CONF_REGION_MODE, DEFAULT_REGION_MODE)
        self._mmc: bool = config.get(CONF_MMC, DEFAULT_MMC)

        self._save_folder: str = config.get(CONF_SAVE_FILE_FOLDER, "")
        self._save_timestamped: bool = config.get(CONF_SAVE_TIMESTAMPED, DEFAULT_SAVE_TIMESTAMPED)
        self._always_save_latest: bool = config.get(CONF_ALWAYS_SAVE_LATEST, DEFAULT_ALWAYS_SAVE_LATEST)

        self._vehicles: list[dict[str, Any]] = []
        self._all_plates: list[str] = []
        self._watched_plate_status: dict[str, bool] = {p: False for p in self._watched_plates}
        self._statistics: dict[str, Any] = {}
        self._last_detection: str | None = None
        self._last_results: list[dict] = []

        camera_slug = self._attr_camera_entity.replace("camera.", "")
        self._camera_slug = camera_slug
        self._attr_name = f"platerecognizer_{camera_slug}"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}"

    @property
    def camera_entity(self) -> str:
        return self._attr_camera_entity

    @property
    def confidence(self) -> float | None:
        return self._vehicles[0].get(ATTR_CONFIDENCE) if self._vehicles else None

    @property
    def state(self) -> int:
        return len(self._vehicles)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "vehicles": self._vehicles,
            "statistics": self._statistics,
            "last_detection": self._last_detection,
        }
        if self._watched_plates:
            attrs["watched_plates"] = self._watched_plate_status
        if self._regions:
            attrs["regions"] = self._regions
        if self._detection_rule != "none":
            attrs["detection_rule"] = self._detection_rule
        if self._region_mode != "none":
            attrs["region_mode"] = self._region_mode
        attrs["mmc"] = self._mmc
        return attrs

    @property
    def _api_url(self) -> str:
        return f"{self._server}/v1/plate-reader/" if self._on_premise else API_URL_CLOUD

    @property
    def _auth_headers(self) -> dict[str, str]:
        return {} if self._on_premise else {"Authorization": f"Token {self._api_token}"}

    async def _async_fetch_statistics(self) -> None:
        if self._on_premise:
            return
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                API_URL_STATISTICS,
                headers=self._auth_headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    usage = data.get("usage", {})
                    total_calls = data.get("total_calls", 0)
                    calls_used = usage.get("calls", 0)
                    self._statistics = {
                        "total_calls": total_calls,
                        "calls_used": calls_used,
                        ATTR_CALLS_REMAINING: total_calls - calls_used,
                        **{k: v for k, v in usage.items() if k != "calls"},
                    }
        except aiohttp.ClientError as err:
            _LOGGER.warning("Could not fetch statistics: %s", err)

    def _push_image_to_entity(self, image: bytes) -> None:
        """Annotate image with bounding boxes and push to image entity."""
        entity = self.hass.data.get(DOMAIN, {}).get(f"image_entity_{self._entry_id}")
        if entity is None:
            return

        async def _annotate_and_push() -> None:
            annotated = await self.hass.async_add_executor_job(
                _annotate_image, image, self._last_results
            )
            entity.update_image(annotated, self._vehicles, dict(self._watched_plate_status))

        self.hass.async_create_task(_annotate_and_push())

    async def async_process_image(self, image: bytes) -> None:
        session = async_get_clientsession(self.hass)
        post_data = aiohttp.FormData()
        post_data.add_field(
            "upload", io.BytesIO(image),
            filename="image.jpg", content_type="image/jpeg",
        )
        post_data.add_field("camera_id", self._attr_camera_entity)

        for region in self._regions:
            post_data.add_field("regions", region)
        if self._mmc:
            post_data.add_field("mmc", "true")

        config_parts: list[str] = []
        if self._detection_rule and self._detection_rule != "none":
            config_parts.append(f'"detection_rule":"{self._detection_rule}"')
        if self._region_mode and self._region_mode != "none":
            config_parts.append(f'"region":"{self._region_mode}"')
        if config_parts:
            post_data.add_field("config", "{" + ",".join(config_parts) + "}")

        try:
            async with session.post(
                self._api_url,
                headers=self._auth_headers,
                data=post_data,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status not in (200, 201):
                    _LOGGER.error("API error HTTP %s: %s", resp.status, await resp.text())
                    return
                payload = await resp.json()
                _LOGGER.debug("API response: %s", payload)
        except aiohttp.ClientError as err:
            _LOGGER.error("Connection error: %s", err)
            return

        self._handle_response(payload)
        self._push_image_to_entity(image)

        if self._save_folder:
            self.hass.async_create_task(
                self._async_save_image(image, bool(self._vehicles))
            )
        await self._async_fetch_statistics()

    def _handle_response(self, payload: dict[str, Any]) -> None:
        results: list[dict] = payload.get("results", [])
        self._last_results = results

        usage = payload.get("usage", {})
        if usage:
            max_calls = usage.get("max_calls", usage.get("total_calls", 0))
            calls_used = usage.get("calls", 0)
            self._statistics = {**usage, ATTR_CALLS_REMAINING: max_calls - calls_used}

        self._vehicles = []
        self._all_plates = []

        for r in results:
            candidates = r.get("candidates", [])
            if candidates:
                best = max(candidates, key=lambda c: c.get("score", 0))
                plate_str = best.get("plate", r.get("plate", "")).upper()
                confidence = best.get("score", r.get("score", 0.0))
            else:
                plate_str = r.get("plate", "").upper()
                confidence = r.get("score", 0.0)

            box = r.get("box", {})
            vehicle: dict[str, Any] = {
                ATTR_PLATE: plate_str,
                ATTR_CONFIDENCE: round(confidence, 3),
                ATTR_REGION_CODE: r.get("region", {}).get("code", "unknown"),
                ATTR_VEHICLE_TYPE: r.get("vehicle", {}).get("type", "unknown"),
                ATTR_BOX_Y_CENTRE: round((box.get("ymin", 0) + box.get("ymax", 0)) / 2, 1),
                ATTR_BOX_X_CENTRE: round((box.get("xmin", 0) + box.get("xmax", 0)) / 2, 1),
            }

            if self._mmc:
                vdata = r.get("vehicle", {})
                try:
                    vehicle[ATTR_ORIENTATION] = vdata.get("orientation", [{}])[0].get("orientation", "unknown")
                    vehicle[ATTR_MMC] = {
                        "make": vdata.get("make", [{}])[0].get("name", "unknown"),
                        "model": vdata.get("model", [{}])[0].get("name", "unknown"),
                        "color": vdata.get("color", [{}])[0].get("name", "unknown"),
                    }
                except (IndexError, KeyError, TypeError):
                    pass

            self._vehicles.append(vehicle)
            self._all_plates.append(plate_str)
            self.hass.bus.fire(EVENT_VEHICLE_DETECTED, {"entity_id": self.entity_id, **vehicle})

        # Update watched plate status (kept in attributes for automation use)
        if self._watched_plates:
            detected_lower = [p.lower() for p in self._all_plates]
            self._watched_plate_status = {
                wp: wp.lower() in detected_lower or
                    any(self._fuzzy_match(wp, dp) for dp in detected_lower)
                for wp in self._watched_plates
            }

        if results:
            self._last_detection = utcnow().strftime("%Y-%m-%d_%H-%M-%S")

    async def _async_save_image(self, image: bytes, had_detections: bool) -> None:
        from pathlib import Path
        folder = Path(self._save_folder) if self._save_folder else Path("/config/www/platerecognizer")

        def _write_files() -> None:
            folder.mkdir(parents=True, exist_ok=True)
            slug = self._attr_camera_entity.replace("camera.", "").replace(".", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if self._always_save_latest or had_detections:
                (folder / f"{slug}_latest.jpg").write_bytes(image)
            if self._save_timestamped and had_detections:
                (folder / f"{slug}_{timestamp}.jpg").write_bytes(image)

        try:
            await self.hass.async_add_executor_job(_write_files)
        except OSError as err:
            _LOGGER.error("Failed to save image: %s", err)

    @staticmethod
    def _fuzzy_match(watched: str, detected: str, tolerance: int = 2) -> bool:
        w, d = watched.lower(), detected.lower()
        if w == d:
            return True
        if abs(len(w) - len(d)) > tolerance:
            return False
        return sum(c1 != c2 for c1, c2 in zip(w, d)) + abs(len(w) - len(d)) <= tolerance
=======
"""Image processing platform for Plate Recognizer."""
from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Any

import aiohttp

from homeassistant.components.image_processing import ImageProcessingEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.dt import utcnow

from .const import (
    API_URL_CLOUD,
    API_URL_STATISTICS,
    ATTR_BOX_X_CENTRE,
    ATTR_BOX_Y_CENTRE,
    ATTR_CALLS_REMAINING,
    ATTR_CONFIDENCE,
    ATTR_MMC,
    ATTR_ORIENTATION,
    ATTR_PLATE,
    ATTR_REGION_CODE,
    ATTR_VEHICLE_TYPE,
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
    if isinstance(value, list):
        return [v.strip().lower() for v in value if v.strip()]
    if isinstance(value, str):
        return [v.strip().lower() for v in value.split(",") if v.strip()]
    return []


def _annotate_image(image: bytes, results: list[dict]) -> bytes:
    """Draw bounding boxes and plate labels onto image using PIL."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.open(io.BytesIO(image)).convert("RGB")
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16
            )
        except Exception:
            font = ImageFont.load_default()

        for r in results:
            box = r.get("box", {})
            xmin, ymin = box.get("xmin", 0), box.get("ymin", 0)
            xmax, ymax = box.get("xmax", 0), box.get("ymax", 0)
            plate = r.get("plate", "").upper()
            score = r.get("score", 0)

            # Red bounding box
            draw.rectangle([xmin, ymin, xmax, ymax], outline="red", width=2)
            # Label above box
            label = f"{plate} {score:.0%}"
            bbox = draw.textbbox((xmin, ymin - 20), label, font=font)
            draw.rectangle(bbox, fill="red")
            draw.text((xmin, ymin - 20), label, fill="white", font=font)

        out = io.BytesIO()
        img.save(out, format="JPEG", quality=90)
        return out.getvalue()
    except ImportError:
        _LOGGER.debug("PIL not available — returning unannotated image")
        return image
    except Exception as err:
        _LOGGER.warning("Image annotation failed: %s", err)
        return image


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up via platform discovery (legacy image_processing style)."""
    if discovery_info is None:
        return
    entry_id = discovery_info["entry_id"]
    cfg = hass.data[DOMAIN][entry_id]
    entity = PlateRecognizerEntity(hass, entry_id, cfg)
    async_add_entities([entity], update_before_add=False)


class PlateRecognizerEntity(ImageProcessingEntity):
    """Plate Recognizer image processing entity."""

    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry_id: str, config: dict[str, Any]) -> None:
        self.hass = hass
        self._entry_id = entry_id

        self._attr_camera_entity: str = config[CONF_CAMERA_ENTITY]
        self._api_token: str = config.get(CONF_API_TOKEN, "")
        self._on_premise: bool = config.get(CONF_ON_PREMISE, DEFAULT_ON_PREMISE)
        self._server: str = config.get(CONF_SERVER, DEFAULT_SERVER).rstrip("/")

        self._regions: list[str] = _parse_list_option(config.get(CONF_REGIONS, []))
        self._watched_plates: list[str] = _parse_list_option(config.get(CONF_WATCHED_PLATES, []))
        self._detection_rule: str = config.get(CONF_DETECTION_RULE, DEFAULT_DETECTION_RULE)
        self._region_mode: str = config.get(CONF_REGION_MODE, DEFAULT_REGION_MODE)
        self._mmc: bool = config.get(CONF_MMC, DEFAULT_MMC)

        self._save_folder: str = config.get(CONF_SAVE_FILE_FOLDER, "")
        self._save_timestamped: bool = config.get(CONF_SAVE_TIMESTAMPED, DEFAULT_SAVE_TIMESTAMPED)
        self._always_save_latest: bool = config.get(CONF_ALWAYS_SAVE_LATEST, DEFAULT_ALWAYS_SAVE_LATEST)

        self._vehicles: list[dict[str, Any]] = []
        self._all_plates: list[str] = []
        self._watched_plate_status: dict[str, bool] = {p: False for p in self._watched_plates}
        self._statistics: dict[str, Any] = {}
        self._last_detection: str | None = None
        self._last_results: list[dict] = []  # raw API results for PIL annotation

        camera_slug = self._attr_camera_entity.replace("camera.", "")
        self._camera_slug = camera_slug
        self._attr_name = f"platerecognizer_{camera_slug}"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}"

    @property
    def camera_entity(self) -> str:
        return self._attr_camera_entity

    @property
    def confidence(self) -> float | None:
        return self._vehicles[0].get(ATTR_CONFIDENCE) if self._vehicles else None

    @property
    def state(self) -> int:
        return len(self._vehicles)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "vehicles": self._vehicles,
            "statistics": self._statistics,
            "last_detection": self._last_detection,
        }
        if self._watched_plates:
            attrs["watched_plates"] = self._watched_plate_status
        if self._regions:
            attrs["regions"] = self._regions
        if self._detection_rule != "none":
            attrs["detection_rule"] = self._detection_rule
        if self._region_mode != "none":
            attrs["region_mode"] = self._region_mode
        attrs["mmc"] = self._mmc
        return attrs

    @property
    def _api_url(self) -> str:
        return f"{self._server}/v1/plate-reader/" if self._on_premise else API_URL_CLOUD

    @property
    def _auth_headers(self) -> dict[str, str]:
        return {} if self._on_premise else {"Authorization": f"Token {self._api_token}"}

    async def _async_fetch_statistics(self) -> None:
        if self._on_premise:
            return
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                API_URL_STATISTICS,
                headers=self._auth_headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    usage = data.get("usage", {})
                    total_calls = data.get("total_calls", 0)
                    calls_used = usage.get("calls", 0)
                    self._statistics = {
                        "total_calls": total_calls,
                        "calls_used": calls_used,
                        ATTR_CALLS_REMAINING: total_calls - calls_used,
                        **{k: v for k, v in usage.items() if k != "calls"},
                    }
        except aiohttp.ClientError as err:
            _LOGGER.warning("Could not fetch statistics: %s", err)

    def _push_image_to_entity(self, image: bytes) -> None:
        """Annotate image with bounding boxes and push to image entity."""
        entity = self.hass.data.get(DOMAIN, {}).get(f"image_entity_{self._entry_id}")
        if entity is None:
            return

        async def _annotate_and_push() -> None:
            annotated = await self.hass.async_add_executor_job(
                _annotate_image, image, self._last_results
            )
            entity.update_image(annotated, self._vehicles)

        self.hass.async_create_task(_annotate_and_push())

    async def async_process_image(self, image: bytes) -> None:
        session = async_get_clientsession(self.hass)
        post_data = aiohttp.FormData()
        post_data.add_field(
            "upload", io.BytesIO(image),
            filename="image.jpg", content_type="image/jpeg",
        )
        post_data.add_field("camera_id", self._attr_camera_entity)

        for region in self._regions:
            post_data.add_field("regions", region)
        if self._mmc:
            post_data.add_field("mmc", "true")

        config_parts: list[str] = []
        if self._detection_rule and self._detection_rule != "none":
            config_parts.append(f'"detection_rule":"{self._detection_rule}"')
        if self._region_mode and self._region_mode != "none":
            config_parts.append(f'"region":"{self._region_mode}"')
        if config_parts:
            post_data.add_field("config", "{" + ",".join(config_parts) + "}")

        try:
            async with session.post(
                self._api_url,
                headers=self._auth_headers,
                data=post_data,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status not in (200, 201):
                    _LOGGER.error("API error HTTP %s: %s", resp.status, await resp.text())
                    return
                payload = await resp.json()
                _LOGGER.debug("API response: %s", payload)
        except aiohttp.ClientError as err:
            _LOGGER.error("Connection error: %s", err)
            return

        self._handle_response(payload)
        self._push_image_to_entity(image)

        if self._save_folder:
            self.hass.async_create_task(
                self._async_save_image(image, bool(self._vehicles))
            )
        await self._async_fetch_statistics()

    def _handle_response(self, payload: dict[str, Any]) -> None:
        results: list[dict] = payload.get("results", [])
        self._last_results = results

        usage = payload.get("usage", {})
        if usage:
            max_calls = usage.get("max_calls", usage.get("total_calls", 0))
            calls_used = usage.get("calls", 0)
            self._statistics = {**usage, ATTR_CALLS_REMAINING: max_calls - calls_used}

        self._vehicles = []
        self._all_plates = []

        for r in results:
            candidates = r.get("candidates", [])
            if candidates:
                best = max(candidates, key=lambda c: c.get("score", 0))
                plate_str = best.get("plate", r.get("plate", "")).upper()
                confidence = best.get("score", r.get("score", 0.0))
            else:
                plate_str = r.get("plate", "").upper()
                confidence = r.get("score", 0.0)

            box = r.get("box", {})
            vehicle: dict[str, Any] = {
                ATTR_PLATE: plate_str,
                ATTR_CONFIDENCE: round(confidence, 3),
                ATTR_REGION_CODE: r.get("region", {}).get("code", "unknown"),
                ATTR_VEHICLE_TYPE: r.get("vehicle", {}).get("type", "unknown"),
                ATTR_BOX_Y_CENTRE: round((box.get("ymin", 0) + box.get("ymax", 0)) / 2, 1),
                ATTR_BOX_X_CENTRE: round((box.get("xmin", 0) + box.get("xmax", 0)) / 2, 1),
            }

            if self._mmc:
                vdata = r.get("vehicle", {})
                try:
                    vehicle[ATTR_ORIENTATION] = vdata.get("orientation", [{}])[0].get("orientation", "unknown")
                    vehicle[ATTR_MMC] = {
                        "make": vdata.get("make", [{}])[0].get("name", "unknown"),
                        "model": vdata.get("model", [{}])[0].get("name", "unknown"),
                        "color": vdata.get("color", [{}])[0].get("name", "unknown"),
                    }
                except (IndexError, KeyError, TypeError):
                    pass

            self._vehicles.append(vehicle)
            self._all_plates.append(plate_str)
            self.hass.bus.fire(EVENT_VEHICLE_DETECTED, {"entity_id": self.entity_id, **vehicle})

        if self._watched_plates:
            detected_lower = [p.lower() for p in self._all_plates]
            self._watched_plate_status = {
                wp: wp.lower() in detected_lower or
                    any(self._fuzzy_match(wp, dp) for dp in detected_lower)
                for wp in self._watched_plates
            }

        if results:
            self._last_detection = utcnow().strftime("%Y-%m-%d_%H-%M-%S")

    async def _async_save_image(self, image: bytes, had_detections: bool) -> None:
        from pathlib import Path
        folder = Path(self._save_folder) if self._save_folder else Path("/config/www/platerecognizer")

        def _write_files() -> None:
            folder.mkdir(parents=True, exist_ok=True)
            slug = self._attr_camera_entity.replace("camera.", "").replace(".", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if self._always_save_latest or had_detections:
                (folder / f"{slug}_latest.jpg").write_bytes(image)
            if self._save_timestamped and had_detections:
                (folder / f"{slug}_{timestamp}.jpg").write_bytes(image)

        try:
            await self.hass.async_add_executor_job(_write_files)
        except OSError as err:
            _LOGGER.error("Failed to save image: %s", err)

    @staticmethod
    def _fuzzy_match(watched: str, detected: str, tolerance: int = 2) -> bool:
        w, d = watched.lower(), detected.lower()
        if w == d:
            return True
        if abs(len(w) - len(d)) > tolerance:
            return False
        return sum(c1 != c2 for c1, c2 in zip(w, d)) + abs(len(w) - len(d)) <= tolerance
>>>>>>> 6d11309c36a402dcef785300801a53539221bb28
