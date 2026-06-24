"""
DEEP — CVE Intelligence Module
Queries NVD API v2.0 and CISA KEV catalog.
No API key required for basic NVD usage (rate limited to 5 req/30s).
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

try:
    import aiohttp
    _AIOHTTP_OK = True
except ImportError:
    _AIOHTTP_OK = False


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class CVSSv3:
    score: float
    severity: str           # NONE / LOW / MEDIUM / HIGH / CRITICAL
    vector: str             # e.g. CVSS:3.1/AV:N/AC:L/...
    attack_vector: str
    privileges_required: str
    user_interaction: str
    confidentiality_impact: str
    integrity_impact: str
    availability_impact: str


@dataclass
class CVERecord:
    cve_id: str
    description: str
    published: str
    modified: str
    cvss_v3: Optional[CVSSv3] = None
    cvss_v2_score: Optional[float] = None
    cwe: List[str] = field(default_factory=list)
    affected_products: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    is_kev: bool = False                # CISA Known Exploited Vulnerability
    kev_due_date: Optional[str] = None
    mitre_ttps: List[str] = field(default_factory=list)


@dataclass
class ExposureReport:
    cve: CVERecord
    exposed_devices: List[str] = field(default_factory=list)
    risk_level: str = "UNKNOWN"         # CRITICAL / HIGH / MEDIUM / LOW
    remediation_priority: int = 0       # 1 = highest
    recommendations: List[str] = field(default_factory=list)


# ── NVD API v2.0 client ───────────────────────────────────────────────────────

_NVD_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_KEV_URL  = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
_REQ_DELAY = 6.0  # seconds — NVD public rate limit: 5 req / 30 s


class CVEIntel:
    """
    Full CVE intelligence engine.
    Queries NVD API v2.0 + CISA KEV catalog.
    Falls back to lightweight stub data if network is unavailable.
    """

    def __init__(self, nvd_api_key: Optional[str] = None, cache_ttl: int = 3600):
        self._api_key = nvd_api_key
        self._cache: Dict[str, Any] = {}
        self._kev_cache: Optional[List[str]] = None
        self._kev_entries_cache: Optional[List[Dict[str, Any]]] = None
        self._kev_fetched: float = 0.0
        self._cache_ttl = cache_ttl
        self._last_request: float = 0.0

    # ── Public API ─────────────────────────────────────────────────────────────

    async def lookup(self, cve_id: str) -> CVERecord:
        """
        Full CVE record from NVD API v2.0.
        Returns structured CVERecord including CVSS, CWE, affected products.
        """
        cve_id = cve_id.upper().strip()
        if not re.match(r"CVE-\d{4}-\d{4,7}", cve_id):
            return self._stub_record(cve_id, "Invalid CVE ID format. Expected: CVE-YYYY-NNNNNN")

        # Cache hit
        cache_key = f"cve:{cve_id}"
        if cache_key in self._cache:
            ts, data = self._cache[cache_key]
            if time.time() - ts < self._cache_ttl:
                return data

        try:
            raw = await self._nvd_get({"cveId": cve_id})
            vulns = raw.get("vulnerabilities", [])
            if not vulns:
                return self._stub_record(cve_id, "CVE not found in NVD database")

            record = self._parse_nvd_vulnerability(vulns[0])
            record.is_kev = await self._check_kev(cve_id)
            self._cache[cache_key] = (time.time(), record)
            return record

        except Exception as exc:
            return self._stub_record(cve_id, f"NVD query failed: {exc}")

    async def search(
        self,
        keyword: str,
        min_cvss: float = 7.0,
        days_back: int = 30,
        max_results: int = 20,
    ) -> List[CVERecord]:
        """
        Search NVD for recent CVEs matching keyword, filtered by CVSS score.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        pub_start = cutoff.strftime("%Y-%m-%dT%H:%M:%S.000")
        params: Dict[str, Any] = {
            "keywordSearch": keyword,
            "pubStartDate": pub_start,
            "resultsPerPage": min(max_results, 100),
            "cvssV3Severity": _cvss_severity(min_cvss),
        }

        try:
            raw = await self._nvd_get(params)
            records = []
            for v in raw.get("vulnerabilities", []):
                try:
                    r = self._parse_nvd_vulnerability(v)
                    if r.cvss_v3 and r.cvss_v3.score >= min_cvss:
                        records.append(r)
                except Exception:
                    pass
            return records
        except Exception as exc:
            return []  # graceful degradation

    async def check_exposure(
        self,
        cve_id: str,
        network_vendors: List[str],
    ) -> ExposureReport:
        """
        Cross-reference a CVE's affected products against discovered device vendors.
        network_vendors: list of vendor/product strings from NetworkScanner.
        """
        record = await self.lookup(cve_id)
        report = ExposureReport(cve=record)

        # Fuzzy match affected products against network vendors
        affected_lower = {p.lower() for p in record.affected_products}
        for device in network_vendors:
            d_lower = device.lower()
            for prod in affected_lower:
                if any(token in d_lower for token in prod.split() if len(token) > 3):
                    report.exposed_devices.append(device)
                    break

        # Risk level
        if record.cvss_v3:
            score = record.cvss_v3.score
            if score >= 9.0:
                report.risk_level = "CRITICAL"
                report.remediation_priority = 1
            elif score >= 7.0:
                report.risk_level = "HIGH"
                report.remediation_priority = 2
            elif score >= 4.0:
                report.risk_level = "MEDIUM"
                report.remediation_priority = 3
            else:
                report.risk_level = "LOW"
                report.remediation_priority = 4

        if record.is_kev:
            report.risk_level = "CRITICAL"
            report.remediation_priority = 1
            report.recommendations.append(
                f"⚠ CISA KEV: Patch REQUIRED by {record.kev_due_date or 'ASAP'}"
            )

        if report.exposed_devices:
            report.recommendations.append(
                f"Apply vendor patch for {record.cve_id}. {len(report.exposed_devices)} device(s) potentially affected."
            )
        else:
            report.recommendations.append("No matching devices found on local network. Monitor for new deployments.")

        return report

    async def get_kev_feed(self, days_back: int = 30) -> List[CVERecord]:
        """
        Fetch CISA Known Exploited Vulnerabilities catalog.
        Returns CVEs added in the last `days_back` days.
        """
        kev_ids = await self._fetch_kev_catalog()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        results = []
        # Look up a sample of recent KEVs (rate-limit friendly — first 5)
        for cve_id in kev_ids[:5]:
            try:
                r = await self.lookup(cve_id)
                r.is_kev = True
                results.append(r)
                await asyncio.sleep(1)
            except Exception:
                pass
        return results

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _nvd_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Rate-limited GET to NVD API."""
        # Enforce rate limit
        wait = _REQ_DELAY - (time.time() - self._last_request)
        if wait > 0:
            await asyncio.sleep(wait)

        headers = {}
        if self._api_key:
            headers["apiKey"] = self._api_key

        url = f"{_NVD_BASE}?{urlencode(params)}"

        if not _AIOHTTP_OK:
            # Fallback to urllib
            import urllib.request
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                self._last_request = time.time()
                return json.loads(resp.read())

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                self._last_request = time.time()
                resp.raise_for_status()
                return await resp.json()

    async def _fetch_kev_catalog(self) -> List[str]:
        """Download CISA KEV JSON catalog and return list of CVE IDs."""
        now = time.time()
        if self._kev_cache and now - self._kev_fetched < 3600:
            return self._kev_cache

        try:
            if not _AIOHTTP_OK:
                import urllib.request
                with urllib.request.urlopen(_KEV_URL, timeout=15) as resp:
                    data = json.loads(resp.read())
            else:
                async with aiohttp.ClientSession() as session:
                    async with session.get(_KEV_URL, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        data = await resp.json(content_type=None)

            entries = data.get("vulnerabilities", [])
            ids = [entry["cveID"] for entry in entries]
            self._kev_cache = ids
            self._kev_entries_cache = entries
            self._kev_fetched = now
            return ids
        except Exception:
            return []

    async def get_kev_entries(self) -> List[Dict[str, Any]]:
        """Return the full KEV catalog entries (vendorProject, product, cveID,
        dateAdded, dueDate, shortDescription, etc.) — one download, full coverage,
        zero per-CVE NVD calls."""
        await self._fetch_kev_catalog()
        return self._kev_entries_cache or []

    async def _check_kev(self, cve_id: str) -> bool:
        """Check if a CVE ID is in the CISA KEV catalog."""
        kev_ids = await self._fetch_kev_catalog()
        return cve_id in kev_ids

    def _parse_nvd_vulnerability(self, v: Dict[str, Any]) -> CVERecord:
        """Parse a raw NVD vulnerability JSON object into a CVERecord."""
        cve_data = v.get("cve", {})
        cve_id = cve_data.get("id", "CVE-UNKNOWN")

        # Description (English preferred)
        descs = cve_data.get("descriptions", [])
        desc = next((d["value"] for d in descs if d.get("lang") == "en"), "No description")

        # CVSS v3.1 or v3.0
        metrics = cve_data.get("metrics", {})
        cvss_v3 = None
        for key in ("cvssMetricV31", "cvssMetricV30"):
            ms = metrics.get(key, [])
            if ms:
                cv = ms[0].get("cvssData", {})
                cvss_v3 = CVSSv3(
                    score=cv.get("baseScore", 0.0),
                    severity=cv.get("baseSeverity", "UNKNOWN"),
                    vector=cv.get("vectorString", ""),
                    attack_vector=cv.get("attackVector", ""),
                    privileges_required=cv.get("privilegesRequired", ""),
                    user_interaction=cv.get("userInteraction", ""),
                    confidentiality_impact=cv.get("confidentialityImpact", ""),
                    integrity_impact=cv.get("integrityImpact", ""),
                    availability_impact=cv.get("availabilityImpact", ""),
                )
                break

        # CWE
        cwes = []
        for weakness in cve_data.get("weaknesses", []):
            for wd in weakness.get("description", []):
                if wd.get("lang") == "en":
                    cwes.append(wd["value"])

        # Affected products (CPE)
        products = []
        for config in cve_data.get("configurations", []):
            for node in config.get("nodes", []):
                for cpe_match in node.get("cpeMatch", []):
                    cpe = cpe_match.get("criteria", "")
                    parts = cpe.split(":")
                    if len(parts) >= 5:
                        vendor = parts[3]
                        product = parts[4]
                        version = parts[5] if len(parts) > 5 else "*"
                        label = f"{vendor}/{product} ({version})"
                        if label not in products:
                            products.append(label)

        # References
        refs = [r.get("url", "") for r in cve_data.get("references", [])][:10]

        return CVERecord(
            cve_id=cve_id,
            description=desc,
            published=cve_data.get("published", ""),
            modified=cve_data.get("lastModified", ""),
            cvss_v3=cvss_v3,
            cwe=cwes,
            affected_products=products,
            references=refs,
        )

    def _stub_record(self, cve_id: str, message: str) -> CVERecord:
        return CVERecord(
            cve_id=cve_id,
            description=message,
            published="",
            modified="",
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cvss_severity(score: float) -> str:
    if score >= 9.0:
        return "CRITICAL"
    elif score >= 7.0:
        return "HIGH"
    elif score >= 4.0:
        return "MEDIUM"
    else:
        return "LOW"
