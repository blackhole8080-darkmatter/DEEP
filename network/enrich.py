"""
network/enrich.py — sensing enrichment helpers.

Turns raw radio observations into *understanding*: BLE company-ID → vendor,
service-UUID → device class, RSSI → distance, tracker (AirTag/Tile/SmartTag)
signatures, and MAC/BSSID OUI → vendor. Pure functions, offline-friendly.
"""
from __future__ import annotations

from typing import Iterable

# ── Bluetooth SIG company identifiers (common subset) ────────────────────
BLE_COMPANY_IDS: dict[int, str] = {
    0x0006: "Microsoft", 0x004C: "Apple", 0x0075: "Samsung", 0x00E0: "Google",
    0x0059: "Nordic", 0x012D: "Sony", 0x009E: "Bose", 0x0087: "Garmin",
    0x0157: "Amazfit/Huami", 0x038F: "Xiaomi", 0x00C4: "Fitbit", 0x0171: "Amazon",
    0x0131: "Cypress", 0x0499: "Ruuvi", 0x0001: "Ericsson", 0x000F: "Broadcom",
    0x0118: "Tile", 0x05A7: "Sonos", 0x0085: "BlueRadios", 0x004F: "APT/Qualcomm",
}

# ── 16-bit service UUID → human class ────────────────────────────────────
BLE_SERVICE_NAMES: dict[int, str] = {
    0x180D: "Heart Rate", 0x180F: "Battery", 0x1812: "HID (keyboard/mouse)",
    0x110B: "Audio Sink", 0x111E: "Handsfree", 0x180A: "Device Info",
    0x1809: "Thermometer", 0x1816: "Cycling", 0x1818: "Cycling Power",
    0xFEAA: "Eddystone Beacon", 0xFE9F: "Google", 0xFD5A: "Samsung SmartThings",
    0xFEED: "Tile Tracker", 0xFEEC: "Tile Tracker", 0xFD6F: "Exposure Notify",
    0xFE2C: "Google Fast Pair", 0xFDF3: "Amazon", 0xFE07: "Sonos",
}

# Tracker signatures (potential location trackers worth flagging).
_TRACKER_SERVICES = {0xFEED, 0xFEEC, 0xFD5A}      # Tile, Samsung SmartTag
_TRACKER_COMPANIES = {0x0118}                      # Tile


def ble_vendor(manufacturer_data: dict | None) -> tuple[str | None, int | None]:
    """Return (vendor_name, company_id) from BLE manufacturer_data dict."""
    if not manufacturer_data:
        return None, None
    cid = next(iter(manufacturer_data.keys()), None)
    if cid is None:
        return None, None
    return BLE_COMPANY_IDS.get(cid, f"0x{cid:04X}"), cid


def _u16_from_uuid(uuid: str) -> int | None:
    # 128-bit UUIDs of the form 0000XXXX-0000-1000-8000-00805f9b34fb carry a 16-bit id
    try:
        s = str(uuid).lower()
        if len(s) >= 8 and s[8:] == "-0000-1000-8000-00805f9b34fb":
            return int(s[4:8], 16)
        if len(s) == 4:
            return int(s, 16)
    except Exception:
        return None
    return None


def ble_services(service_uuids: Iterable[str] | None) -> list[str]:
    names: list[str] = []
    for u in (service_uuids or []):
        u16 = _u16_from_uuid(u)
        if u16 is not None and u16 in BLE_SERVICE_NAMES:
            names.append(BLE_SERVICE_NAMES[u16])
    return names


def is_tracker(manufacturer_data: dict | None, service_uuids: Iterable[str] | None) -> tuple[bool, str | None]:
    """Detect potential location trackers. Returns (is_tracker, kind)."""
    # Apple Find My / AirTag: Apple company (0x004C) with payload type 0x12.
    if manufacturer_data:
        apple = manufacturer_data.get(0x004C)
        if apple and len(apple) >= 1 and apple[0] == 0x12:
            return True, "Apple Find My / AirTag"
        for cid in manufacturer_data.keys():
            if cid in _TRACKER_COMPANIES:
                return True, BLE_COMPANY_IDS.get(cid, "tracker")
    for u in (service_uuids or []):
        u16 = _u16_from_uuid(u)
        if u16 in _TRACKER_SERVICES:
            return True, BLE_SERVICE_NAMES.get(u16, "tracker")
    return False, None


def rssi_distance(rssi: int | None, tx_power: int | None = None) -> float | None:
    """Rough free-space distance estimate in metres from RSSI."""
    if rssi is None or rssi == 0:
        return None
    measured = tx_power if (tx_power is not None and tx_power != 0) else -59  # power at 1 m
    n = 2.0  # path-loss exponent (open indoor)
    try:
        return round(10 ** ((measured - rssi) / (10 * n)), 1)
    except Exception:
        return None


def wifi_band(channel: int) -> str:
    if not channel:
        return "?"
    if channel <= 14:
        return "2.4 GHz"
    if channel <= 196:
        return "5 GHz"
    return "6 GHz"


# ── OUI vendor (MAC / BSSID) ─────────────────────────────────────────────
_OUI_FALLBACK = {
    "FC:FB:FB": "Cisco", "00:1A:11": "Google", "3C:5A:B4": "Google",
    "B8:27:EB": "Raspberry Pi", "DC:A6:32": "Raspberry Pi", "00:0D:3A": "Microsoft",
    "F0:18:98": "Apple", "A4:83:E7": "Apple", "AC:DE:48": "Apple",
    "00:50:F2": "Microsoft", "C4:9A:31": "TP-Link", "50:C7:BF": "TP-Link",
    "B0:BE:76": "TP-Link", "E4:5F:01": "Raspberry Pi", "D8:0D:17": "TP-Link",
}
_mac_lookup = None
_vendor_cache: dict[str, str] = {}


def mac_vendor(mac: str | None) -> str | None:
    """OUI → vendor, via mac_vendor_lookup if present, else a small fallback map."""
    if not mac or len(mac) < 8:
        return None
    key = mac.upper()[:8]
    if key in _vendor_cache:
        return _vendor_cache[key] or None
    # Locally-administered / randomized MACs (2nd nibble 2,6,A,E) never resolve —
    # cache that fact so we don't retry them every scan.
    try:
        if int(mac.replace(":", "").replace("-", "")[1], 16) & 0x2:
            _vendor_cache[key] = ""
            return None
    except Exception:
        pass

    global _mac_lookup
    vendor = None
    try:
        if _mac_lookup is None:
            from mac_vendor_lookup import MacLookup
            _mac_lookup = MacLookup()
        # MacLookup.lookup() internally drives an event loop; calling it from
        # within the server's running loop leaks an un-awaited coroutine and
        # fails. Run it in a worker thread (no running loop there) so the sync
        # wrapper works correctly and the warning disappears.
        import concurrent.futures as _cf
        with _cf.ThreadPoolExecutor(max_workers=1) as _ex:
            vendor = _ex.submit(_mac_lookup.lookup, mac).result(timeout=5)
    except Exception:
        vendor = _OUI_FALLBACK.get(key)
    # Only cache successful lookups; transient failures (e.g. OUI DB still
    # downloading) should be retried on the next scan rather than cached as None.
    if vendor:
        _vendor_cache[key] = vendor
    return vendor
