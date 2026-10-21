"""Per-camera scan runtime shared by the entity platforms."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
import io
import json
import logging
from pathlib import Path
from typing import Any

import aiohttp

from homeassistant.components.camera import async_get_image
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import (
    CLOUD_READ_URL,
    CLOUD_USAGE_URL,
    DEFAULT_SDK_URL,
    EVENT_PLATE_READ,
    OPT_CAMERA,
    OPT_COUNTRIES,
    OPT_LOCAL_SDK,
    OPT_MATCH_COUNTRY_FORMAT,
    OPT_PLATE_IN_VEHICLE_ONLY,
    OPT_SDK_URL,
    OPT_SNAPSHOT_DIR,
    OPT_SNAPSHOT_EVERY_SCAN,
    OPT_SNAPSHOT_KEEP_HISTORY,
    OPT_TOKEN,
    OPT_VEHICLE_DETAILS,
    OPT_WATCHLIST,
    WATCHLIST_TOLERANCE,
)

_LOGGER = logging.getLogger(__name__)


def split_csv(value: Any) -> list[str]:
    """Turn a comma separated string (or list) into a clean upper-case list."""
    items = value if isinstance(value, list) else str(value or "").split(",")
    return [str(item).strip().upper() for item in items if str(item).strip()]


def near_match(wanted: str, seen: str) -> bool:
    """True when two plates differ by at most WATCHLIST_TOLERANCE characters."""
    if wanted == seen:
        return True
    if abs(len(wanted) - len(seen)) > WATCHLIST_TOLERANCE:
        return False
    misses = sum(a != b for a, b in zip(wanted, seen)) + abs(len(wanted) - len(seen))
    return misses <= WATCHLIST_TOLERANCE


def draw_reads(frame: bytes, reads: list[dict[str, Any]]) -> bytes:
    """Return the frame with an outline and label around every plate."""
    try:
        from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415
    except ImportError:
        return frame
    try:
        picture = Image.open(io.BytesIO(frame)).convert("RGB")
        pen = ImageDraw.Draw(picture)
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24
            )
        except OSError:
            font = ImageFont.load_default()
        for read in reads:
            box = read["box"]
            corners = [box["xmin"], box["ymin"], box["xmax"], box["ymax"]]
            pen.rectangle(corners, outline="red", width=4)
            caption = f"{read['plate']} {read['score']:.0%}"
            anchor = (box["xmin"], max(box["ymin"] - 28, 0))
            pen.rectangle(pen.textbbox(anchor, caption, font=font), fill="red")
            pen.text(anchor, caption, fill="white", font=font)
        buffer = io.BytesIO()
        picture.save(buffer, format="JPEG", quality=90)
        return buffer.getvalue()
    except (OSError, ValueError) as err:
        _LOGGER.warning("Could not draw plate outlines: %s", err)
        return frame


@dataclass
class ScanResult:
    """Outcome of the most recent scan."""

    reads: list[dict[str, Any]] = field(default_factory=list)
    watchlist: dict[str, bool] = field(default_factory=dict)
    scanned_at: datetime | None = None
    frame: bytes | None = None


def snapshot_dir_error(hass: HomeAssistant, folder: str) -> str | None:
    """Return an error key when frames must not be written to this folder.

    Anything under /config/www is served at /local/ without authentication,
    so camera frames are never written there. The folder must also be on
    Home Assistant's allowlist (allowlist_external_dirs, which includes the
    media folders by default).
    """
    if not folder:
        return None
    path = Path(folder)
    if not path.is_absolute():
        return "snapshot_dir_not_absolute"
    resolved = path.resolve()
    www = Path(hass.config.path("www")).resolve()
    if resolved == www or www in resolved.parents:
        return "snapshot_dir_public"
    if not hass.config.is_allowed_path(str(resolved)):
        return "snapshot_dir_not_allowed"
    return None


class PlateScanner:
    """Grabs a camera frame, sends it to Plate Recognizer and keeps the result."""

    def __init__(self, hass: HomeAssistant, entry_id: str, settings: dict[str, Any]) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.camera: str = settings[OPT_CAMERA]
        self._token: str = settings.get(OPT_TOKEN, "")
        self._local: bool = settings.get(OPT_LOCAL_SDK, False)
        self._sdk_url: str = str(settings.get(OPT_SDK_URL) or DEFAULT_SDK_URL).rstrip("/")
        self._countries = [c.lower() for c in split_csv(settings.get(OPT_COUNTRIES))]
        self.watchlist = split_csv(settings.get(OPT_WATCHLIST))
        self._vehicle_only: bool = settings.get(OPT_PLATE_IN_VEHICLE_ONLY, False)
        self._country_format: bool = settings.get(OPT_MATCH_COUNTRY_FORMAT, False)
        self._vehicle_details: bool = settings.get(OPT_VEHICLE_DETAILS, False)
        self._snapshot_dir: str = str(settings.get(OPT_SNAPSHOT_DIR) or "").strip()
        self._keep_history: bool = settings.get(OPT_SNAPSHOT_KEEP_HISTORY, False)
        self._every_scan: bool = settings.get(OPT_SNAPSHOT_EVERY_SCAN, False)
        if self._snapshot_dir and (problem := snapshot_dir_error(hass, self._snapshot_dir)):
            _LOGGER.warning(
                "Not saving frames for %s to %s (%s); pick another folder in the options",
                self.camera,
                self._snapshot_dir,
                problem,
            )
            self._snapshot_dir = ""

        self.result = ScanResult(watchlist={p: False for p in self.watchlist})
        self.usage: dict[str, Any] = {}
        self._listeners: list[Callable[[], None]] = []

    @callback
    def add_listener(self, update: Callable[[], None]) -> CALLBACK_TYPE:
        """Register an entity callback, returns the remover."""
        self._listeners.append(update)

        @callback
        def _remove() -> None:
            self._listeners.remove(update)

        return _remove

    @callback
    def _notify(self) -> None:
        for update in list(self._listeners):
            update()

    @property
    def is_local(self) -> bool:
        """True when talking to a self-hosted SDK instead of the cloud."""
        return self._local

    @property
    def _headers(self) -> dict[str, str]:
        return {} if self._local else {"Authorization": f"Token {self._token}"}

    async def async_scan(self) -> None:
        """Run one scan of the configured camera."""
        try:
            image = await async_get_image(self.hass, self.camera)
        except HomeAssistantError as err:
            raise HomeAssistantError(f"Cannot get a frame from {self.camera}: {err}") from err

        form = aiohttp.FormData()
        form.add_field("upload", image.content, filename="frame.jpg", content_type="image/jpeg")
        form.add_field("camera_id", self.camera)
        for country in self._countries:
            form.add_field("regions", country)
        if self._vehicle_details:
            form.add_field("mmc", "true")
        engine: dict[str, str] = {}
        if self._vehicle_only:
            engine["detection_rule"] = "strict"
        if self._country_format:
            engine["region"] = "strict"
        if engine:
            form.add_field("config", json.dumps(engine))

        url = f"{self._sdk_url}/v1/plate-reader/" if self._local else CLOUD_READ_URL
        session = async_get_clientsession(self.hass)
        try:
            async with session.post(
                url, headers=self._headers, data=form, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status not in (200, 201):
                    raise HomeAssistantError(
                        f"Plate Recognizer returned HTTP {resp.status}: {await resp.text()}"
                    )
                body = await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise HomeAssistantError(f"Cannot reach Plate Recognizer: {err!r}") from err

        reads = [self._to_read(item) for item in body.get("results", [])]
        seen = [read["plate"] for read in reads]
        watch = {wanted: any(near_match(wanted, plate) for plate in seen) for wanted in self.watchlist}

        frame = await self.hass.async_add_executor_job(draw_reads, image.content, reads)
        self.result = ScanResult(reads=reads, watchlist=watch, scanned_at=dt_util.utcnow(), frame=frame)

        for read in reads:
            self.hass.bus.async_fire(
                EVENT_PLATE_READ,
                {
                    "config_entry_id": self.entry_id,
                    "camera": self.camera,
                    "on_watchlist": any(near_match(w, read["plate"]) for w in self.watchlist),
                    **read,
                },
            )

        if self._snapshot_dir and (reads or self._every_scan):
            try:
                await self.hass.async_add_executor_job(
                    self._write_snapshot, image.content, bool(reads)
                )
            except OSError as err:
                _LOGGER.error("Could not save snapshot to %s: %s", self._snapshot_dir, err)

        await self.async_refresh_usage()
        self._notify()

    def _to_read(self, item: dict[str, Any]) -> dict[str, Any]:
        """Flatten one API result into what the entities and event expose."""
        best = max(item.get("candidates") or [item], key=lambda c: c.get("score", 0))
        vehicle = item.get("vehicle") or {}
        read: dict[str, Any] = {
            "plate": str(best.get("plate", item.get("plate", ""))).upper(),
            "score": round(float(best.get("score", item.get("score", 0.0))), 3),
            "country": (item.get("region") or {}).get("code"),
            "vehicle": vehicle.get("type"),
            "box": {k: (item.get("box") or {}).get(k, 0) for k in ("xmin", "ymin", "xmax", "ymax")},
        }
        if self._vehicle_details:
            def first(key: str) -> dict[str, Any]:
                values = item.get(key) or []
                return values[0] if values else {}

            read["make"] = first("model_make").get("make")
            read["model"] = first("model_make").get("model")
            read["color"] = first("color").get("color")
            read["orientation"] = first("orientation").get("orientation")
        return read

    async def async_refresh_usage(self) -> None:
        """Read the cloud account usage (not available for the local SDK)."""
        if self._local:
            return
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                CLOUD_USAGE_URL, headers=self._headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return
                body = await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.debug("Usage lookup failed: %r", err)
            return
        allowance = body.get("total_calls", 0)
        used = (body.get("usage") or {}).get("calls", 0)
        self.usage = {
            "allowance": allowance,
            "used": used,
            "remaining": allowance - used,
            "resets_on": body.get("resets_on"),
        }

    def _write_snapshot(self, frame: bytes, found: bool) -> None:
        folder = Path(self._snapshot_dir)
        folder.mkdir(parents=True, exist_ok=True)
        name = self.camera.split(".", 1)[-1]
        (folder / f"{name}_last.jpg").write_bytes(frame)
        if self._keep_history and found:
            stamp = dt_util.now().strftime("%Y%m%d_%H%M%S")
            (folder / f"{name}_{stamp}.jpg").write_bytes(frame)
