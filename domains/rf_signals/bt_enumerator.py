"""
DEEP — Bluetooth/BLE Enumerator
Device discovery, RSSI distance estimation, GATT service parsing.
Uses: bleak (BLE), pybluez (classic BT), or OS CLI tools as fallback.
"""
from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import bleak
    from bleak import BleakScanner, BleakClient
    from bleak.backends.device import BLEDevice
    _BLEAK_OK = True
except ImportError:
    _BLEAK_OK = False

# ── Data models ───────────────────────────────────────────────────────────────

# Bluetooth Class of Device → human-readable description (partial)
_COD_MAP: Dict[int, str] = {
    0x000100: "Computer",
    0x000200: "Phone",
    0x000300: "LAN/Network Access Point",
    0x000400: "Audio/Video (headset/speaker/camera)",
    0x000500: "Peripheral (mouse/keyboard/joystick)",
    0x000600: "Imaging (printer/scanner/camera/display)",
    0x000700: "Wearable",
    0x000800: "Toy",
    0x000900: "Health Device",
    0x001f00: "Uncategorized",
}

# Company ID → vendor name (partial BT SIG assigned numbers)
_COMPANY_IDS: Dict[int, str] = {
    0x0006: "Microsoft",
    0x004C: "Apple Inc.",
    0x0075: "Samsung Electronics",
    0x00E0: "Google",
    0x0499: "Ruuvi Innovations",
    0x0157: "Bose",
    0x0171: "Dell Computer",
    0x0059: "Nordic Semiconductor",
    0x000F: "Texas Instruments",
    0x0046: "Garmin International",
    0x00D7: "Fitbit",
    0x0087: "Polar Electro",
}


@dataclass
class GATTService:
    uuid: str
    name: str
    characteristics: List[str] = field(default_factory=list)


@dataclass
class BTDevice:
    address: str            # MAC address or UUID (macOS)
    name: Optional[str]
    rssi: int               # dBm
    device_type: str        # "BLE" | "Classic" | "Dual"
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    class_of_device: Optional[int] = None
    class_description: Optional[str] = None
    services: List[GATTService] = field(default_factory=list)
    manufacturer_data: Dict[int, bytes] = field(default_factory=dict)
    service_uuids: List[str] = field(default_factory=list)
    estimated_distance_m: Optional[float] = None
    address_type: str = "public"    # "public" | "random"
    is_suspicious: bool = False
    suspicion_reason: str = ""
    last_seen: float = field(default_factory=time.time)


@dataclass
class BTScanReport:
    devices: List[BTDevice] = field(default_factory=list)
    scan_duration: float = 0.0
    alerts: List[str] = field(default_factory=list)
    error: Optional[str] = None


# ── BLE enumerator ────────────────────────────────────────────────────────────

class BTEnumerator:
    """
    Bluetooth & BLE device enumerator.
    Uses `bleak` for BLE (cross-platform).
    Classic BT: subprocess fallback (btmgmt/hcitool on Linux, PowerShell on Windows).
    """

    # RSSI reference power at 1 meter (calibrate per hardware)
    _RSSI_1M = -65.0
    # Path loss exponent (2.0 = free space; 2.5-3.5 indoors)
    _N = 2.5

    def __init__(self, scan_duration: float = 10.0):
        self._scan_duration = scan_duration

    # ── Public API ─────────────────────────────────────────────────────────────

    async def scan_ble(self) -> BTScanReport:
        """
        BLE active scan using bleak.
        Returns all advertising devices with parsed manufacturer data.
        """
        report = BTScanReport()

        if not _BLEAK_OK:
            report.error = (
                "bleak not installed. Run: pip install bleak\n"
                "BLE scanning requires bleak for cross-platform support."
            )
            return report

        start = time.monotonic()
        try:
            discovered: Dict[str, Any] = {}

            def detection_callback(device: "BLEDevice", adv_data: Any) -> None:
                discovered[device.address] = (device, adv_data)

            async with BleakScanner(detection_callback=detection_callback) as scanner:
                await asyncio.sleep(self._scan_duration)

            for addr, (dev, adv) in discovered.items():
                bt_dev = self._parse_ble_device(dev, adv)
                report.devices.append(bt_dev)

        except Exception as exc:
            report.error = f"BLE scan failed: {exc}"

        report.scan_duration = time.monotonic() - start
        report.alerts = self._generate_alerts(report.devices)
        return report

    async def enumerate_services(self, address: str) -> List[GATTService]:
        """
        Connect to a BLE device and enumerate GATT services/characteristics.
        Only use on devices you own or have authorization to test.
        """
        if not _BLEAK_OK:
            return []

        services = []
        try:
            async with BleakClient(address) as client:
                for service in client.services:
                    gatt = GATTService(
                        uuid=str(service.uuid),
                        name=service.description or "Unknown",
                        characteristics=[
                            f"{c.uuid} ({c.description}) [{','.join(str(p) for p in c.properties)}]"
                            for c in service.characteristics
                        ],
                    )
                    services.append(gatt)
        except Exception as exc:
            services.append(GATTService(
                uuid="error",
                name=f"Connection failed: {exc}",
            ))

        return services

    # ── Device parsing ────────────────────────────────────────────────────────

    def _parse_ble_device(self, dev: Any, adv: Any) -> BTDevice:
        rssi = getattr(adv, "rssi", -90)
        dist = self._estimate_distance(rssi)

        # Manufacturer data
        mfr_data: Dict[int, bytes] = {}
        company_id = None
        company_name = None
        if hasattr(adv, "manufacturer_data"):
            mfr_data = dict(adv.manufacturer_data)
            if mfr_data:
                company_id = next(iter(mfr_data))
                company_name = _COMPANY_IDS.get(company_id, f"0x{company_id:04X}")

        # Service UUIDs
        service_uuids = []
        if hasattr(adv, "service_uuids"):
            service_uuids = [str(u) for u in adv.service_uuids]

        # Address type
        addr_type = "public"
        if hasattr(dev, "address_type"):
            addr_type = str(dev.address_type).lower()
        elif ":" not in dev.address:  # macOS uses UUID-style addresses
            addr_type = "random"

        device = BTDevice(
            address=dev.address,
            name=dev.name,
            rssi=rssi,
            device_type="BLE",
            company_id=company_id,
            company_name=company_name,
            manufacturer_data=mfr_data,
            service_uuids=service_uuids,
            estimated_distance_m=dist,
            address_type=addr_type,
        )

        # Threat assessment
        self._assess_device(device)
        return device

    def _estimate_distance(self, rssi: int) -> float:
        """RSSI-based distance estimate using log-distance path loss model."""
        if rssi >= 0:
            return 0.0
        try:
            exponent = (self._RSSI_1M - rssi) / (10 * self._N)
            return round(10 ** exponent, 2)
        except Exception:
            return -1.0

    def _assess_device(self, device: BTDevice) -> None:
        """Flag potentially suspicious BLE devices."""
        reasons = []

        # Unknown company in manufacturer data
        if device.company_id is not None and device.company_id not in _COMPANY_IDS:
            reasons.append(f"Unknown company ID: 0x{device.company_id:04X}")

        # Random-rotating address (privacy, but also used by tracking devices)
        if device.address_type == "random" and not device.name:
            reasons.append("Random address + no name (could be tracking beacon)")

        # Very strong signal from unknown device
        if device.rssi > -40 and not device.name:
            reasons.append(f"Strong signal ({device.rssi} dBm) from unnamed device — possibly nearby hidden tracker")

        if reasons:
            device.is_suspicious = True
            device.suspicion_reason = "; ".join(reasons)

    def _generate_alerts(self, devices: List[BTDevice]) -> List[str]:
        alerts = []
        suspicious = [d for d in devices if d.is_suspicious]
        if suspicious:
            for d in suspicious:
                alerts.append(
                    f"[BT ALERT] Suspicious device: {d.address} "
                    f"(dist: ~{d.estimated_distance_m}m) — {d.suspicion_reason}"
                )

        # Check for Apple AirTag / Tile tracker signatures
        for d in devices:
            if d.company_id == 0x004C:  # Apple
                mfr_bytes = d.manufacturer_data.get(0x004C, b"")
                if len(mfr_bytes) >= 2 and mfr_bytes[0] == 0x12:
                    alerts.append(
                        f"[BT ALERT] Possible Apple AirTag detected near you: {d.address} "
                        f"(dist: ~{d.estimated_distance_m}m). Verify this is yours."
                    )

        return alerts
