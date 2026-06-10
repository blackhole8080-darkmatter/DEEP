"""
core/research_engine.py

DEEP Background Research Engine — Autonomous information gathering.

Features:
- RSS feed crawling (no API key)
- Local file/directory monitoring
- DuckDuckGo search scraping (no API key)
- Topic-based tracking with configurable sources
- Automatic briefing synthesis
- Scheduled execution or on-demand triggers
- All data stays local

Usage:
    from DEEP.core.research_engine import ResearchEngine
    
    engine = ResearchEngine()
    engine.add_topic("AI safety", sources=["rss:https://news.ycombinator.com/rss"])
    engine.add_topic("My project", sources=["local:~/Documents/notes"])
    
    # Run scheduled scans
    engine.start_scheduler()
    
    # Or trigger on demand
    briefing = await engine.run_briefing()
    
    # Get findings
    findings = engine.get_findings(topic="AI safety", limit=10)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Set
from urllib.parse import urlparse

try:
    from core.event_bus import EventBus
except ImportError:
    from event_bus import EventBus

logger = logging.getLogger(__name__)

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    logger.warning("feedparser not installed — RSS crawling disabled")


# ═══════════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ResearchTopic:
    """A topic being tracked by the research engine."""
    id: str
    name: str
    keywords: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)  # rss:url, local:path, web:query
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_scan: Optional[datetime] = None
    scan_count: int = 0
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "keywords": self.keywords,
            "sources": self.sources,
            "created_at": self.created_at.isoformat(),
            "last_scan": self.last_scan.isoformat() if self.last_scan else None,
            "scan_count": self.scan_count,
            "active": self.active,
        }


@dataclass
class ResearchFinding:
    """A single piece of information discovered by the engine."""
    id: str
    topic_id: str
    source: str  # Where it came from
    source_type: str  # "rss", "local", "web", "manual"
    title: str
    content: str
    url: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    relevance_score: float = 0.0  # 0.0 to 1.0
    keywords_matched: List[str] = field(default_factory=list)
    read: bool = False
    archived: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic_id": self.topic_id,
            "source": self.source,
            "source_type": self.source_type,
            "title": self.title,
            "content": self.content[:500] if self.content else "",
            "url": self.url,
            "author": self.author,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "discovered_at": self.discovered_at.isoformat(),
            "relevance_score": round(self.relevance_score, 3),
            "keywords_matched": self.keywords_matched,
            "read": self.read,
        }


@dataclass
class Briefing:
    """A synthesized briefing of recent findings."""
    id: str
    created_at: datetime
    topic_findings: Dict[str, List[ResearchFinding]]  # topic_id -> findings
    summary: str
    total_new: int
    total_topics: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "summary": self.summary,
            "total_new": self.total_new,
            "total_topics": self.total_topics,
            "topics": {
                tid: [f.to_dict() for f in findings]
                for tid, findings in self.topic_findings.items()
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Default RSS Sources (Tech, AI, Science — no API key needed)
# ═══════════════════════════════════════════════════════════════════════════════

_DEFAULT_RSS_SOURCES = [
    # Tech & AI
    "https://news.ycombinator.com/rss",
    "https://www.reddit.com/r/MachineLearning/.rss",
    "https://www.reddit.com/r/artificial/.rss",
    # Science
    "https://www.sciencedaily.com/rss/all.xml",
    # General tech
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
]


# ═══════════════════════════════════════════════════════════════════════════════
# Research Engine
# ═══════════════════════════════════════════════════════════════════════════════

class ResearchEngine:
    """
    Autonomous background research and information gathering.
    Tracks topics, crawls sources, synthesizes briefings.
    """

    def __init__(self, data_dir: Optional[Path] = None, event_bus: EventBus = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / "data" / "research"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.topics: Dict[str, ResearchTopic] = {}
        self.findings: List[ResearchFinding] = []
        self.briefings: List[Briefing] = []
        self._seen_hashes: Set[str] = set()  # Deduplication
        self.event_bus = event_bus

        # Runtime
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False
        self._scan_interval_hours = 6
        self._briefing_time = "06:00"  # Daily briefing at 6 AM

        # Load persisted state
        self._load_state()

        # Ensure at least one default topic
        if not self.topics:
            self.add_topic(
                "AI & Technology",
                keywords=["AI", "machine learning", "technology", "software"],
                sources=[f"rss:{url}" for url in _DEFAULT_RSS_SOURCES[:3]],
            )

    async def start(self) -> None:
        """Activate the research engine scheduler."""
        self.start_scheduler()
        logger.info("[ResearchEngine] Started")

    async def stop(self) -> None:
        """Deactivate the research engine."""
        self.stop_scheduler()
        logger.info("[ResearchEngine] Stopped")

    def status(self) -> Dict[str, Any]:
        """Return operational status."""
        return {
            "topics": len(self.topics),
            "findings": len(self.findings),
            "scheduler_running": self._running,
        }

    def _publish(self, event_type: str, payload: Dict):
        """Fire-and-forget event publish on the bus from any context."""
        if self.event_bus:
            try:
                asyncio.create_task(self.event_bus.publish(event_type, payload))
            except RuntimeError:
                pass

    # ─── Persistence ─────────────────────────────────────────────────────────

    def _state_file(self) -> Path:
        return self.data_dir / "research_state.json"

    def _findings_file(self) -> Path:
        return self.data_dir / "findings.json"

    def _load_state(self):
        """Load topics and findings from disk."""
        # Load topics
        sf = self._state_file()
        if sf.exists():
            try:
                data = json.loads(sf.read_text(encoding="utf-8"))
                for t_data in data.get("topics", []):
                    t = ResearchTopic(
                        id=t_data["id"],
                        name=t_data["name"],
                        keywords=t_data.get("keywords", []),
                        sources=t_data.get("sources", []),
                        created_at=datetime.fromisoformat(t_data["created_at"]),
                        last_scan=datetime.fromisoformat(t_data["last_scan"]) if t_data.get("last_scan") else None,
                        scan_count=t_data.get("scan_count", 0),
                        active=t_data.get("active", True),
                    )
                    self.topics[t.id] = t
                self._briefing_time = data.get("briefing_time", "06:00")
                logger.info(f"[ResearchEngine] Loaded {len(self.topics)} topics")
            except Exception as e:
                logger.warning(f"[ResearchEngine] Failed to load state: {e}")

        # Load findings
        ff = self._findings_file()
        if ff.exists():
            try:
                data = json.loads(ff.read_text(encoding="utf-8"))
                for f_data in data.get("findings", [])[-500:]:  # Keep last 500
                    f = ResearchFinding(
                        id=f_data["id"],
                        topic_id=f_data["topic_id"],
                        source=f_data["source"],
                        source_type=f_data["source_type"],
                        title=f_data["title"],
                        content=f_data.get("content", ""),
                        url=f_data.get("url"),
                        author=f_data.get("author"),
                        published_at=datetime.fromisoformat(f_data["published_at"]) if f_data.get("published_at") else None,
                        discovered_at=datetime.fromisoformat(f_data["discovered_at"]),
                        relevance_score=f_data.get("relevance_score", 0),
                        keywords_matched=f_data.get("keywords_matched", []),
                        read=f_data.get("read", False),
                    )
                    self.findings.append(f)
                    self._seen_hashes.add(self._hash_finding(f))
                logger.info(f"[ResearchEngine] Loaded {len(self.findings)} findings")
            except Exception as e:
                logger.warning(f"[ResearchEngine] Failed to load findings: {e}")

    def _save_state(self):
        """Persist topics and configuration."""
        try:
            data = {
                "saved_at": datetime.utcnow().isoformat(),
                "briefing_time": self._briefing_time,
                "topics": [t.to_dict() for t in self.topics.values()],
            }
            self._state_file().write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"[ResearchEngine] Failed to save state: {e}")

    def _save_findings(self):
        """Persist findings."""
        try:
            data = {
                "saved_at": datetime.utcnow().isoformat(),
                "findings": [f.to_dict() for f in self.findings[-500:]],  # Keep last 500
            }
            self._findings_file().write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"[ResearchEngine] Failed to save findings: {e}")

    def _hash_finding(self, f: ResearchFinding) -> str:
        """Create a hash for deduplication."""
        text = f"{f.source}|{f.title}|{f.url or ''}"
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    # ─── Public API ────────────────────────────────────────────────────────


    def add_topic(self, name: str, keywords: Optional[List[str]] = None,
                  sources: Optional[List[str]] = None) -> ResearchTopic:
        """Add a new research topic."""
        topic_id = f"topic_{int(time.time()*1000)}"
        topic = ResearchTopic(
            id=topic_id,
            name=name,
            keywords=keywords or [name.lower()],
            sources=sources or [],
        )
        self.topics[topic_id] = topic
        self._save_state()
        logger.info(f"[ResearchEngine] Added topic '{name}' ({topic_id})")
        self._publish("topic_added", topic.to_dict())
        return topic

    def remove_topic(self, topic_id: str) -> bool:
        if topic_id in self.topics:
            name = self.topics[topic_id].name
            del self.topics[topic_id]
            self.findings = [f for f in self.findings if f.topic_id != topic_id]
            self._save_state()
            self._save_findings()
            self._publish("topic_removed", {"id": topic_id, "name": name})
            return True
        return False

    def get_topics(self) -> List[Dict]:
        return [t.to_dict() for t in self.topics.values()]

    def get_findings(self, topic_id: Optional[str] = None, unread_only: bool = False,
                     limit: int = 50, since: Optional[datetime] = None) -> List[Dict]:
        """Get findings with optional filters."""
        results = self.findings
        if topic_id:
            results = [f for f in results if f.topic_id == topic_id]
        if unread_only:
            results = [f for f in results if not f.read]
        if since:
            results = [f for f in results if f.discovered_at >= since]
        results = sorted(results, key=lambda f: f.discovered_at, reverse=True)
        return [f.to_dict() for f in results[:limit]]

    def mark_read(self, finding_id: str) -> bool:
        for f in self.findings:
            if f.id == finding_id:
                f.read = True
                self._save_findings()
                return True
        return False

    def mark_all_read(self, topic_id: Optional[str] = None):
        for f in self.findings:
            if topic_id is None or f.topic_id == topic_id:
                f.read = True
        self._save_findings()

    def get_latest_briefing(self) -> Optional[Dict]:
        if not self.briefings:
            return None
        return self.briefings[-1].to_dict()

    def get_stats(self) -> Dict:
        """Summary statistics."""
        total = len(self.findings)
        unread = len([f for f in self.findings if not f.read])
        today = datetime.utcnow() - timedelta(days=1)
        last_24h = len([f for f in self.findings if f.discovered_at >= today])
        return {
            "topics": len(self.topics),
            "total_findings": total,
            "unread_findings": unread,
            "last_24h": last_24h,
            "briefings_generated": len(self.briefings),
            "last_briefing": self.briefings[-1].created_at.isoformat() if self.briefings else None,
        }

    # ─── Scheduler ─────────────────────────────────────────────────────────

    def start_scheduler(self):
        """Start the background research loop."""
        if self._running:
            return
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("[ResearchEngine] Scheduler started")

    def stop_scheduler(self):
        """Stop the background loop."""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            self._scheduler_task = None
        logger.info("[ResearchEngine] Scheduler stopped")

    async def _scheduler_loop(self):
        """Main scheduler: scans topics periodically and generates briefings."""
        while self._running:
            now = datetime.utcnow()
            
            # Scan topics every N hours
            for topic in self.topics.values():
                if not topic.active:
                    continue
                if (topic.last_scan is None or 
                    (now - topic.last_scan).total_seconds() > self._scan_interval_hours * 3600):
                    await self._scan_topic(topic)
            
            # Check if it's briefing time
            current_time = now.strftime("%H:%M")
            if current_time == self._briefing_time:
                # Only generate once per day at briefing time
                last_briefing_today = any(
                    b.created_at.date() == now.date() for b in self.briefings
                )
                if not last_briefing_today:
                    await self.run_briefing()
            
            await asyncio.sleep(60)  # Check every minute

    # ─── Scanning ──────────────────────────────────────────────────────────

    async def _scan_topic(self, topic: ResearchTopic):
        """Scan all sources for a single topic."""
        logger.info(f"[ResearchEngine] Scanning topic '{topic.name}'...")
        topic.last_scan = datetime.utcnow()
        topic.scan_count += 1
        new_findings = 0

        for source in topic.sources:
            try:
                if source.startswith("rss:"):
                    count = await self._scan_rss(topic, source[4:])
                    new_findings += count
                elif source.startswith("local:"):
                    count = await self._scan_local(topic, source[6:])
                    new_findings += count
                elif source.startswith("web:"):
                    count = await self._scan_web(topic, source[4:])
                    new_findings += count
            except Exception as e:
                logger.warning(f"[ResearchEngine] Source scan failed ({source}): {e}")

        self._save_state()
        self._save_findings()
        
        if new_findings > 0:
            self._publish("topic_scanned", {
                "topic_id": topic.id,
                "topic_name": topic.name,
                "new_findings": new_findings,
            })
        
        logger.info(f"[ResearchEngine] Topic '{topic.name}': {new_findings} new findings")

    async def _scan_rss(self, topic: ResearchTopic, url: str) -> int:
        """Fetch and parse an RSS feed."""
        if not FEEDPARSER_AVAILABLE:
            logger.debug("feedparser not available, skipping RSS")
            return 0

        new_count = 0
        try:
            # Use aiohttp for async fetch, then feedparser for parsing
            if AIOHTTP_AVAILABLE:
                timeout = aiohttp.ClientTimeout(total=15)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers={"User-Agent": "DEEP-Research/1.0"}) as resp:
                        if resp.status == 200:
                            content = await resp.read()
                            feed = feedparser.parse(content)
                        else:
                            return 0
            else:
                # Fallback to synchronous
                import urllib.request
                req = urllib.request.Request(url, headers={"User-Agent": "DEEP-Research/1.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    feed = feedparser.parse(resp.read())

            for entry in feed.entries[:20]:  # Process last 20 entries
                title = entry.get("title", "Untitled")
                content = entry.get("summary", entry.get("description", ""))
                url_ = entry.get("link", "")
                author = entry.get("author", "")
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                
                published_dt = None
                if published:
                    try:
                        published_dt = datetime(*published[:6])
                    except Exception:
                        pass

                # Skip old entries (older than 7 days)
                if published_dt and (datetime.utcnow() - published_dt).days > 7:
                    continue

                # Check keyword relevance
                matched, score = self._score_relevance(title + " " + content, topic.keywords)
                if score < 0.1:  # Too irrelevant
                    continue

                finding = ResearchFinding(
                    id=f"find_{int(time.time()*1000)}_{new_count}",
                    topic_id=topic.id,
                    source=feed.feed.get("title", url),
                    source_type="rss",
                    title=title,
                    content=content,
                    url=url_,
                    author=author,
                    published_at=published_dt,
                    relevance_score=score,
                    keywords_matched=matched,
                )

                h = self._hash_finding(finding)
                if h not in self._seen_hashes:
                    self._seen_hashes.add(h)
                    self.findings.append(finding)
                    new_count += 1

        except Exception as e:
            logger.debug(f"RSS scan error for {url}: {e}")

        return new_count

    async def _scan_local(self, topic: ResearchTopic, path_str: str) -> int:
        """Monitor a local directory for new/changed files."""
        new_count = 0
        try:
            path = Path(path_str).expanduser()
            if not path.exists():
                return 0

            # Track file modification times
            for file_path in path.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() not in (".txt", ".md", ".json", ".py", ".js", ".html", ".css", ".pdf"):
                    continue

                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                # Only files modified in last 7 days
                if (datetime.utcnow() - mtime).days > 7:
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")[:2000]
                except Exception:
                    continue

                matched, score = self._score_relevance(content, topic.keywords)
                if score < 0.2:
                    continue

                finding = ResearchFinding(
                    id=f"find_local_{int(time.time()*1000)}_{new_count}",
                    topic_id=topic.id,
                    source=str(file_path),
                    source_type="local",
                    title=file_path.name,
                    content=content[:500],
                    url=None,
                    author=None,
                    published_at=mtime,
                    relevance_score=score,
                    keywords_matched=matched,
                )

                h = self._hash_finding(finding)
                if h not in self._seen_hashes:
                    self._seen_hashes.add(h)
                    self.findings.append(finding)
                    new_count += 1

        except Exception as e:
            logger.debug(f"Local scan error for {path_str}: {e}")

        return new_count

    async def _scan_web(self, topic: ResearchTopic, query: str) -> int:
        """Lightweight web search via DuckDuckGo HTML scraping."""
        # This is a placeholder — full implementation would scrape DDG results
        # For now, return 0 to avoid complexity
        return 0

    def _score_relevance(self, text: str, keywords: List[str]) -> tuple:
        """Score how relevant text is to keywords. Returns (matched_keywords, score)."""
        text_lower = text.lower()
        matched = []
        total_score = 0.0

        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in text_lower:
                matched.append(kw)
                # Simple scoring: longer/more specific keywords score higher
                total_score += min(len(kw_lower.split()) * 0.3, 1.0)

        # Normalize by keyword count
        score = min(total_score / max(len(keywords), 1), 1.0)
        return matched, score

    # ─── Briefing Generation ─────────────────────────────────────────────────

    async def run_briefing(self) -> Optional[Briefing]:
        """Generate a synthesized briefing of recent findings."""
        logger.info("[ResearchEngine] Generating briefing...")
        
        # Get unread findings from last 24h
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent = [f for f in self.findings if f.discovered_at >= cutoff and not f.read]

        if not recent:
            logger.info("[ResearchEngine] No new findings for briefing")
            return None

        # Group by topic
        by_topic: Dict[str, List[ResearchFinding]] = defaultdict(list)
        for f in recent:
            by_topic[f.topic_id].append(f)

        # Build summary
        summary_parts = []
        for tid, findings in by_topic.items():
            topic = self.topics.get(tid)
            name = topic.name if topic else "Unknown"
            summary_parts.append(f"{name}: {len(findings)} new items")

        summary = "; ".join(summary_parts)

        briefing = Briefing(
            id=f"brief_{int(time.time()*1000)}",
            created_at=datetime.utcnow(),
            topic_findings=dict(by_topic),
            summary=summary,
            total_new=len(recent),
            total_topics=len(by_topic),
        )

        self.briefings.append(briefing)
        if len(self.briefings) > 30:
            self.briefings = self.briefings[-30:]

        # Mark findings as read
        for f in recent:
            f.read = True
        self._save_findings()

        self._publish("briefing_ready", briefing.to_dict())
        logger.info(f"[ResearchEngine] Briefing generated: {len(recent)} findings across {len(by_topic)} topics")
        return briefing

    async def force_scan_all(self) -> Dict:
        """Force-scan all topics immediately."""
        results = {}
        for topic in self.topics.values():
            if topic.active:
                await self._scan_topic(topic)
                results[topic.id] = {
                    "name": topic.name,
                    "new_findings": len([f for f in self.findings if f.topic_id == topic.id and f.discovered_at > topic.last_scan]) if topic.last_scan else 0,
                }
        return results
