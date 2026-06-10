"""
core/graph_enrich.py — densify + enrich the knowledge graph for the Memory Graph UI.

Two jobs, both optional and fail-soft (if anything errors, callers fall back to
the raw graph):

1. SEMANTIC EDGES — the explicitly-extracted relationships are sparse (most
   entities are isolated `concept` nodes). We embed each entity with a local
   MiniLM model and connect every node to its top-k nearest neighbours above a
   cosine threshold. These "similar" edges turn a fact list into a dense web —
   the interconnection an advanced AI memory graph should show.

2. RICHER NODES — attach the context sentences (pulled from relationship
   evidence) + a one-line summary to each entity, so the UI bubble can show
   real detail (sentences, numbers, category) instead of just a bare word.

The embedder is loaded lazily and shared; per-entity vectors are cached by a
content hash so repeat vault calls are cheap.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_MODEL = None                      # lazily-loaded SentenceTransformer
_VEC_CACHE: Dict[str, Any] = {}    # content-hash -> np.ndarray (unit vector)
_CACHE_LOADED = False
_CACHE_DIRTY = False

from pathlib import Path
_CACHE_FILE = Path(__file__).parent.parent / "data" / "knowledge_graph" / "vec_cache.json"


def _load_cache() -> None:
    """Load persisted entity vectors so a restart doesn't re-embed everything
    (that was the 20-35s cold load). Vectors are keyed by content hash, so stale
    entries simply go unused."""
    global _CACHE_LOADED
    if _CACHE_LOADED:
        return
    _CACHE_LOADED = True
    try:
        if _CACHE_FILE.exists():
            import numpy as np
            raw = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            for h, v in raw.items():
                _VEC_CACHE[h] = np.asarray(v, dtype="float32")
            logger.info(f"[graph_enrich] loaded {len(_VEC_CACHE)} cached vectors")
    except Exception as e:
        logger.warning(f"[graph_enrich] vec cache load failed: {e}")


def _save_cache() -> None:
    global _CACHE_DIRTY
    if not _CACHE_DIRTY:
        return
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        out = {h: (v.tolist() if hasattr(v, "tolist") else list(v)) for h, v in _VEC_CACHE.items()}
        _CACHE_FILE.write_text(json.dumps(out), encoding="utf-8")
        _CACHE_DIRTY = False
    except Exception as e:
        logger.warning(f"[graph_enrich] vec cache save failed: {e}")


def _get_model():
    """Load the MiniLM embedder once (same model academic_rag uses)."""
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("[graph_enrich] embedder loaded (all-MiniLM-L6-v2)")
    return _MODEL


def _doc_for(ent: Dict[str, Any], context: str) -> str:
    """The text we embed for an entity — name carries most signal, type/aliases/
    context disambiguate single-word concepts."""
    parts = [str(ent.get("name", ""))]
    t = ent.get("type")
    if t and t != "unknown":
        parts.append(str(t))
    al = ent.get("aliases") or []
    if al:
        parts.append(", ".join(al[:4]))
    desc = ent.get("description")
    if desc:
        parts.append(str(desc)[:160])
    if context:
        parts.append(context[:160])
    return ". ".join(p for p in parts if p)


def _hash(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _context_map(relationships: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """entity-id -> de-duped evidence sentences drawn from its relationships."""
    out: Dict[str, List[str]] = {}
    for r in relationships:
        ev = [e for e in (r.get("evidence") or []) if e and len(e.strip()) > 3]
        if not ev:
            continue
        for end in (r.get("source"), r.get("target")):
            if not end:
                continue
            bucket = out.setdefault(end, [])
            for s in ev:
                s = s.strip()
                if s not in bucket:
                    bucket.append(s)
    return out


def enrich(
    entities: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
    knn: int = 3,
    threshold: float = 0.42,
    max_semantic: int = 600,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (enriched_entities, semantic_edges). Never raises — on any failure
    returns the entities with context attached and an empty edge list."""
    ctx = _context_map(relationships)

    # 1) Attach context + derived numbers to every entity (cheap, no model).
    for e in entities:
        eid = e.get("id")
        sentences = ctx.get(eid, [])
        e["context"] = sentences[:4]
        e["link_count"] = sum(
            1 for r in relationships if r.get("source") == eid or r.get("target") == eid
        )

    # 2) Semantic kNN edges (needs the embedder + numpy; fail-soft).
    semantic: List[Dict[str, Any]] = []
    try:
        import numpy as np
        global _CACHE_DIRTY

        _load_cache()
        docs, ids, to_embed, to_embed_idx = [], [], [], []
        vecs: List[Optional[Any]] = [None] * len(entities)

        for i, e in enumerate(entities):
            doc = _doc_for(e, (e.get("context") or [""])[0])
            ids.append(e.get("id"))
            docs.append(doc)
            h = _hash(doc)
            cached = _VEC_CACHE.get(h)
            if cached is not None:
                vecs[i] = cached
            else:
                to_embed.append(doc)
                to_embed_idx.append((i, h))

        # Only pay the model load + encode when there's genuinely new text. With a
        # warm cache this branch is skipped entirely → instant, no model load.
        if to_embed:
            embedded = _get_model().encode(to_embed, normalize_embeddings=True)
            for (i, h), v in zip(to_embed_idx, embedded):
                v = np.asarray(v, dtype="float32")
                _VEC_CACHE[h] = v
                vecs[i] = v
            _CACHE_DIRTY = True
            _save_cache()

        mat = np.vstack([v for v in vecs])           # (N, d), unit-normalised
        sims = mat @ mat.T                            # cosine similarity matrix
        np.fill_diagonal(sims, -1.0)

        # Don't duplicate pairs that already have an explicit relationship.
        explicit = set()
        for r in relationships:
            s, t = r.get("source"), r.get("target")
            if s and t:
                explicit.add(frozenset((s, t)))

        seen = set()
        n = len(entities)
        k = max(1, min(knn, n - 1))
        for i in range(n):
            order = np.argsort(-sims[i])[:k]
            for j in order:
                j = int(j)
                score = float(sims[i, j])
                if score < threshold:
                    continue
                pair = frozenset((ids[i], ids[j]))
                if ids[i] == ids[j] or pair in explicit or pair in seen:
                    continue
                seen.add(pair)
                semantic.append({
                    "id": f"sim_{ids[i]}_{ids[j]}",
                    "source": ids[i],
                    "target": ids[j],
                    "relation": "similar",
                    "confidence": round(score, 3),
                    "kind": "semantic",
                    "evidence": [],
                })
                if len(semantic) >= max_semantic:
                    break
            if len(semantic) >= max_semantic:
                break
    except Exception as e:  # noqa: BLE001 — enrichment must never break the vault
        logger.warning(f"[graph_enrich] semantic edges skipped: {e}")
        semantic = []

    return entities, semantic
