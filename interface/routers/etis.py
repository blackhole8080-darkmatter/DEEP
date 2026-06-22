"""
DEEP — ETIS Expert Domain API Router
All /api/etis/* endpoints for the Expert Technical Intelligence System.
Mounted via app.include_router() at server startup.
"""
from __future__ import annotations

import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse

# Ensure DEEP root is on path
_DEEP_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_DEEP_ROOT) not in sys.path:
    sys.path.insert(0, str(_DEEP_ROOT))

router = APIRouter(prefix="/api/etis", tags=["etis"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _ok(data: Any) -> Dict:
    return {"ok": True, "data": data}


def _err(msg: str, status: int = 400) -> JSONResponse:
    return JSONResponse(status_code=status, content={"ok": False, "error": msg})


# ── Domain status ──────────────────────────────────────────────────────────────

@router.get("/status")
async def etis_status():
    """ETIS system status — which domains are available."""
    domains: Dict[str, Dict] = {}

    # Physics
    try:
        from domains.physics.engine import PhysicsEngine
        PhysicsEngine()
        domains["physics"] = {"available": True, "capabilities": ["compute", "simulate", "constants"]}
    except Exception as e:
        domains["physics"] = {"available": False, "error": str(e)}

    # Cybersecurity
    try:
        from domains.cybersec.cve_intel import CVEIntel
        domains["cybersec"] = {"available": True, "capabilities": ["cve_lookup", "cve_search", "kev_feed", "mitre", "osint", "exploits"]}
    except Exception as e:
        domains["cybersec"] = {"available": False, "error": str(e)}

    # RF Signals
    try:
        from domains.rf_signals.protocol_id import ProtocolIdentifier
        domains["rf"] = {"available": True, "capabilities": ["wifi_scan", "ble_scan", "spectrum", "protocol_id"]}
    except Exception as e:
        domains["rf"] = {"available": False, "error": str(e)}

    # Protocols
    try:
        from domains.protocols.binary_protocol import BinaryProtocolRE
        domains["protocols"] = {"available": True, "capabilities": ["pcap_analysis", "binary_re", "dissector_gen"]}
    except Exception as e:
        domains["protocols"] = {"available": False, "error": str(e)}

    # Hardware
    try:
        from domains.hardware.firmware_analyzer import FirmwareAnalyzer
        domains["hardware"] = {"available": True, "capabilities": ["firmware_analysis", "string_extraction"]}
    except Exception as e:
        domains["hardware"] = {"available": False, "error": str(e)}

    # Robotics
    try:
        from domains.robotics.kinematics import make_ur5
        domains["robotics"] = {"available": True, "capabilities": ["forward_kinematics", "inverse_kinematics", "trajectory"]}
    except Exception as e:
        domains["robotics"] = {"available": False, "error": str(e)}

    # Sandbox
    try:
        from core.sandbox_executor import SandboxExecutor
        executor = SandboxExecutor()
        docker_ok = await executor._check_docker()
        domains["sandbox"] = {"available": True, "docker": docker_ok, "languages": ["python", "bash", "node"]}
    except Exception as e:
        domains["sandbox"] = {"available": False, "error": str(e)}

    return _ok({"domains": domains, "version": "ETIS-1.0"})


# ── Intelligence Feed ──────────────────────────────────────────────────────────

@router.get("/intel/feed")
async def intel_feed(days_back: int = 7):
    """Live CISA KEV + arXiv threat intel feed."""
    try:
        from core.intel_feeds import get_intel_feeds
        feeds = get_intel_feeds()
        items = await feeds.fetch_all(days_back=days_back)
        return _ok({
            "count": len(items),
            "items": [
                {
                    "source": i.source,
                    "id": i.item_id,
                    "title": i.title,
                    "summary": i.summary,
                    "published": i.published,
                    "severity": i.severity,
                    "url": i.url,
                    "tags": i.tags,
                    "is_kev": i.is_kev,
                    "cvss_score": i.cvss_score,
                }
                for i in items
            ],
        })
    except Exception as e:
        return _err(str(e))


@router.get("/intel/kev")
async def kev_feed(days_back: int = 30):
    """CISA Known Exploited Vulnerabilities only."""
    try:
        from core.intel_feeds import get_intel_feeds
        feeds = get_intel_feeds()
        items = await feeds.fetch_kev()
        return _ok({"count": len(items), "items": [
            {"id": i.item_id, "title": i.title, "published": i.published, "url": i.url}
            for i in items if i.is_kev
        ]})
    except Exception as e:
        return _err(str(e))


# ── Cross-domain classifier ────────────────────────────────────────────────────

@router.post("/classify")
async def classify_domain(payload: dict):
    """Classify a query into expert domains + suggest tool invocations."""
    query = (payload or {}).get("query", "").strip()
    if not query:
        raise HTTPException(400, "query required")
    try:
        from core.cross_domain_synthesizer import get_synthesizer
        synth = get_synthesizer()
        result = await synth.synthesize(query)
        return _ok({
            "active_domains": result.active_domains,
            "is_cross_domain": result.is_cross_domain,
            "confidence": result.confidence,
            "synthesis": result.synthesis,
            "tool_invocations": result.tool_invocations,
            "contexts": [
                {"domain": c.domain, "relevance": c.relevance, "keywords": c.keywords_matched}
                for c in result.domain_contexts
            ],
        })
    except Exception as e:
        return _err(str(e))


# ── Cybersecurity ──────────────────────────────────────────────────────────────

@router.get("/cve/{cve_id}")
async def cve_lookup(cve_id: str):
    """Full CVE record from NVD API v2 + KEV check."""
    try:
        from domains.cybersec.cve_intel import CVEIntel
        intel = CVEIntel()
        r = await intel.lookup(cve_id.upper())
        # lookup() returns a CVERecord; not-found comes back as a stub with empty
        # published/modified and the message in `description` (no `.error` field).
        if not r.published:
            return _err(r.description or "CVE not found", 404)
        return _ok({
            "cve_id": r.cve_id,
            "description": r.description,
            "severity": r.cvss_v3.severity if r.cvss_v3 else None,
            "cvss_score": r.cvss_v3.score if r.cvss_v3 else r.cvss_v2_score,
            "cvss_vector": r.cvss_v3.vector if r.cvss_v3 else None,
            "published": r.published,
            "modified": r.modified,
            "cwes": r.cwe,
            "affected_products": r.affected_products,
            "references": r.references,
            "is_kev": r.is_kev,
        })
    except Exception as e:
        return _err(str(e))


@router.post("/cve/search")
async def cve_search(payload: dict):
    """Search NVD for recent CVEs by keyword."""
    keyword = (payload or {}).get("keyword", "")
    min_cvss = float((payload or {}).get("min_cvss", 7.0))
    days_back = int((payload or {}).get("days_back", 30))
    try:
        from domains.cybersec.cve_intel import CVEIntel
        intel = CVEIntel()
        results = await intel.search_recent(keyword=keyword, min_cvss=min_cvss, days_back=days_back)
        return _ok({
            "count": len(results),
            "results": [
                {
                    "cve_id": r.cve_id,
                    "description": r.description[:200],
                    "severity": r.cvss_v3.severity if r.cvss_v3 else None,
                    "cvss_score": r.cvss_v3.score if r.cvss_v3 else r.cvss_v2_score,
                    "published": r.published,
                    "is_kev": r.is_kev,
                }
                for r in results
            ],
        })
    except Exception as e:
        return _err(str(e))


@router.post("/mitre/search")
async def mitre_search(payload: dict):
    """Search MITRE ATT&CK techniques."""
    query = (payload or {}).get("query", "")
    try:
        from domains.cybersec.mitre_attack import MITREAttack
        mitre = MITREAttack()
        results = mitre.search_ttp(query)  # sync; returns List[Technique]
        return _ok({
            "count": len(results),
            "techniques": [
                {
                    "id": t.id,
                    "name": t.name,
                    "tactics": t.tactics,
                    "description": t.description[:300],
                    "mitigation": t.mitigation,
                    "detection": t.detection,
                    "platforms": t.platforms,
                }
                for t in results[:15]
            ],
        })
    except Exception as e:
        return _err(str(e))


@router.post("/mitre/map-cve")
async def mitre_map_cve(payload: dict):
    """Map CVE to ATT&CK kill chain phases."""
    cve_id = (payload or {}).get("cve_id", "")
    description = (payload or {}).get("description", "")
    try:
        from domains.cybersec.mitre_attack import MITREAttack
        mitre = MITREAttack()
        kill_chain = mitre.get_kill_chain_for_cve(cve_id=cve_id, description=description)
        return _ok({
            "cve_id": cve_id,
            "vulnerability_class": kill_chain.vulnerability_class,
            "phase": kill_chain.kill_chain_phase,
            "narrative": kill_chain.narrative,
            "ttps": [
                {"id": t.id, "name": t.name, "phase": kill_chain.kill_chain_phase}
                for t in kill_chain.likely_techniques
            ],
        })
    except Exception as e:
        return _err(str(e))


@router.post("/osint/recon")
async def osint_recon(payload: dict):
    """Passive OSINT recon: DNS, certs, subdomains, geolocation."""
    target = (payload or {}).get("target", "").strip()
    if not target:
        raise HTTPException(400, "target required")
    try:
        from domains.cybersec.osint_engine import OSINTEngine
        engine = OSINTEngine()
        result = await engine.recon(target)
        if result.error:
            return _err(result.error)
        return _ok({
            "target": result.target,
            "ip_addresses": result.ip_addresses,
            "subdomains": result.subdomains[:30],
            "open_ports": result.open_ports[:20],
            "ssl_info": result.ssl_info,
            "geolocation": result.geolocation,
            "email_addresses": result.email_addresses,
            "technology_stack": result.technology_stack,
            "shodan_data": result.shodan_data,
        })
    except Exception as e:
        return _err(str(e))


@router.post("/exploit/search")
async def exploit_search(payload: dict):
    """Search public exploits for a CVE."""
    cve_id = (payload or {}).get("cve_id", "").strip().upper()
    if not cve_id:
        raise HTTPException(400, "cve_id required")
    try:
        from domains.cybersec.exploit_lookup import ExploitLookup
        lookup = ExploitLookup()
        results = await lookup.search(cve_id)
        return _ok({
            "cve_id": cve_id,
            "count": len(results),
            "exploits": [
                {
                    "title": e.title,
                    "type": e.exploit_type,
                    "poc_url": e.poc_url,
                    "cvss_score": e.cvss_score,
                    "description": e.description[:200],
                }
                for e in results[:10]
            ],
        })
    except Exception as e:
        return _err(str(e))


# ── RF Signals ────────────────────────────────────────────────────────────────

@router.get("/rf/protocol")
async def rf_protocol_id(center_freq: float, bandwidth: float = 0):
    """Identify RF protocol from center frequency + bandwidth."""
    try:
        from domains.rf_signals.protocol_id import ProtocolIdentifier
        pid = ProtocolIdentifier()
        matches = pid.identify(center_freq_hz=center_freq, bandwidth_hz=bandwidth)
        return _ok({
            "center_freq_mhz": center_freq / 1e6,
            "bandwidth_khz": bandwidth / 1e3,
            "matches": [
                {
                    "protocol": m.protocol_name,
                    "confidence": m.confidence,
                    "modulation": m.modulation,
                    "frequency_range": m.frequency_range,
                    "typical_use": m.typical_use,
                    "standards": m.standards,
                    "security_notes": m.security_notes,
                }
                for m in matches[:8]
            ],
        })
    except Exception as e:
        return _err(str(e))


@router.get("/rf/protocols/list")
async def rf_list_protocols():
    """List all known RF protocols in the database."""
    try:
        from domains.rf_signals.protocol_id import ProtocolIdentifier, _PROTOCOLS
        return _ok({"count": len(_PROTOCOLS), "protocols": _PROTOCOLS})
    except Exception as e:
        return _err(str(e))


@router.post("/rf/wifi/scan")
async def wifi_scan():
    """Trigger WiFi deep scan."""
    try:
        from domains.rf_signals.wifi_scanner import WiFiScanner
        scanner = WiFiScanner()
        result = await scanner.deep_scan()
        if result.error:
            return _err(result.error)
        return _ok({
            "count": len(result.networks),
            "networks": [
                {
                    "ssid": n.ssid,
                    "bssid": n.bssid,
                    "channel": n.channel,
                    "frequency_ghz": n.frequency_ghz,
                    "signal_strength": n.signal_strength,
                    "security": n.security,
                    "vendor": n.vendor,
                    "is_hidden": n.is_hidden,
                    "clients": n.clients,
                }
                for n in sorted(result.networks, key=lambda x: x.signal_strength, reverse=True)
            ],
            "evil_twins": result.evil_twins,
            "scan_time": result.scan_time,
        })
    except Exception as e:
        return _err(str(e))


@router.post("/rf/ble/scan")
async def ble_scan(payload: dict = None):
    """Trigger BLE scan."""
    duration = float((payload or {}).get("duration", 8.0))
    try:
        from domains.rf_signals.bt_enumerator import BTEnumerator
        enumerator = BTEnumerator()
        result = await enumerator.scan(duration=duration)
        if result.error:
            return _err(result.error)
        return _ok({
            "count": len(result.devices),
            "scan_duration_s": result.scan_duration_s,
            "devices": [
                {
                    "address": d.address,
                    "name": d.name,
                    "rssi": d.rssi,
                    "distance_m": d.estimated_distance_m,
                    "is_airtag": d.is_airtag,
                    "manufacturer_id": list(d.manufacturer_data.keys())[0] if d.manufacturer_data else None,
                    "services": d.service_uuids[:5],
                    "address_type": d.address_type,
                }
                for d in sorted(result.devices, key=lambda d: d.rssi or -999, reverse=True)
            ],
        })
    except Exception as e:
        return _err(str(e))


# ── Protocol RE ───────────────────────────────────────────────────────────────

@router.post("/protocols/pcap")
async def analyze_pcap(file: UploadFile = File(...)):
    """Upload and analyze a PCAP file."""
    import tempfile
    try:
        suffix = ".pcap" if file.filename.endswith(".pcap") else ".pcapng"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        from domains.protocols.pcap_analyzer import PCAPAnalyzer
        analyzer = PCAPAnalyzer()
        report = await analyzer.analyze(tmp_path)
        os.unlink(tmp_path)

        if report.error:
            return _err(report.error)

        return _ok({
            "file": file.filename,
            "total_packets": report.total_packets,
            "total_bytes": report.total_bytes,
            "duration_s": report.duration_s,
            "flows": [
                {
                    "src": f"{flow.src_ip}:{flow.src_port}",
                    "dst": f"{flow.dst_ip}:{flow.dst_port}",
                    "proto": flow.protocol,
                    "app": flow.app_layer,
                    "packets": flow.packet_count,
                    "bytes": flow.byte_count,
                }
                for flow in report.flows[:20]
            ],
            "dns_queries": report.dns_queries[:30],
            "http_hosts": report.http_hosts[:15],
            "tls_snis": report.tls_snis[:15],
            "findings": [
                {
                    "severity": f.severity,
                    "title": f.title,
                    "description": f.description,
                    "recommendation": f.recommendation,
                }
                for f in report.findings
            ],
        })
    except Exception as e:
        return _err(str(e))


@router.post("/protocols/binary-re")
async def binary_protocol_re(payload: dict):
    """Reverse engineer binary protocol from hex samples."""
    hex_samples = (payload or {}).get("hex_samples", [])
    if not hex_samples:
        raise HTTPException(400, "hex_samples required")
    try:
        from domains.protocols.binary_protocol import BinaryProtocolRE
        samples = [bytes.fromhex(h.replace(" ", "")) for h in hex_samples]
        engine = BinaryProtocolRE()
        proto = engine.analyze(samples)
        return _ok({
            "description": proto.description,
            "entropy": proto.entropy_bits_per_byte,
            "confidence": proto.confidence,
            "is_encrypted": proto.is_encrypted,
            "has_magic": proto.has_magic,
            "has_checksum": proto.has_checksum,
            "has_sequence": proto.has_sequence,
            "has_length_field": proto.has_length_field,
            "header_size": proto.header_size,
            "fields": [
                {
                    "offset": f.offset,
                    "size": f.size,
                    "type": f.field_type,
                    "description": f.description,
                    "examples": f.example_values[:4],
                    "entropy": f.entropy,
                    "constant": f.is_constant,
                }
                for f in proto.fields
            ],
            "security_issues": proto.security_issues,
        })
    except Exception as e:
        return _err(str(e))


@router.post("/protocols/dissector")
async def generate_dissector(payload: dict):
    """Generate Wireshark Lua dissector from binary samples."""
    hex_samples = (payload or {}).get("hex_samples", [])
    protocol_name = (payload or {}).get("protocol_name", "unknown")
    port = int((payload or {}).get("port", 9999))
    transport = (payload or {}).get("transport", "tcp")
    try:
        from domains.protocols.binary_protocol import BinaryProtocolRE
        from domains.protocols.dissector_gen import DissectorGenerator
        samples = [bytes.fromhex(h.replace(" ", "")) for h in hex_samples]
        engine = BinaryProtocolRE()
        proto = engine.analyze(samples)
        gen = DissectorGenerator()
        lua = gen.generate(proto, protocol_name, port, transport)
        return _ok({"lua": lua, "filename": f"{protocol_name.lower().replace(' ','_')}.lua"})
    except Exception as e:
        return _err(str(e))


# ── Hardware / Firmware ───────────────────────────────────────────────────────

@router.post("/firmware/analyze")
async def firmware_analyze(file: UploadFile = File(...)):
    """Upload and analyze a firmware binary."""
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        from domains.hardware.firmware_analyzer import FirmwareAnalyzer
        analyzer = FirmwareAnalyzer()
        report = await analyzer.analyze(tmp_path)
        os.unlink(tmp_path)

        if report.error:
            return _err(report.error)

        # Entropy histogram (downsample for JSON)
        entropy_hist = [
            {"offset": s.offset, "entropy": round(s.entropy, 3), "type": s.segment_type}
            for s in report.entropy_segments[::max(1, len(report.entropy_segments) // 200)]
        ]

        return _ok({
            "file": file.filename,
            "size": report.file_size,
            "md5": report.md5,
            "sha256": report.sha256,
            "architecture": {
                "arch": report.architecture.arch,
                "endianness": report.architecture.endianness,
                "confidence": report.architecture.confidence,
                "evidence": report.architecture.evidence,
            },
            "filesystems": [
                {"offset": fs.offset, "type": fs.fs_type, "description": fs.description}
                for fs in report.filesystems[:10]
            ],
            "entropy_histogram": entropy_hist,
            "security_findings": report.security_findings[:20],
            "interesting_strings": report.interesting_strings[:50],
            "entropy_plot_url": (
                "/science-output/" + os.path.basename(report.entropy_plot_path)
                if report.entropy_plot_path and os.path.exists(report.entropy_plot_path)
                else None
            ),
        })
    except Exception as e:
        return _err(str(e))


# ── Physics ───────────────────────────────────────────────────────────────────

@router.post("/physics/compute")
async def physics_compute(payload: dict):
    """Symbolic/numeric physics computation."""
    expression = (payload or {}).get("expression", "")
    variables = (payload or {}).get("variables", {})
    output_fmt = (payload or {}).get("output", "symbolic")
    if not expression:
        raise HTTPException(400, "expression required")
    try:
        from domains.physics.engine import PhysicsEngine
        engine = PhysicsEngine()
        result = await engine.compute(expression=expression, variables=variables, output=output_fmt)
        from dataclasses import asdict
        return _ok(asdict(result))
    except Exception as e:
        return _err(str(e))


@router.post("/physics/simulate")
async def physics_simulate(payload: dict):
    """Simulate a physical system ODE."""
    system = (payload or {}).get("system", "pendulum")
    params = (payload or {}).get("params", {})
    t_span = tuple((payload or {}).get("t_span", [0, 10]))
    try:
        from domains.physics.engine import PhysicsEngine
        engine = PhysicsEngine()
        result = await engine.simulate(system=system, params=params, t_span=t_span)
        from dataclasses import asdict
        return _ok(asdict(result))
    except Exception as e:
        return _err(str(e))


@router.get("/physics/constants")
async def physics_constants():
    """List all known physical constants."""
    try:
        from domains.physics.constants import CONSTANTS
        return _ok({
            "count": len(CONSTANTS),
            "constants": [
                {"name": k, "value": v["value"], "unit": v["unit"], "description": v.get("description", "")}
                for k, v in CONSTANTS.items()
            ],
        })
    except Exception as e:
        return _err(str(e))


@router.get("/physics/constant/{name}")
async def physics_constant(name: str):
    """Get a specific physical constant."""
    try:
        import math
        from dataclasses import asdict
        from domains.physics.engine import PhysicsEngine
        engine = PhysicsEngine()
        result = engine.get_constant(name)
        # get_constant returns a PhysicsConstant dataclass; the not-found sentinel
        # carries a NaN value. Serialize to a dict for the JSON response.
        if isinstance(result.value, float) and math.isnan(result.value):
            return _err(f"unknown constant: {name}", 404)
        return _ok(asdict(result))
    except Exception as e:
        return _err(str(e))


# ── Robotics ──────────────────────────────────────────────────────────────────

@router.post("/robotics/fk")
async def robot_fk(payload: dict):
    """Forward kinematics for UR5 or PUMA560."""
    joint_angles = (payload or {}).get("joint_angles", [])
    model = (payload or {}).get("model", "ur5").lower()
    if not joint_angles:
        raise HTTPException(400, "joint_angles required")
    try:
        from domains.robotics.kinematics import make_ur5, make_puma560
        arm = make_ur5() if model == "ur5" else make_puma560()
        result = arm.forward_kinematics([float(a) for a in joint_angles])
        if result.error:
            return _err(result.error)
        x, y, z = result.end_effector_position
        return _ok({
            "model": model,
            "joint_angles_rad": result.joint_angles_rad,
            "position": {"x": x, "y": y, "z": z},
            "rotation": result.end_effector_rotation,
            "transform": result.transform_matrix,
            "jacobian": result.jacobian,
            "manipulability": result.manipulability,
            "singularity": result.singularity_detected,
        })
    except Exception as e:
        return _err(str(e))


@router.post("/robotics/ik")
async def robot_ik(payload: dict):
    """Inverse kinematics for UR5 or PUMA560."""
    target = (payload or {}).get("target_pos", [0, 0, 0])
    model = (payload or {}).get("model", "ur5").lower()
    initial = (payload or {}).get("initial_angles")
    try:
        import math
        from domains.robotics.kinematics import make_ur5, make_puma560
        arm = make_ur5() if model == "ur5" else make_puma560()
        result = arm.inverse_kinematics(
            tuple(float(c) for c in target),
            initial_angles=[float(a) for a in initial] if initial else None,
        )
        if result.error:
            return _err(result.error)
        x, y, z = result.end_effector_position
        error = ((x - target[0])**2 + (y - target[1])**2 + (z - target[2])**2) ** 0.5
        return _ok({
            "model": model,
            "target": {"x": target[0], "y": target[1], "z": target[2]},
            "achieved": {"x": x, "y": y, "z": z},
            "error_mm": error * 1000,
            "joint_angles_rad": result.joint_angles_rad,
            "joint_angles_deg": [math.degrees(q) for q in result.joint_angles_rad],
            "manipulability": result.manipulability,
            "singularity": result.singularity_detected,
        })
    except Exception as e:
        return _err(str(e))


@router.post("/robotics/trajectory")
async def robot_trajectory(payload: dict):
    """Generate cubic polynomial trajectory."""
    q_start = (payload or {}).get("q_start", [])
    q_end = (payload or {}).get("q_end", [])
    duration = float((payload or {}).get("duration", 3.0))
    n_points = int((payload or {}).get("n_points", 50))
    if not q_start or not q_end:
        raise HTTPException(400, "q_start and q_end required")
    try:
        from domains.robotics.path_planner import PathPlanner
        planner = PathPlanner()
        result = planner.cubic_trajectory(
            [float(a) for a in q_start],
            [float(a) for a in q_end],
            duration=duration,
            n_points=n_points,
        )
        if result.error:
            return _err(result.error)
        return _ok({
            "duration_s": result.total_duration,
            "n_points": len(result.waypoints),
            "max_velocities_rad_s": result.max_velocities,
            "waypoints": [
                {"t": w.time, "q": w.joint_angles, "dq": w.velocity}
                for w in result.waypoints[::max(1, len(result.waypoints)//20)]  # downsample for JSON
            ],
        })
    except Exception as e:
        return _err(str(e))


# ── Sandbox ───────────────────────────────────────────────────────────────────

@router.get("/sandbox/status")
async def sandbox_status():
    """Check Docker sandbox availability."""
    try:
        from core.sandbox_executor import SandboxExecutor
        executor = SandboxExecutor()
        docker_ok = await executor._check_docker()
        return _ok({
            "docker_available": docker_ok,
            "isolation": "docker" if docker_ok else "subprocess",
            "languages": ["python", "bash", "node"],
            "max_timeout_s": 120,
            "security": "--network none --cap-drop ALL --read-only" if docker_ok else "local subprocess",
        })
    except Exception as e:
        return _err(str(e))


@router.post("/sandbox/execute")
async def sandbox_execute(payload: dict):
    """Execute code in isolated sandbox."""
    code = (payload or {}).get("code", "").strip()
    language = (payload or {}).get("language", "python")
    timeout = min(int((payload or {}).get("timeout", 30)), 120)
    if not code:
        raise HTTPException(400, "code required")
    try:
        from core.sandbox_executor import SandboxExecutor
        executor = SandboxExecutor()
        result = await executor.execute(code=code, language=language, timeout=timeout)
        return _ok({
            "success": result.success,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time_ms": result.execution_time_ms,
            "timed_out": result.timed_out,
            "runtime": result.language,
            "isolated": result.was_isolated,
            "error": result.error,
        })
    except Exception as e:
        return _err(str(e))
