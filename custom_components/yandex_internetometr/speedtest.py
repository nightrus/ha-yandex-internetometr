# Copyright 2025 Nikita Erilov
# Copyright 2026 nightrus
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Derived from yaspeedtest 0.1.7 by Nikita Erilov
# (https://github.com/ErilovNikita/yaspeedtest). Modified: the probe list and
# latency method are kept; download and upload are measured as the aggregate
# throughput of parallel streams over a fixed time window instead of the peak
# of a single stream, and upload sends the real probe volume (the "size" of
# Yandex upload probes is in KiB, yaspeedtest sent that many bytes).

"""Yandex Internetometr speed test client."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
import logging
import statistics
import time
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

PROBES_URL = "https://yandex.ru/internet/api/v0/get-probes"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Referer": "https://yandex.ru/internet",
}
# Test files must not be compressed, or the byte count is not what crossed the wire.
TRANSFER_HEADERS = {**HEADERS, "Accept-Encoding": "identity"}

# Upload goes in requests of this size and is counted when the server confirms
# one, so data still sitting in (growing) socket buffers is never counted.
UPLOAD_REQUEST = 4 * 1024 * 1024


class SpeedtestError(Exception):
    """The test could not be run."""


@dataclass
class SpeedtestResult:
    """Outcome of one run."""

    ping_ms: float | None
    download_mbps: float
    upload_mbps: float
    servers: list[str] = field(default_factory=list)
    download_bytes: int = 0
    upload_bytes: int = 0
    duration_s: float = 0.0


class _Meter:
    """Byte counter shared by all streams of one direction."""

    def __init__(self) -> None:
        self.total = 0

    def add(self, n: int) -> None:
        self.total += n


@dataclass
class _Probe:
    host: str
    url: str
    size: int | None = None


def _host(url: str) -> str:
    return url.split("/")[2] if "://" in url else url


def _parse_probes(data: dict[str, Any]) -> tuple[list[_Probe], list[_Probe], list[_Probe]]:
    def items(key: str) -> list[dict[str, Any]]:
        return ((data.get(key) or {}).get("probes")) or []

    latency = [_Probe(_host(p["url"]), p["url"]) for p in items("latency") if p.get("url")]
    # Only the big files are useful for throughput; 100 KB ones end during TCP slow start.
    download = [
        _Probe(_host(p["url"]), p["url"])
        for p in items("download")
        if p.get("url") and "/probes/" in p["url"] and not p["url"].split("?")[0].endswith("kb")
    ]
    upload_all = [
        _Probe(_host(p["url"]), p["url"], int(p.get("size") or 0))
        for p in items("upload")
        if p.get("url") and int(p.get("size") or 0) > 0
    ]
    # Largest upload probe per server.
    upload: dict[str, _Probe] = {}
    for p in upload_all:
        if p.host not in upload or (p.size or 0) > (upload[p.host].size or 0):
            upload[p.host] = p
    return latency, download, list(upload.values())


class YandexSpeedtest:
    """Run a speed test against the Yandex Internetometr CDN probes."""

    def __init__(
        self,
        *,
        duration: float = 8.0,
        warmup: float = 1.5,
        streams_per_server: int = 2,
        latency_samples: int = 8,
    ) -> None:
        self.duration = duration
        self.warmup = warmup
        self.streams_per_server = streams_per_server
        self.latency_samples = latency_samples

    async def run(self) -> SpeedtestResult:
        started = time.monotonic()
        connector = aiohttp.TCPConnector(limit=0, ttl_dns_cache=300)
        async with aiohttp.ClientSession(connector=connector) as session:
            latency, download, upload = await self._get_probes(session)
            if not download or not upload:
                raise SpeedtestError("Yandex returned no download/upload probes")

            ping = await self._measure_latency(session, latency)
            dl_mbps, dl_bytes = await self._measure(
                session, self._download_worker, [p.url for p in download]
            )
            ul_mbps, ul_bytes = await self._measure(
                session,
                self._upload_worker,
                # Probe size is in KiB (the browser test sends 30 MiB for size=30720).
                [(p.url, (p.size or 0) * 1024) for p in upload],
            )

        return SpeedtestResult(
            ping_ms=ping,
            download_mbps=dl_mbps,
            upload_mbps=ul_mbps,
            servers=sorted({p.host for p in download}),
            download_bytes=dl_bytes,
            upload_bytes=ul_bytes,
            duration_s=round(time.monotonic() - started, 1),
        )

    async def _get_probes(self, session: aiohttp.ClientSession):
        try:
            async with asyncio.timeout(15):
                async with session.get(PROBES_URL, headers=HEADERS) as resp:
                    if resp.status != 200:
                        raise SpeedtestError(f"get-probes: HTTP {resp.status}")
                    data = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise SpeedtestError(f"get-probes failed: {err}") from err
        return _parse_probes(data)

    async def _measure_latency(
        self, session: aiohttp.ClientSession, probes: list[_Probe]
    ) -> float | None:
        """Median HTTP round trip on a warm keep-alive connection, best server."""

        async def one(probe: _Probe) -> float | None:
            times: list[float] = []
            for i in range(self.latency_samples + 1):
                t0 = time.perf_counter()
                try:
                    async with asyncio.timeout(3):
                        async with session.head(probe.url, headers=HEADERS) as resp:
                            await resp.read()
                except (aiohttp.ClientError, TimeoutError):
                    continue
                if i:  # the first request pays for DNS, TCP and TLS
                    times.append((time.perf_counter() - t0) * 1000)
                await asyncio.sleep(0.05)
            return statistics.median(times) if times else None

        results = [r for r in await asyncio.gather(*(one(p) for p in probes)) if r is not None]
        return round(min(results), 2) if results else None

    async def _measure(
        self,
        session: aiohttp.ClientSession,
        worker: Callable[..., Coroutine[Any, Any, None]],
        targets: list[Any],
    ) -> tuple[float, int]:
        """Run parallel streams for `duration`, rate = bytes after warmup / time."""
        meter = _Meter()
        stop = asyncio.Event()
        tasks = [
            asyncio.create_task(worker(session, target, meter, stop))
            for target in targets
            for _ in range(self.streams_per_server)
        ]
        try:
            await asyncio.sleep(self.warmup)
            t1, b1 = time.perf_counter(), meter.total
            await asyncio.sleep(self.duration - self.warmup)
            t2, b2 = time.perf_counter(), meter.total
        finally:
            stop.set()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        mbps = (b2 - b1) * 8 / (t2 - t1) / 1_000_000 if t2 > t1 else 0.0
        return round(mbps, 2), meter.total

    @staticmethod
    async def _download_worker(
        session: aiohttp.ClientSession, url: str, meter: _Meter, stop: asyncio.Event
    ) -> None:
        while not stop.is_set():
            try:
                async with session.get(url, headers=TRANSFER_HEADERS) as resp:
                    if resp.status != 200:
                        _LOGGER.debug("download %s: HTTP %s", _host(url), resp.status)
                        await asyncio.sleep(0.5)
                        continue
                    async for chunk in resp.content.iter_any():
                        meter.add(len(chunk))
                        if stop.is_set():
                            return
            except aiohttp.ClientError as err:
                _LOGGER.debug("download %s: %s", _host(url), err)
                await asyncio.sleep(0.5)

    @staticmethod
    async def _upload_worker(
        session: aiohttp.ClientSession,
        target: tuple[str, int],
        meter: _Meter,
        stop: asyncio.Event,
    ) -> None:
        url, size = target
        payload = bytes(min(size, UPLOAD_REQUEST))
        headers = {**TRANSFER_HEADERS, "Content-Type": "application/octet-stream"}
        while not stop.is_set():
            try:
                async with session.post(url, data=payload, headers=headers) as resp:
                    await resp.read()
                    if resp.status == 200:
                        meter.add(len(payload))
                    else:
                        _LOGGER.debug("upload %s: HTTP %s", _host(url), resp.status)
                        await asyncio.sleep(0.5)
            except aiohttp.ClientError as err:
                _LOGGER.debug("upload %s: %s", _host(url), err)
                await asyncio.sleep(0.5)
