"""
deep/knowledge/ingester.py

Scheduled knowledge ingester that pulls papers from:
    - arXiv RSS feeds (free, no key)
    - PubMed E-utilities (free, no key)
    - NVD CVE feed (free, no key)
    - NASA ADS (optional, requires API key)

Runs on a schedule defined by config.INGEST_INTERVAL_HOURS.
Publishes "papers_ingested" and "ingest_error" events.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not installed — KnowledgeIngester will be non-functional")

try:
    from core.config import Settings
except ImportError:
    from config import Settings

try:
    from core.event_bus import EventBus
except ImportError:
    from event_bus import EventBus

from .knowledge_store import Paper


# ═══════════════════════════════════════════════════════════════════════════════
# IngestResult
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class IngestResult:
    total_fetched: int = 0
    total_new: int = 0
    by_domain: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    duration_ms: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# KnowledgeIngester
# ═══════════════════════════════════════════════════════════════════════════════

class KnowledgeIngester:
    """
    Pulls scientific papers from multiple free sources.

    Lifecycle: __init__ → start() → ... → stop() → status()
    """

    def __init__(
        self,
        event_bus: EventBus,
        knowledge_store,
    ) -> None:
        self.event_bus = event_bus
        self.knowledge_store = knowledge_store
        self.settings = Settings()
        self._started = False
        self._task: Optional[asyncio.Task] = None
        self._client: Optional[Any] = None
        if HTTPX_AVAILABLE:
            self._client = httpx.AsyncClient(timeout=30.0)

        # Source health tracking
        self._source_health: Dict[str, str] = {}
        self._last_run: Optional[str] = None
        self._next_run: Optional[str] = None
        self._runs_today = 0

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the scheduled ingestion loop."""
        self._started = True
        self._task = asyncio.create_task(self._scheduled_loop())
        logger.info("[KnowledgeIngester] Started")

    async def stop(self) -> None:
        """Stop the ingestion loop."""
        self._started = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("[KnowledgeIngester] Stopped")

    def status(self) -> Dict[str, Any]:
        return {
            "last_run": self._last_run,
            "next_run": self._next_run,
            "total_runs_today": self._runs_today,
            "source_health": self._source_health,
        }

    # ── Scheduling ──────────────────────────────────────────────────────────

    async def _scheduled_loop(self) -> None:
        """Run ingest_all() immediately, then repeat every N hours."""
        interval_hours = getattr(self.settings, "ingest_interval_hours", 6)

        # Initial run
        await self.ingest_all()

        while self._started:
            next_time = datetime.now(timezone.utc) + timedelta(hours=interval_hours)
            self._next_run = next_time.isoformat()
            await asyncio.sleep(interval_hours * 3600)
            if self._started:
                await self.ingest_all()

    # ── Public API ────────────────────────────────────────────────────────

    async def ingest_all(self) -> IngestResult:
        """
        Run all enabled sources concurrently.
        Deduplicate by paper.id before adding to store.
        """
        if not HTTPX_AVAILABLE or not self._client:
            logger.error("httpx not installed — cannot ingest")
            return IngestResult(errors=["httpx not installed"])

        if not self.knowledge_store._started:
            logger.error("KnowledgeStore not started — cannot ingest")
            return IngestResult(errors=["KnowledgeStore not started"])

        t0 = time.perf_counter()
        sources = self._resolve_sources()
        all_papers: List[Paper] = []
        errors: List[str] = []

        # Run enabled sources concurrently
        coros = []
        for source_name, config in sources.items():
            if config.get("enabled", True):
                if source_name == "arxiv":
                    coros.append(self._ingest_arxiv(config))
                elif source_name == "pubmed":
                    coros.append(self._ingest_pubmed(config))
                elif source_name == "nvd":
                    coros.append(self._ingest_nvd())
                elif source_name == "nasa_ads":
                    coros.append(self._ingest_nasa_ads(config))

        if not coros:
            return IngestResult(errors=["No sources enabled"])

        results = await asyncio.gather(*coros, return_exceptions=True)
        for idx, (source_name, result) in enumerate(zip(
            [s for s, c in sources.items() if c.get("enabled", True)],
            results,
        )):
            if isinstance(result, Exception):
                errors.append(f"{source_name}: {result}")
                self._source_health[source_name] = "error"
            else:
                all_papers.extend(result)
                self._source_health[source_name] = "ok"

        # Deduplicate by ID
        seen: set = set()
        unique_papers = []
        for p in all_papers:
            if p.id not in seen:
                seen.add(p.id)
                unique_papers.append(p)

        total_fetched = len(unique_papers)

        # Add to store (batch)
        total_new = await self.knowledge_store.add_papers(unique_papers)

        # Build domain breakdown from the newly added papers
        by_domain: Dict[str, int] = {}
        for p in unique_papers:
            dom = p.domain or "unknown"
            by_domain[dom] = by_domain.get(dom, 0) + 1

        duration_ms = int((time.perf_counter() - t0) * 1000)
        self._last_run = datetime.now(timezone.utc).isoformat()
        self._runs_today += 1

        result = IngestResult(
            total_fetched=total_fetched,
            total_new=total_new,
            by_domain=by_domain,
            errors=errors,
            duration_ms=duration_ms,
        )

        # Publish events
        await self.event_bus.publish("papers_ingested", {
            "total_new": total_new,
            "by_domain": by_domain,
            "duration_ms": duration_ms,
            "errors": errors,
        })
        for err in errors:
            await self.event_bus.publish("ingest_error", {"message": err})

        logger.info(
            f"[KnowledgeIngester] ingested {total_new} new papers "
            f"({total_fetched} fetched) in {duration_ms}ms"
        )
        return result

    async def ingest_domain(self, domain: str) -> IngestResult:
        """Run only sources matching the given domain."""
        sources = self._resolve_sources()
        papers: List[Paper] = []
        errors: List[str] = []

        for source_name, config in sources.items():
            if not config.get("enabled", True):
                continue
            matched = config.get("domain") == domain or domain in str(config.get("feeds", ""))
            if not matched:
                continue

            try:
                if source_name == "arxiv":
                    # Filter arxiv feeds for this domain
                    for feed_url in config.get("feeds", []):
                        if domain in feed_url:
                            papers.extend(await self._parse_arxiv(feed_url, domain))
                elif source_name == "pubmed":
                    for term in config.get("queries", []):
                        if domain in term.lower():
                            papers.extend(await self._parse_pubmed(term, domain))
                elif source_name == "nvd" and domain == "cybersecurity":
                    papers.extend(await self._parse_nvd())
            except Exception as e:
                errors.append(f"{source_name}: {e}")

        seen: set = set()
        unique_papers = [p for p in papers if not (p.id in seen or seen.add(p.id))]
        total_new = await self.knowledge_store.add_papers(unique_papers)

        by_domain = {domain: total_new}
        return IngestResult(
            total_fetched=len(unique_papers),
            total_new=total_new,
            by_domain=by_domain,
            errors=errors,
            duration_ms=0,
        )

    # ── Source Config Resolution ────────────────────────────────────────────

    def _resolve_sources(self) -> Dict[str, Dict[str, Any]]:
        """Return source configuration from config or built-in defaults."""
        sources = getattr(self.settings, "ingest_sources", None)
        if sources:
            return dict(sources)

        # Built-in defaults
        return {
            "arxiv": {
                "enabled": True,
                "feeds": [
                    "https://arxiv.org/rss/cs.AI",
                    "https://arxiv.org/rss/cs.LG",
                    "https://arxiv.org/rss/cs.RO",
                    "https://arxiv.org/rss/cs.CR",
                    "https://arxiv.org/rss/physics",
                    "https://arxiv.org/rss/quant-ph",
                    "https://arxiv.org/rss/math",
                    "https://arxiv.org/rss/astro-ph",
                ],
            },
            "pubmed": {
                "enabled": True,
                "queries": [
                    "neural interface",
                    "CRISPR 2024",
                    "quantum computing",
                    "protein structure prediction",
                ],
            },
            "nvd": {"enabled": True},
            "nasa_ads": {
                "enabled": getattr(self.settings, "nasa_ads_key", None) is not None,
                "queries": ["star formation"],
            },
        }

    # ── arXiv Parser ──────────────────────────────────────────────────────

    async def _ingest_arxiv(self, config: Dict[str, Any]) -> List[Paper]:
        """Fetch and parse all enabled arXiv RSS feeds."""
        papers: List[Paper] = []
        feeds = config.get("feeds", [])

        # Map feed URLs to domains
        domain_map = {
            "cs.AI": "ai_ml",
            "cs.LG": "ai_ml",
            "cs.RO": "robotics",
            "cs.CR": "cybersecurity",
            "physics": "physics",
            "quant-ph": "quantum",
            "math": "mathematics",
            "astro-ph": "space",
        }

        coros = []
        for feed_url in feeds:
            # Infer domain from URL
            inferred_domain = "general"
            for key, dom in domain_map.items():
                if key in feed_url:
                    inferred_domain = dom
                    break
            coros.append(self._parse_arxiv(feed_url, inferred_domain))

        results = await asyncio.gather(*coros, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                papers.extend(result)

        return papers

    async def _parse_arxiv(self, feed_url: str, domain: str) -> List[Paper]:
        """Parse an arXiv RSS feed into Paper objects."""
        if not self._client:
            return []

        try:
            resp = await self._client.get(feed_url)
            resp.raise_for_status()
            content = resp.text
        except Exception as e:
            logger.warning(f"[Ingester] arXiv fetch failed ({feed_url}): {e}")
            return []

        # Parse RSS manually (feedparser is optional)
        try:
            import feedparser
            feed = feedparser.parse(content)
            papers: List[Paper] = []
            for entry in feed.entries:
                paper_id = entry.get("id", entry.get("link", ""))
                # Normalize ID
                if "arxiv.org" in paper_id:
                    arxiv_id = paper_id.split("/")[-1].replace("abs:", "").strip()
                    paper_id = f"arxiv:{arxiv_id}"
                else:
                    paper_id = f"arxiv:{paper_id}"

                authors = []
                if "authors" in entry:
                    for a in entry.authors:
                        if hasattr(a, "name"):
                            authors.append(a.name)
                        elif isinstance(a, dict):
                            authors.append(a.get("name", ""))

                paper = Paper(
                    id=paper_id,
                    title=entry.get("title", "").replace("\n", " ").strip(),
                    authors=authors,
                    abstract=entry.get("summary", "").strip(),
                    source="arxiv",
                    domain=domain,
                    published_date=entry.get("published", ""),
                    url=entry.get("link", ""),
                )
                papers.append(paper)
            return papers
        except ImportError:
            # Fallback: simple regex-based parsing
            logger.warning("feedparser not installed — using fallback arXiv parser")
            return self._parse_arxiv_fallback(content, domain)

    def _parse_arxiv_fallback(self, content: str, domain: str) -> List[Paper]:
        """Regex fallback for arXiv RSS without feedparser."""
        papers: List[Paper] = []
        # Find <item> blocks
        items = re.findall(r"<item>(.*?)</item>", content, re.DOTALL)
        for item in items:
            title = self._xml_extract(item, "title")
            link = self._xml_extract(item, "link")
            desc = self._xml_extract(item, "description")
            pub_date = self._xml_extract(item, "pubDate")
            # Try to extract arXiv ID from link
            arxiv_id = ""
            if "arxiv.org" in link:
                arxiv_id = link.split("/")[-1].strip()
            paper_id = f"arxiv:{arxiv_id}" if arxiv_id else f"arxiv:unknown-{hash(item)}"
            papers.append(Paper(
                id=paper_id,
                title=title,
                abstract=desc,
                source="arxiv",
                domain=domain,
                published_date=pub_date,
                url=link,
            ))
        return papers

    # ── PubMed Parser ─────────────────────────────────────────────────────

    async def _ingest_pubmed(self, config: Dict[str, Any]) -> List[Paper]:
        """Fetch papers from PubMed for each configured query term."""
        papers: List[Paper] = []
        queries = config.get("queries", [])
        for term in queries:
            papers.extend(await self._parse_pubmed(term, "biomedical"))
        return papers

    async def _parse_pubmed(self, term: str, domain: str) -> List[Paper]:
        """Two-step: search IDs, then fetch abstracts."""
        if not self._client:
            return []

        base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

        # Step 1: Search for IDs
        search_url = (
            f"{base}/esearch.fcgi?db=pubmed"
            f"&term={urllib.parse.quote(term)}&retmax=10&retmode=json"
        )
        try:
            resp = await self._client.get(search_url)
            resp.raise_for_status()
            data = resp.json()
            id_list = data.get("esearchresult", {}).get("idlist", [])
        except Exception as e:
            logger.warning(f"[Ingester] PubMed search failed for '{term}': {e}")
            return []

        if not id_list:
            return []

        # Step 2: Fetch abstracts
        ids_str = ",".join(id_list)
        fetch_url = (
            f"{base}/efetch.fcgi?db=pubmed"
            f"&id={ids_str}&retmode=xml&rettype=abstract"
        )
        try:
            resp = await self._client.get(fetch_url)
            resp.raise_for_status()
            xml_content = resp.text
        except Exception as e:
            logger.warning(f"[Ingester] PubMed fetch failed: {e}")
            return []

        return self._parse_pubmed_xml(xml_content, domain)

    def _parse_pubmed_xml(self, xml_content: str, domain: str) -> List[Paper]:
        """Parse PubMed XML into Paper objects."""
        papers: List[Paper] = []
        try:
            root = ET.fromstring(xml_content.encode("utf-8"))
            for article in root.findall(".//PubmedArticle"):
                pmid_elem = article.find(".//PMID")
                pmid = pmid_elem.text if pmid_elem is not None else ""

                title_elem = article.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None else ""

                abstract_elem = article.find(".//Abstract/AbstractText")
                abstract = abstract_elem.text if abstract_elem is not None else ""

                authors = []
                for author in article.findall(".//Author"):
                    last = author.find("LastName")
                    first = author.find("ForeName")
                    if last is not None:
                        name = last.text or ""
                        if first is not None:
                            name = f"{first.text} {name}"
                        authors.append(name)

                pub_date_elem = article.find(".//PubDate/Year")
                pub_date = pub_date_elem.text if pub_date_elem is not None else ""

                paper = Paper(
                    id=f"pubmed:{pmid}",
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    source="pubmed",
                    domain=domain,
                    published_date=pub_date,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                )
                papers.append(paper)
        except ET.ParseError as e:
            logger.warning(f"[Ingester] PubMed XML parse error: {e}")
        return papers

    # ── NVD Parser ──────────────────────────────────────────────────────────

    async def _ingest_nvd(self) -> List[Paper]:
        """Fetch recent CVEs from NVD."""
        return await self._parse_nvd()

    async def _parse_nvd(self) -> List[Paper]:
        """Fetch and parse NVD CVE feed."""
        if not self._client:
            return []

        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

        url = (
            "https://services.nvd.nist.gov/rest/json/cves/2.0"
            f"?pubStartDate={yesterday}&pubEndDate={today}"
        )

        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"[Ingester] NVD fetch failed: {e}")
            return []

        papers: List[Paper] = []
        for vuln in data.get("vulnerabilities", []):
            cve = vuln.get("cve", {})
            cve_id = cve.get("id", "")
            descriptions = cve.get("descriptions", [])
            desc = descriptions[0].get("value", "") if descriptions else ""
            title = f"{cve_id}: {desc[:80]}" if desc else cve_id

            # Check severity
            metrics = cve.get("metrics", {})
            cvss = metrics.get("cvssMetricV31", [{}])[0] if metrics else {}
            severity = cvss.get("cvssData", {}).get("baseSeverity", "UNKNOWN")

            paper = Paper(
                id=f"nvd:{cve_id}",
                title=title,
                abstract=desc,
                source="nvd",
                domain="cybersecurity",
                published_date=cve.get("published", ""),
                url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
            )
            papers.append(paper)

        return papers

    # ── NASA ADS Parser ─────────────────────────────────────────────────────

    async def _ingest_nasa_ads(self, config: Dict[str, Any]) -> List[Paper]:
        """Fetch papers from NASA ADS (requires API key)."""
        api_key = getattr(self.settings, "nasa_ads_key", None)
        if not api_key:
            return []

        papers: List[Paper] = []
        queries = config.get("queries", ["star formation"])
        for query in queries:
            papers.extend(await self._parse_nasa_ads(query, api_key))
        return papers

    async def _parse_nasa_ads(self, query: str, api_key: str) -> List[Paper]:
        """Fetch from NASA ADS API."""
        if not self._client:
            return []

        url = (
            "https://api.adsabs.harvard.edu/v1/search/query"
            f"?q={urllib.parse.quote(query)}"
            f"&fl=title,abstract,author,pubdate,bibcode"
            f"&rows=10"
        )

        try:
            resp = await self._client.get(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"[Ingester] NASA ADS fetch failed: {e}")
            return []

        papers: List[Paper] = []
        for doc in data.get("response", {}).get("docs", []):
            authors = doc.get("author", [])[:5]  # cap at 5 authors
            paper = Paper(
                id=f"nasa:{doc.get('bibcode', '')}",
                title=doc.get("title", [""])[0] if isinstance(doc.get("title"), list) else doc.get("title", ""),
                authors=authors,
                abstract=doc.get("abstract", ""),
                source="nasa",
                domain="space",
                published_date=doc.get("pubdate", ""),
                url=f"https://ui.adsabs.harvard.edu/abs/{doc.get('bibcode', '')}/abstract",
            )
            papers.append(paper)

        return papers

    # ── Helpers ───────────────────────────────────────────────────────────

    def _xml_extract(self, text: str, tag: str) -> str:
        """Extract text between XML tags using regex."""
        pattern = re.compile(f"<{tag}[^>]*>(.*?)</{tag}>", re.DOTALL)
        match = pattern.search(text)
        return match.group(1).strip() if match else ""
