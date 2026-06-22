"""
core/network_graph_builder.py — EventBus subscriber that auto-builds the network graph.

Wires into DEEP's EventBus and populates NetworkTopologyGraph from live events.
Also handles cross-layer heuristics (same MAC → same device, etc.).
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from core.network_topology_graph import NetworkTopologyGraph, get_network_graph

logger = logging.getLogger(__name__)


class NetworkGraphBuilder:
    """Subscribes to DEEP EventBus and auto-builds the multi-layer network graph."""

    def __init__(self, event_bus: Any, graph: Optional[NetworkTopologyGraph] = None) -> None:
        self._event_bus = event_bus
        self._graph = graph or get_network_graph()
        self._started = False
        self._mac_to_node: dict[str, str] = {}  # MAC → node_id for cross-layer linking
        self._ip_to_node: dict[str, str] = {}  # IP → node_id
        self._ssid_to_node: dict[str, str] = {}  # SSID → node_id

    async def start(self) -> None:
        self._started = True
        self._subscribe()
        logger.info("NetworkGraphBuilder started")

    async def stop(self) -> None:
        self._started = False
        logger.info("NetworkGraphBuilder stopped")

    def _subscribe(self) -> None:
        # LAN / Device events
        self._event_bus.subscribe("device_discovered", self._on_device_discovered)
        self._event_bus.subscribe("known_device_joined", self._on_device_joined)
        self._event_bus.subscribe("unknown_device_detected", self._on_device_discovered)
        self._event_bus.subscribe("device_deep_scanned", self._on_device_deep_scanned)
        self._event_bus.subscribe("device_left", self._on_device_left)

        # WiFi events
        self._event_bus.subscribe("wifi_scan_complete", self._on_wifi_scan)
        self._event_bus.subscribe("evil_twin_detected", self._on_evil_twin)

        # Bluetooth events
        self._event_bus.subscribe("ble_device_seen", self._on_ble_device)

        # VPN events
        self._event_bus.subscribe("tailscale_connected", self._on_tailscale)
        self._event_bus.subscribe("tailscale_status_changed", self._on_tailscale_status)

        # DNS events
        self._event_bus.subscribe("dns_query_logged", self._on_dns_query)
        self._event_bus.subscribe("suspicious_dns_detected", self._on_suspicious_dns)

        # Threat events
        self._event_bus.subscribe("threat_detected", self._on_threat)
        self._event_bus.subscribe("security_alert", self._on_security_alert)

        # LLM / AI events (from metrics or brain)
        self._event_bus.subscribe("llm_provider_health", self._on_llm_health)

    # ── LAN handlers ──────────────────────────────────────────────────────────
    async def _on_device_discovered(self, event_name: str, payload: dict) -> None:
        ip = payload.get("ip", "")
        mac = payload.get("mac", "")
        vendor = payload.get("vendor", "")
        hostname = payload.get("hostname", "")
        node_id = f"lan_{ip.replace('.', '_')}"

        self._graph.upsert_node(
            node_id=node_id,
            layer="lan",
            node_type="host",
            label=hostname or ip,
            metadata={"ip": ip, "mac": mac, "vendor": vendor, "trust": payload.get("trust_status", "unknown")},
        )

        if mac:
            self._ip_to_node[ip] = node_id
            self._mac_to_node[mac.upper()] = node_id
            # Cross-layer link: check if this MAC exists in Bluetooth layer
            bt_id = self._mac_to_node.get(f"bt_{mac.upper()}")
            if bt_id:
                self._graph.upsert_edge(node_id, bt_id, "cross", "same_device", 1.0, {"reason": "same MAC"})

        # Link to gateway if known
        gw = self._graph.list_nodes(layer="lan", node_type="gateway")
        if gw and node_id != gw[0].id:
            self._graph.upsert_edge(node_id, gw[0].id, "lan", "connected_to", 1.0)

    async def _on_device_joined(self, event_name: str, payload: dict) -> None:
        await self._on_device_discovered(event_name, payload)

    async def _on_device_deep_scanned(self, event_name: str, payload: dict) -> None:
        ip = payload.get("ip", "")
        node_id = self._ip_to_node.get(ip)
        if not node_id:
            return
        self._graph.upsert_node(
            node_id=node_id, layer="lan", node_type="host", label=payload.get("hostname", ip),
            metadata={
                "ip": ip,
                "open_ports": payload.get("open_ports", []),
                "os_guess": payload.get("os_guess"),
                "last_deep_scan": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def _on_device_left(self, event_name: str, payload: dict) -> None:
        ip = payload.get("ip", "")
        node_id = self._ip_to_node.pop(ip, None)
        if node_id:
            self._graph.upsert_node(
                node_id=node_id, layer="lan", node_type="host",
                label=payload.get("hostname", ip),
                metadata={"status": "offline", "left_at": datetime.now(timezone.utc).isoformat()},
            )

    # ── WiFi handlers ───────────────────────────────────────────────────────
    async def _on_wifi_scan(self, event_name: str, payload: dict) -> None:
        for net in payload.get("networks", []):
            ssid = net.get("ssid", "")
            bssid = net.get("bssid", "").upper()
            node_id = f"wifi_{bssid.replace(':', '_')}"
            self._ssid_to_node[ssid] = node_id
            self._graph.upsert_node(
                node_id=node_id, layer="wifi", node_type="ap",
                label=ssid or "Hidden",
                metadata={"ssid": ssid, "bssid": bssid, "channel": net.get("channel"), "signal": net.get("signal")},
            )

    async def _on_evil_twin(self, event_name: str, payload: dict) -> None:
        bssid = payload.get("rogue_bssid", "").upper()
        ssid = payload.get("ssid", "")
        node_id = f"wifi_{bssid.replace(':', '_')}"
        self._graph.upsert_node(
            node_id=node_id, layer="wifi", node_type="ap",
            label=f"{ssid} (ROGUE)",
            metadata={"ssid": ssid, "bssid": bssid, "rogue": True, "legitimate_bssid": payload.get("legitimate_bssid")},
        )
        # Link rogue AP to the legitimate one if known
        legit_bssid = payload.get("legitimate_bssid", "").upper()
        if legit_bssid:
            legit_id = f"wifi_{legit_bssid.replace(':', '_')}"
            self._graph.upsert_edge(node_id, legit_id, "wifi", "impersonates", 1.0, {"type": "evil_twin"})

    # ── Bluetooth handlers ──────────────────────────────────────────────────
    async def _on_ble_device(self, event_name: str, payload: dict) -> None:
        mac = payload.get("mac", "").upper()
        node_id = f"bt_{mac.replace(':', '_')}"
        self._mac_to_node[f"bt_{mac}"] = node_id
        self._graph.upsert_node(
            node_id=node_id, layer="bluetooth", node_type="bt_device",
            label=payload.get("name", mac),
            metadata={"mac": mac, "rssi": payload.get("rssi"), "vendor": payload.get("vendor"),
                      "is_tracker": payload.get("is_tracker", False), "distance_m": payload.get("distance_m")},
        )
        # Cross-layer: link to LAN node with same MAC
        lan_id = self._mac_to_node.get(mac)
        if lan_id:
            self._graph.upsert_edge(node_id, lan_id, "cross", "same_device", 1.0, {"reason": "same MAC"})

    # ── VPN handlers ──────────────────────────────────────────────────────────
    async def _on_tailscale(self, event_name: str, payload: dict) -> None:
        for peer in payload.get("peers", []):
            hostname = peer if isinstance(peer, str) else peer.get("hostname", "")
            node_id = f"vpn_{hostname}"
            self._graph.upsert_node(
                node_id=node_id, layer="vpn", node_type="tailscale_peer",
                label=hostname,
                metadata={"tailscale_ip": payload.get("ip"), "online": True},
            )
            # Link to local gateway
            gw = self._graph.list_nodes(layer="lan", node_type="gateway")
            if gw:
                self._graph.upsert_edge(node_id, gw[0].id, "vpn", "tunnels_via", 1.0)

    async def _on_tailscale_status(self, event_name: str, payload: dict) -> None:
        state = payload.get("state", "")
        ip = payload.get("ip", "")
        hostname = payload.get("hostname", "local")
        node_id = f"vpn_{hostname}"
        self._graph.upsert_node(
            node_id=node_id, layer="vpn", node_type="tailscale_peer" if state == "Running" else "exit_node",
            label=hostname,
            metadata={"state": state, "tailscale_ip": ip, "peers": payload.get("peers", [])},
        )

    # ── DNS handlers ────────────────────────────────────────────────────────
    async def _on_dns_query(self, event_name: str, payload: dict) -> None:
        domain = payload.get("domain", "")
        client_ip = payload.get("client_ip", "")
        domain_id = f"dns_{domain.replace('.', '_')}"
        self._graph.upsert_node(
            node_id=domain_id, layer="dns", node_type="domain",
            label=domain,
            metadata={"domain": domain, "queried_by": client_ip},
        )
        # Link to LAN host
        host_id = self._ip_to_node.get(client_ip)
        if host_id:
            self._graph.upsert_edge(host_id, domain_id, "dns", "queried", 1.0)

    async def _on_suspicious_dns(self, event_name: str, payload: dict) -> None:
        await self._on_dns_query(event_name, payload)
        domain = payload.get("domain", "")
        domain_id = f"dns_{domain.replace('.', '_')}"
        self._graph.upsert_node(
            node_id=domain_id, layer="dns", node_type="domain",
            label=domain,
            metadata={"domain": domain, "suspicious": True, "client_ip": payload.get("client_ip")},
        )

    # ── Threat handlers ─────────────────────────────────────────────────────
    async def _on_threat(self, event_name: str, payload: dict) -> None:
        source_ip = payload.get("source_ip", "")
        threat_type = payload.get("threat_type", "unknown")
        node_id = self._ip_to_node.get(source_ip)
        if node_id:
            self._graph.upsert_node(
                node_id=node_id, layer="lan", node_type="host",
                label=f"Threat: {source_ip}",
                metadata={"threat_type": threat_type, "confidence": payload.get("confidence"), "evidence": payload.get("evidence")},
            )
            # Mark edges with threat flag
            for edge in self._graph.get_edges(node_id=node_id):
                self._graph.upsert_edge(edge.source_id, edge.target_id, edge.layer, edge.relation_type,
                                        edge.strength, {**(edge.metadata or {}), "threat_flag": threat_type})

    async def _on_security_alert(self, event_name: str, payload: dict) -> None:
        alert_type = payload.get("type", "")
        if alert_type == "evil_twin":
            await self._on_evil_twin(event_name, payload)
        elif alert_type == "unknown_device":
            device = payload.get("device", {})
            await self._on_device_discovered(event_name, device)

    # ── LLM / AI handlers ───────────────────────────────────────────────────
    async def _on_llm_health(self, event_name: str, payload: dict) -> None:
        provider = payload.get("provider", "ollama")
        model = payload.get("model", "")
        node_id = f"ai_{provider}_{model}"
        self._graph.upsert_node(
            node_id=node_id, layer="ai", node_type="llm_provider",
            label=f"{provider} / {model}",
            metadata={"provider": provider, "model": model, "latency_ms": payload.get("latency_ms"),
                      "tokens_per_sec": payload.get("tokens_per_sec"), "healthy": payload.get("healthy", True)},
        )
        # Link to local gateway
        gw = self._graph.list_nodes(layer="lan", node_type="gateway")
        if gw:
            self._graph.upsert_edge(node_id, gw[0].id, "ai", "connects_via", payload.get("latency_ms", 100) / 1000)

    # ── Public API ──────────────────────────────────────────────────────────
    def ensure_gateway(self, ip: str, mac: str, hostname: str = "Gateway") -> None:
        """Manually register the gateway/router node."""
        node_id = f"lan_{ip.replace('.', '_')}"
        self._graph.upsert_node(
            node_id=node_id, layer="lan", node_type="gateway",
            label=hostname,
            metadata={"ip": ip, "mac": mac, "is_gateway": True},
        )
        self._ip_to_node[ip] = node_id
        if mac:
            self._mac_to_node[mac.upper()] = node_id
