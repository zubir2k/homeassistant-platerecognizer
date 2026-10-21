"""Config and options flow for Plate Recognizer."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CLOUD_DASHBOARD_URL,
    CLOUD_USAGE_URL,
    DEFAULT_SDK_URL,
    DOMAIN,
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
)
from .scanner import snapshot_dir_error


async def _check_connection(hass: HomeAssistant, data: dict[str, Any]) -> str | None:
    """Return an error key, or None when the token / SDK answers."""
    if data.get(OPT_LOCAL_SDK):
        url = f"{str(data.get(OPT_SDK_URL) or DEFAULT_SDK_URL).rstrip('/')}/info/"
        headers: dict[str, str] = {}
    else:
        url = CLOUD_USAGE_URL
        headers = {"Authorization": f"Token {data.get(OPT_TOKEN, '')}"}
    session = async_get_clientsession(hass)
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                return None
            if resp.status in (401, 403):
                return "invalid_auth"
            return "cannot_connect"
    except (aiohttp.ClientError, TimeoutError):
        return "cannot_connect"


class PlateRecognizerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a camera."""

    VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[OPT_CAMERA])
            self._abort_if_unique_id_configured()
            if (error := await _check_connection(self.hass, user_input)) is None:
                camera = self.hass.states.get(user_input[OPT_CAMERA])
                title = camera.name if camera else user_input[OPT_CAMERA]
                return self.async_create_entry(title=title, data=user_input)
            errors["base"] = error

        schema = vol.Schema(
            {
                vol.Required(OPT_CAMERA): EntitySelector(EntitySelectorConfig(domain="camera")),
                vol.Optional(OPT_TOKEN, default=""): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
                vol.Optional(OPT_LOCAL_SDK, default=False): BooleanSelector(),
                vol.Optional(OPT_SDK_URL, default=DEFAULT_SDK_URL): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.URL)
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
            description_placeholders={"dashboard_url": CLOUD_DASHBOARD_URL},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> PlateRecognizerOptionsFlow:
        return PlateRecognizerOptionsFlow()


class PlateRecognizerOptionsFlow(OptionsFlow):
    """Tune how scans are made and stored."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            folder = str(user_input.get(OPT_SNAPSHOT_DIR) or "").strip()
            user_input[OPT_SNAPSHOT_DIR] = folder
            if error := snapshot_dir_error(self.hass, folder):
                errors[OPT_SNAPSHOT_DIR] = error
            else:
                return self.async_create_entry(data=user_input)

        text = TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT))
        schema = vol.Schema(
            {
                vol.Optional(OPT_COUNTRIES, default=""): text,
                vol.Optional(OPT_WATCHLIST, default=""): text,
                vol.Optional(OPT_PLATE_IN_VEHICLE_ONLY, default=False): BooleanSelector(),
                vol.Optional(OPT_MATCH_COUNTRY_FORMAT, default=False): BooleanSelector(),
                vol.Optional(OPT_VEHICLE_DETAILS, default=False): BooleanSelector(),
                vol.Optional(OPT_SNAPSHOT_DIR, default=""): text,
                vol.Optional(OPT_SNAPSHOT_KEEP_HISTORY, default=False): BooleanSelector(),
                vol.Optional(OPT_SNAPSHOT_EVERY_SCAN, default=False): BooleanSelector(),
            }
        )
        current = {**self.config_entry.data, **self.config_entry.options, **(user_input or {})}
        for key in (OPT_COUNTRIES, OPT_WATCHLIST):
            if isinstance(current.get(key), list):
                current[key] = ", ".join(current[key])
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, current),
            errors=errors,
        )
