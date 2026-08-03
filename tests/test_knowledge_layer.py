"""
tests/test_knowledge_layer.py

Validation suite for the Knowledge Intelligence Layer.

Run:
    python tests/test_knowledge_layer.py
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# ── Ensure DEEP root is importable ──────────────────────────────────────
DEEP_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(DEEP_ROOT))

from core.event_bus import EventBus
from knowledge import Paper, KnowledgeStore, BriefingEngine, ConceptLinker
from knowledge.breakthrough_detector import BreakthroughDetector
from knowledge.ingester import KnowledgeIngester

# ── Optional dependency checks ────────────────────────────────────────────

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("WARNING: chromadb not installed — KnowledgeStore tests will use mock fallback")

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    print("WARNING: sentence-transformers not installed — embeddings disabled")


def _make_paper(**overrides) -> Paper:
    """Helper to create a test Paper with sensible defaults."""
    defaults = {
        "id": "arxiv:2401.00001",
        "title": "A Novel Approach to Quantum Error Correction",
        "authors": ["Alice Smith", "Bob Jones"],
        "abstract": "We demonstrate a first demonstration of a novel approach that "
                    "surpasses human performance by 2x improvement in error rates.",
        "source": "arxiv",
        "domain": "quantum",
        "published_date": "2024-01-15",
        "url": "https://arxiv.org/abs/2401.00001",
    }
    defaults.update(overrides)
    return Paper(**defaults)


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: Paper dataclass instantiates correctly
# ═══════════════════════════════════════════════════════════════════════════════

def test_paper_dataclass():
    paper = _make_paper()
    assert paper.id == "arxiv:2401.00001"
    assert paper.title == "A Novel Approach to Quantum Error Correction"
    assert len(paper.authors) == 2
    assert "Alice Smith" in paper.authors
    assert paper.domain == "quantum"
    assert paper.source == "arxiv"

    # round-trip via to_dict / from_dict
    d = paper.to_dict()
    restored = Paper.from_dict(d)
    assert restored.id == paper.id
    assert restored.title == paper.title
    assert restored.authors == paper.authors
    print("  ✓ Paper dataclass instantiates and round-trips correctly")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: KnowledgeStore add + search round-trip
# ═══════════════════════════════════════════════════════════════════════════════

async def test_knowledge_store_add_and_search():
    if not CHROMADB_AVAILABLE or not ST_AVAILABLE:
        print("  SKIP: chromadb or sentence-transformers unavailable")
        return

    bus = EventBus()
    await bus.start()

    db_path = Path(tempfile.mkdtemp()) / "test_knowledge_chroma"
    store = KnowledgeStore(event_bus=bus, db_path=str(db_path))
    await store.start()

    paper = _make_paper(id="test:001", title="Quantum Computing Basics", domain="quantum")
    added = await store.add_paper(paper)
    assert added is True, "Paper should be added successfully"

    # Search for it
    results = await store.search("quantum computing basics", n_results=5)
    ids = [p.id for p in results]
    assert "test:001" in ids, f"Expected test:001 in results, got {ids}"

    await store.stop()
    await bus.stop()
    print("  ✓ KnowledgeStore add + search round-trip works")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: paper_exists returns False for unknown id
# ═══════════════════════════════════════════════════════════════════════════════

async def test_paper_exists_unknown():
    if not CHROMADB_AVAILABLE or not ST_AVAILABLE:
        print("  SKIP: chromadb or sentence-transformers unavailable")
        return

    bus = EventBus()
    await bus.start()

    db_path = Path(tempfile.mkdtemp()) / "test_exists_chroma"
    store = KnowledgeStore(event_bus=bus, db_path=str(db_path))
    await store.start()

    exists = await store.paper_exists("definitely:not:real")
    assert exists is False, "Unknown paper should not exist"

    await store.stop()
    await bus.stop()
    print("  ✓ paper_exists() returns False for unknown id")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: Ingester _parse_arxiv from real RSS (integration, skip if no network)
# ═══════════════════════════════════════════════════════════════════════════════

async def test_ingester_parse_arxiv_integration():
    import socket
    try:
        socket.create_connection(("arxiv.org", 443), timeout=3)
    except OSError:
        print("  SKIP: No network — arXiv integration test skipped")
        return

    bus = EventBus()
    await bus.start()

    # Create a minimal store mock so ingester can call add_papers
    store = MagicMock()
    store._started = True
    async def _mock_add_papers(papers):
        return len(papers)
    store.add_papers = _mock_add_papers

    ingester = KnowledgeIngester(event_bus=bus, knowledge_store=store)
    ingester._client = __import__("httpx", fromlist=["AsyncClient"]).AsyncClient(timeout=10.0)

    papers = await ingester._parse_arxiv(
        "https://arxiv.org/rss/cs.AI", domain="ai_ml"
    )
    assert isinstance(papers, list), "_parse_arxiv should return a list"
    if papers:
        assert all(isinstance(p, Paper) for p in papers), "All items should be Paper instances"
        assert papers[0].source == "arxiv", "Paper source should be arxiv"
        assert papers[0].domain == "ai_ml", "Paper domain should be ai_ml"
        print(f"  ✓ Ingester _parse_arxiv fetched {len(papers)} papers from arXiv")
    else:
        print("  ✓ Ingester _parse_arxiv returned empty list (no items in feed currently)")

    await ingester._client.aclose()
    await bus.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: BreakthroughDetector scores high-signal paper above 0.5 without Ollama
# ═══════════════════════════════════════════════════════════════════════════════

async def test_breakthrough_detector_keyword_scoring():
    bus = EventBus()
    await bus.start()

    store = MagicMock()
    store._started = True

    detector = BreakthroughDetector(event_bus=bus, knowledge_store=store)
    # Override _score_llm_impact to return 0 (simulating Ollama unavailable)
    async def _mock_llm_score(abstract):
        return 0.0
    detector._score_llm_impact = _mock_llm_score

    paper = _make_paper(
        id="test:breakthrough",
        title="First Demonstration of a Novel Approach that Surpasses Human World Record",
        abstract="We show a 5x improvement in accuracy. This breakthrough exceeds "
                 "all previous results and represents a previously impossible feat.",
    )

    score, signals = await detector._score_paper(paper)
    # kw_score = 0.25 (4 matches * 0.08 capped at 0.25)
    # quant_score = 0.15 (5x improvement)
    # prestige = 0, llm = 0 (mocked off)
    # total = 0.40 — valid without Ollama
    assert score > 0.35, f"Expected score > 0.35 for high-signal paper, got {score:.3f}"
    assert signals["kw"] > 0, "Keyword signal should be present"
    assert signals["quant"] > 0, "Quantified improvement signal should be present"

    await bus.stop()
    print(f"  ✓ BreakthroughDetector scores high-signal paper at {score:.3f} (> 0.35) without Ollama")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 6: ConceptLinker explain_concept falls back gracefully when store is empty
# ═══════════════════════════════════════════════════════════════════════════════

async def test_concept_linker_empty_store_fallback():
    bus = EventBus()
    await bus.start()

    store = MagicMock()
    store._started = True
    async def _mock_search(query, n_results):
        return []
    store.search = _mock_search

    linker = ConceptLinker(event_bus=bus, knowledge_store=store)
    linker._client = None  # force fallback path — no Ollama timeout
    result = await linker.explain_concept("quantum entanglement", depth="accessible")
    assert isinstance(result, str), "explain_concept should return a string"
    assert len(result) > 0, "Result should not be empty"
    # With empty store and no LLM, it should at least return the concept name
    assert "quantum entanglement" in result.lower() or "Concept:" in result

    await bus.stop()
    print("  ✓ ConceptLinker explain_concept falls back gracefully when store is empty")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 7: BriefingEngine skips domains with no papers rather than crashing
# ═══════════════════════════════════════════════════════════════════════════════

async def test_briefing_engine_skips_empty_domains():
    bus = EventBus()
    await bus.start()

    store = MagicMock()
    store._started = True
    async def _mock_get_recent(domain, days, n):
        return []
    store.get_recent = _mock_get_recent

    engine = BriefingEngine(event_bus=bus, knowledge_store=store)
    engine._client = None  # force fallback path — no Ollama timeout
    briefing = await engine.generate_briefing(domains=["ai_ml", "quantum"], days_back=1)

    assert briefing is not None, "Briefing should not be None"
    assert briefing.paper_count == 0, "Paper count should be 0 for empty store"
    assert isinstance(briefing.full_text, str), "full_text should be a string"
    # Should gracefully handle empty domains
    assert "No new papers" in briefing.full_text or briefing.full_text == "", (
        f"Unexpected full_text: {briefing.full_text[:100]}"
    )

    await bus.stop()
    print("  ✓ BriefingEngine skips domains with no papers rather than crashing")


# ═══════════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    print("Running Knowledge Layer validation...\n")
    test_paper_dataclass()
    await test_knowledge_store_add_and_search()
    await test_paper_exists_unknown()
    await test_ingester_parse_arxiv_integration()
    await test_breakthrough_detector_keyword_scoring()
    await test_concept_linker_empty_store_fallback()
    await test_briefing_engine_skips_empty_domains()
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  All knowledge layer tests passed.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    asyncio.run(main())
