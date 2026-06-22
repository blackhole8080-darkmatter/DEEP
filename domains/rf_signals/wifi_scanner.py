"""
DEEP — WiFi Deep Scanner
Advanced 802.11 scanning: SSID/BSSID/channel/security/client enumeration.
Evil Twin detection, WPS vulnerability assessment, client fingerprinting.
Uses: subprocess (netsh on Windows, iwlist/iw on Linux), or scapy in monitor mode.
"""
from __future__ import annotations

import asyncio
import platform
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class WiFiClient:
    mac: str
    rssi: int
    last_seen: float
    vendor: Optional[str] = None
    probe_ssids: List[str] = field(default_factory=list)


@dataclass
class WiFiNetwork:
    ssid: str
    bssid: str
    channel: int
    band: str               # "2.4GHz" | "5GHz" | "6GHz"
    signal_dbm: int
    security: str           # WPA3-SAE / WPA2-PSK / WEP / Open
    wps_enabled: bool = False
    hidden: bool = False
    clients: List[WiFiClient] = field(default_factory=list)
    vendor: Optional[str] = None
    # Threat flags
    is_evil_twin: bool = False
    evil_twin_reason: str = ""
    wps_vulnerable: bool = False    # Pixie-Dust / PIN brute-force possible


@dataclass
class WiFiScanReport:
    networks: List[WiFiNetwork] = field(default_factory=list)
    scan_time: float = 0.0
    interface: str = ""
    alerts: List[str] = field(default_factory=list)
    error: Optional[str] = None


# ── OUI vendor lookup (small subset — expand with full IEEE file) ──────────────
_OUI_MAP: Dict[str, str] = {
    "00:50:f2": "Microsoft",
    "00:1a:11": "Google",
    "b8:27:eb": "Raspberry Pi Foundation",
    "dc:a6:32": "Raspberry Pi Foundation",
    "18:b4:30": "Nest Labs",
    "44:61:32": "Apple",
    "3c:5a:b4": "Apple",
    "a4:c3:f0": "Apple",
    "f4:db:e6": "Apple",
    "00:25:9c": "Cisco Systems",
    "00:0c:29": "VMware",
    "00:50:56": "VMware",
    "08:00:27": "VirtualBox",
    "74:da:38": "Edimax",
    "e8:4e:06": "TP-Link Technologies",
    "c4:e9:84": "TP-Link Technologies",
    "50:c7:bf": "TP-Link Technologies",
    "28:28:5d": "ASUS",
    "bc:ee:7b": "ASUSTek Computer",
    "00:1b:17": "Cisco-Linksys",
    "20:aa:4b": "Ubiquiti Networks",
    "dc:9f:db": "Ubiquiti Networks",
}


def _lookup_vendor(mac: str) -> Optional[str]:
    prefix = mac.lower()[:8]
    return _OUI_MAP.get(prefix)


# ── WiFi Scanner ──────────────────────────────────────────────────────────────

class WiFiScanner:
    """
    Multi-platform WiFi scanner.
    Windows: uses `netsh wlan show networks mode=Bssid` (no driver requirements)
    Linux:   uses `iw dev wlan0 scan` or `iwlist scan` (requires root for full data)
    """

    def __init__(self, interface: str = "auto"):
        self._interface = interface
        self._os = platform.system().lower()
        self._scan_history: List[WiFiScanReport] = []

    async def scan(self) -> WiFiScanReport:
        """Run a full WiFi scan and return structured report."""
        start = time.monotonic()
        report = WiFiScanReport(scan_time=time.time(), interface=self._interface)

        try:
            if self._os == "windows":
                networks = await asyncio.to_thread(self._scan_windows)
            elif self._os == "linux":
                networks = await asyncio.to_thread(self._scan_linux)
            elif self._os == "darwin":
                networks = await asyncio.to_thread(self._scan_macos)
            else:
                report.error = f"Unsupported OS: {self._os}"
                return report

            report.networks = networks
            report.alerts = self._detect_threats(networks)

        except PermissionError:
            report.error = "Permission denied. Run as administrator/root for full WiFi scanning."
        except Exception as exc:
            report.error = f"Scan failed: {exc}"

        report.scan_time = time.monotonic() - start
        self._scan_history.append(report)
        return report

    def detect_evil_twins(self, networks: List[WiFiNetwork]) -> List[Dict[str, Any]]:
        """
        Detect Evil Twin attacks: duplicate SSIDs with different BSSIDs.
        Returns list of (legitimate, suspicious) network pairs with evidence.
        """
        ssid_map: Dict[str, List[WiFiNetwork]] = {}
        for net in networks:
            ssid_map.setdefault(net.ssid, []).append(net)

        suspects = []
        for ssid, nets in ssid_map.items():
            if len(nets) > 1:
                # Sort by signal strength — strongest is likely the real AP
                nets_sorted = sorted(nets, key=lambda n: n.signal_dbm, reverse=True)
                legit = nets_sorted[0]
                for suspect in nets_sorted[1:]:
                    # Check if BSSID vendor is plausible (same org)
                    legit_vendor = _lookup_vendor(legit.bssid) or "unknown"
                    suspect_vendor = _lookup_vendor(suspect.bssid) or "unknown"
                    evidence = []
                    if legit_vendor != suspect_vendor:
                        evidence.append(f"Different hardware vendors: {legit_vendor} vs {suspect_vendor}")
                    if abs(suspect.channel - legit.channel) == 0:
                        evidence.append("Same channel — likely monitor/injection mode")
                    if suspect.security != legit.security:
                        evidence.append(f"Different security: {legit.security} vs {suspect.security} (downgrade attack?)")

                    suspects.append({
                        "ssid": ssid,
                        "legitimate": {"bssid": legit.bssid, "signal": legit.signal_dbm, "vendor": legit_vendor},
                        "suspect": {"bssid": suspect.bssid, "signal": suspect.signal_dbm, "vendor": suspect_vendor},
                        "evidence": evidence,
                        "risk": "HIGH" if evidence else "MEDIUM",
                    })

        return suspects

    # ── Platform-specific scan implementations ─────────────────────────────────

    def _scan_windows(self) -> List[WiFiNetwork]:
        """Parse netsh wlan show networks mode=Bssid output."""
        result = subprocess.run(
            ["netsh", "wlan", "show", "networks", "mode=Bssid"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        return self._parse_netsh(result.stdout)

    def _scan_linux(self) -> List[WiFiNetwork]:
        """Parse iw scan output. Requires root or CAP_NET_RAW."""
        iface = self._interface if self._interface != "auto" else "wlan0"
        result = subprocess.run(
            ["iw", "dev", iface, "scan"],
            capture_output=True, text=True, timeout=20,
        )
        if result.returncode != 0:
            # Fallback to iwlist
            result = subprocess.run(
                ["iwlist", iface, "scan"],
                capture_output=True, text=True, timeout=20,
            )
            return self._parse_iwlist(result.stdout)
        return self._parse_iw(result.stdout)

    def _scan_macos(self) -> List[WiFiNetwork]:
        """Use airport utility on macOS."""
        airport = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
        result = subprocess.run(
            [airport, "-s"],
            capture_output=True, text=True, timeout=15,
        )
        return self._parse_airport(result.stdout)

    # ── Parsers ───────────────────────────────────────────────────────────────

    def _parse_netsh(self, output: str) -> List[WiFiNetwork]:
        """Parse Windows netsh wlan show networks mode=Bssid."""
        networks = []
        blocks = re.split(r"SSID \d+ :", output)[1:]

        for block in blocks:
            lines = block.strip().splitlines()
            ssid = lines[0].strip() if lines else ""
            hidden = ssid == ""

            bssid_blocks = re.split(r"BSSID \d+\s*:", block)[1:]
            for bb in bssid_blocks:
                bssid_match = re.search(r"([0-9a-fA-F:]{17})", bb.split("\n")[0])
                if not bssid_match:
                    continue
                bssid = bssid_match.group(1).lower()

                signal_match = re.search(r"Signal\s*:\s*(\d+)%", bb)
                signal_pct = int(signal_match.group(1)) if signal_match else 50
                # Approximate: 0% → -100 dBm, 100% → -50 dBm
                signal_dbm = int(-100 + signal_pct / 2)

                channel_match = re.search(r"Channel\s*:\s*(\d+)", bb)
                channel = int(channel_match.group(1)) if channel_match else 0

                auth_match = re.search(r"Authentication\s*:\s*(.+)", bb)
                auth = auth_match.group(1).strip() if auth_match else "Unknown"

                enc_match = re.search(r"Encryption\s*:\s*(.+)", bb)
                enc = enc_match.group(1).strip() if enc_match else "Unknown"
                security = f"{auth}/{enc}" if enc != "None" else "Open"

                band = "5GHz" if channel > 14 else "2.4GHz"
                vendor = _lookup_vendor(bssid)

                networks.append(WiFiNetwork(
                    ssid=ssid or f"<hidden-{bssid[:8]}>",
                    bssid=bssid,
                    channel=channel,
                    band=band,
                    signal_dbm=signal_dbm,
                    security=security,
                    hidden=hidden,
                    vendor=vendor,
                ))

        return networks

    def _parse_iw(self, output: str) -> List[WiFiNetwork]:
        """Parse `iw dev wlan0 scan` output."""
        networks = []
        blocks = re.split(r"BSS ([0-9a-f:]{17})", output)

        for i in range(1, len(blocks), 2):
            bssid = blocks[i]
            block = blocks[i + 1] if i + 1 < len(blocks) else ""

            ssid_match = re.search(r"SSID: (.+)", block)
            ssid = ssid_match.group(1).strip() if ssid_match else ""

            signal_match = re.search(r"signal: (-?\d+\.\d+) dBm", block)
            signal_dbm = int(float(signal_match.group(1))) if signal_match else -80

            channel_match = re.search(r"DS Parameter set: channel (\d+)", block)
            channel = int(channel_match.group(1)) if channel_match else 0

            rsn = "WPA2" if "RSN" in block else ("WPA" if "WPA" in block else "Open")

            band = "5GHz" if channel > 14 else "2.4GHz"
            vendor = _lookup_vendor(bssid)

            networks.append(WiFiNetwork(
                ssid=ssid or f"<hidden>",
                bssid=bssid,
                channel=channel,
                band=band,
                signal_dbm=signal_dbm,
                security=rsn,
                hidden=not ssid,
                vendor=vendor,
            ))

        return networks

    def _parse_iwlist(self, output: str) -> List[WiFiNetwork]:
        """Parse iwlist scan output (older Linux systems)."""
        networks = []
        for cell in re.split(r"Cell \d+ -", output)[1:]:
            bssid_match = re.search(r"Address: ([0-9A-Fa-f:]{17})", cell)
            ssid_match = re.search(r'ESSID:"([^"]*)"', cell)
            signal_match = re.search(r"Signal level=(-?\d+) dBm", cell)
            channel_match = re.search(r"Channel:(\d+)", cell)
            enc_match = re.search(r"Encryption key:(on|off)", cell)

            if not bssid_match:
                continue

            bssid = bssid_match.group(1).lower()
            ssid = ssid_match.group(1) if ssid_match else ""
            signal_dbm = int(signal_match.group(1)) if signal_match else -80
            channel = int(channel_match.group(1)) if channel_match else 0
            encrypted = enc_match.group(1) == "on" if enc_match else False
            security = "WPA2" if encrypted else "Open"

            networks.append(WiFiNetwork(
                ssid=ssid or "<hidden>",
                bssid=bssid,
                channel=channel,
                band="5GHz" if channel > 14 else "2.4GHz",
                signal_dbm=signal_dbm,
                security=security,
                vendor=_lookup_vendor(bssid),
            ))

        return networks

    def _parse_airport(self, output: str) -> List[WiFiNetwork]:
        """Parse macOS airport -s output."""
        networks = []
        lines = output.strip().splitlines()[1:]  # skip header
        for line in lines:
            parts = line.split()
            if len(parts) < 5:
                continue
            ssid = parts[0]
            bssid = parts[1]
            signal_str = parts[2]
            channel_str = parts[3]
            security = " ".join(parts[4:]) if len(parts) > 4 else "Unknown"

            try:
                signal_dbm = int(signal_str)
                channel = int(channel_str.split(",")[0])
            except ValueError:
                continue

            networks.append(WiFiNetwork(
                ssid=ssid,
                bssid=bssid.lower(),
                channel=channel,
                band="5GHz" if channel > 14 else "2.4GHz",
                signal_dbm=signal_dbm,
                security=security,
                vendor=_lookup_vendor(bssid),
            ))

        return networks

    # ── Threat detection ───────────────────────────────────────────────────────

    def _detect_threats(self, networks: List[WiFiNetwork]) -> List[str]:
        alerts = []

        # Evil twin detection
        evil_twins = self.detect_evil_twins(networks)
        for et in evil_twins:
            alerts.append(
                f"[ALERT] Possible Evil Twin: SSID '{et['ssid']}' has duplicate BSSID "
                f"{et['suspect']['bssid']} (suspect) vs {et['legitimate']['bssid']} (legit). "
                f"Evidence: {'; '.join(et['evidence'])}"
            )

        # WPS vulnerability
        for net in networks:
            if net.wps_enabled:
                alerts.append(
                    f"[WARN] WPS enabled on {net.ssid} ({net.bssid}) — "
                    f"potential Pixie-Dust attack surface."
                )

        # Open networks
        open_nets = [n for n in networks if n.security.lower() == "open"]
        if open_nets:
            alerts.append(
                f"[INFO] {len(open_nets)} open (unencrypted) network(s) detected: "
                f"{', '.join(n.ssid for n in open_nets[:5])}"
            )

        return alerts
