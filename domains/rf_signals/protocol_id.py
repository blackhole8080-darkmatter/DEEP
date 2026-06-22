"""
DEEP — RF Protocol Identifier
Identifies radio protocols from signal characteristics (bandwidth, duty cycle, modulation).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ProtocolMatch:
    protocol_name: str
    confidence: float               # 0.0 – 1.0
    frequency_range: str
    modulation: str
    typical_use: str
    standards: List[str] = field(default_factory=list)
    security_notes: str = ""


# Protocol signature database
_PROTOCOLS: List[Dict[str, Any]] = [
    {
        "name": "WiFi 802.11b/g/n (2.4 GHz)",
        "freq_min": 2.400e9, "freq_max": 2.484e9,
        "bw_min": 20e6, "bw_max": 40e6,
        "modulation": "OFDM/DSSS",
        "typical_use": "WLAN data networking",
        "standards": ["IEEE 802.11b", "IEEE 802.11g", "IEEE 802.11n"],
        "security_notes": "WPA3 recommended. WEP is broken. WPS PIN attack surface.",
    },
    {
        "name": "WiFi 802.11a/n/ac/ax (5 GHz)",
        "freq_min": 5.150e9, "freq_max": 5.850e9,
        "bw_min": 20e6, "bw_max": 160e6,
        "modulation": "OFDM",
        "typical_use": "High-speed WLAN data networking",
        "standards": ["IEEE 802.11a", "IEEE 802.11ac", "IEEE 802.11ax (WiFi 6)"],
        "security_notes": "Generally more secure than 2.4GHz (less congestion, shorter range).",
    },
    {
        "name": "Bluetooth Classic",
        "freq_min": 2.402e9, "freq_max": 2.480e9,
        "bw_min": 1e6, "bw_max": 1e6,
        "modulation": "GFSK/π/4-DPSK/8DPSK",
        "typical_use": "Audio, serial data, HID devices",
        "standards": ["Bluetooth Core 5.x"],
        "security_notes": "KNOB attack, BlueBorne vulns patched in modern stacks. Pair with numeric comparison or OOB.",
    },
    {
        "name": "Bluetooth Low Energy (BLE)",
        "freq_min": 2.402e9, "freq_max": 2.480e9,
        "bw_min": 2e6, "bw_max": 2e6,
        "modulation": "GFSK",
        "typical_use": "IoT sensors, health devices, asset tracking",
        "standards": ["Bluetooth Core 5.x LE"],
        "security_notes": "BLE MITM possible without out-of-band pairing. Random address privacy often implemented.",
    },
    {
        "name": "LoRa/LoRaWAN",
        "freq_min": 868e6, "freq_max": 868.6e6,
        "bw_min": 125e3, "bw_max": 500e3,
        "modulation": "CSS (Chirp Spread Spectrum)",
        "typical_use": "Long-range IoT (sensors, smart meters, agriculture)",
        "standards": ["LoRaWAN 1.0", "LoRaWAN 1.1"],
        "security_notes": "AES-128 but key derivation issues in 1.0. Device EUI often hardcoded.",
    },
    {
        "name": "Zigbee / IEEE 802.15.4",
        "freq_min": 2.405e9, "freq_max": 2.480e9,
        "bw_min": 2e6, "bw_max": 2e6,
        "modulation": "O-QPSK/DSSS",
        "typical_use": "Home automation (Philips Hue, smart plugs), industrial sensors",
        "standards": ["IEEE 802.15.4", "Zigbee 3.0"],
        "security_notes": "Network key sniffing during join. TouchLink commissioning attacks documented.",
    },
    {
        "name": "Z-Wave",
        "freq_min": 868.42e6, "freq_max": 868.42e6,
        "bw_min": 9e3, "bw_max": 40e3,
        "modulation": "FSK/GFSK",
        "typical_use": "Smart home automation (locks, lights, thermostats)",
        "standards": ["Z-Wave Plus (ITU-T G.9959)"],
        "security_notes": "S2 security framework (ECDH key exchange) in newer devices. S0 legacy is weak.",
    },
    {
        "name": "ADS-B (1090 MHz)",
        "freq_min": 1090e6, "freq_max": 1090e6,
        "bw_min": 1e6, "bw_max": 1e6,
        "modulation": "PPM (Pulse Position Modulation)",
        "typical_use": "Aircraft transponders (ICAO 24-bit address, altitude, position)",
        "standards": ["ICAO Annex 10", "DO-260B"],
        "security_notes": "No authentication — ADS-B is completely unauthenticated. Ghost aircraft injection possible.",
    },
    {
        "name": "NOAA Weather (137 MHz APT)",
        "freq_min": 137.100e6, "freq_max": 137.925e6,
        "bw_min": 34e3, "bw_max": 34e3,
        "modulation": "FM-APT",
        "typical_use": "NOAA weather satellite imagery",
        "standards": ["APT (Automatic Picture Transmission)"],
        "security_notes": "Unencrypted public broadcast. Safe to receive freely.",
    },
    {
        "name": "ISM 433 MHz (remote controls, sensors)",
        "freq_min": 433.050e6, "freq_max": 434.790e6,
        "bw_min": 5e3, "bw_max": 200e3,
        "modulation": "OOK/ASK/FSK",
        "typical_use": "Garage doors, car remotes, weather stations, 433MHz sensors",
        "standards": ["ETSI EN 300 220"],
        "security_notes": "Most 433 MHz remotes use no authentication — trivially replayed. Rolling codes (KeeLoq) are better but still broken.",
    },
    {
        "name": "NFC (13.56 MHz)",
        "freq_min": 13.553e6, "freq_max": 13.567e6,
        "bw_min": 14e3, "bw_max": 14e3,
        "modulation": "ASK (amplitude-shift keying)",
        "typical_use": "Contactless payment, transit cards, access control",
        "standards": ["ISO 14443", "ISO 15693", "MIFARE"],
        "security_notes": "MIFARE Classic is cryptographically broken (Crypto-1). MIFARE DESFire EV2/EV3 is secure.",
    },
]


class ProtocolIdentifier:
    """Identifies RF protocols from center frequency and bandwidth."""

    def identify(
        self,
        center_freq_hz: float,
        bandwidth_hz: float,
        modulation_hint: Optional[str] = None,
    ) -> List[ProtocolMatch]:
        """
        Return ranked list of possible protocols matching the given signal parameters.
        """
        matches = []

        for proto in _PROTOCOLS:
            freq_match = proto["freq_min"] * 0.995 <= center_freq_hz <= proto["freq_max"] * 1.005
            bw_match = proto["bw_min"] * 0.5 <= bandwidth_hz <= proto["bw_max"] * 2.0
            freq_only = proto["freq_min"] * 0.99 <= center_freq_hz <= proto["freq_max"] * 1.01

            confidence = 0.0
            if freq_match and bw_match:
                confidence = 0.9
            elif freq_match:
                confidence = 0.6
            elif freq_only:
                confidence = 0.4

            if modulation_hint and modulation_hint.lower() in proto["modulation"].lower():
                confidence = min(1.0, confidence + 0.2)

            if confidence > 0.3:
                matches.append(ProtocolMatch(
                    protocol_name=proto["name"],
                    confidence=confidence,
                    frequency_range=f"{proto['freq_min']/1e6:.3f}–{proto['freq_max']/1e6:.3f} MHz",
                    modulation=proto["modulation"],
                    typical_use=proto["typical_use"],
                    standards=proto["standards"],
                    security_notes=proto["security_notes"],
                ))

        # Sort by confidence
        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches

    def list_all(self) -> List[Dict[str, Any]]:
        return _PROTOCOLS
