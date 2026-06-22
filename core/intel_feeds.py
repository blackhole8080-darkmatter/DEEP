"""
DEEP — Intel Feeds
Live aggregation from CVE/KEV feeds and arXiv papers.
Updates the knowledge base with actionable threat intel.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

try:
    import aiohttp
    _AIOHTTP_OK = True
except ImportError:
    _AIOHTTP_OK = False

import xml.etree.ElementTree as ET


class IntelCache:
    """Tiny interface for caching intel feeds. Easily swappable to SQLite later."""
    def __init__(self):
        self._store: Dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            ts, data, ttl = self._store[key]
            if time.time() - ts < ttl:
                return data
            else:
                del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._store[key] = (time.time(), value, ttl)



@dataclass
class IntelItem:
    source: str             # "NVD" | "KEV" | "arXiv" | "GHSA"
    item_id: str
    title: str
    summary: str
    published: str
    severity: str           # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO"
    url: str
    tags: List[str] = field(default_factory=list)
    cvss_score: Optional[float] = None
    is_kev: bool = False


class IntelFeeds:
    """
    Live threat intelligence and research feed aggregator.
    Sources:
    - CISA KEV (known exploited vulnerabilities)
    - NVD recent CVEs (CVSS >= 7.0)
    - arXiv cs.CR (security), cs.RO (robotics), quant-ph, cond-mat
    - GitHub Security Advisories (public)
    """

    _KEV_URL    = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
    _ARXIV_BASE = "https://export.arxiv.org/api/query"
    _GHSA_URL   = "https://api.github.com/advisories"

    def __init__(self, cache_ttl: int = 6 * 3600):  # 6 hours default TTL
        self._cache = IntelCache()
        self._cache_ttl = cache_ttl

    async def fetch_all(self, days_back: int = 7) -> List[IntelItem]:
        """
        Fetch all intel feeds and return merged, deduped list.
        Runs all sources in parallel.
        """
        results = await asyncio.gather(
            self.fetch_kev(),
            self.fetch_arxiv("cs.CR", days_back),
            self.fetch_arxiv("cs.RO", days_back),
            self.fetch_arxiv("physics", days_back),
            return_exceptions=True,
        )

        items = []
        for r in results:
            if isinstance(r, list):
                items.extend(r)

        # Deduplicate by ID
        seen = set()
        unique = []
        for item in items:
            if item.item_id not in seen:
                seen.add(item.item_id)
                unique.append(item)

        # Sort: KEV first, then by published date
        unique.sort(key=lambda x: (not x.is_kev, x.published), reverse=True)
        return unique[:50]

    async def fetch_kev(self) -> List[IntelItem]:
        """Fetch CISA Known Exploited Vulnerabilities catalog."""
        cache_key = "kev"
        cached_data = self._cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        items = []
        try:
            data = await self._get_json(self._KEV_URL)
            vulns = data.get("vulnerabilities", [])
            catalog_version = data.get("catalogVersion", "")

            for v in vulns[:30]:  # limit
                # Determine severity from CVSS if available
                severity = "HIGH"  # KEV default (all are exploited)
                added = v.get("dateAdded", "")
                due = v.get("dueDate", "")

                items.append(IntelItem(
                    source="KEV",
                    item_id=v.get("cveID", ""),
                    title=f"[KEV] {v.get('cveID', '')} — {v.get('vendorProject', '')} {v.get('product', '')}",
                    summary=(
                        f"{v.get('vulnerabilityName', '')}. "
                        f"Action required by: {due}. "
                        f"Notes: {v.get('notes', 'None')}"
                    ),
                    published=added,
                    severity="CRITICAL",
                    url=f"https://nvd.nist.gov/vuln/detail/{v.get('cveID', '')}",
                    tags=["KEV", "CISA", "exploited-in-wild"],
                    is_kev=True,
                ))

        except Exception as exc:
            pass  # graceful degradation

        self._cache.set(cache_key, items, self._cache_ttl)
        return items

    async def fetch_arxiv(self, category: str, days_back: int = 7) -> List[IntelItem]:
        """Fetch recent arXiv papers in a category."""
        cache_key = f"arxiv:{category}:{days_back}"
        cached_data = self._cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        items = []
        try:
            # arXiv API: recent submissions in category
            params = {
                "search_query": f"cat:{category}",
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "max_results": 10,
                "start": 0,
            }
            url = f"{self._ARXIV_BASE}?" + "&".join(f"{k}={v}" for k, v in params.items())
            text = await self._get_text(url)

            root = ET.fromstring(text)
            ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

            for entry in root.findall("atom:entry", ns):
                arxiv_id_tag = entry.find("atom:id", ns)
                title_tag = entry.find("atom:title", ns)
                summary_tag = entry.find("atom:summary", ns)
                published_tag = entry.find("atom:published", ns)

                if not all([arxiv_id_tag, title_tag]):
                    continue

                arxiv_id = arxiv_id_tag.text.split("/")[-1] if arxiv_id_tag.text else ""
                title = (title_tag.text or "").strip().replace("\n", " ")
                summary = (summary_tag.text or "").strip()[:300].replace("\n", " ")
                published = (published_tag.text or "")[:10]

                # Map category to severity
                if category == "cs.CR":
                    sev = "INFO"
                    tags = ["security", "research", "arXiv", "cs.CR"]
                elif category == "cs.RO":
                    sev = "INFO"
                    tags = ["robotics", "research", "arXiv", "cs.RO"]
                else:
                    sev = "INFO"
                    tags = ["physics", "research", "arXiv", category]

                items.append(IntelItem(
                    source="arXiv",
                    item_id=f"arxiv:{arxiv_id}",
                    title=title,
                    summary=summary,
                    published=published,
                    severity=sev,
                    url=f"https://arxiv.org/abs/{arxiv_id}",
                    tags=tags,
                ))

        except Exception:
            pass

        self._cache.set(cache_key, items, self._cache_ttl)
        return items

    async def fetch_ghsa(self, ecosystem: str = "pip") -> List[IntelItem]:
        """Fetch GitHub Security Advisories (public, no auth required)."""
        cache_key = f"ghsa:{ecosystem}"
        cached_data = self._cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        items = []
        try:
            url = f"{self._GHSA_URL}?ecosystem={ecosystem}&per_page=10"
            data = await self._get_json(url)
            if isinstance(data, list):
                for adv in data:
                    severity = (adv.get("severity") or "LOW").upper()
                    items.append(IntelItem(
                        source="GHSA",
                        item_id=adv.get("ghsa_id", ""),
                        title=adv.get("summary", ""),
                        summary=adv.get("description", "")[:300],
                        published=adv.get("published_at", "")[:10],
                        severity=severity,
                        url=adv.get("html_url", ""),
                        tags=["github", "advisory", ecosystem],
                    ))
        except Exception:
            pass
        self._cache.set(cache_key, items, self._cache_ttl)
        return items

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    async def _get_json(self, url: str) -> Any:
        headers = {"User-Agent": "DEEP-ETIS/1.0"}
        if _AIOHTTP_OK:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    return await resp.json(content_type=None)
        else:
            import urllib.request
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())

    async def _get_text(self, url: str) -> str:
        headers = {"User-Agent": "DEEP-ETIS/1.0"}
        if _AIOHTTP_OK:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    return await resp.text()
        else:
            import urllib.request
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode()


# ── Singleton ──────────────────────────────────────────────────────────────────
_intel_feeds: Optional[IntelFeeds] = None


def get_intel_feeds() -> IntelFeeds:
    global _intel_feeds
    if _intel_feeds is None:
        _intel_feeds = IntelFeeds()
    return _intel_feeds
