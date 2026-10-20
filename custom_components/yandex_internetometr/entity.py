"""Shared base entity."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import InternetometrCoordinator


class InternetometrEntity(CoordinatorEntity[InternetometrCoordinator]):
    """Entity attached to the single Internetometr device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: InternetometrCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Интернетометр",
            manufacturer="Яндекс",
            model="Интернетометр",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://yandex.ru/internet",
        )
