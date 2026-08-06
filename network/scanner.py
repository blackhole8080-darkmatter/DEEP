"""
network/scanner.py

Continuous device discovery and inventory across the local network.
Uses python-nmap for host discovery and deep port scanning.

Monitors for new devices joining, known devices leaving, and
publishes security events on the EventBus.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


try:
    import nmap
    NMAP_AVAILABLE = True
except ImportError:
    NMAP_AVAILABLE = False
    logger.warning("python-nmap not installed — NetworkScanner will use passive discovery only")


try:
    from mac_vendor_lookup import MacLookup
    MAC_LOOKUP = MacLookup()
except Exception:
    MAC_LOOKUP = None


@dataclass
class NetworkDevice:
    """Snapshot of a discovered network host."""

    ip: str
    mac: str | None = None
    hostname: str | None = None
    vendor: str | None = None
    first_seen: str = ""
    last_seen: str = ""
    is_known: bool = False
    open_ports: list[int] = field(default_factory=list)
    os_guess: str | None = None


class NetworkScanner:
    """
    Discovers and monitors devices on the local network.

    Lifecycle: __init__ -> start() -> ... -> stop() -> status()
    """

    def __init__(self, event_bus: Any, redis_state: Any) -> None:
        self._event_bus = event_bus
        self._redis_state = redis_state
        self._started = False
        self._stop_event = asyncio.Event()

        self._cidr: str = self._resolve_cidr()
        self._known_devices: dict[str, str] = self._resolve_known()
        self._scan_interval: int = self._resolve_interval("scan_interval_s", 60)
        self._deep_interval: int = self._resolve_interval("deep_scan_interval_s", 300)

        self._device_registry: dict[str, NetworkDevice] = {}
        self._scan_task: asyncio.Task | None = None
        self._deep_task: asyncio.Task | None = None
        self._last_scan: str | None = None
        # Speak unknown-device joins aloud? Default OFF — on a busy home network
        # this was constant TTS spam (esp. after restarts), annoying with the UI
        # closed. The visual toast still surfaces it when the interface is open.
        import os as _os
        self._announce_unknown: bool = _os.environ.get("ANNOUNCE_UNKNOWN_DEVICES", "false").lower() in ("1", "true", "yes", "on")

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    def _resolve_cidr(self) -> str:
        try:
            from core.config import Settings
            return getattr(Settings(), "network_cidr", "192.168.1.0/24")
        except Exception:
            return "192.168.1.0/24"

    def _resolve_known(self) -> dict[str, str]:
        try:
            from core.config import Settings
            return dict(getattr(Settings(), "known_devices", {}))
        except Exception:
            return {}

    def _resolve_interval(self, name: str, default: int) -> int:
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

        # Immediate baseline scan
        try:
            await self._quick_scan()
        except Exception as exc:
            logger.warning(f"Initial quick scan error: {exc}")

        self._scan_task = asyncio.create_task(self._scan_scheduler())
        self._deep_task = asyncio.create_task(self._deep_scheduler())
        logger.info("NetworkScanner started")

    async def stop(self) -> None:
        self._started = False
        self._stop_event.set()
        for task in (self._scan_task, self._deep_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        logger.info("NetworkScanner stopped")

    def status(self) -> dict[str, Any]:
        known = sum(1 for d in self._device_registry.values() if d.is_known)
        unknown = len(self._device_registry) - known
        return {
            "total_devices": len(self._device_registry),
            "known_devices": known,
            "unknown_devices": unknown,
            "last_scan": self._last_scan,
            "next_scan": self._last_scan,  # simplistic
            "cidr": self._cidr,
        }

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    async def _scan_scheduler(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._quick_scan()
            except Exception as exc:
                logger.warning(f"Quick scan error: {exc}")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._scan_interval)
            except asyncio.TimeoutError:
                pass

    async def _deep_scheduler(self) -> None:
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._deep_interval)
            except asyncio.TimeoutError:
                pass
            if not self._started:
                break
            try:
                await self._deep_scan()
            except Exception as exc:
                logger.warning(f"Deep scan error: {exc}")

    async def _quick_scan(self) -> list[NetworkDevice]:
        if not NMAP_AVAILABLE:
            logger.debug("nmap unavailable — skipping quick scan")
            return list(self._device_registry.values())

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._run_nmap_ping)
        self._last_scan = self._now()

        current_ips = set()
        new_devices: list[NetworkDevice] = []

        for host_data in result:
            ip = host_data.get("ip")
            if not ip:
                continue
            current_ips.add(ip)

            mac = host_data.get("mac")
            hostname = host_data.get("hostname")
            vendor = self._lookup_vendor(mac)
            is_known = mac is not None and mac.upper() in {k.upper() for k in self._known_devices}

            if ip in self._device_registry:
                existing = self._device_registry[ip]
                existing.last_seen = self._now()
                if mac and not existing.mac:
                    existing.mac = mac
                if vendor and not existing.vendor:
                    existing.vendor = vendor
            else:
                device = NetworkDevice(
                    ip=ip,
                    mac=mac,
                    hostname=hostname,
                    vendor=vendor,
                    first_seen=self._now(),
                    last_seen=self._now(),
                    is_known=is_known,
                )
                self._device_registry[ip] = device
                new_devices.append(device)
                await self._handle_new_device(device)

        # Detect departed devices
        for ip, device in list(self._device_registry.items()):
            if ip not in current_ips:
                # Only mark gone if missing for > 2 scan cycles
                # (simplistic: we just note it for now)
                pass  # future: track missing count

        # Persist to Redis
        await self._sync_to_redis()
        return list(self._device_registry.values())

    def _run_nmap_ping(self) -> list[dict[str, Any]]:
        """Blocking nmap ping scan — must run in executor."""
        try:
            nm = nmap.PortScanner()
            nm.scan(hosts=self._cidr, arguments="-sn")
            hosts = []
            for ip in nm.all_hosts():
                data = {"ip": ip}
                if "mac" in nm[ip].get("addresses", {}):
                    data["mac"] = nm[ip]["addresses"]["mac"]
                if "hostnames" in nm[ip] and nm[ip]["hostnames"]:
                    data["hostname"] = nm[ip]["hostnames"][0].get("name", "")
                hosts.append(data)
            return hosts
        except Exception as exc:
            logger.warning(f"nmap ping scan failed: {exc}")
            return []

    async def _deep_scan(self, target_ip: str | None = None) -> None:
        if not NMAP_AVAILABLE:
            return

        targets = [target_ip] if target_ip else list(self._device_registry.keys())
        if not targets:
            return

        hosts_str = ",".join(targets)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, self._run_nmap_deep, hosts_str)

        for ip, scan_data in results.items():
            if ip not in self._device_registry:
                continue
            device = self._device_registry[ip]
            device.open_ports = scan_data.get("open_ports", [])
            device.os_guess = scan_data.get("os_guess")
            await self._event_bus.publish(
                "device_deep_scanned",
                {
                    "ip": ip,
                    "open_ports": device.open_ports,
                    "os_guess": device.os_guess,
                    "hostname": device.hostname,
                },
            )

        await self._sync_to_redis()

    def _run_nmap_deep(self, hosts: str) -> dict[str, dict[str, Any]]:
        """Blocking deep nmap scan — must run in executor."""
        try:
            nm = nmap.PortScanner()
            nm.scan(hosts=hosts, arguments="-sV -O --top-ports 100")
            results: dict[str, dict[str, Any]] = {}
            for ip in nm.all_hosts():
                open_ports = [
                    int(port)
                    for proto in nm[ip].all_protocols()
                    for port in nm[ip][proto].keys()
                    if nm[ip][proto][port].get("state") == "open"
                ]
                os_guess = None
                if "osmatch" in nm[ip] and nm[ip]["osmatch"]:
                    os_guess = nm[ip]["osmatch"][0].get("name")
                results[ip] = {"open_ports": open_ports, "os_guess": os_guess}
            return results
        except Exception as exc:
            logger.warning(f"nmap deep scan failed: {exc}")
            return {}

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def _handle_new_device(self, device: NetworkDevice) -> None:
        if not device.is_known:
            await self._event_bus.publish(
                "unknown_device_detected",
                {
                    "ip": device.ip,
                    "mac": device.mac,
                    "vendor": device.vendor,
                    "hostname": device.hostname,
                    "timestamp": self._now(),
                },
            )
            # Only SPEAK it aloud if explicitly enabled (ANNOUNCE_UNKNOWN_DEVICES).
            # The event above already drives the on-screen toast + activity feed.
            if self._announce_unknown:
                await self._event_bus.publish(
                    "tts_speak",
                    {
                        "text": f"Unknown device detected on network. IP {device.ip}. Vendor: {device.vendor or 'unknown'}.",
                        "priority": "urgent",
                    },
                )
            await self._redis_state.set_global(
                "security_alert",
                {
                    "type": "unknown_device",
                    "device": device.__dict__,
                    "timestamp": self._now(),
                },
            )
        else:
            name = self._known_devices.get(device.mac.upper(), device.mac)
            await self._event_bus.publish(
                "known_device_joined",
                {
                    "ip": device.ip,
                    "mac": device.mac,
                    "name": name,
                },
            )

    # ------------------------------------------------------------------
    # Vendor lookup
    # ------------------------------------------------------------------

    def _lookup_vendor(self, mac: str | None) -> str | None:
        if not mac or not MAC_LOOKUP:
            return None
        try:
            # Run in a worker thread (no running event loop) so MacLookup's sync
            # wrapper works instead of leaking an un-awaited coroutine.
            import concurrent.futures as _cf
            with _cf.ThreadPoolExecutor(max_workers=1) as _ex:
                return _ex.submit(MAC_LOOKUP.lookup, mac).result(timeout=5)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Redis sync
    # ------------------------------------------------------------------

    async def _sync_to_redis(self) -> None:
        try:
            devices = [d.__dict__ for d in self._device_registry.values()]
            await self._redis_state.set_global("network_devices", devices)
        except Exception as exc:
            logger.debug(f"Redis sync error: {exc}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_devices(self) -> list[NetworkDevice]:
        return list(self._device_registry.values())

    async def get_device(self, ip: str) -> NetworkDevice | None:
        return self._device_registry.get(ip)

    async def scan_target(self, ip: str) -> NetworkDevice | None:
        await self._deep_scan(target_ip=ip)
        return self._device_registry.get(ip)

    async def is_ip_on_network(self, ip: str) -> bool:
        if ip in self._device_registry:
            return True
        # Quick single-host ping scan
        if NMAP_AVAILABLE:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: nmap.PortScanner().scan(hosts=ip, arguments="-sn")
            )
            return ip in result.get("scan", {})
        return False
