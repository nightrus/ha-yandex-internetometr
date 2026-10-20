"""«Измерить сейчас» button."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import InternetometrConfigEntry
from .entity import InternetometrEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InternetometrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([InternetometrRunButton(entry.runtime_data, "run_now")])


class InternetometrRunButton(InternetometrEntity, ButtonEntity):
    """Starts a measurement; `in_progress` is true while one runs."""

    @property
    def available(self) -> bool:
        return True

    @property
    def icon(self) -> str:
        return "mdi:progress-clock" if self.coordinator.running else "mdi:speedometer"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"in_progress": self.coordinator.running}

    async def async_press(self) -> None:
        if not self.coordinator.running:
            await self.coordinator.async_refresh()
