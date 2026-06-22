"""
DEEP — Cross-Domain Synthesizer
Routes complex multi-domain queries to coordinated expert agent swarms
and synthesizes structured responses.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

# Domain classifiers
_PHYSICS_KW = {
    "quantum", "electromagnetic", "hamiltonian", "dispersion", "wavefunction",
    "lagrangian", "derive", "proof", "theorem", "plasma", "entropy", "thermo",
    "maxwell", "schrödinger", "fourier", "eigenvalue", "partition function",
}
_SECURITY_KW = {
    "cve", "exploit", "vulnerability", "hack", "penetration", "payload",
    "shellcode", "injection", "mitre", "attack", "red team", "pentest",
    "reverse shell", "privilege escalation", "lateral movement", "c2",
}
_RF_KW = {
    "frequency", "spectrum", "signal", "modulation", "sdr", "antenna",
    "wavelength", "iq", "fft", "waterfall", "rf", "radio", "wifi", "ssid",
    "bssid", "bluetooth", "ble", "zigbee", "lora", "adsb",
}
_PROTOCOL_KW = {
    "pcap", "packet", "protocol", "dissect", "binary", "reverse", "wireshark",
    "can bus", "modbus", "gatt", "ble", "mqtt", "scada", "ics",
}
_HARDWARE_KW = {
    "firmware", "binwalk", "entropy", "jtag", "uart", "spi", "i2c",
    "microcontroller", "fpga", "schematic", "pcb", "embedded", "flash",
}
_ROBOTICS_KW = {
    "kinematics", "ros", "slam", "lidar", "pid", "trajectory",
    "inverse kinematics", "jacobian", "path planning", "auv", "uav",
    "drone", "manipulator", "robot",
}

_DOMAIN_MAP = {
    "PHYSICS":   _PHYSICS_KW,
    "SECURITY":  _SECURITY_KW,
    "RF":        _RF_KW,
    "PROTOCOL":  _PROTOCOL_KW,
    "HARDWARE":  _HARDWARE_KW,
    "ROBOTICS":  _ROBOTICS_KW,
}


@dataclass
class DomainContext:
    domain: str
    relevance: float    # 0.0 – 1.0
    keywords_matched: List[str]


@dataclass
class SynthesisResult:
    query: str
    active_domains: List[str]
    domain_contexts: List[DomainContext]
    synthesis: str
    is_cross_domain: bool
    confidence: float
    tool_invocations: List[str] = field(default_factory=list)
    error: Optional[str] = None


class CrossDomainSynthesizer:
    """
    Analyzes a query, identifies which expert domains it touches,
    and synthesizes a coordinated multi-domain briefing.
    """

    def classify_query(self, query: str) -> List[DomainContext]:
        """
        Identify which expert domains are relevant to a query.
        Returns: ranked list of DomainContext objects.
        """
        q_lower = query.lower()
        contexts = []

        for domain, keywords in _DOMAIN_MAP.items():
            matched = [kw for kw in keywords if kw in q_lower]
            if matched:
                # Relevance proportional to fraction of domain keywords matched
                relevance = min(1.0, len(matched) / 3)
                contexts.append(DomainContext(
                    domain=domain,
                    relevance=relevance,
                    keywords_matched=matched,
                ))

        # Sort by relevance (highest first)
        contexts.sort(key=lambda c: c.relevance, reverse=True)
        return contexts

    async def synthesize(
        self,
        query: str,
        llm_response_fn=None,
    ) -> SynthesisResult:
        """
        Full synthesis for a cross-domain query.
        llm_response_fn: optional async function(prompt: str) -> str for LLM responses.
        """
        contexts = self.classify_query(query)
        active_domains = [c.domain for c in contexts if c.relevance > 0.2]

        if not active_domains:
            return SynthesisResult(
                query=query,
                active_domains=[],
                domain_contexts=contexts,
                synthesis="[GENERAL] No specific expert domain detected. Routing to general assistant.",
                is_cross_domain=False,
                confidence=0.5,
            )

        is_cross = len(active_domains) > 1
        prefix = "[SYNTHESIS]" if is_cross else f"[{active_domains[0]}]"

        # Build domain activation log
        activation_lines = []
        for ctx in contexts:
            if ctx.relevance > 0.2:
                activation_lines.append(
                    f"  → [{ctx.domain}] relevance={ctx.relevance:.0%} "
                    f"(keywords: {', '.join(ctx.keywords_matched[:4])})"
                )

        domain_log = "\n".join(activation_lines)
        tool_invocations = self._suggest_tool_invocations(active_domains, query)

        synthesis = (
            f"{prefix} Cross-domain query detected across {len(active_domains)} domain(s):\n"
            f"{domain_log}\n\n"
            f"Recommended tool invocations:\n"
            + "\n".join(f"  • {t}" for t in tool_invocations)
        )

        return SynthesisResult(
            query=query,
            active_domains=active_domains,
            domain_contexts=contexts,
            synthesis=synthesis,
            is_cross_domain=is_cross,
            confidence=max(c.relevance for c in contexts),
            tool_invocations=tool_invocations,
        )

    def _suggest_tool_invocations(self, domains: List[str], query: str) -> List[str]:
        """Suggest which tools to invoke for the given domains."""
        suggestions = []
        q_lower = query.lower()

        if "SECURITY" in domains:
            cve_match = re.search(r"CVE-\d{4}-\d+", query, re.IGNORECASE)
            if cve_match:
                suggestions.append(f"cve_lookup('{cve_match.group(0)}')")
                suggestions.append(f"mitre_ttp_search(cve='{cve_match.group(0)}')")
            if any(kw in q_lower for kw in ["domain", "ip", "host"]):
                suggestions.append("osint_passive_recon(target='<TARGET>')")
            if any(kw in q_lower for kw in ["scan", "network", "port"]):
                suggestions.append("scan_target(target='<TARGET>', scope=['<SCOPE>'])")

        if "RF" in domains:
            if any(kw in q_lower for kw in ["wifi", "ssid", "wireless"]):
                suggestions.append("wifi_deep_scan()")
            if any(kw in q_lower for kw in ["bluetooth", "ble"]):
                suggestions.append("bt_enumerate(scan_duration=10)")
            if any(kw in q_lower for kw in ["spectrum", "frequency", "sdr"]):
                suggestions.append("spectrum_analyze(center_freq=<Hz>, bandwidth=<Hz>)")

        if "PROTOCOL" in domains:
            if "pcap" in q_lower or "capture" in q_lower:
                suggestions.append("parse_pcap(file_path='<PATH>')")
            if "binary" in q_lower or "unknown" in q_lower:
                suggestions.append("analyze_binary_protocol(samples=<BYTES_LIST>)")
                suggestions.append("generate_dissector(protocol=<INFERRED>, port=<PORT>)")

        if "HARDWARE" in domains:
            if "firmware" in q_lower or "binary" in q_lower or "flash" in q_lower:
                suggestions.append("analyze_firmware(file_path='<PATH>')")

        if "PHYSICS" in domains:
            suggestions.append("compute_physics(expression='<EXPR>', variables={...})")
            if "simulate" in q_lower or "system" in q_lower:
                suggestions.append("simulate_system(system='<SYSTEM>', params={...})")

        if "ROBOTICS" in domains:
            suggestions.append("forward_kinematics(joint_angles=[...])")
            if "inverse" in q_lower or "reach" in q_lower or "target" in q_lower:
                suggestions.append("inverse_kinematics(target_pos=(x, y, z))")

        return suggestions or ["general_llm_response()"]


# ── Singleton ──────────────────────────────────────────────────────────────────
_synthesizer: Optional[CrossDomainSynthesizer] = None


def get_synthesizer() -> CrossDomainSynthesizer:
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = CrossDomainSynthesizer()
    return _synthesizer
