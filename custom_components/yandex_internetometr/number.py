"""Measurement interval (minutes, 0 = only on demand)."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    STEP_UPDATE_INTERVAL,
)
from .coordinator import InternetometrConfigEntry
from .entity import InternetometrEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InternetometrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([InternetometrInterval(entry.runtime_data, CONF_UPDATE_INTERVAL)])


class InternetometrInterval(InternetometrEntity, NumberEntity):
    """Stored in the config entry options, so it survives restarts."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:timer-cog-outline"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = MIN_UPDATE_INTERVAL
    _attr_native_max_value = MAX_UPDATE_INTERVAL
    _attr_native_step = STEP_UPDATE_INTERVAL
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> float:
        entry = self.coordinator.config_entry
        return entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    async def async_set_native_value(self, value: float) -> None:
        minutes = int(value)
        entry = self.coordinator.config_entry
        self.hass.config_entries.async_update_entry(
            entry, options={**entry.options, CONF_UPDATE_INTERVAL: minutes}
        )
        self.coordinator.set_interval(minutes)
        self.async_write_ha_state()
