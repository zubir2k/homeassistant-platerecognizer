"""Config flow for Plate Recognizer integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.components.camera import DOMAIN as CAMERA_DOMAIN
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
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
    DETECTION_RULES,
    DOMAIN,
    REGION_MODES,
)

_LOGGER = logging.getLogger(__name__)


async def _validate_api_token(
    hass: HomeAssistant, token: str, on_premise: bool, server: str
) -> dict[str, str]:
    """Try a lightweight API call and return errors dict (empty = success)."""
    session = async_get_clientsession(hass)
    if on_premise:
        url = f"{server.rstrip('/')}/info/"
        headers: dict[str, str] = {}
    else:
        url = "https://api.platerecognizer.com/v1/statistics/"
        headers = {"Authorization": f"Token {token}"}

    try:
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status == 200:
                return {}
            if resp.status in (401, 403):
                return {"base": "invalid_auth"}
            return {"base": "cannot_connect"}
    except aiohttp.ClientConnectorError:
        return {"base": "cannot_connect"}
    except Exception:  # noqa: BLE001
        return {"base": "unknown"}


class PlateRecognizerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Plate Recognizer."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1 — API credentials and source camera."""
        errors: dict[str, str] = {}

        if user_input is not None:
            on_premise = user_input.get(CONF_ON_PREMISE, DEFAULT_ON_PREMISE)
            server = user_input.get(CONF_SERVER, DEFAULT_SERVER)
            token = user_input.get(CONF_API_TOKEN, "")

            errors = await _validate_api_token(hass=self.hass, token=token, on_premise=on_premise, server=server)

            if not errors:
                camera = user_input[CONF_CAMERA_ENTITY]
                title = f"Plate Recognizer — {camera}"
                return self.async_create_entry(title=title, data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(CONF_ON_PREMISE, default=DEFAULT_ON_PREMISE): BooleanSelector(),
                vol.Optional(CONF_API_TOKEN, default=""): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_SERVER, default=DEFAULT_SERVER): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.URL)
                ),
                vol.Required(CONF_CAMERA_ENTITY): EntitySelector(
                    EntitySelectorConfig(domain=CAMERA_DOMAIN)
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "dashboard_url": "https://app.platerecognizer.com/service/snapshot-cloud/"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "PlateRecognizerOptionsFlow":
        """Return the options flow."""
        return PlateRecognizerOptionsFlow()


class PlateRecognizerOptionsFlow(OptionsFlow):
    """Handle options for Plate Recognizer."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}

        def _list_to_str(val: Any) -> str:
            if isinstance(val, list):
                return ", ".join(val)
            return val or ""

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_REGIONS,
                    default=_list_to_str(current.get(CONF_REGIONS, "")),
                ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),

                vol.Optional(
                    CONF_WATCHED_PLATES,
                    default=_list_to_str(current.get(CONF_WATCHED_PLATES, "")),
                ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),

                vol.Optional(
                    CONF_DETECTION_RULE,
                    default=current.get(CONF_DETECTION_RULE, DEFAULT_DETECTION_RULE),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=DETECTION_RULES,
                        mode=SelectSelectorMode.LIST,
                    )
                ),

                vol.Optional(
                    CONF_REGION_MODE,
                    default=current.get(CONF_REGION_MODE, DEFAULT_REGION_MODE),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=REGION_MODES,
                        mode=SelectSelectorMode.LIST,
                    )
                ),

                vol.Optional(
                    CONF_MMC,
                    default=current.get(CONF_MMC, DEFAULT_MMC),
                ): BooleanSelector(),

                vol.Optional(
                    CONF_SAVE_FILE_FOLDER,
                    default=current.get(CONF_SAVE_FILE_FOLDER, ""),
                ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),

                vol.Optional(
                    CONF_SAVE_TIMESTAMPED,
                    default=current.get(CONF_SAVE_TIMESTAMPED, DEFAULT_SAVE_TIMESTAMPED),
                ): BooleanSelector(),

                vol.Optional(
                    CONF_ALWAYS_SAVE_LATEST,
                    default=current.get(CONF_ALWAYS_SAVE_LATEST, DEFAULT_ALWAYS_SAVE_LATEST),
                ): BooleanSelector(),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
