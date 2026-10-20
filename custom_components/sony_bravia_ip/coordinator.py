"""Data coordinator for Sony Bravia TV."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import (
    SonyBraviaAuthError,
    SonyBraviaClient,
    SonyBraviaConnectionError,
    SonyBraviaError,
    send_wol,
)
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SOURCES,
    DEFAULT_IRCC_CODES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    IRCC_ALIASES,
    SOURCE_APP,
    SOURCE_INPUT,
    STATIC_REFRESH,
)

_LOGGER = logging.getLogger(__name__)

type SonyConfigEntry = ConfigEntry[SonyBraviaCoordinator]


@dataclass
class SonyBraviaData:
    """Live state of the TV."""

    power: bool = False
    volume: int | None = None
    max_volume: int = 100
    muted: bool = False
    volume_target: str = "speaker"
    playing: dict[str, Any] | None = None
    picture_mode: str | None = None
    picture_modes: list[str] = field(default_factory=list)
    sound_output: str | None = None
    sound_outputs: list[str] = field(default_factory=list)


class SonyBraviaCoordinator(DataUpdateCoordinator[SonyBraviaData]):
    """Poll the TV and hold static lists (inputs, apps, IRCC codes)."""

    config_entry: SonyConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: SonyConfigEntry, client: SonyBraviaClient
    ) -> None:
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.client = client
        self.system_info: dict[str, Any] = {}
        self.inputs: list[dict[str, Any]] = []
        self.apps: list[dict[str, Any]] = []
        self.ircc_codes: dict[str, str] = dict(DEFAULT_IRCC_CODES)
        self._static_ts = 0.0
        self._last_volume_target = "speaker"

    # ----------------------------------------------------------- static data
    async def async_load_static(self, force: bool = False) -> None:
        if not force and time.monotonic() - self._static_ts < STATIC_REFRESH:
            return
        if not self.system_info:
            try:
                self.system_info = await self.client.get_system_info()
            except SonyBraviaError as err:
                _LOGGER.debug("System info unavailable: %s", err)
        try:
            codes = await self.client.get_remote_codes()
            if codes:
                self.ircc_codes = {**DEFAULT_IRCC_CODES, **codes}
        except SonyBraviaError as err:
            _LOGGER.debug("Remote codes unavailable: %s", err)
        try:
            self.inputs = await self.client.get_external_inputs()
        except SonyBraviaError as err:
            _LOGGER.debug("Inputs unavailable: %s", err)
        try:
            self.apps = await self.client.get_apps()
        except SonyBraviaError as err:
            _LOGGER.debug("Apps unavailable: %s", err)
        if self.inputs or self.apps:
            self._static_ts = time.monotonic()

    # ------------------------------------------------------------- polling
    async def _async_update_data(self) -> SonyBraviaData:
        client = self.client
        try:
            power = await client.get_power_status()
        except SonyBraviaAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SonyBraviaError:
            # Fully off / network standby disabled: report "off" so turn_on (WoL) works.
            return SonyBraviaData(power=False)

        data = SonyBraviaData(power=power)
        if not power:
            return data

        await self.async_load_static()

        async def _volume() -> None:
            try:
                vols = await client.get_volume_info()
            except SonyBraviaError:
                return
            if not vols:
                return
            vol = next((v for v in vols if v.get("target") == "speaker"), vols[0])
            data.volume = vol.get("volume")
            data.max_volume = vol.get("maxVolume") or 100
            data.muted = bool(vol.get("mute"))
            data.volume_target = vol.get("target") or "speaker"
            self._last_volume_target = data.volume_target

        async def _playing() -> None:
            try:
                data.playing = await client.get_playing_content()
            except SonyBraviaError:
                data.playing = None

        async def _picture() -> None:
            try:
                pm = await client.get_picture_setting("pictureMode")
            except SonyBraviaError:
                return
            if pm:
                data.picture_mode = pm.get("currentValue")
                data.picture_modes = [
                    c["value"] for c in pm.get("candidate", []) if "value" in c
                ]

        async def _sound() -> None:
            try:
                so = await client.get_sound_setting("outputTerminal")
            except SonyBraviaError:
                return
            if so:
                data.sound_output = so.get("currentValue")
                data.sound_outputs = [
                    c["value"] for c in so.get("candidate", []) if "value" in c
                ]

        await asyncio.gather(_volume(), _playing(), _picture(), _sound())
        return data

    # ------------------------------------------------------------- sources
    @property
    def all_sources(self) -> dict[str, tuple[str, str]]:
        """name -> (kind, uri). Input label (e.g. "Denon") wins over title."""
        sources: dict[str, tuple[str, str]] = {}
        for inp in self.inputs:
            name = inp.get("label") or inp.get("title")
            if name and inp.get("uri"):
                sources[name] = (SOURCE_INPUT, inp["uri"])
        for app in self.apps:
            name = app.get("title")
            if name and app.get("uri") and name not in sources:
                sources[name] = (SOURCE_APP, app["uri"])
        return sources

    @property
    def sources(self) -> dict[str, tuple[str, str]]:
        """Sources filtered by the options flow selection."""
        allowed = self.config_entry.options.get(CONF_SOURCES) or []
        all_src = self.all_sources
        if not allowed:
            return all_src
        return {n: all_src[n] for n in allowed if n in all_src}

    def current_source(self) -> str | None:
        playing = self.data.playing if self.data else None
        if not playing:
            return None
        uri = playing.get("uri", "")
        for name, (kind, s_uri) in self.all_sources.items():
            if kind == SOURCE_INPUT and s_uri == uri:
                return name
        if uri.startswith("tv:"):
            return "TV"
        return playing.get("title")

    # ------------------------------------------------------------- actions
    async def async_select_source(self, name: str) -> None:
        src = self.all_sources.get(name)
        if src is None:
            # Allow raw URIs / app titles typed by hand
            if name.startswith(("extInput:", "tv:")):
                await self.client.set_play_content(name)
                return
            if "://" in name or name.startswith("com.sony.dtv"):
                await self.client.set_active_app(name)
                return
            raise HomeAssistantError(f"Unknown source: {name}")
        kind, uri = src
        if kind == SOURCE_INPUT:
            await self.client.set_play_content(uri)
        else:
            await self.client.set_active_app(uri)

    async def async_launch_app(self, app: str) -> None:
        for item in self.apps:
            if app in (item.get("title"), item.get("uri")) or (
                item.get("title", "").lower() == app.lower()
            ):
                await self.client.set_active_app(item["uri"])
                return
        await self.client.set_active_app(app)

    def resolve_ircc(self, command: str) -> str:
        """Command name (case-insensitive / alias) or raw base64 code."""
        key = IRCC_ALIASES.get(command.lower(), command)
        for name, code in self.ircc_codes.items():
            if name.lower() == key.lower():
                return code
        if command.endswith("=") and len(command) >= 16:
            return command
        raise HomeAssistantError(f"Unknown IRCC command: {command}")

    async def async_send_command(self, command: str) -> None:
        await self.client.send_ircc(self.resolve_ircc(command))

    async def async_turn_on(self) -> None:
        mac = self.system_info.get("macAddr")
        if mac:
            try:
                await self.hass.async_add_executor_job(send_wol, mac)
            except (OSError, ValueError) as err:
                _LOGGER.debug("WoL failed: %s", err)
        try:
            await self.client.set_power(True)
        except SonyBraviaConnectionError:
            if not mac:
                raise HomeAssistantError(
                    "TV unreachable. Enable 'Remote start' on the TV."
                ) from None

    async def async_set_volume(self, level: float) -> None:
        max_vol = self.data.max_volume if self.data else 100
        await self.client.set_volume(round(level * max_vol), self._last_volume_target)

    async def async_volume_step(self, up: bool) -> None:
        await self.client.set_volume("+1" if up else "-1", self._last_volume_target)
