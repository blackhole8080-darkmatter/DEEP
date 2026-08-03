"""Catalog of the public cybersecurity APIs DEEP speaks.

This is the registry behind DEEP's OSINT surface: one declarative entry per
upstream service, describing what it answers, which indicator types it accepts,
and whether it needs a credential. The investigator (``osint_investigator.py``)
reads this catalog to decide who to ask about a given indicator, and the
``/api/intel/sources`` endpoint renders it so the operator can see exactly
what is live, what is gated behind a key they haven't set, and where the data
in a dossier came from.

The bar for inclusion here is deliberately high:

* **Keyless first.** Every source marked ``auth=NONE`` works on a fresh clone
  with no signup. That is what makes DEEP useful in the first five minutes.
  Key-gated sources are catalogued too, but they self-report as ``configured:
  false`` rather than failing at call time.
* **Attributable.** Each entry records its documentation URL and terms, so a
  finding in a dossier can always be traced back to who said it.
* **Honest.** A source appears here only if DEEP actually calls it. This file
  is not a wishlist.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class Auth(str, Enum):
    """How a source authenticates."""

    NONE = "none"
    """No credential at all — works out of the box."""

    KEY = "key"
    """Requires an API key, supplied via the environment variable in ``env_var``."""


class Indicator(str, Enum):
    """The kinds of things DEEP can pivot on."""

    IP = "ip"
    DOMAIN = "domain"
    CVE = "cve"
    HASH = "hash"
    ASN = "asn"
    PACKAGE = "package"
    MAC = "mac"


class Category(str, Enum):
    VULNERABILITY = "vulnerability"
    REPUTATION = "reputation"
    EXPOSURE = "exposure"
    NETWORK = "network"
    CERTIFICATE = "certificate"
    BREACH = "breach"
    FEED = "feed"
    GEO = "geo"


@dataclass(frozen=True, slots=True)
class PublicAPI:
    """One upstream intelligence source."""

    id: str
    name: str
    category: Category
    auth: Auth
    base_url: str
    docs_url: str
    description: str
    indicators: tuple[Indicator, ...] = ()
    env_var: Optional[str] = None
    rate_limit: str = "unspecified"
    ttl_seconds: int = 900

    @property
    def configured(self) -> bool:
        """True when this source can actually be called right now."""
        if self.auth is Auth.NONE:
            return True
        return bool(self.env_var and os.environ.get(self.env_var))

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "auth": self.auth.value,
            "base_url": self.base_url,
            "docs_url": self.docs_url,
            "description": self.description,
            "indicators": [i.value for i in self.indicators],
            "env_var": self.env_var,
            "rate_limit": self.rate_limit,
            "configured": self.configured,
        }


# ═══════════════════════════════════════════════════════════════════════════
# The catalog
# ═══════════════════════════════════════════════════════════════════════════

CATALOG: tuple[PublicAPI, ...] = (
    # ── Vulnerability intelligence ──────────────────────────────────────────
    PublicAPI(
        id="cisa_kev",
        name="CISA Known Exploited Vulnerabilities",
        category=Category.VULNERABILITY,
        auth=Auth.NONE,
        base_url="https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
        docs_url="https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
        description=(
            "The authoritative list of CVEs with confirmed in-the-wild exploitation. "
            "Presence here outranks any CVSS score for prioritisation."
        ),
        indicators=(Indicator.CVE,),
        rate_limit="none published; DEEP caches for 6h",
        ttl_seconds=6 * 3600,
    ),
    PublicAPI(
        id="epss",
        name="FIRST EPSS",
        category=Category.VULNERABILITY,
        auth=Auth.NONE,
        base_url="https://api.first.org/data/v1/epss",
        docs_url="https://www.first.org/epss/api_access",
        description=(
            "Exploit Prediction Scoring System: probability a CVE will be exploited "
            "in the next 30 days. Answers 'is this worth paging someone for' in a "
            "way CVSS severity alone cannot."
        ),
        indicators=(Indicator.CVE,),
        rate_limit="unauthenticated, fair-use",
        ttl_seconds=6 * 3600,
    ),
    PublicAPI(
        id="nvd",
        name="NIST NVD 2.0",
        category=Category.VULNERABILITY,
        auth=Auth.NONE,
        base_url="https://services.nvd.nist.gov/rest/json/cves/2.0",
        docs_url="https://nvd.nist.gov/developers/vulnerabilities",
        description="Canonical CVE records: CVSS vectors, CWE mapping, CPE match, references.",
        indicators=(Indicator.CVE,),
        rate_limit="5 req / 30s without a key, 50 with one",
        ttl_seconds=6 * 3600,
    ),
    PublicAPI(
        id="osv",
        name="OSV.dev",
        category=Category.VULNERABILITY,
        auth=Auth.NONE,
        base_url="https://api.osv.dev/v1",
        docs_url="https://google.github.io/osv.dev/api/",
        description=(
            "Open Source Vulnerabilities: package-level advisories across PyPI, npm, "
            "Go, crates.io, Maven and more, with precise affected-version ranges."
        ),
        indicators=(Indicator.PACKAGE, Indicator.CVE),
        rate_limit="unauthenticated, fair-use",
        ttl_seconds=3600,
    ),
    PublicAPI(
        id="ghsa",
        name="GitHub Security Advisories",
        category=Category.VULNERABILITY,
        auth=Auth.NONE,
        base_url="https://api.github.com/advisories",
        docs_url="https://docs.github.com/rest/security-advisories/global-advisories",
        description="Reviewed advisories for ecosystem packages, with severity and patched versions.",
        indicators=(Indicator.PACKAGE, Indicator.CVE),
        rate_limit="60 req/h unauthenticated",
        ttl_seconds=3600,
    ),
    # ── Exposure ────────────────────────────────────────────────────────────
    PublicAPI(
        id="shodan_internetdb",
        name="Shodan InternetDB",
        category=Category.EXPOSURE,
        auth=Auth.NONE,
        base_url="https://internetdb.shodan.io",
        docs_url="https://internetdb.shodan.io/",
        description=(
            "Shodan's keyless endpoint: open ports, hostnames, detected CPEs and known "
            "CVEs for an IP. Gives DEEP real internet-exposure data without a paid key."
        ),
        indicators=(Indicator.IP,),
        rate_limit="fair-use, no key",
        ttl_seconds=3600,
    ),
    PublicAPI(
        id="shodan",
        name="Shodan (full API)",
        category=Category.EXPOSURE,
        auth=Auth.KEY,
        env_var="SHODAN_API_KEY",
        base_url="https://api.shodan.io",
        docs_url="https://developer.shodan.io/api",
        description="Full host records: banners, service fingerprints, historical scans.",
        indicators=(Indicator.IP,),
        rate_limit="per plan",
    ),
    # ── Reputation ──────────────────────────────────────────────────────────
    PublicAPI(
        id="sans_isc",
        name="SANS Internet Storm Center",
        category=Category.REPUTATION,
        auth=Auth.NONE,
        base_url="https://isc.sans.edu/api",
        docs_url="https://isc.sans.edu/api/",
        description=(
            "Aggregated attack telemetry from a global sensor network: per-IP report "
            "counts and the current top attacking sources."
        ),
        indicators=(Indicator.IP,),
        rate_limit="fair-use",
        ttl_seconds=1800,
    ),
    PublicAPI(
        id="tor_exits",
        name="Tor Project exit list",
        category=Category.REPUTATION,
        auth=Auth.NONE,
        base_url="https://check.torproject.org/torbulkexitlist",
        docs_url="https://check.torproject.org/",
        description="Authoritative list of Tor exit-node IPs, for attributing anonymised traffic.",
        indicators=(Indicator.IP,),
        rate_limit="fair-use",
        ttl_seconds=3600,
    ),
    PublicAPI(
        id="feodo",
        name="abuse.ch Feodo Tracker",
        category=Category.REPUTATION,
        auth=Auth.NONE,
        base_url="https://feodotracker.abuse.ch/downloads/ipblocklist.json",
        docs_url="https://feodotracker.abuse.ch/",
        description="Active botnet command-and-control servers (Emotet, Dridex, TrickBot, QakBot).",
        indicators=(Indicator.IP,),
        rate_limit="fair-use",
        ttl_seconds=3600,
    ),
    PublicAPI(
        id="abuseipdb",
        name="AbuseIPDB",
        category=Category.REPUTATION,
        auth=Auth.KEY,
        env_var="ABUSEIPDB_API_KEY",
        base_url="https://api.abuseipdb.com/api/v2",
        docs_url="https://docs.abuseipdb.com/",
        description="Crowd-sourced IP abuse reports with a 0-100 confidence score.",
        indicators=(Indicator.IP,),
        rate_limit="1000 checks/day free",
    ),
    PublicAPI(
        id="virustotal",
        name="VirusTotal",
        category=Category.REPUTATION,
        auth=Auth.KEY,
        env_var="VIRUSTOTAL_API_KEY",
        base_url="https://www.virustotal.com/api/v3",
        docs_url="https://docs.virustotal.com/reference/overview",
        description="Multi-engine reputation for files, URLs, IPs and domains.",
        indicators=(Indicator.IP, Indicator.DOMAIN, Indicator.HASH),
        rate_limit="4 req/min free",
    ),
    PublicAPI(
        id="otx",
        name="AlienVault OTX",
        category=Category.REPUTATION,
        auth=Auth.KEY,
        env_var="OTX_API_KEY",
        base_url="https://otx.alienvault.com/api/v1",
        docs_url="https://otx.alienvault.com/api",
        description="Community threat-intel pulses linking indicators to campaigns.",
        indicators=(Indicator.IP, Indicator.DOMAIN, Indicator.HASH),
        rate_limit="fair-use",
    ),
    # ── Network / registry ──────────────────────────────────────────────────
    PublicAPI(
        id="rdap",
        name="RDAP (regional registries)",
        category=Category.NETWORK,
        auth=Auth.NONE,
        base_url="https://rdap.org",
        docs_url="https://about.rdap.org/",
        description=(
            "The successor to WHOIS: structured registration data for IPs, ASNs and "
            "domains, auto-routed to the responsible registry."
        ),
        indicators=(Indicator.IP, Indicator.DOMAIN, Indicator.ASN),
        rate_limit="per-registry, fair-use",
        ttl_seconds=6 * 3600,
    ),
    PublicAPI(
        id="ripestat",
        name="RIPEstat",
        category=Category.NETWORK,
        auth=Auth.NONE,
        base_url="https://stat.ripe.net/data",
        docs_url="https://stat.ripe.net/docs/data_api",
        description=(
            "Routing-layer truth: announcing ASN, covering prefix, abuse contact and "
            "BGP visibility for any address."
        ),
        indicators=(Indicator.IP, Indicator.ASN),
        rate_limit="fair-use",
        ttl_seconds=3600,
    ),
    PublicAPI(
        id="dns_doh",
        name="Cloudflare DNS-over-HTTPS",
        category=Category.NETWORK,
        auth=Auth.NONE,
        base_url="https://cloudflare-dns.com/dns-query",
        docs_url="https://developers.cloudflare.com/1.1.1.1/encryption/dns-over-https/",
        description=(
            "Encrypted resolver used for A/AAAA/MX/TXT/NS lookups, so DEEP's own recon "
            "isn't visible to the local resolver."
        ),
        indicators=(Indicator.DOMAIN,),
        rate_limit="fair-use",
        ttl_seconds=600,
    ),
    PublicAPI(
        id="macvendors",
        name="macvendors.com",
        category=Category.NETWORK,
        auth=Auth.NONE,
        base_url="https://api.macvendors.com",
        docs_url="https://macvendors.com/api",
        description="OUI-to-manufacturer resolution for MAC addresses seen on the local network.",
        indicators=(Indicator.MAC,),
        rate_limit="1 req/s unauthenticated",
        ttl_seconds=24 * 3600,
    ),
    # ── Certificates ────────────────────────────────────────────────────────
    PublicAPI(
        id="crtsh",
        name="crt.sh certificate transparency",
        category=Category.CERTIFICATE,
        auth=Auth.NONE,
        base_url="https://crt.sh",
        docs_url="https://crt.sh/",
        description=(
            "Every certificate ever issued for a domain, which in practice enumerates "
            "subdomains — including internal-looking ones nobody meant to publish."
        ),
        indicators=(Indicator.DOMAIN,),
        rate_limit="fair-use, slow under load",
        ttl_seconds=3600,
    ),
    # ── Breach ──────────────────────────────────────────────────────────────
    PublicAPI(
        id="hibp_breaches",
        name="Have I Been Pwned (breach catalog)",
        category=Category.BREACH,
        auth=Auth.NONE,
        base_url="https://haveibeenpwned.com/api/v3/breaches",
        docs_url="https://haveibeenpwned.com/API/v3",
        description=(
            "The public breach catalog — which domains were breached, when, how many "
            "accounts and what classes of data. The per-account endpoint needs a key; "
            "this one does not."
        ),
        indicators=(Indicator.DOMAIN,),
        rate_limit="fair-use",
        ttl_seconds=12 * 3600,
    ),
    # ── Geo ─────────────────────────────────────────────────────────────────
    PublicAPI(
        id="ipapi_co",
        name="ipapi.co",
        category=Category.GEO,
        auth=Auth.NONE,
        base_url="https://ipapi.co",
        docs_url="https://ipapi.co/api/",
        description="HTTPS geolocation and ASN/org attribution for an IP address.",
        indicators=(Indicator.IP,),
        rate_limit="1000/day unauthenticated",
        ttl_seconds=6 * 3600,
    ),
)


_BY_ID: Dict[str, PublicAPI] = {api.id: api for api in CATALOG}


def get(api_id: str) -> Optional[PublicAPI]:
    return _BY_ID.get(api_id)


def for_indicator(kind: Indicator, *, keyless_only: bool = False) -> List[PublicAPI]:
    """Sources that can answer questions about ``kind``."""
    out = [api for api in CATALOG if kind in api.indicators]
    if keyless_only:
        out = [api for api in out if api.auth is Auth.NONE]
    return out


def summary() -> Dict[str, object]:
    """Catalog overview, including which key-gated sources are actually set up."""
    keyless = [a for a in CATALOG if a.auth is Auth.NONE]
    gated = [a for a in CATALOG if a.auth is Auth.KEY]
    active_gated = [a for a in gated if a.configured]
    by_category: Dict[str, int] = {}
    for api in CATALOG:
        by_category[api.category.value] = by_category.get(api.category.value, 0) + 1
    return {
        "total": len(CATALOG),
        "keyless": len(keyless),
        "key_required": len(gated),
        "key_configured": len(active_gated),
        "available_now": len(keyless) + len(active_gated),
        "by_category": by_category,
        "sources": [a.to_dict() for a in CATALOG],
    }
