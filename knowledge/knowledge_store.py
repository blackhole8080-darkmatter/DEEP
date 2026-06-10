"""
deep/knowledge/knowledge_store.py

ChromaDB-backed persistent vector store for scientific papers.
All other knowledge components depend on this.

Embedding: sentence-transformers "all-MiniLM-L6-v2" (384-dim)
Collection: "deep_papers"
Schema: id, title, authors, abstract, source, domain, published_date, url,
        ingested_at, embedding
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from core.config import Settings
except ImportError:
    from config import Settings

try:
    from core.event_bus import EventBus
except ImportError:
    from event_bus import EventBus

# ── Optional heavy imports ───────────────────────────────────────────────────

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("chromadb not installed — KnowledgeStore uses in-memory fallback")

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    logger.warning("sentence-transformers not installed — embeddings disabled")


# ═══════════════════════════════════════════════════════════════════════════════
# Paper dataclass
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Paper:
    """A single scientific paper or research document."""

    id: str                 # source:unique_id e.g. arxiv:2301.00001
    title: str
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    source: str = ""       # "arxiv", "pubmed", "nvd", "nasa"
    domain: str = ""       # "physics", "ai_ml", "cybersecurity", etc.
    published_date: str = ""  # ISO format
    url: str = ""
    ingested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "authors": ",".join(self.authors),
            "abstract": self.abstract,
            "source": self.source,
            "domain": self.domain,
            "published_date": self.published_date,
            "url": self.url,
            "ingested_at": self.ingested_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Paper":
        authors_raw = data.get("authors", "")
        authors = [a.strip() for a in authors_raw.split(",") if a.strip()] if isinstance(authors_raw, str) else list(authors_raw)
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            authors=authors,
            abstract=data.get("abstract", ""),
            source=data.get("source", ""),
            domain=data.get("domain", ""),
            published_date=data.get("published_date", ""),
            url=data.get("url", ""),
            ingested_at=data.get("ingested_at", datetime.now(timezone.utc).isoformat()),
            embedding=data.get("embedding"),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# KnowledgeStore
# ═══════════════════════════════════════════════════════════════════════════════

class KnowledgeStore:
    """
    ChromaDB-backed persistent vector store for papers.

    Lifecycle: __init__ → start() → ... → stop() → status()
    """

    _EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    _COLLECTION_NAME = "deep_papers"

    def __init__(
        self,
        event_bus: EventBus,
        db_path: Optional[str] = None,
    ) -> None:
        self.event_bus = event_bus
        self._db_path = db_path or self._default_db_path()
        self._client: Optional[Any] = None
        self._collection: Optional[Any] = None
        self._embedding_model: Optional[Any] = None
        self._started = False

    def _default_db_path(self) -> str:
        try:
            settings = Settings()
            return str(getattr(settings, "knowledge_db_path", "data/chroma_research"))
        except Exception:
            return str(Path(__file__).parent.parent.parent / "data" / "chroma_research")

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Load ChromaDB client and embedding model."""
        if not CHROMADB_AVAILABLE or not ST_AVAILABLE:
            logger.error("KnowledgeStore requires chromadb and sentence-transformers")
            return

        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=self._db_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=self._COLLECTION_NAME,
            metadata={"description": "DEEP scientific paper store"},
        )

        logger.info(f"[KnowledgeStore] Loading embedding model '{self._EMBEDDING_MODEL}'...")
        self._embedding_model = SentenceTransformer(self._EMBEDDING_MODEL)
        logger.info("[KnowledgeStore] Embedding model loaded")

        self._started = True
        logger.info(f"[KnowledgeStore] Ready — collection '{self._COLLECTION_NAME}' at {self._db_path}")

    async def stop(self) -> None:
        """Release resources."""
        self._client = None
        self._collection = None
        self._embedding_model = None
        self._started = False
        logger.info("[KnowledgeStore] Stopped")

    def status(self) -> Dict[str, Any]:
        """Return operational status."""
        if not self._started or not CHROMADB_AVAILABLE:
            return {
                "total_papers": 0,
                "papers_by_domain": {},
                "db_size_mb": 0.0,
                "last_updated": None,
            }

        total = 0
        try:
            total = self._collection.count()
        except Exception as e:
            logger.warning(f"[KnowledgeStore] count error: {e}")

        # Aggregate by domain (lightweight peek)
        domain_counts: Dict[str, int] = {}
        try:
            if total > 0:
                result = self._collection.get(limit=min(total, 1000))
                for meta in result.get("metadatas", []):
                    dom = meta.get("domain", "unknown") if meta else "unknown"
                    domain_counts[dom] = domain_counts.get(dom, 0) + 1
        except Exception:
            pass

        db_size_mb = 0.0
        try:
            db_path = Path(self._db_path)
            if db_path.exists():
                db_size_mb = round(
                    sum(f.stat().st_size for f in db_path.rglob("*") if f.is_file()) / (1024 * 1024),
                    2,
                )
        except Exception:
            pass

        return {
            "total_papers": total,
            "papers_by_domain": domain_counts,
            "db_size_mb": db_size_mb,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    # ── Core API ────────────────────────────────────────────────────────────

    async def add_paper(self, paper: Paper) -> bool:
        """
        Embed and upsert a single paper.
        Returns True if added, False if skipped (already exists).
        """
        if not self._started or not self._collection or not self._embedding_model:
            logger.warning("KnowledgeStore not started — skipping add_paper")
            return False

        if self._paper_exists_sync(paper.id):
            logger.debug(f"[KnowledgeStore] Paper '{paper.id}' already exists — skipping")
            return False

        text = f"{paper.title} {paper.abstract[:500]}"
        embedding = self._embedding_model.encode(text).tolist()

        self._collection.add(
            ids=[paper.id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[paper.to_dict()],
        )
        logger.debug(f"[KnowledgeStore] Added paper '{paper.id}'")
        return True

    async def add_papers(self, papers: List[Paper]) -> int:
        """
        Batch embed and upsert papers. Returns count of newly added papers.
        Skips silently if id already exists.
        """
        if not self._started or not self._collection or not self._embedding_model:
            logger.warning("KnowledgeStore not started — skipping add_papers")
            return 0

        # Filter out existing papers
        new_papers = [p for p in papers if not self._paper_exists_sync(p.id)]
        if not new_papers:
            return 0

        texts = [f"{p.title} {p.abstract[:500]}" for p in new_papers]
        embeddings = self._embedding_model.encode(texts).tolist()

        self._collection.add(
            ids=[p.id for p in new_papers],
            documents=texts,
            embeddings=embeddings,
            metadatas=[p.to_dict() for p in new_papers],
        )
        logger.info(f"[KnowledgeStore] Batch added {len(new_papers)} papers")
        return len(new_papers)

    async def search(
        self,
        query: str,
        domain: Optional[str] = None,
        n_results: int = 5,
    ) -> List[Paper]:
        """Semantic search over papers. Optionally filter by domain."""
        if not self._started or not self._collection or not self._embedding_model:
            logger.warning("KnowledgeStore not started — search returning empty")
            return []

        query_embedding = self._embedding_model.encode(query).tolist()

        where_filter = None
        if domain:
            where_filter = {"domain": domain}

        try:
            result = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter,
            )
        except Exception as e:
            logger.warning(f"[KnowledgeStore] query error: {e}")
            return []

        papers: List[Paper] = []
        metas = result.get("metadatas", [[]])[0]
        docs = result.get("documents", [[]])[0]
        dists = result.get("distances", [[]])[0]

        for meta, doc, dist in zip(metas, docs, dists):
            if meta is None:
                continue
            paper = Paper.from_dict(meta)
            paper.embedding = None  # not returned in query
            papers.append(paper)

        return papers

    async def get_recent(
        self,
        domain: Optional[str] = None,
        days: int = 7,
        n: int = 10,
    ) -> List[Paper]:
        """Get papers ingested within the last N days, optionally filtered by domain."""
        if not self._started or not self._collection:
            return []

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        where_filter: Dict[str, Any] = {"ingested_at": {"$gte": cutoff}}
        if domain:
            where_filter = {"$and": [{"domain": domain}, {"ingested_at": {"$gte": cutoff}}]}

        try:
            total = self._collection.count()
            result = self._collection.get(
                where=where_filter,
                limit=min(n, max(total, 1)),
            )
        except Exception as e:
            logger.warning(f"[KnowledgeStore] get_recent error: {e}")
            return []

        papers: List[Paper] = []
        metas = result.get("metadatas", [])
        if metas and isinstance(metas, list):
            for meta in metas:
                if meta is None:
                    continue
                papers.append(Paper.from_dict(meta))

        # Sort by ingested_at descending
        papers.sort(key=lambda p: p.ingested_at, reverse=True)
        return papers[:n]

    async def get_by_domain(self, domain: str, n: int = 20) -> List[Paper]:
        """Get papers for a specific domain."""
        if not self._started or not self._collection:
            return []

        try:
            result = self._collection.get(
                where={"domain": domain},
                limit=n,
            )
        except Exception as e:
            logger.warning(f"[KnowledgeStore] get_by_domain error: {e}")
            return []

        papers: List[Paper] = []
        for meta in result.get("metadatas", []):
            if meta is None:
                continue
            papers.append(Paper.from_dict(meta))
        return papers

    async def paper_exists(self, paper_id: str) -> bool:
        """Check if a paper ID exists in the store."""
        if not self._started or not self._collection:
            return False
        return self._paper_exists_sync(paper_id)

    def _paper_exists_sync(self, paper_id: str) -> bool:
        """Synchronous existence check (used inside async methods)."""
        try:
            result = self._collection.get(ids=[paper_id])
            docs = result.get("documents", [])
            return len(docs) > 0 and docs[0] is not None
        except Exception:
            return False
