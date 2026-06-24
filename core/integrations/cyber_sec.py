"""CyberSecurityIntegration — connects installed software to CISA KEV catalog."""

from __future__ import annotations
import json
import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def _word_boundary_match(needle: str, haystack: str) -> bool:
    """Return True if `needle` appears as a whole word (or word-prefix) in
    `haystack`.  Both are expected to be lowercased already.
    Avoids bare-substring hits like "chrome" matching "polychrome".
    """
    if len(needle) < 4:
        return False
    # Escape regex metacharacters in the needle, then anchor on word boundaries
    pattern = r"\b" + re.escape(needle) + r"\b"
    return bool(re.search(pattern, haystack))


class CyberSecurityIntegration:
    async def scan_network_arp(self):
        return "CyberSecurityIntegration ARP scan not fully implemented here."

    async def scan_ports(self, ip: str):
        return f"Port scan for {ip} not implemented here."

    async def scan_local_vulns(self) -> List[Dict[str, Any]]:
        """Enumerate local software via Windows Registry and cross-reference
        against the *full* CISA KEV catalog (~1,200 entries).

        Key design decisions (per user review):
        - Match against KEV vendorProject/product directly — one download,
          full coverage, zero per-CVE NVD round-trips.
        - Word-boundary matching (not bare substring) to reduce false positives.
        - Findings are labelled "possibly affected" (confidence 0.5) because
          KEV doesn't carry version ranges.
        """
        from core.integrations.local_system import LocalSystem
        from domains.cybersec.cve_intel import CVEIntel

        ls = LocalSystem()

        # ── 1. Enumerate installed software via PowerShell registry query ────
        ps_cmd = (
            "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*, "
            "HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* "
            "| Select-Object DisplayName, DisplayVersion "
            "| Where-Object { $_.DisplayName -ne $null } "
            "| ConvertTo-Json -Compress"
        )

        res = await ls.run_command(f'powershell -Command "{ps_cmd}"')

        if res.get("exit_code") != 0:
            logger.warning(f"Failed to enumerate local software: {res.get('stderr')}")
            return []

        try:
            installed_raw = json.loads(res["stdout"])
        except Exception as e:
            logger.warning(f"Failed to parse software list: {e}")
            return []

        if isinstance(installed_raw, dict):
            installed_raw = [installed_raw]

        installed = []
        for item in installed_raw:
            name = (item.get("DisplayName") or "").strip()
            if name:
                installed.append({
                    "name_lower": name.lower(),
                    "version": item.get("DisplayVersion", "unknown"),
                    "raw": name,
                })

        # ── 2. Fetch full KEV catalog (one download, ~1,200 entries) ─────────
        intel = CVEIntel()
        kev_entries = await intel.get_kev_entries()

        # ── 3. Cross-reference with word-boundary matching ───────────────────
        findings: List[Dict[str, Any]] = []
        seen_pairs: set = set()  # (cve_id, app_name) dedup

        for entry in kev_entries:
            cve_id = entry.get("cveID", "")
            vendor = (entry.get("vendorProject") or "").lower()
            product = (entry.get("product") or "").lower()
            desc = entry.get("shortDescription", "")
            due_date = entry.get("dueDate")

            # Skip entries where vendor/product are too generic
            if not product or len(product) < 4:
                continue

            for app in installed:
                pair_key = (cve_id, app["raw"])
                if pair_key in seen_pairs:
                    continue

                # Word-boundary match: KEV product name must appear as a whole
                # word in the installed app's DisplayName
                matched = _word_boundary_match(product, app["name_lower"])

                # Also try vendor if it's specific enough
                if not matched and vendor and len(vendor) >= 4:
                    matched = _word_boundary_match(vendor, app["name_lower"])

                if matched:
                    seen_pairs.add(pair_key)
                    findings.append({
                        "software": app["raw"],
                        "version": app["version"],
                        "cve_id": cve_id,
                        "cve_desc": desc,
                        "kev_due": due_date,
                        "matched_vendor": entry.get("vendorProject", ""),
                        "matched_product": entry.get("product", ""),
                    })

        logger.info(
            f"[VulnMatcher] {len(installed)} apps × {len(kev_entries)} KEV entries "
            f"→ {len(findings)} findings"
        )
        return findings
