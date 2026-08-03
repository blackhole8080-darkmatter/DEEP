"""
DEEP — Intel Feeds
Live aggregation from CVE/KEV feeds and arXiv papers.
Updates the knowledge base with actionable threat intel.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
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

logger = logging.getLogger(__name__)


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

    # No-auth security news feeds — RSS 2.0 or Atom, mixed. (source_name, url)
    _SECURITY_BLOGS = [
        ("Krebs on Security", "https://krebsonsecurity.com/feed/"),
        ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews"),
        ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
        ("SANS ISC", "https://isc.sans.edu/rssfeed_full.xml"),
        ("Cisco Talos", "https://blog.talosintelligence.com/rss/"),
        ("Google Project Zero", "https://googleprojectzero.blogspot.com/feeds/posts/default"),
        ("Microsoft MSRC", "https://msrc.microsoft.com/blog/rss/"),
    ]

    _OTX_PULSES_URL = "https://otx.alienvault.com/api/v1/pulses/subscribed"
    _URLHAUS_URL = "https://urlhaus-api.abuse.ch/v1/urls/recent/limit/25/"
    _THREATFOX_URL = "https://threatfox-api.abuse.ch/api/v1/"

    def __init__(self, cache_ttl: int = 6 * 3600):  # 6 hours default TTL
        self._cache = IntelCache()
        self._cache_ttl = cache_ttl

    async def fetch_all(self, days_back: int = 7) -> List[IntelItem]:
        """
        Fetch all intel feeds and return merged, deduped list.
        Runs all sources in parallel. Only no-auth sources run by default —
        fetch_otx_pulses()/fetch_urlhaus()/fetch_threatfox() are opt-in
        (they no-op to [] without their API keys, see each method).
        """
        results = await asyncio.gather(
            self.fetch_kev(),
            self.fetch_arxiv("cs.CR", days_back),
            self.fetch_ghsa("pip"),
            self.fetch_ghsa("npm"),
            self.fetch_security_blogs(),
            self.fetch_reddit("netsec"),
            self.fetch_reddit("cybersecurity"),
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

                sev = "INFO"
                tags = ["research", "arXiv", category]
                if category == "cs.CR":
                    tags.insert(0, "security")

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

    async def fetch_security_blogs(self) -> List[IntelItem]:
        """Recent posts from major security research/news blogs (no auth).
        Handles both RSS 2.0 (<item>) and Atom (<entry>) formats."""
        cache_key = "security_blogs"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        results = await asyncio.gather(
            *(self._fetch_one_blog(name, url) for name, url in self._SECURITY_BLOGS),
            return_exceptions=True,
        )
        items: List[IntelItem] = []
        for r in results:
            if isinstance(r, list):
                items.extend(r)
        self._cache.set(cache_key, items, self._cache_ttl)
        return items

    async def _fetch_one_blog(self, source_name: str, url: str) -> List[IntelItem]:
        items: List[IntelItem] = []
        try:
            text = await self._get_text(url)
            root = ET.fromstring(text)

            # RSS 2.0: <rss><channel><item>...
            channel = root.find("channel")
            entries = channel.findall("item") if channel is not None else []
            is_atom = False
            if not entries:
                # Atom: <feed xmlns="..."><entry>...
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                entries = root.findall("atom:entry", ns)
                is_atom = True

            for entry in entries[:15]:
                if is_atom:
                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
                    link_el = entry.find("atom:link", ns)
                    link = link_el.get("href", "") if link_el is not None else ""
                    summary = (entry.findtext("atom:summary", default="", namespaces=ns)
                               or entry.findtext("atom:content", default="", namespaces=ns) or "")
                    published = (entry.findtext("atom:published", default="", namespaces=ns)
                                 or entry.findtext("atom:updated", default="", namespaces=ns) or "")
                    item_id = (entry.findtext("atom:id", default="", namespaces=ns) or link or title)
                else:
                    title = (entry.findtext("title") or "").strip()
                    link = (entry.findtext("link") or "").strip()
                    summary = entry.findtext("description") or ""
                    published = entry.findtext("pubDate") or ""
                    item_id = entry.findtext("guid") or link or title

                if not title:
                    continue
                items.append(IntelItem(
                    source=source_name,
                    item_id=str(item_id)[:200],
                    title=title[:300],
                    summary=re.sub(r"<[^>]+>", "", summary or "")[:400].strip(),
                    published=published,
                    severity="INFO",
                    url=link,
                    tags=["security-news", "blog"],
                ))
        except Exception as e:
            logger.debug(f"[intel_feeds] blog fetch failed ({source_name}): {e}")
        return items

    async def fetch_reddit(self, subreddit: str, limit: int = 15) -> List[IntelItem]:
        """Hot posts from a subreddit's public JSON endpoint — no auth, but
        Reddit rate-limits generic User-Agents, hence the descriptive one."""
        cache_key = f"reddit:{subreddit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        items: List[IntelItem] = []
        try:
            url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
            data = await self._get_json(url, user_agent=f"DEEP-ETIS/1.0 (intel feed; r/{subreddit})")
            for child in data.get("data", {}).get("children", []):
                p = child.get("data", {})
                if p.get("stickied"):
                    continue
                created = p.get("created_utc")
                published = (
                    datetime.fromtimestamp(created, tz=timezone.utc).isoformat()
                    if created else ""
                )
                items.append(IntelItem(
                    source=f"r/{subreddit}",
                    item_id=p.get("id", ""),
                    title=(p.get("title") or "")[:300],
                    summary=(p.get("selftext") or "")[:400],
                    published=published,
                    severity="INFO",
                    url=f"https://www.reddit.com{p.get('permalink', '')}",
                    tags=["reddit", subreddit, f"score:{p.get('score', 0)}"],
                ))
        except Exception as e:
            logger.debug(f"[intel_feeds] reddit fetch failed (r/{subreddit}): {e}")

        self._cache.set(cache_key, items, self._cache_ttl)
        return items

    async def fetch_otx_pulses(self, limit: int = 20) -> List[IntelItem]:
        """AlienVault/LevelBlue OTX subscribed pulses (needs OTX_API_KEY).
        Note: only returns pulses from authors you're subscribed to on OTX —
        subscribe to a few active contributors (e.g. AlienVault's own feed)
        at otx.alienvault.com for this to return meaningful volume."""
        api_key = os.environ.get("OTX_API_KEY")
        if not api_key:
            return []

        cache_key = "otx_pulses"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        items: List[IntelItem] = []
        try:
            url = f"{self._OTX_PULSES_URL}?limit={limit}&page=1"
            data = await self._get_json(url, headers={"X-OTX-API-KEY": api_key})
            for pulse in data.get("results", []):
                tags = pulse.get("tags", []) or []
                items.append(IntelItem(
                    source="OTX",
                    item_id=pulse.get("id", ""),
                    title=(pulse.get("name") or "")[:300],
                    summary=(pulse.get("description") or "")[:400],
                    published=pulse.get("created", ""),
                    severity="HIGH",
                    url=f"https://otx.alienvault.com/pulse/{pulse.get('id', '')}",
                    tags=["otx", "threat-intel"] + tags[:8],
                ))
        except Exception as e:
            logger.debug(f"[intel_feeds] OTX fetch failed: {e}")

        self._cache.set(cache_key, items, self._cache_ttl)
        return items

    async def fetch_urlhaus(self, limit: int = 25) -> List[IntelItem]:
        """abuse.ch URLhaus recent malicious URLs (needs ABUSECH_AUTH_KEY,
        free at auth.abuse.ch — same key covers ThreatFox/MalwareBazaar too)."""
        api_key = os.environ.get("ABUSECH_AUTH_KEY")
        if not api_key:
            return []

        cache_key = "urlhaus"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        items: List[IntelItem] = []
        try:
            url = f"https://urlhaus-api.abuse.ch/v1/urls/recent/limit/{limit}/"
            data = await self._get_json(url, headers={"Auth-Key": api_key})
            for u in (data.get("urls") or [])[:limit]:
                items.append(IntelItem(
                    source="URLhaus",
                    item_id=str(u.get("id", "")),
                    title=f"{u.get('threat', 'malware_download')} — {u.get('host', '')}",
                    summary=f"URL status: {u.get('url_status', '?')}. Tags: {', '.join(u.get('tags') or [])}",
                    published=u.get("date_added", ""),
                    severity="HIGH",
                    url=u.get("urlhaus_reference", u.get("url", "")),
                    tags=["urlhaus", "malware"] + (u.get("tags") or [])[:5],
                ))
        except Exception as e:
            logger.debug(f"[intel_feeds] URLhaus fetch failed: {e}")

        self._cache.set(cache_key, items, self._cache_ttl)
        return items

    async def fetch_threatfox(self, days: int = 3) -> List[IntelItem]:
        """abuse.ch ThreatFox recent IOCs (needs ABUSECH_AUTH_KEY)."""
        api_key = os.environ.get("ABUSECH_AUTH_KEY")
        if not api_key:
            return []

        cache_key = f"threatfox:{days}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        items: List[IntelItem] = []
        try:
            data = await self._post_json(
                self._THREATFOX_URL,
                body={"query": "get_iocs", "days": min(max(days, 1), 7)},
                headers={"Auth-Key": api_key},
            )
            for ioc in (data.get("data") or [])[:50]:
                items.append(IntelItem(
                    source="ThreatFox",
                    item_id=str(ioc.get("id", "")),
                    title=f"{ioc.get('ioc_type', 'IOC')}: {ioc.get('ioc', '')[:80]}",
                    summary=f"Malware: {ioc.get('malware_printable', '?')}. "
                            f"Confidence: {ioc.get('confidence_level', '?')}%",
                    published=ioc.get("first_seen", ""),
                    severity="HIGH" if (ioc.get("confidence_level") or 0) >= 75 else "MEDIUM",
                    url=ioc.get("reference", "") or "",
                    tags=["threatfox", "ioc", ioc.get("threat_type", "")],
                ))
        except Exception as e:
            logger.debug(f"[intel_feeds] ThreatFox fetch failed: {e}")

        self._cache.set(cache_key, items, self._cache_ttl)
        return items

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    async def _get_json(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        user_agent: str = "DEEP-ETIS/1.0",
    ) -> Any:
        req_headers = {"User-Agent": user_agent}
        req_headers.update(headers or {})
        if _AIOHTTP_OK:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=req_headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    return await resp.json(content_type=None)
        else:
            import urllib.request
            req = urllib.request.Request(url, headers=req_headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())

    async def _post_json(
        self,
        url: str,
        body: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """POST a JSON body and parse a JSON response (ThreatFox etc.)."""
        req_headers = {"User-Agent": "DEEP-ETIS/1.0", "Content-Type": "application/json"}
        req_headers.update(headers or {})
        if _AIOHTTP_OK:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=body, headers=req_headers, timeout=aiohttp.ClientTimeout(total=20)
                ) as resp:
                    return await resp.json(content_type=None)
        else:
            import urllib.request
            data = json.dumps(body).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
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
