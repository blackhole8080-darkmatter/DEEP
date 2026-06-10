"""
network package for DEEP v2.

VPN, remote access, network scanning, and Bluetooth integration.
"""

from __future__ import annotations

from network.tailscale import TailscaleManager
from network.remote_access import RemoteAccessManager
from network.scanner import NetworkScanner, NetworkDevice
from network.threat_monitor import ThreatMonitor, Threat
from network.evil_twin_detector import EvilTwinDetector
from network.pihole_client import PiholeClient
from network.proximity_monitor import ProximityMonitor

__all__ = [
    "TailscaleManager",
    "RemoteAccessManager",
    "NetworkScanner",
    "NetworkDevice",
    "ThreatMonitor",
    "Threat",
    "EvilTwinDetector",
    "PiholeClient",
    "ProximityMonitor",
]
