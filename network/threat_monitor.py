"""
network/threat_monitor.py

Detects active attacks against your network using packet analysis
and pattern matching. Uses Scapy for packet capture.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LEGAL NOTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

All monitoring targets YOUR OWN network only.
config.NETWORK_CIDR must be your home subnet.
Packet capture on networks you do not own is illegal in most
jurisdictions. DEEP defends inward — never outward.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import asyncio
import logging
import platform
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Scapy is optional — gracefully degrade if unavailable
try:
    from scapy.all import sniff, ARP, IP, TCP, Dot11Deauth
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    sniff = None
    ARP = None
    IP = None
    TCP = None
    Dot11Deauth = None
    logger.warning("scapy not installed — ThreatMonitor will run without packet capture")


@dataclass
class Threat:
    """Detected security threat."""

    threat_type: str
    source_ip: str
    target_ip: str | None = None
    confidence: float = 0.0
    evidence: dict = field(default_factory=dict)
    timestamp: str = ""
    mitigated: bool = False


class ThreatMonitor:
    """
    Passive network threat detection via packet analysis.

    Lifecycle: __init__ -> start() -> ... -> stop() -> status()
    """

    def __init__(self, event_bus: Any, redis_state: Any) -> None:
        self._event_bus = event_bus
        self._redis_state = redis_state
        self._started = False
        self._stop_event = asyncio.Event()

        self._interface: str | None = self._resolve_interface()
        self._port_scan_threshold: int = self._resolve_int("port_scan_threshold", 15)
        self._port_scan_window: int = self._resolve_int("port_scan_window_s", 10)
        self._deauth_threshold: int = self._resolve_int("deauth_threshold", 5)

        # Detection state
        self._port_hits: dict[str, dict[str, Any]] = {}  # src_ip -> {timestamp: [ports]}
        self._arp_table: dict[str, str] = {}             # ip -> mac
        self._deauth_counts: dict[str, list[float]] = {} # src_mac -> [timestamps]
        self._threats: list[Threat] = []
        self._packets_analysed = 0

        self._packet_buffer: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self._sniff_task: Any = None
        self._analyse_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    def _resolve_interface(self) -> str | None:
        try:
            from core.config import Settings
            iface = getattr(Settings(), "monitor_interface", None)
            if iface:
                return iface
        except Exception:
            pass
        # Auto-detect
        if sys.platform == "win32":
            return None  # scapy will use default
        return None

    def _resolve_int(self, name: str, default: int) -> int:
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

        if not SCAPY_AVAILABLE:
            logger.warning("ThreatMonitor starting without Scapy — no packet capture")
            return

        # Start packet capture in executor thread
        loop = asyncio.get_event_loop()
        self._sniff_task = loop.run_in_executor(None, self._packet_capture_loop)
        self._analyse_task = asyncio.create_task(self._analyse_loop())
        logger.info("ThreatMonitor started")

    async def stop(self) -> None:
        self._started = False
        self._stop_event.set()

        if self._analyse_task and not self._analyse_task.done():
            self._analyse_task.cancel()
            try:
                await self._analyse_task
            except asyncio.CancelledError:
                pass

        # Scapy sniff can't be cleanly cancelled from asyncio,
        # but setting _started=False causes the prn callback to drop packets.
        logger.info("ThreatMonitor stopped")

    def status(self) -> dict[str, Any]:
        return {
            "monitoring": self._started and SCAPY_AVAILABLE,
            "interface": self._interface or "default",
            "threats_today": len(self._threats),
            "last_threat": self._threats[-1].timestamp if self._threats else None,
            "packets_analysed": self._packets_analysed,
        }

    # ------------------------------------------------------------------
    # Packet capture (runs in executor thread)
    # ------------------------------------------------------------------

    def _packet_capture_loop(self) -> None:
        """Blocking Scapy sniff loop — runs in a thread."""
        if not SCAPY_AVAILABLE:
            return
        try:
            sniff(
                iface=self._interface,
                prn=self._packet_callback,
                store=False,
                stop_filter=lambda _: not self._started,
            )
        except Exception as exc:
            logger.error(f"Packet capture error: {exc}")

    def _packet_callback(self, packet) -> None:
        """Called by Scapy for every captured packet (in thread context)."""
        try:
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(
                self._packet_buffer.put(packet), loop
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Analysis loop
    # ------------------------------------------------------------------

    async def _analyse_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                packet = await asyncio.wait_for(self._packet_buffer.get(), timeout=1.0)
                self._packets_analysed += 1
                await self._analyse_packet(packet)
            except asyncio.TimeoutError:
                continue
            except Exception as exc:
                logger.debug(f"Packet analyse error: {exc}")

    async def _analyse_packet(self, packet) -> None:
        if not SCAPY_AVAILABLE:
            return

        await self._detect_port_scan(packet)
        await self._detect_arp_spoof(packet)
        await self._detect_deauth(packet)

    # ------------------------------------------------------------------
    # Port scan detection
    # ------------------------------------------------------------------

    async def _detect_port_scan(self, packet) -> None:
        if not SCAPY_AVAILABLE:
            return
        if not packet.haslayer(IP) or not packet.haslayer(TCP):
            return

        src = packet[IP].src
        dst_port = int(packet[TCP].dport)
        now = time.monotonic()

        entry = self._port_hits.setdefault(src, {"ports": {}, "last_seen": 0})
        entry["ports"][dst_port] = now
        entry["last_seen"] = now

        # Clean old entries
        cutoff = now - self._port_scan_window
        entry["ports"] = {p: t for p, t in entry["ports"].items() if t > cutoff}

        if len(entry["ports"]) >= self._port_scan_threshold:
            threat = Threat(
                threat_type="port_scan",
                source_ip=src,
                confidence=0.9,
                evidence={"ports_scanned": list(entry["ports"].keys())[:20]},
                timestamp=self._now(),
            )
            await self._handle_threat(threat)
            # Reset to avoid repeated alerts
            entry["ports"].clear()

    # ------------------------------------------------------------------
    # ARP spoof detection
    # ------------------------------------------------------------------

    async def _detect_arp_spoof(self, packet) -> None:
        if not SCAPY_AVAILABLE:
            return
        if not packet.haslayer(ARP):
            return

        arp = packet[ARP]
        if arp.op != 2:  # is-at (reply)
            return

        ip = arp.psrc
        mac = arp.hwsrc
        if not ip or not mac:
            return

        if ip in self._arp_table:
            old_mac = self._arp_table[ip]
            if old_mac.upper() != mac.upper():
                threat = Threat(
                    threat_type="arp_spoof",
                    source_ip=ip,
                    confidence=0.85,
                    evidence={"ip": ip, "old_mac": old_mac, "new_mac": mac},
                    timestamp=self._now(),
                )
                await self._handle_threat(threat)
        self._arp_table[ip] = mac.upper()

    # ------------------------------------------------------------------
    # Deauth detection
    # ------------------------------------------------------------------

    async def _detect_deauth(self, packet) -> None:
        if not SCAPY_AVAILABLE:
            return
        if not packet.haslayer(Dot11Deauth):
            return

        src = packet.addr2
        if not src:
            return

        now = time.monotonic()
        window = self._deauth_counts.setdefault(src, [])
        window.append(now)

        # Clean old
        cutoff = now - 5.0
        self._deauth_counts[src] = [t for t in window if t > cutoff]

        if len(self._deauth_counts[src]) >= self._deauth_threshold:
            threat = Threat(
                threat_type="deauth",
                source_ip=src,
                confidence=0.8,
                evidence={"deauth_count": len(self._deauth_counts[src])},
                timestamp=self._now(),
            )
            await self._handle_threat(threat)
            self._deauth_counts[src].clear()

    # ------------------------------------------------------------------
    # Threat handling
    # ------------------------------------------------------------------

    async def _handle_threat(self, threat: Threat) -> None:
        self._threats.append(threat)
        if len(self._threats) > 100:
            self._threats.pop(0)

        await self._redis_state.set_global("active_threat", threat.__dict__, broadcast=True)

        await self._event_bus.publish("threat_detected", threat.__dict__)
        await self._event_bus.publish("threat_raw_detected", {
            "threat_type": threat.threat_type,
            "source_ip": threat.source_ip,
            "timestamp": threat.timestamp,
            "confidence": threat.confidence,
            "evidence": threat.evidence,
        })
        await self._event_bus.publish(
            "tts_speak",
            {
                "text": f"Security alert. {threat.threat_type.replace('_', ' ')} detected from {threat.source_ip}.",
                "priority": "urgent",
            },
        )

        if threat.threat_type == "port_scan":
            await self._auto_block(threat.source_ip)

    async def _auto_block(self, ip: str) -> None:
        """Attempt to block IP at firewall level."""
        logger.warning(f"Auto-blocking {ip} due to port scan")
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["netsh", "advfirewall", "firewall", "add", "rule",
                     f"name=DEEP-BLOCK-{ip}", "dir=in", "action=block",
                     f"remoteip={ip}"],
                    capture_output=True, timeout=5,
                )
            else:
                subprocess.run(
                    ["iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"],
                    capture_output=True, timeout=5,
                )
            await self._event_bus.publish(
                "ip_blocked",
                {"ip": ip, "reason": "port_scan"},
            )
        except Exception as exc:
            logger.warning(f"Auto-block failed for {ip}: {exc}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_threats(self, hours: int = 24) -> list[Threat]:
        cutoff = time.time() - (hours * 3600)
        return [
            t for t in self._threats
            if datetime.fromisoformat(t.timestamp.replace("Z", "+00:00")).timestamp() > cutoff
        ]
