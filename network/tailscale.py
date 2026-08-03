"""
network/tailscale.py

Tailscale VPN integration for DEEP v2.

Monitors Tailscale VPN state, publishes events on the EventBus,
and exposes control methods (connect / disconnect / status).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SETUP INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tailscale is installed at the OS level — this module manages and
monitors it, it does not install it.

Windows:
  1. Download Tailscale from https://tailscale.com/download
  2. Install and sign in with a free account
  3. DEEP will auto-detect the binary path

Raspberry Pi:
  1. curl -fsSL https://tailscale.com/install.sh | sh
  2. sudo tailscale up
  3. Sign in — same account as Windows
  4. Both devices now share a private 100.x.x.x network

Result: DEEP on Pi becomes reachable at its Tailscale IP from
your Windows PC, phone, or anywhere — no port forwarding, no
public IP needed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Platform defaults
# ═══════════════════════════════════════════════════════════════════════════════

_DEFAULT_TAILSCALE_BIN = (
    "C:/Program Files/Tailscale/tailscale.exe"
    if sys.platform == "win32"
    else "/usr/bin/tailscale"
)

# ═══════════════════════════════════════════════════════════════════════════════
# Data model
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class TailscaleStatus:
    """Snapshot of Tailscale daemon state."""

    state: str = "Unknown"       # "Running", "Stopped", "NeedsLogin", etc.
    ip: str = ""                 # 100.x.x.x Tailscale IP
    hostname: str = ""           # this device's TS hostname
    peers: list[str] = None      # type: ignore[assignment]  # other device hostnames
    exit_node: str | None = None  # active exit node, if any

    def __post_init__(self):
        # dataclass(frozen=True) with mutable default workaround
        object.__setattr__(self, "peers", self.peers if self.peers is not None else [])


# ═══════════════════════════════════════════════════════════════════════════════
# Manager
# ═══════════════════════════════════════════════════════════════════════════════


class TailscaleManager:
    """
    Manages and monitors the Tailscale VPN daemon.

    Lifecycle: __init__ -> start() -> ... -> stop() -> status()
    """

    def __init__(self, event_bus: Any) -> None:
        self._event_bus = event_bus
        self._tailscale_bin: str = self._resolve_bin_path()
        self._monitor_task: asyncio.Task | None = None
        self._started = False
        self._stop_event = asyncio.Event()

        # State tracking
        self._last_status: TailscaleStatus = TailscaleStatus()
        self._connected_since: float | None = None
        self._last_checked: str | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_bin_path(self) -> str:
        """Return Tailscale binary path from config or platform default."""
        try:
            from core.config import Settings

            settings = Settings()
            if hasattr(settings, "tailscale_bin_path") and settings.tailscale_bin_path:
                return str(settings.tailscale_bin_path)
        except Exception:
            pass
        return _DEFAULT_TAILSCALE_BIN

    def _binary_exists(self) -> bool:
        return Path(self._tailscale_bin).exists()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start monitoring. If binary is missing, publish a warning and return."""
        if not self._binary_exists():
            logger.warning(
                f"Tailscale binary not found at {self._tailscale_bin}. "
                "DEEP will run without VPN."
            )
            await self._event_bus.publish(
                "tailscale_not_installed",
                {"path": self._tailscale_bin, "timestamp": self._now()},
            )
            self._started = True
            return

        self._started = True
        self._stop_event.clear()
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("TailscaleManager started")

    async def stop(self) -> None:
        """Stop the monitor loop."""
        self._started = False
        self._stop_event.set()
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("TailscaleManager stopped")

    def status(self) -> dict[str, Any]:
        """Return current operational status."""
        uptime = 0.0
        if self._connected_since is not None:
            uptime = time.monotonic() - self._connected_since

        return {
            "state": self._last_status.state,
            "ip": self._last_status.ip or None,
            "hostname": self._last_status.hostname or None,
            "peers_count": len(self._last_status.peers),
            "last_checked": self._last_checked,
            "uptime_connected_s": round(uptime, 2) if self._connected_since else 0.0,
        }

    # ------------------------------------------------------------------
    # Monitor loop
    # ------------------------------------------------------------------

    async def _monitor_loop(self) -> None:
        """Poll Tailscale status and publish events on change."""
        poll_interval = 30
        try:
            from core.config import Settings

            settings = Settings()
            poll_interval = getattr(settings, "tailscale_poll_interval_s", 30)
        except Exception:
            pass

        while not self._stop_event.is_set():
            status = await self._get_status()
            self._last_checked = self._now()

            # Detect state changes
            if status.state != self._last_status.state:
                await self._event_bus.publish(
                    "tailscale_status_changed",
                    {
                        "state": status.state,
                        "ip": status.ip,
                        "hostname": status.hostname,
                        "peers": status.peers,
                        "exit_node": status.exit_node,
                    },
                )

                # Connected transition
                if status.state == "Running" and self._last_status.state != "Running":
                    self._connected_since = time.monotonic()
                    await self._event_bus.publish(
                        "tailscale_connected",
                        {
                            "ip": status.ip,
                            "peers": len(status.peers),
                        },
                    )
                    await self._event_bus.publish(
                        "tts_speak",
                        {
                            "text": "VPN connected. Remote access active.",
                            "priority": "normal",
                        },
                    )

                # Disconnected transition
                elif status.state != "Running" and self._last_status.state == "Running":
                    self._connected_since = None
                    await self._event_bus.publish(
                        "tailscale_disconnected",
                        {},
                    )

            self._last_status = status

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=poll_interval)
            except asyncio.TimeoutError:
                pass

    # ------------------------------------------------------------------
    # Status fetching
    # ------------------------------------------------------------------

    async def _get_status(self) -> TailscaleStatus:
        """Run `tailscale status --json` and parse the output."""
        if not self._binary_exists():
            return TailscaleStatus(state="Unknown")

        try:
            proc = await asyncio.create_subprocess_exec(
                self._tailscale_bin,
                "status",
                "--json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10.0)
        except Exception as exc:
            logger.warning(f"Tailscale status query failed: {exc}")
            return TailscaleStatus(state="Unknown")

        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="ignore").strip()
            logger.warning(f"Tailscale status returned {proc.returncode}: {err}")
            return TailscaleStatus(state="Unknown")

        try:
            data = json.loads(stdout.decode("utf-8", errors="ignore"))
        except json.JSONDecodeError as exc:
            logger.warning(f"Tailscale status JSON parse error: {exc}")
            return TailscaleStatus(state="Unknown")

        # Extract fields from Tailscale JSON schema
        backend_state = data.get("BackendState", "Unknown")
        self_node = data.get("Self", {})
        tailscale_ips = self_node.get("TailscaleIPs", [])
        ip = tailscale_ips[0] if tailscale_ips else ""
        hostname = self_node.get("HostName", "")
        exit_node = data.get("ExitNodeStatus", {}).get("TailscaleIPs", [None])[0]

        # Peer hostnames
        peers: list[str] = []
        peer_map = data.get("Peer", {})
        for peer_id, peer_info in peer_map.items():
            if isinstance(peer_info, dict):
                peer_hostname = peer_info.get("HostName", "")
                if peer_hostname:
                    peers.append(peer_hostname)

        return TailscaleStatus(
            state=backend_state,
            ip=ip,
            hostname=hostname,
            peers=peers,
            exit_node=exit_node,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_ip(self) -> str | None:
        """Return this device's Tailscale IP if connected."""
        if self._last_status.state == "Running" and self._last_status.ip:
            return self._last_status.ip
        # Fresh query if cached state is stale or not Running
        status = await self._get_status()
        return status.ip if status.state == "Running" else None

    async def get_peers(self) -> list[str]:
        """Return list of connected peer hostnames."""
        if self._last_status.state == "Running" and self._last_status.peers:
            return list(self._last_status.peers)
        status = await self._get_status()
        return list(status.peers) if status.state == "Running" else []

    async def connect(self) -> bool:
        """Run `tailscale up`. Return True if successful."""
        if not self._binary_exists():
            return False
        try:
            proc = await asyncio.create_subprocess_exec(
                self._tailscale_bin,
                "up",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            if proc.returncode != 0:
                err = stderr.decode("utf-8", errors="ignore").strip()
                logger.error(f"tailscale up failed: {err}")
                return False
            return True
        except Exception as exc:
            logger.error(f"tailscale connect error: {exc}")
            return False

    async def disconnect(self) -> bool:
        """Run `tailscale down`. Return True if successful."""
        if not self._binary_exists():
            return False
        try:
            proc = await asyncio.create_subprocess_exec(
                self._tailscale_bin,
                "down",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            if proc.returncode != 0:
                err = stderr.decode("utf-8", errors="ignore").strip()
                logger.error(f"tailscale down failed: {err}")
                return False
            return True
        except Exception as exc:
            logger.error(f"tailscale disconnect error: {exc}")
            return False

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
