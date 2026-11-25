"""Per-camera scan runtime shared by the entity platforms."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
import io
import logging
from pathlib import Path
from typing import Any

from platerecognizer import (
    PlateRecognizerAuthError,
    PlateRecognizerClient,
    PlateRecognizerError,
)

from homeassistant.components.camera import async_get_image
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import (
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

    Touches the filesystem (Path.resolve), so run it in the executor.

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
        self._client = PlateRecognizerClient(
            api_token=self._token,
            local_sdk=self._local,
            sdk_url=self._sdk_url,
            session=async_get_clientsession(hass),
        )
        self._countries = [c.lower() for c in split_csv(settings.get(OPT_COUNTRIES))]
        self.watchlist = split_csv(settings.get(OPT_WATCHLIST))
        self._vehicle_only: bool = settings.get(OPT_PLATE_IN_VEHICLE_ONLY, False)
        self._country_format: bool = settings.get(OPT_MATCH_COUNTRY_FORMAT, False)
        self._vehicle_details: bool = settings.get(OPT_VEHICLE_DETAILS, False)
        self._snapshot_dir: str = str(settings.get(OPT_SNAPSHOT_DIR) or "").strip()
        self._keep_history: bool = settings.get(OPT_SNAPSHOT_KEEP_HISTORY, False)
        self._every_scan: bool = settings.get(OPT_SNAPSHOT_EVERY_SCAN, False)

        self.result = ScanResult(watchlist={p: False for p in self.watchlist})
        self.usage: dict[str, Any] = {}
        self._listeners: list[Callable[[], None]] = []
        self._scan_lock = asyncio.Lock()

    async def async_check_snapshot_dir(self) -> None:
        """Turn saving off when the folder is public or not allowed."""
        if not self._snapshot_dir:
            return
        problem = await self.hass.async_add_executor_job(
            snapshot_dir_error, self.hass, self._snapshot_dir
        )
        if problem:
            _LOGGER.warning(
                "Not saving frames for %s to %s (%s); pick another folder in the options",
                self.camera,
                self._snapshot_dir,
                problem,
            )
            self._snapshot_dir = ""

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

    async def async_scan(self) -> None:
        """Run one scan of the configured camera."""
        if self._scan_lock.locked():
            _LOGGER.warning(
                "Scan already in progress for %s, skipping duplicate request", self.camera
            )
            return

        async with self._scan_lock:
            try:
                image = await async_get_image(self.hass, self.camera)
            except HomeAssistantError as err:
                raise HomeAssistantError(f"Cannot get a frame from {self.camera}: {err}") from err

            try:
                plate_reads = await self._client.async_read_plate(
                    image.content,
                    camera_id=self.camera,
                    regions=self._countries,
                    vehicle_details=self._vehicle_details,
                    plate_in_vehicle_only=self._vehicle_only,
                    match_country_format=self._country_format,
                )
            except PlateRecognizerAuthError as err:
                if entry := self.hass.config_entries.async_get_entry(self.entry_id):
                    entry.async_start_reauth(self.hass)
                raise ConfigEntryAuthFailed("Invalid API token for Plate Recognizer") from err
            except PlateRecognizerError as err:
                raise HomeAssistantError(str(err)) from err

            reads = [
                read.to_dict(include_vehicle_details=self._vehicle_details)
                for read in plate_reads
            ]
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

    async def async_refresh_usage(self) -> None:
        """Read the cloud account usage (not available for the local SDK)."""
        if self._local:
            return
        try:
            usage = await self._client.async_get_usage()
        except PlateRecognizerAuthError:
            if entry := self.hass.config_entries.async_get_entry(self.entry_id):
                entry.async_start_reauth(self.hass)
            return
        except PlateRecognizerError as err:
            _LOGGER.debug("Usage lookup failed: %r", err)
            return
        if usage is not None:
            self.usage = usage.to_dict()

    def _write_snapshot(self, frame: bytes, found: bool) -> None:
        folder = Path(self._snapshot_dir)
        folder.mkdir(parents=True, exist_ok=True)
        name = self.camera.split(".", 1)[-1]
        (folder / f"{name}_last.jpg").write_bytes(frame)
        if self._keep_history and found:
            stamp = dt_util.now().strftime("%Y%m%d_%H%M%S")
            (folder / f"{name}_{stamp}.jpg").write_bytes(frame)
