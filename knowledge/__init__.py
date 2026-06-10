"""
deep/knowledge — Knowledge Intelligence Layer for DEEP.

Components:
    KnowledgeStore        — ChromaDB persistent vector store for papers
    KnowledgeIngester     — Scheduled pull from arXiv, PubMed, NVD, NASA ADS
    BreakthroughDetector  — Scores papers for genuine significance
    BriefingEngine        — Daily spoken science briefings
    ConceptLinker         — Cross-domain synthesis and concept explanation

Usage:
    from knowledge import KnowledgeStore, KnowledgeIngester
"""

from __future__ import annotations

from .knowledge_store import Paper, KnowledgeStore
from .ingester import KnowledgeIngester, IngestResult
from .breakthrough_detector import BreakthroughDetector
from .briefing_engine import BriefingEngine, Briefing
from .concept_linker import ConceptLinker, ConnectionResult, FieldSummary

__all__ = [
    "Paper",
    "KnowledgeStore",
    "KnowledgeIngester",
    "IngestResult",
    "BreakthroughDetector",
    "BriefingEngine",
    "Briefing",
    "ConceptLinker",
    "ConnectionResult",
    "FieldSummary",
]
