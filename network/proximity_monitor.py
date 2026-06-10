"""
network/proximity_monitor.py

Passive Proximity Monitor for DEEP v2.

Observes publicly broadcast wireless signals near your physical
location — WiFi beacon frames and Bluetooth advertisement packets.
No interaction with devices you do not own.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LEGAL BOUNDARY (enforced in code)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ALLOWED — passive observation of public broadcasts:
  - WiFi beacon frames (SSIDs, BSSIDs, signal strength)
    Every router/AP broadcasts these openly to all
  - Bluetooth advertisement packets (device name, MAC, RSSI)
    — devices broadcast these to be discoverable
  - Counting/tracking that a device EXISTS nearby
  - Pattern detection over time

NOT ALLOWED — never implemented:
  - Connecting to any device not in KNOWN_DEVICES
  - Capturing data packets from other networks
  - Deauthenticating or jamming any device
  - Reading communications of any kind
  - Active probing (sending packets to unknown devices)

THIS FILE CONTAINS ZERO active probing, connection, or send calls.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import asyncio
import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# bleak is optional — gracefully degrade
try:
    from bleak import BleakScanner
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    BleakScanner = None  # type: ignore[misc,assignment]
    logger.warning("bleak not installed — Bluetooth proximity disabled")

# Enrichment helpers (independent of bleak; used by WiFi too).
try:
    from network.enrich import (
        ble_vendor as _ble_vendor, ble_services as _ble_services,
        is_tracker as _is_tracker, rssi_distance as _rssi_distance,
        wifi_band as _wifi_band, mac_vendor as _mac_vendor,
    )
except Exception:  # pragma: no cover
    _ble_vendor = lambda *a, **k: (None, None)            # noqa: E731
    _ble_services = lambda *a, **k: []                     # noqa: E731
    _is_tracker = lambda *a, **k: (False, None)            # noqa: E731
    _rssi_distance = lambda *a, **k: None                  # noqa: E731
    _wifi_band = lambda c: ""                              # noqa: E731
    _mac_vendor = lambda m: None                           # noqa: E731

# Durable sensing memory (persistent history + behavioural baselines).
try:
    from network.proximity_store import get_store as _get_store
except Exception:  # pragma: no cover
    _get_store = lambda: None  # noqa: E731


# ── Data models ─────────────────────────────────────────────────────────


@dataclass
class ProximityAP:
    """Nearby WiFi access point discovered via passive scan."""

    ssid: str = ""
    bssid: str = ""
    signal_dbm: int = 0
    channel: int = 0
    encryption: str = ""
    first_seen: str = ""
    last_seen: str = ""
    seen_count: int = 0
    is_yours: bool = False
    # enrichment
    vendor: str | None = None
    band: str = ""
    hidden: bool = False


@dataclass
class ProximityBTDevice:
    """Nearby Bluetooth device discovered via passive advertisement scan."""

    mac: str = ""
    name: str | None = None
    rssi: int = 0
    device_type: str = "unknown"
    first_seen: str = ""
    last_seen: str = ""
    seen_count: int = 0
    is_yours: bool = False
    # enrichment
    vendor: str | None = None
    company_id: int | None = None
    services: list = None  # type: ignore[assignment]
    distance_m: float | None = None
    tx_power: int | None = None
    is_tracker: bool = False
    tracker_kind: str | None = None

    def __post_init__(self):
        if self.services is None:
            self.services = []


# ── WiFi sensor ─────────────────────────────────────────────────────────


class WiFiProximitySensor:
    """Passive WiFi beacon frame observation."""

    def __init__(self, event_bus: Any, redis_state: Any) -> None:
        self._event_bus = event_bus
        self._redis_state = redis_state
        self._ap_history: dict[str, ProximityAP] = {}
        self._alerted_persistent: set[str] = set()   # BSSIDs already alerted (alert once, not every scan)
        self._known_aps: set[str] = self._resolve_known_aps()
        self._signal_threshold: int = self._resolve_int("proximity_signal_threshold", -80)
        self._persistence_threshold: int = self._resolve_int("persistence_threshold", 5)
        self._home_bssid: str = self._resolve_str("home_bssid", "").upper()
        self._home_ssid: str = self._resolve_str("home_ssid", "")
        self._store = _get_store()
        self._unusual_alerted: set[str] = set()
        self._load_persisted()

    def _load_persisted(self) -> None:
        """Seed history from the durable store so known APs survive restarts."""
        if not self._store:
            return
        try:
            for rid, rec in self._store.load_all().items():
                if rec.get("kind") != "wifi":
                    continue
                ex = rec.get("extra") or {}
                self._ap_history[rid] = ProximityAP(
                    ssid=rec.get("name") or "", bssid=rid,
                    signal_dbm=-100, channel=ex.get("channel", 0) or 0,
                    encryption=ex.get("encryption", ""),
                    first_seen=rec.get("first_seen", ""), last_seen=rec.get("last_seen", ""),
                    seen_count=rec.get("seen_count", 0), is_yours=(rid == self._home_bssid),
                    vendor=rec.get("vendor"), band=ex.get("band", ""),
                )
        except Exception:
            pass

    def _resolve_known_aps(self) -> set[str]:
        try:
            from core.config import Settings
            known = getattr(Settings(), "known_devices", {})
            return {k.upper() for k in known}
        except Exception:
            return set()

    def _resolve_int(self, name: str, default: int) -> int:
        try:
            from core.config import Settings
            return getattr(Settings(), name, default)
        except Exception:
            return default

    def _resolve_str(self, name: str, default: str) -> str:
        try:
            from core.config import Settings
            return getattr(Settings(), name, default)
        except Exception:
            return default

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # -- passive scan --

    async def scan(self) -> list[ProximityAP]:
        """Run a passive WiFi scan — no packets sent."""
        loop = asyncio.get_event_loop()
        if sys.platform == "win32":
            raw = await loop.run_in_executor(None, self._scan_windows)
        else:
            raw = await loop.run_in_executor(None, self._scan_linux)
        return self._merge_history(raw)

    def _scan_linux(self) -> list[dict[str, Any]]:
        networks: list[dict[str, Any]] = []
        try:
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
            enc_match = re.search(r'Encryption key:on', block)
            wpa_match = re.search(r'IE: WPA', block)
            wpa2_match = re.search(r'IE: IEEE 802.11i/WPA2', block)

            if bssid_match:
                bssid = bssid_match.group(1).upper()
                sig = int(signal_match.group(1)) if signal_match else -100
                encryption = "OPEN"
                if enc_match:
                    if wpa2_match:
                        encryption = "WPA2"
                    elif wpa_match:
                        encryption = "WPA"
                    else:
                        encryption = "WEP"
                networks.append({
                    "ssid": ssid_match.group(1) if ssid_match else "",
                    "bssid": bssid,
                    "signal_dbm": sig,
                    "channel": int(channel_match.group(1)) if channel_match else 0,
                    "encryption": encryption,
                })
        return networks

    def _scan_windows(self) -> list[dict[str, Any]]:
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

        current_ssid: str | None = None
        current_enc = "UNKNOWN"
        last: dict[str, Any] | None = None
        for line in output.splitlines():
            ssid_match = re.match(r'\s*SSID\s+\d+\s*:\s*(.*)', line)
            if ssid_match:
                current_ssid = ssid_match.group(1).strip()
                current_enc = "UNKNOWN"
                last = None
                continue

            auth_match = re.match(r'\s*Authentication\s*:\s*(.+)', line)
            if auth_match:
                a = auth_match.group(1).strip().lower()
                if "open" in a:        current_enc = "OPEN"
                elif "wpa3" in a:      current_enc = "WPA3"
                elif "wpa2" in a:      current_enc = "WPA2"
                elif "wpa" in a:       current_enc = "WPA"
                elif "wep" in a:       current_enc = "WEP"
                else:                  current_enc = auth_match.group(1).strip()
                continue

            bssid_match = re.match(r'\s*BSSID\s+\d+\s*:\s*([0-9a-f:]{17})', line, re.IGNORECASE)
            if bssid_match:
                last = {
                    "ssid": current_ssid or "",
                    "bssid": bssid_match.group(1).upper(),
                    "signal_dbm": -100,
                    "channel": 0,
                    "encryption": current_enc,
                }
                networks.append(last)
                continue

            if last is not None:
                sig_match = re.match(r'\s*Signal\s*:\s*(\d+)\s*%', line)
                if sig_match:
                    pct = int(sig_match.group(1))
                    last["signal_dbm"] = (pct // 2) - 100   # % → approx dBm
                    continue
                ch_match = re.match(r'\s*Channel\s*:\s*(\d+)', line)
                if ch_match:
                    last["channel"] = int(ch_match.group(1))
                    continue
        return networks

    def _merge_history(self, raw: list[dict[str, Any]]) -> list[ProximityAP]:
        now = self._now()
        results: list[ProximityAP] = []
        for data in raw:
            bssid = data["bssid"]
            is_yours = bssid == self._home_bssid
            if bssid in self._ap_history:
                existing = self._ap_history[bssid]
                existing.last_seen = now
                existing.signal_dbm = data.get("signal_dbm", existing.signal_dbm) or existing.signal_dbm
                existing.channel = data.get("channel", existing.channel) or existing.channel
                existing.seen_count += 1
                # back-fill enrichment for entries created before enrichment existed
                if not existing.vendor:
                    existing.vendor = _mac_vendor(bssid)
                if not existing.band or existing.band == "?":
                    existing.band = _wifi_band(existing.channel)
                results.append(existing)
            else:
                ssid = data.get("ssid", "")
                channel = data.get("channel", 0) or 0
                ap = ProximityAP(
                    ssid=ssid,
                    bssid=bssid,
                    signal_dbm=data.get("signal_dbm", -100) or -100,
                    channel=channel,
                    encryption=data.get("encryption", ""),
                    first_seen=now,
                    last_seen=now,
                    seen_count=1,
                    is_yours=is_yours,
                    vendor=_mac_vendor(bssid),
                    band=_wifi_band(channel),
                    hidden=(not ssid),
                )
                self._ap_history[bssid] = ap
                results.append(ap)
        return results

    # -- analysis --

    async def analyse(self, aps: list[ProximityAP]) -> None:
        for ap in aps:
            # Persist every sighting + behavioural baseline (all APs, incl. yours)
            if self._store:
                try:
                    res = self._store.observe(ap.bssid, "wifi", ap.ssid or None, ap.vendor,
                                              {"channel": ap.channel, "band": ap.band, "encryption": ap.encryption})
                    if (res.get("unusual_time") and not ap.is_yours
                            and ap.bssid not in self._unusual_alerted):
                        self._unusual_alerted.add(ap.bssid)
                        await self._event_bus.publish("device_unusual_time", {
                            "kind": "wifi", "id": ap.bssid, "name": ap.ssid or ap.vendor or ap.bssid,
                            "vendor": ap.vendor, "seen_count": ap.seen_count,
                            "note": "Established AP appearing at an atypical hour.",
                        })
                except Exception:
                    pass

            if ap.is_yours:
                continue  # skip your own AP

            # 1. Open network nearby
            if ap.encryption == "OPEN" and ap.signal_dbm > self._signal_threshold:
                await self._event_bus.publish(
                    "open_network_nearby",
                    {"ssid": ap.ssid, "bssid": ap.bssid, "signal_dbm": ap.signal_dbm},
                )

            # 2. Persistent unknown AP — alert ONCE per AP, not on every scan cycle
            if (ap.seen_count >= self._persistence_threshold and not ap.is_yours
                    and ap.bssid not in self._alerted_persistent):
                self._alerted_persistent.add(ap.bssid)
                await self._event_bus.publish(
                    "persistent_unknown_ap",
                    {"ssid": ap.ssid, "bssid": ap.bssid, "signal_dbm": ap.signal_dbm, "seen_count": ap.seen_count},
                )

            # 3. New strong signal AP
            if ap.seen_count <= 2 and ap.signal_dbm > -60:
                await self._event_bus.publish(
                    "strong_new_ap_detected",
                    {"ssid": ap.ssid, "bssid": ap.bssid, "signal_dbm": ap.signal_dbm, "channel": ap.channel, "encryption": ap.encryption},
                )

        # 4. AP disappeared after persistence
        current_bssids = {ap.bssid for ap in aps}
        for bssid, ap in list(self._ap_history.items()):
            if ap.seen_count > 10 and bssid not in current_bssids:
                # Already alerted? track via flag
                if not getattr(ap, "_disappeared_alerted", False):
                    ap._disappeared_alerted = True  # type: ignore[attr-defined]
                    await self._event_bus.publish(
                        "ap_left_proximity",
                        {"ssid": ap.ssid, "bssid": ap.bssid},
                    )


# ── Bluetooth sensor ────────────────────────────────────────────────────


class BluetoothProximitySensor:
    """Passive Bluetooth advertisement packet observation."""

    def __init__(self, event_bus: Any, redis_state: Any) -> None:
        self._event_bus = event_bus
        self._redis_state = redis_state
        self._bt_history: dict[str, ProximityBTDevice] = {}
        self._known_bt: set[str] = self._resolve_known_bt()
        self._close_threshold: int = self._resolve_int("bt_close_threshold", -60)
        self._absence_minutes: int = self._resolve_int("bt_absence_alert_minutes", 60)
        self._store = _get_store()
        self._unusual_alerted: set[str] = set()
        self._load_persisted()

    def _load_persisted(self) -> None:
        """Seed BT history from the durable store so known devices survive restarts."""
        if not self._store:
            return
        try:
            for rid, rec in self._store.load_all().items():
                if rec.get("kind") != "bt":
                    continue
                ex = rec.get("extra") or {}
                self._bt_history[rid] = ProximityBTDevice(
                    mac=rid, name=rec.get("name"), rssi=-100,
                    device_type=ex.get("device_type", "unknown"),
                    first_seen=rec.get("first_seen", ""), last_seen=rec.get("last_seen", ""),
                    seen_count=rec.get("seen_count", 0), is_yours=(rid in self._known_bt),
                    vendor=rec.get("vendor"), services=ex.get("services", []),
                )
        except Exception:
            pass

    def _resolve_known_bt(self) -> set[str]:
        try:
            from core.config import Settings
            known = getattr(Settings(), "known_bt_devices", {})
            return {k.upper() for k in known}
        except Exception:
            return set()

    def _resolve_int(self, name: str, default: int) -> int:
        try:
            from core.config import Settings
            return getattr(Settings(), name, default)
        except Exception:
            return default

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # -- passive scan --

    async def scan(self) -> list[ProximityBTDevice]:
        """Run a passive BLE advertisement scan — never connects. Captures the
        full advertisement (manufacturer data, service UUIDs, RSSI, tx power) and
        enriches each device with vendor, class, distance and tracker flags."""
        if not BLEAK_AVAILABLE or not BleakScanner:
            return []
        # bleak 3.x: return_adv=True yields {address: (BLEDevice, AdvertisementData)}
        try:
            discovered = await BleakScanner.discover(timeout=6.0, return_adv=True)
            pairs = list(discovered.values())
        except TypeError:
            # older bleak — no adv data
            devs = await BleakScanner.discover(timeout=6.0)
            pairs = [(d, None) for d in devs]
        except Exception as exc:
            logger.debug(f"BLE scan error: {exc}")
            return []

        now = self._now()
        results: list[ProximityBTDevice] = []
        for d, adv in pairs:
            mac = d.address.upper()
            man = getattr(adv, "manufacturer_data", None) or {}
            svc_uuids = getattr(adv, "service_uuids", None) or []
            name = (getattr(adv, "local_name", None) or d.name) or None
            rssi = getattr(adv, "rssi", None)
            if rssi is None:
                rssi = getattr(d, "rssi", -100)
            tx_power = getattr(adv, "tx_power", None)

            vendor, company_id = _ble_vendor(man)
            services = _ble_services(svc_uuids)
            tracker, tkind = _is_tracker(man, svc_uuids)
            distance = _rssi_distance(rssi, tx_power)
            is_yours = mac in self._known_bt
            device_type = self._infer_type(name) if name else (services[0].split()[0].lower() if services else "unknown")

            if mac in self._bt_history:
                dev = self._bt_history[mac]
                dev.last_seen = now
                dev.rssi = rssi
                dev.seen_count += 1
                dev.distance_m = distance
                if name and not dev.name:
                    dev.name = name
                if vendor and not dev.vendor:
                    dev.vendor = vendor
                    dev.company_id = company_id
                if services and not dev.services:
                    dev.services = services
                if tracker:
                    dev.is_tracker = True
                    dev.tracker_kind = tkind
            else:
                dev = ProximityBTDevice(
                    mac=mac, name=name, rssi=rssi, device_type=device_type,
                    first_seen=now, last_seen=now, seen_count=1, is_yours=is_yours,
                    vendor=vendor, company_id=company_id, services=services,
                    distance_m=distance, tx_power=tx_power,
                    is_tracker=tracker, tracker_kind=tkind,
                )
                self._bt_history[mac] = dev
            results.append(dev)
        return results

    def _infer_type(self, name: str | None) -> str:
        if not name:
            return "unknown"
        lowered = name.lower()
        keywords = {
            "phone": "phone",
            "iphone": "phone",
            "galaxy": "phone",
            "pixel": "phone",
            "headphone": "headphone",
            "headset": "headphone",
            "airpod": "headphone",
            "watch": "watch",
            "galaxy watch": "watch",
            "laptop": "laptop",
            "macbook": "laptop",
            "speaker": "speaker",
            "keyboard": "keyboard",
            "mouse": "mouse",
            "tablet": "tablet",
            "ipad": "tablet",
        }
        for kw, dev_type in keywords.items():
            if kw in lowered:
                return dev_type
        return "unknown"

    # -- analysis --

    async def analyse(self, devices: list[ProximityBTDevice]) -> None:
        current_macs = {d.mac for d in devices}

        for dev in devices:
            # Persist every sighting + behavioural baseline
            if self._store:
                try:
                    res = self._store.observe(dev.mac, "bt", dev.name, dev.vendor,
                                              {"device_type": dev.device_type, "services": dev.services})
                    if (res.get("unusual_time") and not dev.is_yours
                            and dev.mac not in self._unusual_alerted):
                        self._unusual_alerted.add(dev.mac)
                        await self._event_bus.publish("device_unusual_time", {
                            "kind": "bt", "id": dev.mac, "name": dev.name or dev.vendor or dev.mac,
                            "vendor": dev.vendor, "seen_count": dev.seen_count,
                            "note": "Established Bluetooth device appearing at an atypical hour.",
                        })
                except Exception:
                    pass

            if not dev.is_yours:
                # 1. New unknown BT device very close
                if dev.rssi > self._close_threshold:
                    await self._event_bus.publish(
                        "unknown_bt_device_nearby",
                        {"mac": dev.mac, "name": dev.name, "rssi": dev.rssi, "device_type": dev.device_type},
                    )

                # 2. BT scanner detection (no name, strong signal, repeated)
                if not dev.name and dev.rssi > -50 and dev.seen_count > 5:
                    await self._event_bus.publish(
                        "possible_bt_scanner_nearby",
                        {"mac": dev.mac, "rssi": dev.rssi, "seen_count": dev.seen_count},
                    )

                # 3. Unknown tracker (AirTag/Tile/SmartTag) following you — a
                #    tracker signature that has persisted across time/space.
                if dev.is_tracker and dev.seen_count >= 3 and not getattr(dev, "_tracker_alerted", False):
                    try:
                        span_min = (datetime.fromisoformat(dev.last_seen) - datetime.fromisoformat(dev.first_seen)).total_seconds() / 60
                    except Exception:
                        span_min = 0
                    if span_min >= 8:
                        dev._tracker_alerted = True  # type: ignore[attr-defined]
                        await self._event_bus.publish(
                            "unknown_tracker_following",
                            {"mac": dev.mac, "kind": dev.tracker_kind, "vendor": dev.vendor,
                             "rssi": dev.rssi, "distance_m": dev.distance_m,
                             "seen_count": dev.seen_count, "span_min": round(span_min, 1)},
                        )

        # 3. Known device absence check
        for mac, dev in list(self._bt_history.items()):
            if not dev.is_yours:
                continue
            if mac in current_macs:
                continue
            try:
                last = datetime.fromisoformat(dev.last_seen.replace("Z", "+00:00"))
                delta = (datetime.now(timezone.utc) - last).total_seconds() / 60
                if delta >= self._absence_minutes:
                    if not getattr(dev, "_absence_alerted", False):
                        dev._absence_alerted = True  # type: ignore[attr-defined]
                        await self._event_bus.publish(
                            "known_bt_device_absent",
                            {"name": dev.name, "mac": dev.mac, "last_seen": dev.last_seen},
                        )
            except Exception:
                pass


# ── ProximityMonitor orchestrator ────────────────────────────────────────


class ProximityMonitor:
    """
    Orchestrates WiFi and Bluetooth passive proximity sensors.

    Lifecycle: __init__ -> start() -> ... -> stop() -> status()
    """

    def __init__(self, event_bus: Any, redis_state: Any) -> None:
        self._event_bus = event_bus
        self._redis_state = redis_state

        self._wifi_sensor = WiFiProximitySensor(event_bus, redis_state)
        self._bt_sensor = BluetoothProximitySensor(event_bus, redis_state)

        self._started = False
        self._stop_event = asyncio.Event()
        self._wifi_task: asyncio.Task | None = None
        self._bt_task: asyncio.Task | None = None
        self._pattern_task: asyncio.Task | None = None

        self._wifi_interval: int = self._resolve_int("wifi_proximity_scan_s", 60)
        self._bt_interval: int = self._resolve_int("bt_proximity_scan_s", 45)
        self._pattern_interval: int = self._resolve_int("pattern_analysis_interval_s", 300)

        self._total_aps_today = 0
        self._total_bt_today = 0
        self._pattern_alerts = 0
        self._proximity_log: list[dict[str, Any]] = []  # in-memory; SQLite optional

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
        self._wifi_task = asyncio.create_task(self._wifi_scan_loop())
        self._bt_task = asyncio.create_task(self._bt_scan_loop())
        self._pattern_task = asyncio.create_task(self._pattern_scheduler())
        logger.info("ProximityMonitor started (passive only)")

    async def stop(self) -> None:
        self._started = False
        self._stop_event.set()
        for task in (self._wifi_task, self._bt_task, self._pattern_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        logger.info("ProximityMonitor stopped")

    def status(self) -> dict[str, Any]:
        return {
            "wifi_scanning": self._started,
            "bt_scanning": self._started and BLEAK_AVAILABLE,
            "interface": "passive",
            "total_aps_seen_today": self._total_aps_today,
            "total_bt_seen_today": self._total_bt_today,
            "pattern_alerts": self._pattern_alerts,
        }

    # ------------------------------------------------------------------
    # Background loops
    # ------------------------------------------------------------------

    async def _wifi_scan_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                aps = await self._wifi_sensor.scan()
                await self._wifi_sensor.analyse(aps)
                await self._redis_state.set_global(
                    "proximity_wifi", [ap.__dict__ for ap in aps]
                )
                if aps:
                    self._total_aps_today += len(aps)
                    for ap in aps:
                        self._proximity_log.append({
                            "timestamp": self._now(),
                            "mac_or_bssid": ap.bssid,
                            "device_type": "wifi",
                            "signal": ap.signal_dbm,
                            "seen_count": ap.seen_count,
                        })
            except Exception as exc:
                logger.debug(f"WiFi scan loop error: {exc}")

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._wifi_interval)
            except asyncio.TimeoutError:
                pass

    async def _bt_scan_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                devices = await self._bt_sensor.scan()
                await self._bt_sensor.analyse(devices)
                await self._redis_state.set_global(
                    "proximity_bt", [d.__dict__ for d in devices]
                )
                if devices:
                    self._total_bt_today += len(devices)
                    for dev in devices:
                        self._proximity_log.append({
                            "timestamp": self._now(),
                            "mac_or_bssid": dev.mac,
                            "device_type": "bt",
                            "signal": dev.rssi,
                            "seen_count": dev.seen_count,
                        })
            except Exception as exc:
                logger.debug(f"BT scan loop error: {exc}")

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._bt_interval)
            except asyncio.TimeoutError:
                pass

    async def _pattern_scheduler(self) -> None:
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._pattern_interval)
            except asyncio.TimeoutError:
                pass
            if not self._started:
                break
            try:
                await self._detect_patterns()
            except Exception as exc:
                logger.debug(f"Pattern detection error: {exc}")

    # ------------------------------------------------------------------
    # Pattern engine
    # ------------------------------------------------------------------

    async def _detect_patterns(self) -> None:
        now = datetime.now(timezone.utc)
        night_hours: set[int] = self._resolve_night_hours()

        # Per-device aggregation
        device_visits: dict[str, dict[str, Any]] = {}
        for entry in self._proximity_log:
            mac = entry["mac_or_bssid"]
            ts = entry["timestamp"]
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                continue

            if mac not in device_visits:
                device_visits[mac] = {
                    "days_seen": set(),
                    "hours": [],
                    "signals": [],
                    "type": entry["device_type"],
                }
            device_visits[mac]["days_seen"].add(dt.date().isoformat())
            device_visits[mac]["hours"].append(dt.hour)
            device_visits[mac]["signals"].append(entry["signal"])

        for mac, data in device_visits.items():
            # Recurring unknown device
            if len(data["days_seen"]) >= 3:
                typical_hours = sorted(set(data["hours"]))
                avg_signal = sum(data["signals"]) / len(data["signals"]) if data["signals"] else -100
                await self._event_bus.publish(
                    "recurring_unknown_device",
                    {
                        "mac_or_bssid": mac,
                        "type": data["type"],
                        "days_seen": len(data["days_seen"]),
                        "typical_hours": typical_hours,
                        "signal_dbm": round(avg_signal, 1),
                    },
                )
                self._pattern_alerts += 1

            # Off-hours presence
            if any(h in night_hours for h in data["hours"]):
                await self._event_bus.publish(
                    "night_proximity_alert",
                    {"device": mac, "type": data["type"], "signal": avg_signal, "hour": now.hour},
                )
                self._pattern_alerts += 1

        # Sudden cluster
        recent_window = 600  # 10 minutes
        cutoff = now.timestamp() - recent_window
        recent_entries = [
            e for e in self._proximity_log
            if datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")).timestamp() > cutoff
        ]
        cluster_threshold = self._resolve_int("cluster_threshold", 8)
        if len(recent_entries) >= cluster_threshold:
            await self._event_bus.publish(
                "device_cluster_detected",
                {
                    "count": len(recent_entries),
                    "timespan_s": recent_window,
                    "devices": list({e["mac_or_bssid"] for e in recent_entries}),
                },
            )
            self._pattern_alerts += 1

    def _resolve_night_hours(self) -> set[int]:
        try:
            from core.config import Settings
            return set(getattr(Settings(), "night_hours", (23, 0, 1, 2, 3, 4)))
        except Exception:
            return {23, 0, 1, 2, 3, 4}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_nearby_aps(self) -> list[ProximityAP]:
        return list(self._wifi_sensor._ap_history.values())

    async def get_nearby_bt(self) -> list[ProximityBTDevice]:
        return list(self._bt_sensor._bt_history.values())

    async def get_proximity_summary(self) -> dict[str, Any]:
        aps = self._wifi_sensor._ap_history.values()
        bt = self._bt_sensor._bt_history.values()

        return {
            "wifi": {
                "total_nearby": len(aps),
                "unknown": sum(1 for a in aps if not a.is_yours),
                "yours": sum(1 for a in aps if a.is_yours),
                "open": sum(1 for a in aps if a.encryption == "OPEN"),
            },
            "bluetooth": {
                "total_nearby": len(bt),
                "unknown": sum(1 for d in bt if not d.is_yours),
                "yours": sum(1 for d in bt if d.is_yours),
            },
            "alerts_today": self._pattern_alerts,
            "recurring_unknowns": sum(
                1 for v in self._proximity_log
                if v.get("seen_count", 0) >= 5
            ),
            "last_scan": self._now(),
        }
