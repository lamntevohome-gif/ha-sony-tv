"""Media player for Sony Bravia TV."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SonyBraviaCoordinator, SonyConfigEntry
from .entity import SonyBraviaEntity

SUPPORTED = (
    MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.PLAY_MEDIA
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SonyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([SonyBraviaMediaPlayer(entry.runtime_data)])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        "launch_app", {vol.Required("app"): cv.string}, "async_launch_app"
    )
    platform.async_register_entity_service(
        "play_content", {vol.Required("uri"): cv.string}, "async_play_content"
    )
    platform.async_register_entity_service(
        "set_picture_setting",
        {vol.Required("target"): cv.string, vol.Required("value"): cv.string},
        "async_set_picture_setting",
    )
    platform.async_register_entity_service(
        "set_sound_setting",
        {vol.Required("target"): cv.string, vol.Required("value"): cv.string},
        "async_set_sound_setting",
    )


class SonyBraviaMediaPlayer(SonyBraviaEntity, MediaPlayerEntity):
    """Sony Bravia TV."""

    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.TV
    _attr_supported_features = SUPPORTED

    def __init__(self, coordinator: SonyBraviaCoordinator) -> None:
        super().__init__(coordinator, "media_player")

    async def _refresh(self) -> None:
        await self.coordinator.async_request_refresh()

    # ---------------------------------------------------------------- state
    @property
    def state(self) -> MediaPlayerState:
        if not self.is_on:
            return MediaPlayerState.OFF
        return MediaPlayerState.PLAYING if self.coordinator.data.playing else MediaPlayerState.ON

    @property
    def volume_level(self) -> float | None:
        d = self.coordinator.data
        if not self.is_on or d.volume is None:
            return None
        return d.volume / (d.max_volume or 100)

    @property
    def is_volume_muted(self) -> bool | None:
        return self.coordinator.data.muted if self.is_on else None

    @property
    def source_list(self) -> list[str]:
        return list(self.coordinator.sources)

    @property
    def source(self) -> str | None:
        return self.coordinator.current_source() if self.is_on else None

    @property
    def _playing(self) -> dict[str, Any]:
        return (self.coordinator.data.playing or {}) if self.is_on else {}

    @property
    def media_content_type(self) -> MediaType | None:
        uri = self._playing.get("uri", "")
        if uri.startswith("tv:"):
            return MediaType.CHANNEL
        return MediaType.VIDEO if uri else None

    @property
    def media_content_id(self) -> str | None:
        return self._playing.get("uri")

    @property
    def media_title(self) -> str | None:
        p = self._playing
        if p.get("programTitle"):
            return p["programTitle"]
        return p.get("title") or self.source

    @property
    def media_channel(self) -> str | None:
        p = self._playing
        if p.get("dispNum"):
            return f"{p['dispNum']} {p.get('title', '')}".strip()
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self.coordinator.data
        return {
            "picture_mode": d.picture_mode if self.is_on else None,
            "sound_output": d.sound_output if self.is_on else None,
            "model": self.coordinator.system_info.get("model"),
        }

    # -------------------------------------------------------------- actions
    async def async_turn_on(self) -> None:
        await self.coordinator.async_turn_on()
        await self._refresh()

    async def async_turn_off(self) -> None:
        await self.coordinator.client.set_power(False)
        await self._refresh()

    async def async_set_volume_level(self, volume: float) -> None:
        await self.coordinator.async_set_volume(volume)
        await self._refresh()

    async def async_volume_up(self) -> None:
        await self.coordinator.async_volume_step(True)
        await self._refresh()

    async def async_volume_down(self) -> None:
        await self.coordinator.async_volume_step(False)
        await self._refresh()

    async def async_mute_volume(self, mute: bool) -> None:
        await self.coordinator.client.set_mute(mute)
        await self._refresh()

    async def async_select_source(self, source: str) -> None:
        await self.coordinator.async_select_source(source)
        await self._refresh()

    async def async_media_play(self) -> None:
        await self.coordinator.async_send_command("Play")

    async def async_media_pause(self) -> None:
        await self.coordinator.async_send_command("Pause")

    async def async_media_stop(self) -> None:
        await self.coordinator.async_send_command("Stop")

    async def async_media_next_track(self) -> None:
        cmd = "ChannelUp" if self.media_content_type == MediaType.CHANNEL else "Next"
        await self.coordinator.async_send_command(cmd)

    async def async_media_previous_track(self) -> None:
        cmd = "ChannelDown" if self.media_content_type == MediaType.CHANNEL else "Prev"
        await self.coordinator.async_send_command(cmd)

    async def async_play_media(
        self, media_type: MediaType | str, media_id: str, **kwargs: Any
    ) -> None:
        """media_type: app | channel | url | input; media_id: app name/uri or content uri."""
        if media_type in ("app", MediaType.APP):
            await self.coordinator.async_launch_app(media_id)
        elif media_id in self.coordinator.all_sources:
            await self.coordinator.async_select_source(media_id)
        else:
            await self.coordinator.client.set_play_content(media_id)
        await self._refresh()

    # ------------------------------------------------------ entity services
    async def async_launch_app(self, app: str) -> None:
        await self.coordinator.async_launch_app(app)
        await self._refresh()

    async def async_play_content(self, uri: str) -> None:
        await self.coordinator.client.set_play_content(uri)
        await self._refresh()

    async def async_set_picture_setting(self, target: str, value: str) -> None:
        await self.coordinator.client.set_picture_setting(target, value)
        await self._refresh()

    async def async_set_sound_setting(self, target: str, value: str) -> None:
        await self.coordinator.client.set_sound_setting(target, value)
        await self._refresh()
