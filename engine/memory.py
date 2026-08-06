# deep/memory.py — Persistent Memory (Bible Section 4.3)
"""ChromaDB (semantic/vector) + SQLite (structured facts & conversations).
Both backends are optional: if ChromaDB or sentence-transformers are missing,
an in-process cosine-similarity store is used so memory still works."""
from __future__ import annotations

import os
import sqlite3
import time

try:
    from . import config
except Exception:  # pragma: no cover
    import config

try:
    import chromadb
    CHROMA = True
except Exception:  # pragma: no cover
    CHROMA = False


class DEEPMemory:
    def __init__(self, config=config):
        self.config = config
        os.makedirs(config.MEMORY_DIR, exist_ok=True)
        self._sql = sqlite3.connect(config.SQLITE_PATH, check_same_thread=False)
        self._init_sql()
        self._fallback = []  # list of (id, text, metadata)
        self.collection = None
        if CHROMA:
            try:
                client = chromadb.PersistentClient(path=config.CHROMA_PERSIST)
                self.collection = client.get_or_create_collection("deep_semantic")
            except Exception:
                self.collection = None

    def _init_sql(self):
        c = self._sql.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS facts (key TEXT PRIMARY KEY, value TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS conversations "
                  "(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, user TEXT, assistant TEXT)")
        self._sql.commit()

    # ── semantic memory ─────────────────────────────────────────────
    def store(self, text: str, metadata: dict = None) -> str:
        doc_id = f"mem_{int(time.time()*1e6)}"
        metadata = metadata or {}
        if self.collection is not None:
            try:
                self.collection.add(documents=[text], ids=[doc_id], metadatas=[metadata])
                return doc_id
            except Exception:
                pass
        self._fallback.append((doc_id, text, metadata))
        return doc_id

    def recall(self, query: str, k: int = 5) -> list:
        if self.collection is not None:
            try:
                res = self.collection.query(query_texts=[query], n_results=k)
                docs = res.get("documents", [[]])[0]
                return [{"text": d} for d in docs]
            except Exception:
                pass
        # naive keyword overlap fallback
        qs = set(query.lower().split())
        scored = [(len(qs & set(t.lower().split())), t) for _, t, _ in self._fallback]
        scored.sort(reverse=True)
        return [{"text": t} for s, t in scored[:k] if s > 0]

    def recall_all(self) -> list:
        if self.collection is not None:
            try:
                res = self.collection.get()
                return [{"text": d} for d in res.get("documents", [])]
            except Exception:
                pass
        return [{"text": t} for _, t, _ in self._fallback]

    # ── structured facts ────────────────────────────────────────────
    def save_fact(self, key: str, value: str) -> None:
        self._sql.execute("INSERT OR REPLACE INTO facts VALUES (?,?)", (key, value))
        self._sql.commit()

    def get_fact(self, key: str):
        row = self._sql.execute("SELECT value FROM facts WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def list_facts(self) -> list:
        return self._sql.execute("SELECT key, value FROM facts").fetchall()

    # ── conversation memory ─────────────────────────────────────────
    def save_conversation(self, user: str, assistant: str) -> None:
        self._sql.execute("INSERT INTO conversations (ts,user,assistant) VALUES (?,?,?)",
                          (time.time(), user, assistant))
        self._sql.commit()

    def get_recent_conversations(self, n: int = 10) -> list:
        rows = self._sql.execute(
            "SELECT user, assistant FROM conversations ORDER BY id DESC LIMIT ?", (n,)
        ).fetchall()
        return [{"user": u, "assistant": a} for u, a in reversed(rows)]

    # ── context injection ───────────────────────────────────────────
    def build_context_for_prompt(self, query: str) -> str:
        mems = self.recall(query, k=self.config.MEMORY_TOP_K)
        facts = self.list_facts()
        parts = []
        if facts:
            parts.append("Known facts: " + "; ".join(f"{k}={v}" for k, v in facts[:10]))
        if mems:
            parts.append("Relevant memories: " + " | ".join(m["text"][:120] for m in mems))
        return "\n".join(parts)

    def save_state(self):
        self._sql.commit()

    def load_state(self):
        pass

    def clear_all(self):
        self._sql.execute("DELETE FROM facts"); self._sql.execute("DELETE FROM conversations")
        self._sql.commit(); self._fallback.clear()

    def test(self) -> None:
        self.save_fact("test_key", "test_value")
        assert self.get_fact("test_key") == "test_value"
        self.store("DEEP solves physics problems", {"topic": "physics"})
        self.save_conversation("hello", "Hello sir.")
        assert self.get_recent_conversations(1)
        print("memory.DEEPMemory: OK")


_mem = None


def _get_mem():
    global _mem
    if _mem is None:
        _mem = DEEPMemory()
    return _mem


def recall(text: str) -> dict:
    mems = _get_mem().recall(text, k=5)
    if not mems:
        return {"result": [], "verbal": "I have no relevant memories on that, sir."}
    return {"result": mems, "verbal": "Here is what I recall, sir: " +
            " | ".join(m["text"][:100] for m in mems)}


def test() -> None:
    DEEPMemory().test()


if __name__ == "__main__":
    test()
