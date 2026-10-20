"""Config flow for Sony Bravia TV (IP Control)."""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SonyBraviaAuthError, SonyBraviaClient, SonyBraviaError
from .const import (
    CONF_PSK,
    CONF_SCAN_INTERVAL,
    CONF_SOURCES,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class SonyBraviaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def _validate(self, host: str, psk: str) -> tuple[dict[str, Any], str | None]:
        client = SonyBraviaClient(host, psk, async_get_clientsession(self.hass))
        try:
            info = await client.get_system_info()
            # getSystemInformation may not need auth; when the TV is on,
            # verify the PSK with a protected call too.
            if await client.get_power_status():
                await client.get_volume_info()
        except SonyBraviaAuthError:
            return {}, "invalid_auth"
        except SonyBraviaError as err:
            _LOGGER.debug("Validation failed: %s", err)
            return {}, "cannot_connect"
        return info, None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            info, error = await self._validate(user_input[CONF_HOST], user_input[CONF_PSK])
            if error:
                errors["base"] = error
            else:
                uid = info.get("serial") or info.get("macAddr") or info.get("cid")
                if uid:
                    await self.async_set_unique_id(str(uid).lower())
                    self._abort_if_unique_id_configured(
                        updates={CONF_HOST: user_input[CONF_HOST]}
                    )
                name = user_input.get(CONF_NAME) or info.get("model") or DEFAULT_NAME
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PSK: user_input[CONF_PSK],
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PSK, default="0000"): str,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            _, error = await self._validate(entry.data[CONF_HOST], user_input[CONF_PSK])
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PSK: user_input[CONF_PSK]}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PSK): str}),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            _, error = await self._validate(user_input[CONF_HOST], user_input[CONF_PSK])
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=entry.data[CONF_HOST]): str,
                vol.Required(CONF_PSK, default=entry.data[CONF_PSK]): str,
            }
        )
        return self.async_show_form(
            step_id="reconfigure", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return SonyBraviaOptionsFlow()


class SonyBraviaOptionsFlow(OptionsFlow):
    """Options: polling interval + which inputs/apps appear in the source list."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        coordinator = getattr(self.config_entry, "runtime_data", None)
        available: list[str] = []
        if coordinator is not None:
            await coordinator.async_load_static(force=True)
            available = list(coordinator.all_sources)
        current = [
            s for s in self.config_entry.options.get(CONF_SOURCES, []) if s in available
        ]

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=3, max=300)),
                vol.Optional(CONF_SOURCES, default=current): cv.multi_select(
                    {s: s for s in available}
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
