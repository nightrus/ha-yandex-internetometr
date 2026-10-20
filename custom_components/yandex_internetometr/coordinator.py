# Copyright 2025 Nikita Erilov
# Copyright 2026 nightrus
# Licensed under the Apache License, Version 2.0 (see LICENSE).
#
# Based on the coordinator of ha-yainternetometr by Nikita Erilov
# (https://github.com/ErilovNikita/ha-yainternetometr). Modified: uses the
# bundled speedtest client; the upload fallback chain is gone because upload is
# now measured correctly; a run in progress is exposed for the button/card.

"""Data update coordinator for Yandex Internetometr."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    KEY_DOWNLOAD,
    KEY_PING,
    KEY_UPLOAD,
    TEST_TIMEOUT,
)
from .speedtest import SpeedtestError, YandexSpeedtest

_LOGGER = logging.getLogger(__name__)

type InternetometrConfigEntry = ConfigEntry[InternetometrCoordinator]


def interval_from_minutes(minutes: int) -> timedelta | None:
    return timedelta(minutes=minutes) if minutes > 0 else None


class InternetometrCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Runs the speed test on a schedule or on demand."""

    config_entry: InternetometrConfigEntry

    def __init__(self, hass: HomeAssistant, entry: InternetometrConfigEntry) -> None:
        minutes = int(entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=interval_from_minutes(minutes),
        )
        self.running = False
        self._lock = asyncio.Lock()

    @callback
    def set_interval(self, minutes: int) -> None:
        self.update_interval = interval_from_minutes(minutes)
        # Re-arm the timer now; otherwise the old schedule (or none, after 0) stays.
        self._schedule_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        if self._lock.locked():
            _LOGGER.debug("Speed test already running, skipping")
            return self.data
        async with self._lock:
            self.running = True
            self.async_update_listeners()
            try:
                async with asyncio.timeout(TEST_TIMEOUT):
                    result = await YandexSpeedtest().run()
            except TimeoutError as err:
                raise UpdateFailed("Speed test timed out") from err
            except SpeedtestError as err:
                raise UpdateFailed(str(err)) from err
            finally:
                self.running = False

        _LOGGER.debug("Speed test result: %s", result)
        if result.download_mbps == 0 and result.upload_mbps == 0:
            raise UpdateFailed("No data could be transferred to Yandex servers")
        return {
            KEY_PING: result.ping_ms,
            KEY_DOWNLOAD: result.download_mbps,
            KEY_UPLOAD: result.upload_mbps,
            "servers": result.servers,
            "download_bytes": result.download_bytes,
            "upload_bytes": result.upload_bytes,
            "duration_s": result.duration_s,
            "measured_at": dt_util.utcnow().isoformat(),
        }
