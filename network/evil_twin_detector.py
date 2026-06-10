"""
network/evil_twin_detector.py

Detects rogue access points mimicking your WiFi SSID.
Compares scanned BSSIDs against your legitimate router MAC.
"""

from __future__ import annotations

import asyncio
import logging
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class EvilTwinDetector:
    """
    Scans for WiFi networks and alerts when an evil twin is detected.

    Lifecycle: __init__ -> start() -> ... -> stop() -> status()
    """

    def __init__(self, event_bus: Any, redis_state: Any) -> None:
        self._event_bus = event_bus
        self._redis_state = redis_state
        self._started = False
        self._stop_event = asyncio.Event()

        self._home_ssid: str = self._resolve("home_ssid", "")
        self._home_bssid: str = self._resolve("home_bssid", "").upper()
        self._scan_interval: int = self._resolve("wifi_scan_interval_s", 120)

        self._scans_today = 0
        self._twins_detected = 0
        self._scan_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    def _resolve(self, name: str, default: Any) -> Any:
        try:
            from core.config import Settings
            return getattr(Settings(), name, default)
        except Exception:
            return default

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        self._started = True
        self._stop_event.clear()

        if not self._home_ssid or not self._home_bssid:
            logger.info("EvilTwinDetector: HOME_SSID or HOME_BSSID not set — skipping scans")
            return

        # Initial scan
        try:
            await self._scan_wifi()
        except Exception as exc:
            logger.debug(f"Initial WiFi scan error: {exc}")

        self._scan_task = asyncio.create_task(self._scan_scheduler())
        logger.info("EvilTwinDetector started")

    async def stop(self) -> None:
        self._started = False
        self._stop_event.set()
        if self._scan_task and not self._scan_task.done():
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
        logger.info("EvilTwinDetector stopped")

    def status(self) -> dict[str, Any]:
        return {
            "monitoring": self._started and bool(self._home_ssid),
            "home_ssid": self._home_ssid or None,
            "scans_today": self._scans_today,
            "twins_detected": self._twins_detected,
        }

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    async def _scan_scheduler(self) -> None:
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._scan_interval)
            except asyncio.TimeoutError:
                pass
            if not self._started:
                break
            try:
                networks = await self._scan_wifi()
                await self._analyse_networks(networks)
            except Exception as exc:
                logger.debug(f"WiFi scan error: {exc}")

    async def _scan_wifi(self) -> list[dict[str, Any]]:
        loop = asyncio.get_event_loop()
        if sys.platform == "win32":
            return await loop.run_in_executor(None, self._scan_windows)
        else:
            return await loop.run_in_executor(None, self._scan_linux)

    def _scan_linux(self) -> list[dict[str, Any]]:
        """Parse iwlist scan output."""
        networks: list[dict[str, Any]] = []
        try:
            result = subprocess.run(
                ["iwlist", "wlan0", "scan"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode != 0:
                # Try without specifying interface
                result = subprocess.run(
                    ["iwlist", "scan"],
                    capture_output=True, text=True, timeout=15,
                )
            output = result.stdout
        except Exception as exc:
            logger.debug(f"iwlist scan failed: {exc}")
            return networks

        cell_blocks = output.split("Cell ")
        for block in cell_blocks[1:]:
            ssid_match = re.search(r'ESSID:"([^"]*)"', block)
            bssid_match = re.search(r'Address:\s*([0-9A-Fa-f:]{17})', block)
            signal_match = re.search(r'Signal level[=:]([-\d]+)', block)
            channel_match = re.search(r'Channel[:=](\d+)', block)

            if ssid_match and bssid_match:
                networks.append({
                    "ssid": ssid_match.group(1),
                    "bssid": bssid_match.group(1).upper(),
                    "signal": int(signal_match.group(1)) if signal_match else None,
                    "channel": int(channel_match.group(1)) if channel_match else None,
                })
        return networks

    def _scan_windows(self) -> list[dict[str, Any]]:
        """Parse netsh wlan show networks output."""
        networks: list[dict[str, Any]] = []
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "networks", "mode=bssid"],
                capture_output=True, text=True, timeout=15,
            )
            output = result.stdout
        except Exception as exc:
            logger.debug(f"netsh wlan scan failed: {exc}")
            return networks

        # Parse SSID and BSSID blocks
        current_ssid = None
        for line in output.splitlines():
            ssid_match = re.search(r'SSID\s+\d+\s*:\s*(.+)', line)
            if ssid_match:
                current_ssid = ssid_match.group(1).strip()

            bssid_match = re.search(r'BSSID\s+\d+\s*:\s*([0-9a-f:]{17})', line, re.IGNORECASE)
            if bssid_match and current_ssid:
                networks.append({
                    "ssid": current_ssid,
                    "bssid": bssid_match.group(1).upper(),
                    "signal": None,
                    "channel": None,
                })
        return networks

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    async def _analyse_networks(self, networks: list[dict[str, Any]]) -> None:
        self._scans_today += 1
        for net in networks:
            if net["ssid"] == self._home_ssid:
                if net["bssid"] != self._home_bssid:
                    self._twins_detected += 1
                    await self._event_bus.publish(
                        "evil_twin_detected",
                        {
                            "ssid": net["ssid"],
                            "legitimate_bssid": self._home_bssid,
                            "rogue_bssid": net["bssid"],
                            "signal": net["signal"],
                            "channel": net["channel"],
                        },
                    )
                    await self._event_bus.publish(
                        "tts_speak",
                        {
                            "text": f"Warning. Evil twin access point detected. A rogue network is impersonating {self._home_ssid}. Do not connect.",
                            "priority": "urgent",
                        },
                    )
                    await self._redis_state.set_global(
                        "security_alert",
                        {
                            "type": "evil_twin",
                            "ssid": net["ssid"],
                            "rogue_bssid": net["bssid"],
                            "timestamp": self._now(),
                        },
                    )
