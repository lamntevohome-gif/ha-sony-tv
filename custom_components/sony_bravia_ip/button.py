"""Buttons for common remote keys + reboot."""
from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SonyBraviaCoordinator, SonyConfigEntry
from .entity import SonyBraviaEntity

KEYS: dict[str, str] = {
    "home": "Home",
    "back": "Return",
    "input": "Input",
    "options": "Options",
    "netflix": "Netflix",
    "guide": "Guide",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SonyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    c = entry.runtime_data
    entities: list[ButtonEntity] = [KeyButton(c, k, v) for k, v in KEYS.items()]
    entities.append(RebootButton(c))
    async_add_entities(entities)


class KeyButton(SonyBraviaEntity, ButtonEntity):
    def __init__(self, coordinator: SonyBraviaCoordinator, key: str, command: str) -> None:
        super().__init__(coordinator, f"key_{key}")
        self._attr_translation_key = key
        self._command = command

    async def async_press(self) -> None:
        await self.coordinator.async_send_command(self._command)


class RebootButton(SonyBraviaEntity, ButtonEntity):
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: SonyBraviaCoordinator) -> None:
        super().__init__(coordinator, "reboot")

    async def async_press(self) -> None:
        await self.coordinator.client.reboot()
