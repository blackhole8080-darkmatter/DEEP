"""
memory.py

Persistent memory / RAG for DEEP using ChromaDB.

What it does (starter implementation):
- Stores each user/assistant message into a Chroma collection with metadata.
- Embeds text via SentenceTransformers.
- Retrieves relevant past messages for a new user prompt (top-k).
- Exposes a small API used by:
  - main.py (add_user_message / add_assistant_message)
  - brain.py (memory.get_rag_context(prompt))
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

try:
    from .config import Settings
except ImportError:
    from config import Settings


@dataclass(frozen=True, slots=True)
class ChatMessageRecord:
    role: str  # "user" or "assistant"
    content: str
    created_at_epoch: float


class MemorySystem:
    """ChromaDB-backed persistent memory for chat + retrieval."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

        # Persistent on-disk storage for memory.
        self._client = chromadb.PersistentClient(path=self._settings.chroma_dir)

        # Embedding function for vectorizing text.
        self._embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        # Create or load the collection.
        self._collection = self._client.get_or_create_collection(
            name=self._settings.chroma_collection,
            embedding_function=self._embedding_fn,
        )

    def add_user_message(self, text: str) -> None:
        self._add_message(role="user", content=text)

    def add_assistant_message(self, text: str) -> None:
        self._add_message(role="assistant", content=text)

    def get_rag_context(self, query_text: str) -> str:
        """
        Retrieve top-k relevant message snippets for the query_text.
        Returns a plain text block to be injected into the LLM prompt.
        """
        query_text = query_text.strip()
        if not query_text:
            return ""

        n_results = max(1, self._settings.rag_top_k)

        results = self._collection.query(
            query_texts=[query_text],
            n_results=n_results,
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        chunks: list[str] = []
        for doc, meta in zip(docs, metas):
            role = ""
            if isinstance(meta, dict):
                role = str(meta.get("role", ""))
            prefix = f"[{role}] " if role else ""
            chunks.append(f"{prefix}{doc}")

        return "\n".join(chunks).strip()

    def _add_message(self, role: str, content: str) -> None:
        content = content.strip()
        if not content:
            return

        created_at = time.time()
        record = ChatMessageRecord(role=role, content=content, created_at_epoch=created_at)

        # Use a deterministic-ish unique id for the record.
        # For a starter this timestamp-based id is fine.
        doc_id = f"{int(created_at * 1000)}_{role}"

        self._collection.add(
            ids=[doc_id],
            documents=[record.content],
            metadatas=[{"role": record.role, "created_at": record.created_at_epoch}],
        )
