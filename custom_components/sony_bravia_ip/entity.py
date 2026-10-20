"""Base entity for Sony Bravia TV."""
from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import SonyBraviaCoordinator


class SonyBraviaEntity(CoordinatorEntity[SonyBraviaCoordinator]):
    """Common device info."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SonyBraviaCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        base_id = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{base_id}_{key}"
        info = coordinator.system_info
        connections = set()
        if mac := info.get("macAddr"):
            connections.add((CONNECTION_NETWORK_MAC, mac.lower()))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, base_id)},
            connections=connections,
            manufacturer=MANUFACTURER,
            model=info.get("model"),
            name=entry.title,
            serial_number=info.get("serial") or None,
            sw_version=info.get("generation"),
            configuration_url=f"http://{coordinator.client.host}",
        )

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data and self.coordinator.data.power)
