"""
core/personal_rag.py — DEEP as a second brain over Aryan's own documents.

Watches a folder, extracts text from new/changed files (PDF/DOCX/TXT/MD/code),
chunks + embeds them into long-term memory as `document` chunks, and offers an
explicit search ("what did I write about X in my notes?") with source citations.

Builds on the existing LTM (Chroma) store — document chunks also surface in normal
chat recall, but `search()` gives a focused, cited answer. Incremental: a manifest
tracks file mtimes so re-scans only ingest what changed. Fail-soft throughout.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_TEXT_EXT = {".txt", ".md", ".markdown", ".py", ".js", ".ts", ".json", ".csv",
             ".html", ".css", ".log", ".rst", ".yaml", ".yml"}


def _chunk(text: str, size: int = 1000, overlap: int = 200) -> List[str]:
    text = " ".join(text.split())
    out, i = [], 0
    while i < len(text):
        out.append(text[i:i + size])
        i += size - overlap
    return [c for c in out if c.strip()]


def _docx_text(path: Path) -> str:
    """Extract text from a .docx without python-docx (it's zipped XML)."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = xml.replace("</w:p>", "\n")
    return re.sub(r"<[^>]+>", "", xml)


def _extract(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        import fitz  # PyMuPDF
        doc = fitz.open(str(path))
        return "\n".join(page.get_text() for page in doc)
    if ext == ".docx":
        return _docx_text(path)
    if ext in _TEXT_EXT:
        for enc in ("utf-8", "latin-1"):
            try:
                return path.read_text(encoding=enc)
            except Exception:
                continue
        return path.read_bytes().decode("utf-8", errors="ignore")
    return ""   # unsupported


class PersonalRAG:
    SUPPORTED = _TEXT_EXT | {".pdf", ".docx"}

    def __init__(self, ltm, folder: Optional[Path] = None):
        self.ltm = ltm
        self.folder = Path(folder) if folder else (Path(__file__).parent.parent / "data" / "personal_docs")
        self.folder.mkdir(parents=True, exist_ok=True)
        self._manifest_file = self.folder / ".manifest.json"
        self.manifest: Dict[str, float] = {}
        try:
            if self._manifest_file.exists():
                self.manifest = json.loads(self._manifest_file.read_text(encoding="utf-8"))
        except Exception:
            self.manifest = {}

    def _save_manifest(self) -> None:
        try:
            self._manifest_file.write_text(json.dumps(self.manifest), encoding="utf-8")
        except Exception as e:
            logger.warning(f"[personal_rag] manifest save failed: {e}")

    # ── ingest ────────────────────────────────────────────────────────────────
    def ingest_text(self, text: str, source: str) -> int:
        chunks = _chunk(text)
        digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:10]
        stored = 0
        for idx, ch in enumerate(chunks):
            try:
                self.ltm.store(
                    memory_type="document",
                    content=ch,
                    metadata={"source": source, "chunk": idx, "doc_id": digest},
                    importance=1.3,
                    memory_id=f"doc_{digest}_{idx}",
                )
                stored += 1
            except Exception as e:
                logger.warning(f"[personal_rag] store chunk {idx} failed: {e}")
        return stored

    def scan(self, force: bool = False) -> Dict[str, Any]:
        """Ingest new/changed files in the watch folder. Returns a summary."""
        ingested, chunks, skipped = [], 0, 0
        for p in sorted(self.folder.rglob("*")):
            if not p.is_file() or p.name.startswith(".") or p.suffix.lower() not in self.SUPPORTED:
                continue
            key = str(p.relative_to(self.folder))
            mtime = p.stat().st_mtime
            if not force and self.manifest.get(key) == mtime:
                skipped += 1
                continue
            try:
                text = _extract(p)
            except Exception as e:
                logger.warning(f"[personal_rag] extract {key} failed: {e}")
                continue
            if not text.strip():
                continue
            n = self.ingest_text(text, source=p.name)
            chunks += n
            ingested.append({"file": key, "chunks": n})
            self.manifest[key] = mtime
        if ingested:
            self._save_manifest()
        return {"folder": str(self.folder), "ingested": ingested,
                "files_ingested": len(ingested), "chunks": chunks, "skipped": skipped}

    # ── query ─────────────────────────────────────────────────────────────────
    def search(self, query: str, k: int = 5) -> Dict[str, Any]:
        try:
            hits = self.ltm.recall(query, k=k, memory_type="document")
        except Exception as e:
            return {"query": query, "error": str(e), "results": []}
        results = []
        for h in hits:
            md = getattr(h, "metadata", {}) or {}
            results.append({
                "source": md.get("source", "document"),
                "chunk": md.get("chunk"),
                "text": (getattr(h, "content", "") or "")[:600],
            })
        return {"query": query, "results": results, "count": len(results)}

    def stats(self) -> Dict[str, Any]:
        docs = {}
        try:
            coll = getattr(self.ltm, "_collection", None)
            if coll is not None:
                got = coll.get(where={"memory_type": "document"})
                for md in (got.get("metadatas") or []):
                    src = (md or {}).get("source", "?")
                    docs[src] = docs.get(src, 0) + 1
        except Exception:
            pass
        return {"folder": str(self.folder), "tracked_files": len(self.manifest),
                "documents": docs, "total_chunks": sum(docs.values())}
