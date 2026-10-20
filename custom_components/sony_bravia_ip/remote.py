"""Remote (IRCC) for Sony Bravia TV."""
from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    ATTR_NUM_REPEATS,
    DEFAULT_DELAY_SECS,
    RemoteEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SonyBraviaCoordinator, SonyConfigEntry
from .entity import SonyBraviaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SonyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([SonyBraviaRemote(entry.runtime_data)])


class SonyBraviaRemote(SonyBraviaEntity, RemoteEntity):
    """Send IRCC key codes."""

    _attr_translation_key = "remote"

    def __init__(self, coordinator: SonyBraviaCoordinator) -> None:
        super().__init__(coordinator, "remote")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"commands": sorted(self.coordinator.ircc_codes)}

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_turn_on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_power(False)
        await self.coordinator.async_request_refresh()

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        repeats = kwargs.get(ATTR_NUM_REPEATS, 1)
        delay = kwargs.get(ATTR_DELAY_SECS, DEFAULT_DELAY_SECS)
        codes = [self.coordinator.resolve_ircc(c) for c in command]
        for i in range(repeats):
            for j, code in enumerate(codes):
                await self.coordinator.client.send_ircc(code)
                if i < repeats - 1 or j < len(codes) - 1:
                    await asyncio.sleep(delay)
