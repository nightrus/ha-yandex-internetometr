"""Ping, download and upload sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfDataRate, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import KEY_DOWNLOAD, KEY_PING, KEY_UPLOAD
from .coordinator import InternetometrConfigEntry, InternetometrCoordinator
from .entity import InternetometrEntity

SENSORS = (
    (KEY_DOWNLOAD, SensorDeviceClass.DATA_RATE, UnitOfDataRate.MEGABITS_PER_SECOND, 0, "mdi:download"),
    (KEY_UPLOAD, SensorDeviceClass.DATA_RATE, UnitOfDataRate.MEGABITS_PER_SECOND, 0, "mdi:upload"),
    (KEY_PING, SensorDeviceClass.DURATION, UnitOfTime.MILLISECONDS, 1, "mdi:timer-outline"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InternetometrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(InternetometrSensor(entry.runtime_data, *spec) for spec in SENSORS)


class InternetometrSensor(InternetometrEntity, SensorEntity, RestoreEntity):
    """One measured value; keeps the last result across restarts."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: InternetometrCoordinator,
        key: str,
        device_class: SensorDeviceClass,
        unit: str,
        precision: int,
        icon: str,
    ) -> None:
        super().__init__(coordinator, key)
        self._key = key
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_suggested_display_precision = precision
        self._attr_icon = icon
        self._restored: float | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (state := await self.async_get_last_state()) is not None:
            try:
                self._restored = float(state.state)
            except ValueError:
                self._restored = None

    @property
    def available(self) -> bool:
        # A failed or skipped run keeps showing the last good value.
        return self.native_value is not None

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if data and data.get(self._key) is not None:
            return data[self._key]
        return self._restored

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        if not data:
            return None
        attrs: dict[str, Any] = {"measured_at": data.get("measured_at")}
        if self._key == KEY_DOWNLOAD:
            attrs["servers"] = data.get("servers")
            attrs["transferred_mb"] = round((data.get("download_bytes") or 0) / 1e6, 1)
        elif self._key == KEY_UPLOAD:
            attrs["transferred_mb"] = round((data.get("upload_bytes") or 0) / 1e6, 1)
        return attrs
