"""Yandex Internetometr — internet speed test for Home Assistant.

Fork of ha-yainternetometr / yaspeedtest by Nikita Erilov (Apache-2.0),
see README and NOTICE.
"""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CARD_URL, DOMAIN, VERSION
from .coordinator import InternetometrConfigEntry, InternetometrCoordinator

PLATFORMS = [Platform.BUTTON, Platform.NUMBER, Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the bundled Lovelace card so no manual resource is needed."""
    card = Path(__file__).parent / "frontend" / "yandex-internetometr-card.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(card), cache_headers=False)]
    )
    add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: InternetometrConfigEntry) -> bool:
    coordinator = InternetometrCoordinator(hass, entry)
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if coordinator.update_interval is not None:
        # The first run takes ~20 s: do it in the background, not during setup.
        entry.async_create_background_task(
            hass, coordinator.async_refresh(), f"{DOMAIN}_first_refresh"
        )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: InternetometrConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
