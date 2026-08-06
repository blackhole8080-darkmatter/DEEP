"""
DEEP — PCAP Analyzer
Flow extraction, protocol identification, IoT traffic analysis,
security finding detection from PCAP files.
Uses: scapy (preferred) or dpkt (fallback).
"""
from __future__ import annotations

import asyncio
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from scapy.all import rdpcap, IP, IPv6, TCP, UDP, Raw, DNS, DNSQR, DNSRR
    from scapy.layers.http import HTTP, HTTPRequest, HTTPResponse
    _SCAPY_OK = True
except ImportError:
    _SCAPY_OK = False

try:
    import dpkt
    _DPKT_OK = True
except ImportError:
    _DPKT_OK = False


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class PCAPFlow:
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str           # "TCP" | "UDP"
    app_layer: str          # Identified application protocol
    packet_count: int
    byte_count: int
    first_seen: float
    last_seen: float
    data_samples: List[bytes] = field(default_factory=list)  # First few payloads
    security_flags: List[str] = field(default_factory=list)


@dataclass
class SecurityFinding:
    severity: str           # CRITICAL | HIGH | MEDIUM | LOW | INFO
    title: str
    description: str
    flow: Optional[PCAPFlow] = None
    evidence: str = ""
    recommendation: str = ""


@dataclass
class PCAPReport:
    file_path: str
    total_packets: int
    total_bytes: int
    duration_s: float
    flows: List[PCAPFlow] = field(default_factory=list)
    dns_queries: List[str] = field(default_factory=list)
    http_hosts: List[str] = field(default_factory=list)
    tls_snis: List[str] = field(default_factory=list)
    findings: List[SecurityFinding] = field(default_factory=list)
    unknown_protocols: List[PCAPFlow] = field(default_factory=list)
    error: Optional[str] = None


# ── Port → Protocol mapping ───────────────────────────────────────────────────

_PORT_PROTOCOLS: Dict[int, str] = {
    20: "FTP-data", 21: "FTP", 22: "SSH", 23: "Telnet",
    25: "SMTP", 53: "DNS", 67: "DHCP", 68: "DHCP",
    80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS/TLS",
    445: "SMB", 465: "SMTPS", 502: "Modbus", 1883: "MQTT",
    3306: "MySQL", 3389: "RDP", 4840: "OPC-UA",
    5353: "mDNS", 5672: "AMQP", 6379: "Redis", 8080: "HTTP-alt",
    8883: "MQTT-TLS", 9200: "Elasticsearch", 27017: "MongoDB",
    47808: "BACnet", 102: "ISO-TSAP (S7/Siemens)",
}

# Ports that indicate cleartext sensitive data
_CLEARTEXT_SENSITIVE = {23, 21, 25, 110, 143, 502, 47808, 102, 1883}


class PCAPAnalyzer:
    """
    PCAP file analyzer.
    Extracts flows, identifies protocols, detects security issues,
    and summarizes IoT/OT/network traffic patterns.
    """

    def __init__(self, data_dir: str = "data/protocols"):
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

    async def analyze(self, file_path: str) -> PCAPReport:
        """
        Full PCAP analysis.
        Returns: flows, DNS queries, HTTP hosts, TLS SNIs, security findings.
        """
        p = Path(file_path)
        if not p.exists():
            return PCAPReport(
                file_path=file_path,
                total_packets=0,
                total_bytes=0,
                duration_s=0.0,
                error=f"File not found: {file_path}",
            )

        if not _SCAPY_OK and not _DPKT_OK:
            return PCAPReport(
                file_path=file_path,
                total_packets=0,
                total_bytes=0,
                duration_s=0.0,
                error=(
                    "Neither scapy nor dpkt is installed.\n"
                    "Install with: pip install scapy  OR  pip install dpkt"
                ),
            )

        if _SCAPY_OK:
            return await asyncio.to_thread(self._analyze_scapy, file_path)
        else:
            return await asyncio.to_thread(self._analyze_dpkt, file_path)

    # ── Scapy analysis ────────────────────────────────────────────────────────

    def _analyze_scapy(self, file_path: str) -> PCAPReport:
        """Full analysis using Scapy."""
        packets = rdpcap(file_path)
        total_packets = len(packets)
        total_bytes = sum(len(p) for p in packets)

        if not packets:
            return PCAPReport(file_path=file_path, total_packets=0, total_bytes=0, duration_s=0.0)

        # Flow tracking
        flows: Dict[Tuple, PCAPFlow] = {}
        dns_queries = set()
        http_hosts = set()
        tls_snis = set()
        timestamps = []

        for pkt in packets:
            ts = float(pkt.time)
            timestamps.append(ts)

            # Extract IP layer
            if IP in pkt:
                src_ip = pkt[IP].src
                dst_ip = pkt[IP].dst
            elif IPv6 in pkt:
                src_ip = pkt[IPv6].src
                dst_ip = pkt[IPv6].dst
            else:
                continue

            # Transport layer
            if TCP in pkt:
                proto = "TCP"
                src_port = pkt[TCP].sport
                dst_port = pkt[TCP].dport
            elif UDP in pkt:
                proto = "UDP"
                src_port = pkt[UDP].sport
                dst_port = pkt[UDP].dport
            else:
                continue

            # Normalize flow direction (bidirectional)
            if (src_ip, src_port) > (dst_ip, dst_port):
                flow_key = (dst_ip, src_ip, dst_port, src_port, proto)
            else:
                flow_key = (src_ip, dst_ip, src_port, dst_port, proto)

            if flow_key not in flows:
                app = _PORT_PROTOCOLS.get(min(src_port, dst_port), "Unknown")
                flows[flow_key] = PCAPFlow(
                    src_ip=flow_key[0], dst_ip=flow_key[1],
                    src_port=flow_key[2], dst_port=flow_key[3],
                    protocol=proto, app_layer=app,
                    packet_count=0, byte_count=0,
                    first_seen=ts, last_seen=ts,
                )

            flow = flows[flow_key]
            flow.packet_count += 1
            flow.byte_count += len(pkt)
            flow.last_seen = max(flow.last_seen, ts)

            # Collect payload samples
            if Raw in pkt and len(flow.data_samples) < 3:
                flow.data_samples.append(bytes(pkt[Raw]))

            # DNS queries
            if DNS in pkt and pkt[DNS].qd:
                try:
                    qname = pkt[DNS].qd.qname.decode(errors="replace").rstrip(".")
                    dns_queries.add(qname)
                except Exception:
                    pass

            # TLS SNI (ClientHello)
            if TCP in pkt and Raw in pkt:
                raw = bytes(pkt[Raw])
                sni = self._extract_tls_sni(raw)
                if sni:
                    tls_snis.add(sni)

            # HTTP Host header
            if HTTPRequest in pkt:
                try:
                    host = pkt[HTTPRequest].Host.decode(errors="replace")
                    if host:
                        http_hosts.add(host)
                except Exception:
                    pass

        duration = (max(timestamps) - min(timestamps)) if len(timestamps) > 1 else 0.0

        # Identify unknown protocols
        flow_list = list(flows.values())
        unknown = [f for f in flow_list if f.app_layer == "Unknown" and f.packet_count > 5]

        # Security analysis
        findings = self._detect_security_issues(flow_list, dns_queries, http_hosts)

        return PCAPReport(
            file_path=file_path,
            total_packets=total_packets,
            total_bytes=total_bytes,
            duration_s=duration,
            flows=sorted(flow_list, key=lambda f: f.byte_count, reverse=True)[:50],
            dns_queries=sorted(dns_queries)[:100],
            http_hosts=sorted(http_hosts)[:50],
            tls_snis=sorted(tls_snis)[:50],
            findings=findings,
            unknown_protocols=unknown[:10],
        )

    # ── dpkt fallback ─────────────────────────────────────────────────────────

    def _analyze_dpkt(self, file_path: str) -> PCAPReport:
        """Basic analysis using dpkt (no HTTP/DNS parsing)."""
        flows: Dict[Tuple, PCAPFlow] = {}
        total_packets = 0
        total_bytes = 0
        timestamps = []

        try:
            with open(file_path, "rb") as f:
                try:
                    pcap = dpkt.pcap.Reader(f)
                except Exception:
                    pcap = dpkt.pcapng.Reader(f)

                for ts, buf in pcap:
                    timestamps.append(ts)
                    total_packets += 1
                    total_bytes += len(buf)

                    try:
                        eth = dpkt.ethernet.Ethernet(buf)
                        ip = eth.data
                        if not isinstance(ip, (dpkt.ip.IP, dpkt.ip6.IP6)):
                            continue

                        src_ip = self._ip_to_str(ip.src)
                        dst_ip = self._ip_to_str(ip.dst)

                        if isinstance(ip.data, dpkt.tcp.TCP):
                            proto = "TCP"
                            src_port = ip.data.sport
                            dst_port = ip.data.dport
                        elif isinstance(ip.data, dpkt.udp.UDP):
                            proto = "UDP"
                            src_port = ip.data.sport
                            dst_port = ip.data.dport
                        else:
                            continue

                        flow_key = tuple(sorted([(src_ip, src_port), (dst_ip, dst_port)])) + (proto,)
                        if flow_key not in flows:
                            app = _PORT_PROTOCOLS.get(min(src_port, dst_port), "Unknown")
                            flows[flow_key] = PCAPFlow(
                                src_ip=src_ip, dst_ip=dst_ip,
                                src_port=src_port, dst_port=dst_port,
                                protocol=proto, app_layer=app,
                                packet_count=0, byte_count=0,
                                first_seen=ts, last_seen=ts,
                            )

                        f2 = flows[flow_key]
                        f2.packet_count += 1
                        f2.byte_count += len(buf)
                        f2.last_seen = ts

                    except Exception:
                        pass

        except Exception as exc:
            return PCAPReport(
                file_path=file_path,
                total_packets=total_packets,
                total_bytes=total_bytes,
                duration_s=0.0,
                error=f"dpkt parse error: {exc}",
            )

        duration = (max(timestamps) - min(timestamps)) if len(timestamps) > 1 else 0.0
        flow_list = list(flows.values())
        findings = self._detect_security_issues(flow_list, set(), set())

        return PCAPReport(
            file_path=file_path,
            total_packets=total_packets,
            total_bytes=total_bytes,
            duration_s=duration,
            flows=sorted(flow_list, key=lambda f: f.byte_count, reverse=True)[:50],
            findings=findings,
        )

    # ── Security analysis ──────────────────────────────────────────────────────

    def _detect_security_issues(
        self,
        flows: List[PCAPFlow],
        dns_queries: set,
        http_hosts: set,
    ) -> List[SecurityFinding]:
        findings = []

        for flow in flows:
            # Cleartext protocols
            port = min(flow.src_port, flow.dst_port)
            if port in _CLEARTEXT_SENSITIVE:
                proto_name = _PORT_PROTOCOLS.get(port, str(port))
                findings.append(SecurityFinding(
                    severity="HIGH" if port in {23, 502} else "MEDIUM",
                    title=f"Cleartext protocol detected: {proto_name}",
                    description=f"Traffic on port {port} ({proto_name}) is unencrypted.",
                    flow=flow,
                    evidence=f"Flow: {flow.src_ip}:{flow.src_port} → {flow.dst_ip}:{flow.dst_port}",
                    recommendation=f"Replace {proto_name} with encrypted equivalent (e.g., SSH, MQTTS, Modbus/TLS).",
                ))

            # MQTT without auth check (heuristic: CONNECT packet without credentials)
            if port == 1883 and flow.data_samples:
                for sample in flow.data_samples:
                    if len(sample) > 4 and sample[0] & 0xF0 == 0x10:  # MQTT CONNECT
                        connect_flags = sample[9] if len(sample) > 9 else 0
                        has_username = bool(connect_flags & 0x80)
                        has_password = bool(connect_flags & 0x40)
                        if not has_username:
                            findings.append(SecurityFinding(
                                severity="HIGH",
                                title="MQTT CONNECT without authentication",
                                description="MQTT broker accepting unauthenticated connections.",
                                flow=flow,
                                evidence=f"MQTT CONNECT packet: no username flag in connect flags (0x{connect_flags:02X})",
                                recommendation="Configure MQTT broker to require username/password. Enable TLS (port 8883).",
                            ))
                        break

        # HTTP (unencrypted web)
        if http_hosts:
            findings.append(SecurityFinding(
                severity="MEDIUM",
                title=f"Unencrypted HTTP traffic to {len(http_hosts)} host(s)",
                description=f"HTTP (not HTTPS) traffic detected to: {', '.join(list(http_hosts)[:5])}",
                evidence=f"Hosts: {', '.join(sorted(http_hosts)[:10])}",
                recommendation="Enforce HTTPS. Configure HSTS. Redirect HTTP → HTTPS.",
            ))

        return findings

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extract_tls_sni(self, data: bytes) -> Optional[str]:
        """Extract Server Name Indication from TLS ClientHello."""
        try:
            if len(data) < 5 or data[0] != 0x16:  # TLS handshake record
                return None
            if data[5] != 0x01:  # ClientHello
                return None
            # Parse TLS extensions to find SNI (type 0x0000)
            idx = 43
            if idx >= len(data):
                return None
            session_len = data[idx]
            idx += 1 + session_len
            if idx + 2 >= len(data):
                return None
            cipher_len = struct.unpack(">H", data[idx:idx+2])[0]
            idx += 2 + cipher_len
            if idx >= len(data):
                return None
            comp_len = data[idx]
            idx += 1 + comp_len
            if idx + 2 >= len(data):
                return None
            ext_total = struct.unpack(">H", data[idx:idx+2])[0]
            idx += 2
            end = idx + ext_total
            while idx + 4 <= end:
                ext_type = struct.unpack(">H", data[idx:idx+2])[0]
                ext_len = struct.unpack(">H", data[idx+2:idx+4])[0]
                idx += 4
                if ext_type == 0:  # SNI extension
                    # server_name_list_length + type + server_name_length
                    sni_len = struct.unpack(">H", data[idx+3:idx+5])[0]
                    sni = data[idx+5:idx+5+sni_len].decode(errors="replace")
                    return sni
                idx += ext_len
        except Exception:
            pass
        return None

    def _ip_to_str(self, ip_bytes: bytes) -> str:
        if len(ip_bytes) == 4:
            return ".".join(str(b) for b in ip_bytes)
        elif len(ip_bytes) == 16:
            return ":".join(f"{ip_bytes[i]:02x}{ip_bytes[i+1]:02x}" for i in range(0, 16, 2))
        return ip_bytes.hex()
