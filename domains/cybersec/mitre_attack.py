"""
DEEP — MITRE ATT&CK Mapper
Loads ATT&CK STIX bundle or falls back to built-in curated technique index.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class Technique:
    id: str                     # T1190
    name: str
    description: str
    tactics: List[str]          # initial-access, execution, etc.
    platforms: List[str]
    detection: str = ""
    mitigation: str = ""
    url: str = ""


@dataclass
class GroupProfile:
    id: str                     # G0001
    name: str
    aliases: List[str]
    description: str
    techniques: List[str]       # technique IDs used by this group
    targets: List[str]          # targeted sectors
    origin_country: str = ""


@dataclass
class KillChain:
    cve_id: str
    vulnerability_class: str
    likely_techniques: List[Technique] = field(default_factory=list)
    kill_chain_phase: str = ""
    narrative: str = ""


# ── Curated built-in technique index ─────────────────────────────────────────
# A representative sample — full ATT&CK has 600+ techniques.
# For production, download the full STIX bundle from attack.mitre.org.

_BUILTIN_TECHNIQUES: List[Dict[str, Any]] = [
    {"id": "T1190", "name": "Exploit Public-Facing Application",
     "tactics": ["initial-access"], "platforms": ["Linux", "Windows", "Network"],
     "description": "Adversaries exploit vulnerabilities in internet-facing software to gain initial access.",
     "detection": "Monitor web server logs for unusual requests. Alert on CVE IDs matching deployed software.",
     "mitigation": "Apply patches. Use WAF. Segment internet-facing systems."},

    {"id": "T1059", "name": "Command and Scripting Interpreter",
     "tactics": ["execution"], "platforms": ["Linux", "Windows", "macOS"],
     "description": "Adversaries abuse command interpreters (bash, PowerShell, Python) to execute malicious commands.",
     "detection": "Monitor process creation events. Unusual parent-child relationships.",
     "mitigation": "Disable unnecessary interpreters. Application whitelisting."},

    {"id": "T1055", "name": "Process Injection",
     "tactics": ["defense-evasion", "privilege-escalation"], "platforms": ["Windows", "Linux", "macOS"],
     "description": "Injecting code into processes to evade detection and run in the context of a legitimate process.",
     "detection": "Monitor for CreateRemoteThread, WriteProcessMemory API calls.",
     "mitigation": "Privileged access management. Endpoint detection tools."},

    {"id": "T1003", "name": "OS Credential Dumping",
     "tactics": ["credential-access"], "platforms": ["Windows", "Linux", "macOS"],
     "description": "Dumping credentials from operating system and software to enable lateral movement.",
     "detection": "Monitor for lsass.exe access, suspicious registry reads (SAM/SECURITY).",
     "mitigation": "Credential Guard. Protected Users group. Disable legacy auth."},

    {"id": "T1021", "name": "Remote Services",
     "tactics": ["lateral-movement"], "platforms": ["Windows", "Linux", "macOS"],
     "description": "Using legitimate remote access tools (RDP, SSH, SMB) for lateral movement.",
     "detection": "Monitor for unusual authentication events, remote service usage.",
     "mitigation": "Network segmentation. MFA on remote services. Disable unused services."},

    {"id": "T1071", "name": "Application Layer Protocol",
     "tactics": ["command-and-control"], "platforms": ["Linux", "Windows", "macOS"],
     "description": "Using standard application layer protocols (HTTP, DNS, SMTP) for C2 communication.",
     "detection": "Traffic analysis for beaconing behavior. DNS query anomaly detection.",
     "mitigation": "Network filtering. Proxy inspection. DNS security (RPZ)."},

    {"id": "T1486", "name": "Data Encrypted for Impact",
     "tactics": ["impact"], "platforms": ["Linux", "Windows", "macOS"],
     "description": "Encrypting data to make it inaccessible (ransomware).",
     "detection": "Unusual file I/O activity. Mass file renaming/extension changes.",
     "mitigation": "Immutable backups. File integrity monitoring. Endpoint detection."},

    {"id": "T1046", "name": "Network Service Scanning",
     "tactics": ["discovery"], "platforms": ["Linux", "Windows", "macOS", "Network"],
     "description": "Port scanning and service enumeration to discover open ports and running services.",
     "detection": "IDS rules for port scan patterns. Honeypots.",
     "mitigation": "Network segmentation. Firewall rules. Host-based IDS."},

    {"id": "T1595", "name": "Active Scanning",
     "tactics": ["reconnaissance"], "platforms": ["PRE"],
     "description": "Actively scanning victim infrastructure (port scans, vulnerability scans) before attack.",
     "detection": "Monitor for scanning activity from external IPs.",
     "mitigation": "Network perimeter monitoring. Minimize internet-facing attack surface."},

    {"id": "T1562", "name": "Impair Defenses",
     "tactics": ["defense-evasion"], "platforms": ["Linux", "Windows", "macOS"],
     "description": "Disabling security tools, logging, or firewall rules to evade detection.",
     "detection": "Alert on security tool process termination. Audit policy changes.",
     "mitigation": "Protect security tools from user-level modification. Centralized logging."},

    {"id": "T1078", "name": "Valid Accounts",
     "tactics": ["initial-access", "persistence", "privilege-escalation", "defense-evasion"],
     "platforms": ["Linux", "Windows", "macOS", "Cloud"],
     "description": "Using legitimate credentials to blend in with normal traffic.",
     "detection": "Behavioral analytics on account usage. Impossible travel detection.",
     "mitigation": "MFA. Least privilege. Regular credential auditing."},

    {"id": "T1110", "name": "Brute Force",
     "tactics": ["credential-access"], "platforms": ["Linux", "Windows", "macOS", "Cloud"],
     "description": "Attempting to gain access by systematically guessing credentials.",
     "detection": "Authentication failure rate monitoring. Account lockout events.",
     "mitigation": "Account lockout policies. MFA. Strong password requirements."},
]

# CWE → ATT&CK TTP mapping (simplified)
_CWE_TO_TTPPS: Dict[str, List[str]] = {
    "CWE-78":  ["T1059"],   # OS Command Injection → Script interpreter
    "CWE-89":  ["T1190"],   # SQL Injection → Exploit public-facing app
    "CWE-22":  ["T1190"],   # Path Traversal
    "CWE-79":  ["T1059"],   # XSS → Script interpreter
    "CWE-119": ["T1055"],   # Buffer Overflow → Process injection
    "CWE-416": ["T1055"],   # Use-after-free
    "CWE-287": ["T1078"],   # Authentication bypass → Valid accounts
    "CWE-306": ["T1078"],   # Missing auth → Valid accounts
    "CWE-798": ["T1003"],   # Hardcoded creds → Credential dumping
    "CWE-502": ["T1059"],   # Deserialization
    "CWE-611": ["T1190"],   # XXE
}

# Vulnerability class keyword → technique mapping
_VULN_CLASS_MAP: Dict[str, List[str]] = {
    "remote code execution": ["T1190", "T1059"],
    "rce": ["T1190", "T1059"],
    "privilege escalation": ["T1055", "T1078"],
    "auth bypass": ["T1078"],
    "sql injection": ["T1190"],
    "command injection": ["T1059"],
    "buffer overflow": ["T1055"],
    "information disclosure": ["T1003"],
    "denial of service": ["T1486"],
    "man-in-the-middle": ["T1071"],
    "credential": ["T1003", "T1110"],
}


class MITREAttack:
    """
    MITRE ATT&CK framework — technique lookup, CVE-to-TTP mapping,
    group profiles, and Navigator layer generation.
    """

    def __init__(self):
        self._techniques: Dict[str, Technique] = {}
        self._groups: Dict[str, GroupProfile] = {}
        self._load_builtin()

    def _load_builtin(self) -> None:
        for t in _BUILTIN_TECHNIQUES:
            tech = Technique(
                id=t["id"],
                name=t["name"],
                description=t.get("description", ""),
                tactics=t.get("tactics", []),
                platforms=t.get("platforms", []),
                detection=t.get("detection", ""),
                mitigation=t.get("mitigation", ""),
                url=f"https://attack.mitre.org/techniques/{t['id']}/",
            )
            self._techniques[t["id"]] = tech

    # ── Public API ─────────────────────────────────────────────────────────────

    def search_ttp(self, query: str) -> List[Technique]:
        """Full-text search across technique names, descriptions, and IDs."""
        q = query.lower()
        results = []
        for tech in self._techniques.values():
            if (q in tech.id.lower()
                    or q in tech.name.lower()
                    or q in tech.description.lower()
                    or any(q in tactic for tactic in tech.tactics)):
                results.append(tech)
        return results

    def get_technique(self, tech_id: str) -> Optional[Technique]:
        """Get a technique by exact ID (e.g. 'T1190')."""
        return self._techniques.get(tech_id.upper())

    def get_kill_chain_for_cve(self, cve_id: str, description: str = "", cwes: Optional[List[str]] = None) -> KillChain:
        """
        Map a CVE to likely ATT&CK techniques based on description and CWE.
        description: CVE description text
        cwes: list of CWE IDs (e.g. ['CWE-78'])
        """
        matched_ids: set = set()

        # CWE mapping
        for cwe in (cwes or []):
            for mapped_id in _CWE_TO_TTPPS.get(cwe, []):
                matched_ids.add(mapped_id)

        # Keyword mapping from description
        desc_lower = description.lower()
        vuln_class = ""
        for kw, tids in _VULN_CLASS_MAP.items():
            if kw in desc_lower:
                matched_ids.update(tids)
                vuln_class = kw

        techniques = [self._techniques[tid] for tid in matched_ids if tid in self._techniques]

        # Determine primary kill-chain phase
        phase = "unknown"
        if techniques:
            phase_priority = ["initial-access", "execution", "privilege-escalation",
                              "credential-access", "lateral-movement", "impact"]
            all_phases = {tactic for t in techniques for tactic in t.tactics}
            for p in phase_priority:
                if p in all_phases:
                    phase = p
                    break

        return KillChain(
            cve_id=cve_id,
            vulnerability_class=vuln_class or "unknown",
            likely_techniques=techniques,
            kill_chain_phase=phase,
            narrative=self._build_narrative(cve_id, techniques, phase),
        )

    def generate_navigator_layer(self, technique_ids: List[str], layer_name: str = "DEEP Analysis") -> Dict[str, Any]:
        """
        Generate an ATT&CK Navigator JSON layer for visualization.
        Can be imported directly at https://mitre-attack.github.io/attack-navigator/
        """
        techniques_out = []
        for tid in technique_ids:
            tech = self._techniques.get(tid)
            color = "#ff6b6b" if tech else "#888"
            techniques_out.append({
                "techniqueID": tid,
                "score": 100,
                "color": color,
                "comment": tech.name if tech else "",
                "enabled": True,
                "metadata": [],
                "links": [],
                "showSubtechniques": False,
            })

        return {
            "name": layer_name,
            "versions": {"attack": "14", "navigator": "4.9", "layer": "4.5"},
            "domain": "enterprise-attack",
            "description": f"DEEP ETIS analysis layer — {layer_name}",
            "filters": {"platforms": ["Linux", "Windows", "macOS", "Network"]},
            "sorting": 3,
            "layout": {"layout": "side", "showID": True, "showName": True},
            "hideDisabled": False,
            "techniques": techniques_out,
            "gradient": {"colors": ["#ff6666", "#0f0"], "minValue": 0, "maxValue": 100},
            "legendItems": [{"label": "Identified technique", "color": "#ff6b6b"}],
            "metadata": [],
            "links": [],
            "showTacticRowBackground": True,
            "tacticRowBackground": "#1a1a2e",
        }

    def get_all_techniques(self) -> List[Technique]:
        return list(self._techniques.values())

    # ── Private ────────────────────────────────────────────────────────────────

    def _build_narrative(self, cve_id: str, techniques: List[Technique], phase: str) -> str:
        if not techniques:
            return f"No ATT&CK techniques mapped for {cve_id}."
        names = ", ".join(f"{t.id} ({t.name})" for t in techniques)
        return (
            f"[{cve_id}] maps to kill-chain phase [{phase.upper()}] via techniques: {names}. "
            f"An adversary exploiting this vulnerability would likely follow the TTPs above. "
            f"Review detection and mitigation guidance per technique."
        )
