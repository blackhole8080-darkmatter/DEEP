"""Knowledge and Science Briefing endpoints."""
from fastapi import APIRouter
from interface.deps import services

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

# Personal-document endpoints live under /api/knowledge/* (what the frontend
# calls). They need their own un-prefixed router — declaring them on `router`
# above served them at /knowledge/api/knowledge/*, so the UI's upload and
# document list both 404'd.
docs_router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

@router.get("/status")
async def knowledge_status():
    """Return KnowledgeStore operational status."""
    return services.knowledge_store.status()

@router.get("/search")
async def knowledge_search(q: str, domain: str = None, n: int = 5):
    """Semantic search over the knowledge store."""
    papers = await services.knowledge_store.search(q, domain=domain, n_results=n)
    return {
        "query": q,
        "results": [p.to_dict() for p in papers],
        "count": len(papers),
    }

@router.get("/recent")
async def knowledge_recent(domain: str = None, days: int = 7):
    """Get recently ingested papers."""
    papers = await services.knowledge_store.get_recent(domain=domain, days=days, n=20)
    return {
        "papers": [p.to_dict() for p in papers],
        "count": len(papers),
    }

@router.post("/briefing")
async def knowledge_briefing(domains: list = None, days_back: int = 1):
    """Generate an on-demand science briefing."""
    briefing = await services.briefing_engine.generate_briefing(
        domains=domains, days_back=days_back,
    )
    return {
        "full_text": briefing.full_text,
        "paper_count": briefing.paper_count,
        "domain_count": len(briefing.domain_sections),
        "duration_estimate_seconds": briefing.duration_estimate_seconds,
    }

@router.get("/domains")
async def knowledge_domains():
    """List available domains in the knowledge store."""
    status = services.knowledge_store.status()
    return {
        "domains": list(status.get("papers_by_domain", {}).keys()),
        "papers_by_domain": status.get("papers_by_domain", {}),
    }

@router.post("/explain")
async def knowledge_explain(body: dict):
    """Explain a concept at requested depth."""
    concept = body.get("concept", "")
    depth = body.get("depth", "graduate")
    explanation = await services.concept_linker.explain_concept(concept, depth=depth)
    return {"concept": concept, "depth": depth, "explanation": explanation}

@router.post("/connect")
async def knowledge_connect(body: dict):
    """Find connections between two concepts."""
    concept_a = body.get("concept_a", "")
    concept_b = body.get("concept_b", "")
    result = await services.concept_linker.find_connections(concept_a, concept_b)
    return {
        "concept_a": result.concept_a,
        "concept_b": result.concept_b,
        "connections": result.connections,
        "evidence": result.evidence,
        "confidence": result.confidence,
    }


import hashlib
from fastapi import UploadFile, File
from typing import Dict
def _chunk_text(text: str, size: int = 900, overlap: int = 150):
    """Split text into overlapping chunks for embedding."""
    text = " ".join(text.split())  # normalise whitespace
    chunks, i = [], 0
    while i < len(text):
        chunks.append(text[i:i + size])
        i += size - overlap
    return [c for c in chunks if c.strip()]


def _extract_text(filename: str, raw: bytes) -> str:
    """Best-effort text extraction from txt/md/pdf bytes."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=raw, filetype="pdf")
            return "\n".join(page.get_text() for page in doc)
        except Exception as e:
            raise RuntimeError(f"PDF parse failed ({type(e).__name__})")
    if name.endswith(".docx"):
        try:
            import io, zipfile, re as _re
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                xml = z.read("word/document.xml").decode("utf-8", "ignore")
            return _re.sub(r"<[^>]+>", "", xml.replace("</w:p>", "\n"))
        except Exception as e:
            raise RuntimeError(f"DOCX parse failed ({type(e).__name__})")
    # txt / md / code / fallback
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


@docs_router.post("/ingest")
async def knowledge_ingest(file: UploadFile = File(...)):
    """
    Personal knowledge ingestion: extract text from an uploaded document
    (pdf/txt/md/code), chunk it, and embed each chunk into long-term memory.
    Ingested chunks are then recalled automatically into chat context — DEEP
    becomes a second brain over Aryan's own files. Fully local.
    """
    try:
        raw = await file.read()
        if not raw:
            return {"ok": False, "error": "empty file"}
        text = _extract_text(file.filename, raw)
        if not text.strip():
            return {"ok": False, "error": "no extractable text"}
        chunks = _chunk_text(text)
        src = file.filename or "document"
        digest = hashlib.sha1(src.encode("utf-8")).hexdigest()[:10]
        stored = 0
        for idx, ch in enumerate(chunks):
            try:
                services.ltm.store(
                    memory_type="document",
                    content=ch,
                    metadata={"source": src, "chunk": idx, "doc_id": digest},
                    importance=1.3,
                    memory_id=f"doc_{digest}_{idx}",
                )
                stored += 1
            except Exception as _e:
                print(f"[knowledge] chunk {idx} store failed: {_e}")
        try:
            await services.event_bus.publish("knowledge_ingested", {"source": src, "chunks": stored})
        except Exception:
            pass
        return {"ok": True, "source": src, "chunks": stored,
                "chars": len(text), "doc_id": digest}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


@docs_router.get("/list")
async def knowledge_list():
    """List ingested documents (grouped by source) from long-term memory."""
    docs: Dict[str, dict] = {}
    try:
        coll = getattr(services.ltm, "_collection", None)
        if coll is not None:
            res = coll.get(where={"memory_type": "document"})
            for meta in (res.get("metadatas") or []):
                src = meta.get("source", "unknown")
                d = docs.setdefault(src, {"source": src, "chunks": 0, "doc_id": meta.get("doc_id")})
                d["chunks"] += 1
    except Exception as e:
        return {"ok": False, "error": str(e), "documents": []}
    return {"ok": True, "documents": list(docs.values()), "count": len(docs)}


