"""Selects: input/app source, picture mode, sound output."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SonyBraviaCoordinator, SonyConfigEntry
from .entity import SonyBraviaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SonyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    c = entry.runtime_data
    async_add_entities(
        [SourceSelect(c), PictureModeSelect(c), SoundOutputSelect(c)]
    )


class SourceSelect(SonyBraviaEntity, SelectEntity):
    _attr_translation_key = "source"

    def __init__(self, coordinator: SonyBraviaCoordinator) -> None:
        super().__init__(coordinator, "source")

    @property
    def available(self) -> bool:
        return super().available and self.is_on and bool(self.options)

    @property
    def options(self) -> list[str]:
        return list(self.coordinator.sources)

    @property
    def current_option(self) -> str | None:
        cur = self.coordinator.current_source()
        return cur if cur in self.options else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_select_source(option)
        await self.coordinator.async_request_refresh()


class PictureModeSelect(SonyBraviaEntity, SelectEntity):
    _attr_translation_key = "picture_mode"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: SonyBraviaCoordinator) -> None:
        super().__init__(coordinator, "picture_mode")

    @property
    def available(self) -> bool:
        return super().available and self.is_on and bool(self.coordinator.data.picture_modes)

    @property
    def options(self) -> list[str]:
        return self.coordinator.data.picture_modes or []

    @property
    def current_option(self) -> str | None:
        return self.coordinator.data.picture_mode

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.client.set_picture_setting("pictureMode", option)
        await self.coordinator.async_request_refresh()


class SoundOutputSelect(SonyBraviaEntity, SelectEntity):
    _attr_translation_key = "sound_output"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: SonyBraviaCoordinator) -> None:
        super().__init__(coordinator, "sound_output")

    @property
    def available(self) -> bool:
        return super().available and self.is_on and bool(self.coordinator.data.sound_outputs)

    @property
    def options(self) -> list[str]:
        return self.coordinator.data.sound_outputs or []

    @property
    def current_option(self) -> str | None:
        return self.coordinator.data.sound_output

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.client.set_sound_setting("outputTerminal", option)
        await self.coordinator.async_request_refresh()
