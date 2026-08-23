"""
core/security/network_monitor.py

DEEP Network Security Monitor — 100% offline, local network intelligence.

Features:
- Passive ARP table monitoring (no external packets sent)
- Active connection tracking via psutil
- Device registry with fingerprinting
- Anomaly detection (new devices, unknown MACs, port changes)
- Network topology mapping
- All data stays local — zero API keys, zero cloud calls

Usage:
    from DEEP.core.security.network_monitor import NetworkMonitor
    
    monitor = NetworkMonitor()
    await monitor.initialize()
    
    # Get current network snapshot
    snapshot = await monitor.get_snapshot()
    
    # Check for anomalies
    alerts = monitor.check_anomalies()
    
    # Stream events to UI
    for event in monitor.poll_events():
        await ws.send_json({"type": "security_alert", ...})
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import socket
import struct
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

try:
    from core.event_bus import EventBus
except ImportError:
    from event_bus import EventBus

logger = logging.getLogger(__name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available — network monitor will use fallback methods")


# ═══════════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class SecuritySeverity(Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class NetworkDevice:
    """A discovered device on the local network."""
    mac: str
    ip: str
    hostname: Optional[str] = None
    vendor: Optional[str] = None  # Derived from MAC OUI
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    is_gateway: bool = False
    is_localhost: bool = False
    trust_status: str = "unknown"  # trusted, unknown, suspicious, blocked
    open_ports: List[int] = field(default_factory=list)
    os_guess: Optional[str] = None
    connection_count: int = 0
    data_sent_mb: float = 0.0
    data_recv_mb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mac": self.mac,
            "ip": self.ip,
            "hostname": self.hostname,
            "vendor": self.vendor,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "is_gateway": self.is_gateway,
            "is_localhost": self.is_localhost,
            "trust_status": self.trust_status,
            "open_ports": self.open_ports,
            "os_guess": self.os_guess,
            "connection_count": self.connection_count,
        }


@dataclass
class SecurityEvent:
    """A security-relevant event detected by the monitor."""
    id: str
    timestamp: datetime
    event_type: str  # new_device, device_offline, port_change, traffic_anomaly, unknown_mac
    severity: SecuritySeverity
    title: str
    description: str
    device_mac: Optional[str] = None
    device_ip: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "device_mac": self.device_mac,
            "device_ip": self.device_ip,
            "details": self.details,
            "acknowledged": self.acknowledged,
        }


@dataclass
class NetworkSnapshot:
    """A point-in-time view of the local network."""
    timestamp: datetime
    interface: str
    local_ip: str
    subnet: str
    gateway: Optional[str]
    devices: List[NetworkDevice]
    active_connections: int
    listening_ports: List[int]
    events_since_last: List[SecurityEvent]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "interface": self.interface,
            "local_ip": self.local_ip,
            "subnet": self.subnet,
            "gateway": self.gateway,
            "device_count": len(self.devices),
            "devices": [d.to_dict() for d in self.devices],
            "active_connections": self.active_connections,
            "listening_ports": self.listening_ports,
            "events": [e.to_dict() for e in self.events_since_last],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MAC OUI Lookup (embedded common vendors — no external DB needed)
# ═══════════════════════════════════════════════════════════════════════════════

_COMMON_OUIS = {
    "00:50:56": "VMware",
    "00:0c:29": "VMware",
    "00:15:5d": "Microsoft Hyper-V",
    "00:1b:21": "Intel Corporate",
    "00:1c:42": "Parallels",
    "00:25:00": "Apple",
    "3c:5a:b4": "Google",
    "40:4d:8e": "Amazon Technologies",
    "48:a4:72": "Liteon Technology",
    "50:1a:c5": "Huawei",
    "5c:cf:7f": "Espressif",  # ESP32
    "64:69:4e": "zte",
    "68:54:fd": "Amazon Technologies",
    "74:75:48": "Amazon Technologies",
    "78:4f:43": "Samsung",
    "7c:49:eb": "Huawei",
    "84:d8:1b": "Intel Corporate",
    "88:79:7e": "Samsung",
    "8c:85:90": "Apple",
    "90:9a:4a": "Espressif",
    "a0:36:9f": "Intel Corporate",
    "a4:77:33": "Huawei",
    "ac:de:48": "Apple",
    "b0:35:0f": "Amazon Technologies",
    "b0:be:76": "Amazon Technologies",
    "b4:e6:2a": "Microsoft",
    "bc:54:2f": "Samsung",
    "c0:49:ef": "Espressif",
    "c8:3a:35": "Espressif",
    "cc:b8:37": "Samsung",
    "d0:59:e3": "ASRock",
    "d4:3d:7e": "Micro-Star",
    "d8:3b:bf": "Huawei",
    "dc:a6:32": "Raspberry Pi",
    "e0:5f:45": "Microsoft",
    "e4:5f:01": "Intel Corporate",
    "ec:11:27": "Samsung",
    "f0:18:98": "Liteon Technology",
    "f4:8c:50": "Intel Corporate",
    "f8:ff:c2": "Intel Corporate",
    "fc:19:99": "Intel Corporate",
    "00:14:22": "Dell",
    "00:1a:a0": "Dell",
    "00:21:70": "Dell",
    "00:26:b9": "Dell",
    "00:50:56": "VMware",
    "08:00:27": "VirtualBox",
    "0a:00:27": "VirtualBox",
}


def _lookup_vendor(mac: str) -> Optional[str]:
    """Look up vendor from MAC address OUI (first 3 bytes)."""
    prefix = mac[:8].upper().replace("-", ":")
    return _COMMON_OUIS.get(prefix)


# ═══════════════════════════════════════════════════════════════════════════════
# Network Monitor
# ═══════════════════════════════════════════════════════════════════════════════

#: A reverse lookup that has not answered in this long will not answer usefully.
#: The device is still tracked; it is simply listed by address.
HOSTNAME_TIMEOUT_S = 1.5

#: How long a resolved (or unresolvable) name is trusted. Names on a home LAN
#: do not move faster than this, and re-asking is what made sweeps expensive.
HOSTNAME_CACHE_TTL_S = 900.0


class NetworkMonitor:
    """
    Local network security monitor.
    Passively observes the network, detects anomalies, and alerts.
    """

    def __init__(self, data_dir: Optional[Path] = None, event_bus: EventBus = None):
        self.data_dir = data_dir or Path(__file__).parent.parent.parent / "data" / "security"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Persistent state
        self.device_registry: Dict[str, NetworkDevice] = {}  # mac -> device
        self.known_macs: Set[str] = set()
        self.trusted_macs: Set[str] = set()
        self.blocked_macs: Set[str] = set()
        self.event_log: List[SecurityEvent] = []
        self.event_bus = event_bus

        # Deduplication: track MACs already notified for unknown-vendor so
        # check_anomalies() doesn't re-fire the same alert every 30 s.
        self._unknown_notified: Set[str] = set()
        
        # Baseline for anomaly detection
        self.baseline_device_count: int = 0
        self.baseline_established: bool = False
        self.baseline_samples: int = 0
        
        # Runtime
        self._initialized = False
        self._scan_task: Optional[asyncio.Task] = None
        self._scan_interval = 30  # seconds
        #: ip -> (hostname or None, monotonic timestamp). Negatives are cached
        #: too; see _resolve_hostnames.
        self._hostname_cache: Dict[str, tuple[Optional[str], float]] = {}
        self._last_scan: Optional[datetime] = None
        
        # Load previous state if exists
        self._load_state()

    async def start(self) -> None:
        """Activate the network monitor, without waiting for the first sweep.

        The baseline used to be established here, synchronously: probe every
        address on the LAN, then return. That is tens of seconds when nmap is
        absent and each probe has to wait out its own timeout — and the caller
        is a server whose port does not open until startup returns, so the
        whole wait was charged to the user as an unreachable server.

        Nothing was gained by waiting. The background loop's first action is
        that identical sweep, so the scan simply ran twice. The loop now marks
        the baseline when its first sweep lands; until then
        ``baseline_established`` stays False and the device-flood check does
        not fire — exactly the state a fresh install is in anyway.
        """
        self.start_monitoring()
        logger.info("[NetworkMonitor] Started")

    async def stop(self) -> None:
        """Deactivate the network monitor."""
        self.stop_monitoring()
        logger.info("[NetworkMonitor] Stopped")

    def status(self) -> Dict[str, Any]:
        """Return operational status."""
        return {
            "devices": len(self.device_registry),
            "events": len(self.event_log),
            "monitoring": self._scan_task is not None and not self._scan_task.done(),
        }

    # ─── Persistence ─────────────────────────────────────────────────────────

    def _state_file(self) -> Path:
        return self.data_dir / "network_state.json"

    def _load_state(self):
        """Load device registry from disk."""
        f = self._state_file()
        if not f.exists():
            return
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            for mac, dev_data in data.get("devices", {}).items():
                self.device_registry[mac] = NetworkDevice(
                    mac=dev_data["mac"],
                    ip=dev_data["ip"],
                    hostname=dev_data.get("hostname"),
                    vendor=dev_data.get("vendor"),
                    first_seen=datetime.fromisoformat(dev_data["first_seen"]),
                    last_seen=datetime.fromisoformat(dev_data["last_seen"]),
                    trust_status=dev_data.get("trust_status", "unknown"),
                    open_ports=dev_data.get("open_ports", []),
                )
                self.known_macs.add(mac)
                if dev_data.get("trust_status") == "trusted":
                    self.trusted_macs.add(mac)
                elif dev_data.get("trust_status") == "blocked":
                    self.blocked_macs.add(mac)
            self.baseline_device_count = data.get("baseline_device_count", 0)
            self.baseline_established = data.get("baseline_established", False)
            logger.info(f"[NetworkMonitor] Loaded {len(self.device_registry)} devices from state")
        except Exception as e:
            logger.warning(f"[NetworkMonitor] Failed to load state: {e}")

    def _save_state(self):
        """Persist device registry to disk."""
        try:
            data = {
                "saved_at": datetime.utcnow().isoformat(),
                "baseline_device_count": self.baseline_device_count,
                "baseline_established": self.baseline_established,
                "devices": {
                    mac: {
                        "mac": d.mac,
                        "ip": d.ip,
                        "hostname": d.hostname,
                        "vendor": d.vendor,
                        "first_seen": d.first_seen.isoformat(),
                        "last_seen": d.last_seen.isoformat(),
                        "trust_status": d.trust_status,
                        "open_ports": d.open_ports,
                    }
                    for mac, d in self.device_registry.items()
                },
            }
            self._state_file().write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"[NetworkMonitor] Failed to save state: {e}")

    # ─── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _is_local_ip(ip: str) -> bool:
        """Return True only for RFC 1918 / link-local / loopback addresses.
        Internet IPs that appear in ARP (via the gateway's cached entry) are not
        real local devices and should not be tracked as network peers."""
        if ip.startswith("127.") or ip.startswith("169.254."):
            return True
        if ip.startswith("10."):
            return True
        if ip.startswith("192.168."):
            return True
        if ip.startswith("172."):
            try:
                second = int(ip.split(".")[1])
                return 16 <= second <= 31
            except (IndexError, ValueError):
                return False
        return False

    # ─── Public API ──────────────────────────────────────────────────────────

    async def initialize(self):
        """Initialize the monitor. Run an initial scan to establish baseline."""
        if self._initialized:
            return
        logger.info("[NetworkMonitor] Initializing...")
        await self._do_scan()
        self._establish_baseline()

    def _establish_baseline(self) -> None:
        """Record what "normal" looks like, once a sweep has actually seen it.

        Called from whichever sweep lands first — the explicit ``initialize()``
        or the background loop — and idempotent, because both may run.
        """
        if not self.baseline_established and self.device_registry:
            self.baseline_device_count = len(self.device_registry)
            self.baseline_established = True
            logger.info(f"[NetworkMonitor] Baseline established: {self.baseline_device_count} devices")
        self._initialized = True

    def start_monitoring(self):
        """Start the background scanning loop."""
        if self._scan_task and not self._scan_task.done():
            return
        self._scan_task = asyncio.create_task(self._scan_loop())
        logger.info("[NetworkMonitor] Background scanning started")

    def stop_monitoring(self):
        """Stop the background scanning loop."""
        if self._scan_task:
            self._scan_task.cancel()
            self._scan_task = None
            logger.info("[NetworkMonitor] Background scanning stopped")

    def get_devices(self) -> List[NetworkDevice]:
        """Return all known devices."""
        return list(self.device_registry.values())

    def get_device(self, mac: str) -> Optional[NetworkDevice]:
        return self.device_registry.get(mac)

    def get_events(self, severity: Optional[SecuritySeverity] = None, limit: int = 50) -> List[SecurityEvent]:
        """Return recent security events."""
        events = sorted(self.event_log, key=lambda e: e.timestamp, reverse=True)
        if severity:
            events = [e for e in events if e.severity == severity]
        return events[:limit]

    def get_unacknowledged_events(self) -> List[SecurityEvent]:
        return [e for e in self.event_log if not e.acknowledged]

    def acknowledge_event(self, event_id: str) -> bool:
        for e in self.event_log:
            if e.id == event_id:
                e.acknowledged = True
                return True
        return False

    def trust_device(self, mac: str):
        """Mark a device as trusted."""
        mac = mac.lower()
        self.trusted_macs.add(mac)
        self.blocked_macs.discard(mac)
        if mac in self.device_registry:
            self.device_registry[mac].trust_status = "trusted"
        self._save_state()

    def block_device(self, mac: str):
        """Mark a device as blocked/suspicious."""
        mac = mac.lower()
        self.blocked_macs.add(mac)
        self.trusted_macs.discard(mac)
        if mac in self.device_registry:
            self.device_registry[mac].trust_status = "blocked"
        self._save_state()

    def untrust_device(self, mac: str):
        """Reset a device to unknown status."""
        mac = mac.lower()
        self.trusted_macs.discard(mac)
        self.blocked_macs.discard(mac)
        if mac in self.device_registry:
            self.device_registry[mac].trust_status = "unknown"
        self._save_state()

    async def get_snapshot(self) -> NetworkSnapshot:
        """Get a full network snapshot."""
        devices = self.get_devices()
        connections = self._get_active_connections()
        listening = self._get_listening_ports()
        interface, local_ip, subnet, gateway = self._get_network_info()
        events = [e for e in self.event_log if self._last_scan and e.timestamp >= self._last_scan]
        return NetworkSnapshot(
            timestamp=datetime.utcnow(),
            interface=interface,
            local_ip=local_ip,
            subnet=subnet,
            gateway=gateway,
            devices=devices,
            active_connections=connections,
            listening_ports=listening,
            events_since_last=events,
        )

    # ─── Background Loop ───────────────────────────────────────────────────

    async def _scan_loop(self):
        while True:
            try:
                await self._do_scan()
                self._establish_baseline()
                self._save_state()
            except Exception as e:
                logger.error(f"[NetworkMonitor] Scan error: {e}")
            await asyncio.sleep(self._scan_interval)

    async def _do_scan(self):
        """Perform one full network scan."""
        self._last_scan = datetime.utcnow()
        
        # Collect data from multiple sources. Both shell out or walk kernel
        # tables and block; on the event loop that stalls every other request.
        arp_entries = await asyncio.to_thread(self._get_arp_table)
        connections = await asyncio.to_thread(self._get_connection_peers)
        
        # Merge into unified device view
        all_ips: Dict[str, str] = {}  # ip -> mac
        all_macs: Dict[str, str] = {}  # mac -> ip
        
        for entry in arp_entries:
            ip, mac = entry["ip"], entry["mac"].lower()
            all_ips[ip] = mac
            all_macs[mac] = ip
        
        for peer in connections:
            ip = peer["ip"]
            mac = peer.get("mac", "").lower()
            if mac and mac != "00:00:00:00:00:00":
                all_ips[ip] = mac
                all_macs[mac] = ip
        
        # Get network info for gateway detection
        _, _, _, gateway = self._get_network_info()

        # Drop internet IPs — only track devices on the local subnet.
        # ARP caches on Windows often contain internet IPs mapped to the gateway
        # MAC, which would otherwise flood the activity feed with "Unknown vendor"
        # alerts for every browser tab open to an external server.
        #
        # This filter runs *before* hostname resolution, not after. Resolving
        # first meant every external address a browser tab had touched got its
        # own reverse-DNS lookup, and the answers were thrown away one line
        # later: 29 lookups to keep 4. That was measured at 121s per sweep.
        all_ips = {ip: mac for ip, mac in all_ips.items() if self._is_local_ip(ip)}

        # Resolve hostnames (only for the devices we are actually keeping)
        hostnames = await self._resolve_hostnames(list(all_ips.keys()))

        # Process each device
        current_macs = set()
        for ip, mac in all_ips.items():
            current_macs.add(mac)
            hostname = hostnames.get(ip)
            vendor = _lookup_vendor(mac)
            is_gateway = (ip == gateway)
            is_localhost = (ip == "127.0.0.1" or ip.startswith("127."))
            
            if mac in self.device_registry:
                # Update existing
                dev = self.device_registry[mac]
                dev.last_seen = datetime.utcnow()
                dev.ip = ip
                if hostname and not dev.hostname:
                    dev.hostname = hostname
                dev.connection_count = sum(1 for p in connections if p["ip"] == ip)
            else:
                # New device detected
                dev = NetworkDevice(
                    mac=mac,
                    ip=ip,
                    hostname=hostname,
                    vendor=vendor,
                    is_gateway=is_gateway,
                    is_localhost=is_localhost,
                )
                self.device_registry[mac] = dev
                self.known_macs.add(mac)
                
                # Determine trust status
                if is_gateway:
                    dev.trust_status = "trusted"
                    self.trusted_macs.add(mac)
                elif is_localhost:
                    dev.trust_status = "trusted"
                    self.trusted_macs.add(mac)
                
                # Only alert for non-trivial new devices (skip gateway/localhost)
                if not (is_gateway or is_localhost):
                    self._emit_event(
                        event_type="new_device",
                        severity=SecuritySeverity.MEDIUM,
                        title=f"New device: {vendor or hostname or ip}",
                        description=f"Device at {ip} ({mac}) has appeared on the network.",
                        device_mac=mac,
                        device_ip=ip,
                        details={"vendor": vendor, "hostname": hostname, "is_gateway": is_gateway},
                    )
        
        # Check for devices that disappeared
        for mac in list(self.device_registry.keys()):
            if mac not in current_macs:
                dev = self.device_registry[mac]
                offline_since = (datetime.utcnow() - dev.last_seen).total_seconds()
                # Only alert if it was recently seen (within last 5 minutes window)
                if offline_since < 300:
                    self._emit_event(
                        event_type="device_offline",
                        severity=SecuritySeverity.LOW,
                        title=f"Device went offline: {dev.hostname or dev.ip}",
                        description=f"Device {dev.ip} ({dev.mac}) is no longer reachable.",
                        device_mac=mac,
                        device_ip=dev.ip,
                    )

    # ─── Event Emission ────────────────────────────────────────────────────

    def _emit_event(self, event_type: str, severity: SecuritySeverity, title: str,
                    description: str, device_mac: Optional[str] = None,
                    device_ip: Optional[str] = None, details: Optional[Dict] = None):
        event = SecurityEvent(
            id=f"sec-{int(time.time()*1000)}-{event_type}",
            timestamp=datetime.utcnow(),
            event_type=event_type,
            severity=severity,
            title=title,
            description=description,
            device_mac=device_mac,
            device_ip=device_ip,
            details=details or {},
        )
        self.event_log.append(event)
        # Keep only last 1000 events
        if len(self.event_log) > 1000:
            self.event_log = self.event_log[-1000:]
        
        logger.info(f"[Security] {severity.value.upper()}: {title}")
        
        if self.event_bus:
            try:
                asyncio.create_task(self.event_bus.publish("security_alert", event.to_dict()))
            except RuntimeError:
                pass

    # ─── Data Collection Methods ─────────────────────────────────────────────

    def _get_arp_table(self) -> List[Dict[str, str]]:
        """Get ARP table entries using platform-specific commands."""
        entries = []
        try:
            # Windows: arp -a
            result = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=10)
            for line in result.stdout.splitlines():
                # Format: Interface: x.x.x.x --- 0xN
                #         Internet Address      Physical Address      Type
                #         192.168.1.1           ab-cd-ef-12-34-56     dynamic
                m = re.match(r"\s+(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F\-]{17})\s+(\w+)", line)
                if m:
                    ip = m.group(1)
                    mac = m.group(2).replace("-", ":").lower()
                    entries.append({"ip": ip, "mac": mac, "type": m.group(3)})
        except Exception as e:
            logger.debug(f"ARP scan fallback: {e}")
        return entries

    def _get_connection_peers(self) -> List[Dict[str, Any]]:
        """Get peer IPs from active connections."""
        peers = []
        if not PSUTIL_AVAILABLE:
            return peers
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.status == psutil.CONN_ESTABLISHED and conn.raddr:
                    ip = conn.raddr.ip
                    if not ip.startswith("127.") and not ip.startswith("::"):
                        peers.append({"ip": ip, "port": conn.raddr.port, "mac": ""})
        except (psutil.AccessDenied, Exception):
            pass
        return peers

    def _get_listening_ports(self) -> List[int]:
        """Get ports this machine is listening on."""
        ports = []
        if not PSUTIL_AVAILABLE:
            return ports
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.status == psutil.CONN_LISTEN:
                    ports.append(conn.laddr.port)
        except (psutil.AccessDenied, Exception):
            pass
        return sorted(set(ports))

    def _get_active_connections(self) -> int:
        """Count total active connections."""
        if not PSUTIL_AVAILABLE:
            return 0
        try:
            return sum(1 for c in psutil.net_connections(kind="inet")
                       if c.status == psutil.CONN_ESTABLISHED)
        except Exception:
            return 0

    def _get_network_info(self) -> tuple:
        """Get local interface, IP, subnet, and gateway."""
        interface = "unknown"
        local_ip = "127.0.0.1"
        subnet = "127.0.0.0/8"
        gateway = None
        
        if PSUTIL_AVAILABLE:
            try:
                # Find the first non-loopback interface with an IP
                for name, addrs in psutil.net_if_addrs().items():
                    for addr in addrs:
                        if addr.family == socket.AF_INET:
                            ip = addr.address
                            if not ip.startswith("127.") and not ip.startswith("169.254."):
                                interface = name
                                local_ip = ip
                                # Estimate subnet from netmask
                                if addr.netmask:
                                    subnet = self._ip_with_mask(ip, addr.netmask)
                                break
                    if interface != "unknown":
                        break
            except Exception:
                pass
        
        # Try to get gateway via route print (Windows)
        try:
            result = subprocess.run(["route", "print", "0.0.0.0"], capture_output=True, text=True, timeout=5)
            for line in result.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 3 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                    gateway = parts[2]
                    break
        except Exception:
            pass
        
        return interface, local_ip, subnet, gateway

    def _ip_with_mask(self, ip: str, mask: str) -> str:
        """Calculate CIDR notation from IP and netmask."""
        try:
            ip_int = struct.unpack("!I", socket.inet_aton(ip))[0]
            mask_int = struct.unpack("!I", socket.inet_aton(mask))[0]
            prefix = bin(mask_int).count("1")
            return f"{ip}/{prefix}"
        except Exception:
            return ip

    async def _resolve_hostnames(self, ips: List[str]) -> Dict[str, str]:
        """Reverse-resolve a set of IPs, concurrently and with a deadline.

        ``socket.gethostbyaddr`` is blocking and has no timeout argument: an
        address with no PTR record costs whatever the resolver decides, and a
        serial loop pays that per IP. Measured here, one sweep spent 121s
        inside this function while the event loop — the whole server, HUD and
        API included — sat frozen behind it, then did it again 30s later.

        So: each lookup goes to a worker thread, they run together rather than
        in sequence, and each is abandoned at ``HOSTNAME_TIMEOUT_S``. A device
        whose name we cannot learn quickly is listed by address, which is what
        the UI showed for it anyway.

        Answers are cached, negatives included — an address that has no PTR
        record still has none 30 seconds later, and re-asking is how a sweep
        that should be instant becomes a stall.
        """
        if not ips:
            return {}

        now = time.monotonic()
        fresh = {
            ip: name
            for ip, (name, at) in self._hostname_cache.items()
            if now - at < HOSTNAME_CACHE_TTL_S
        }
        unknown = [ip for ip in ips if ip not in fresh]

        async def resolve(ip: str) -> tuple[str, Optional[str]]:
            try:
                name, _, _ = await asyncio.wait_for(
                    asyncio.to_thread(socket.gethostbyaddr, ip),
                    timeout=HOSTNAME_TIMEOUT_S,
                )
                return ip, name
            except (socket.herror, socket.gaierror, asyncio.TimeoutError, OSError):
                return ip, None

        for ip, name in await asyncio.gather(*(resolve(ip) for ip in unknown)):
            self._hostname_cache[ip] = (name, now)

        resolved: Dict[str, str] = {}
        for ip in ips:
            name = fresh.get(ip) if ip in fresh else self._hostname_cache.get(ip, (None, 0))[0]
            if name:
                resolved[ip] = name
        return resolved

    # ─── Anomaly Detection ───────────────────────────────────────────────────

    def check_anomalies(self) -> List[SecurityEvent]:
        """Run anomaly detection rules and return any new events."""
        anomalies = []
        
        # Rule 1: Too many new devices
        current_count = len([d for d in self.device_registry.values() if not d.is_localhost])
        if self.baseline_established and current_count > self.baseline_device_count + 3:
            event = SecurityEvent(
                id=f"sec-{int(time.time()*1000)}-anomaly",
                timestamp=datetime.utcnow(),
                event_type="device_count_anomaly",
                severity=SecuritySeverity.HIGH,
                title="Unusual number of devices detected",
                description=f"Expected ~{self.baseline_device_count} devices, found {current_count}.",
                details={"expected": self.baseline_device_count, "found": current_count},
            )
            anomalies.append(event)
        
        # Rule 2: Unknown vendor on local device — emit ONCE per MAC lifetime
        for mac, dev in self.device_registry.items():
            if (mac not in self.trusted_macs
                    and not dev.is_localhost
                    and not dev.vendor
                    and mac not in self._unknown_notified):
                self._unknown_notified.add(mac)
                event = SecurityEvent(
                    id=f"sec-{int(time.time()*1000)}-unknown",
                    timestamp=datetime.utcnow(),
                    event_type="unknown_mac",
                    severity=SecuritySeverity.MEDIUM,
                    title=f"Unknown device vendor: {dev.ip}",
                    description=f"Device {dev.ip} ({mac}) has an unrecognized MAC address.",
                    device_mac=mac,
                    device_ip=dev.ip,
                )
                anomalies.append(event)
        
        # Rule 3: Gateway IP changed unexpectedly
        _, _, _, current_gateway = self._get_network_info()
        gateway_devs = [d for d in self.device_registry.values() if d.is_gateway]
        if gateway_devs:
            known_gateway = gateway_devs[0].ip
            if current_gateway and current_gateway != known_gateway:
                event = SecurityEvent(
                    id=f"sec-{int(time.time()*1000)}-gateway",
                    timestamp=datetime.utcnow(),
                    event_type="gateway_change",
                    severity=SecuritySeverity.CRITICAL,
                    title="Gateway IP has changed!",
                    description=f"Gateway changed from {known_gateway} to {current_gateway}. Possible network compromise or reconfiguration.",
                    details={"old": known_gateway, "new": current_gateway},
                )
                anomalies.append(event)
        
        return anomalies

    # ─── Trust & Reputation ────────────────────────────────────────────────

    def get_trust_summary(self) -> Dict[str, Any]:
        """Summary of device trust status."""
        devices = self.get_devices()
        return {
            "total": len(devices),
            "trusted": len([d for d in devices if d.trust_status == "trusted"]),
            "unknown": len([d for d in devices if d.trust_status == "unknown"]),
            "suspicious": len([d for d in devices if d.trust_status == "blocked"]),
            "recent_events": len([e for e in self.event_log
                                    if e.timestamp > datetime.utcnow() - timedelta(hours=24)]),
        }
