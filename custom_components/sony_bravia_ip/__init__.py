"""Sony Bravia TV (IP Control) integration."""
from __future__ import annotations

from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SonyBraviaClient
from .const import CONF_PSK
from .coordinator import SonyBraviaCoordinator, SonyConfigEntry

PLATFORMS: list[Platform] = [
    Platform.MEDIA_PLAYER,
    Platform.REMOTE,
    Platform.SELECT,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: SonyConfigEntry) -> bool:
    client = SonyBraviaClient(
        entry.data[CONF_HOST], entry.data[CONF_PSK], async_get_clientsession(hass)
    )
    coordinator = SonyBraviaCoordinator(hass, entry, client)
    await coordinator.async_load_static(force=True)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SonyConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: SonyConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
