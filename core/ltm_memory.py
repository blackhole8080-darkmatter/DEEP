"""
ltm_memory.py

Long-term Memory (LTM) with vector embeddings for JARVIS.

Features:
- Persistent memory storage with ChromaDB
- Semantic search via embeddings
- Conversation threading
- Fact storage and retrieval
- User preferences learning
- Contextual recall

Usage:
    from DEEP.core.ltm_memory import LongTermMemory
    
    ltm = LongTermMemory()
    
    # Store a memory
    ltm.store("fact", "User's favorite color is blue", metadata={"topic": "preferences"})
    
    # Recall relevant memories
    results = ltm.recall("What does the user like?", k=5)
    
    # Conversation threading
    thread_id = ltm.start_conversation_thread("Project Alpha Discussion")
    ltm.add_to_thread(thread_id, "We decided to use Python for the backend")

Requirements:
    pip install chromadb sentence-transformers
"""

from __future__ import annotations

import os
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path

# ChromaDB for vector storage
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

# Sentence transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Optional cross-encoder for reranking (gold-standard relevance, but heavier)
try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False

# Fallback: numpy for basic operations
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    content: str
    memory_type: str  # "fact", "conversation", "preference", "event"
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 1.0  # 0.0 to 2.0, higher = more important
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "importance": self.importance,
            "embedding": self.embedding
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "MemoryEntry":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            content=data["content"],
            memory_type=data["memory_type"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
            importance=data.get("importance", 1.0),
            embedding=data.get("embedding")
        )


@dataclass
class ConversationThread:
    """A threaded conversation with context."""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    entries: List[Dict[str, Any]] = field(default_factory=list)
    summary: Optional[str] = None
    is_active: bool = True
    
    def add_entry(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add entry to thread."""
        self.entries.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
        self.updated_at = datetime.now()


class LongTermMemory:
    """
    Long-term memory with semantic search for JARVIS.
    
    Provides:
    - Persistent storage of facts, preferences, and conversations
    - Semantic search via embeddings
    - Conversation threading with context
    - Automatic importance scoring
    """
    
    def __init__(
        self,
        data_dir: str = "./data/ltm",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Lazy cross-encoder reranker (loaded on first use if DEEP_RERANK=1)
        self._reranker = None
        self._reranker_name = os.getenv(
            "DEEP_RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

        # Initialize embedding model
        self._embedding_model = None
        self._embedding_model_name = embedding_model
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                print(f"Loading embedding model: {embedding_model}")
                self._embedding_model = SentenceTransformer(embedding_model)
                print(f"OK: Embedding model loaded")
            except Exception as e:
                print(f"WARN: Failed to load embedding model: {e}")
        
        # Initialize ChromaDB.
        # NOTE: chromadb.Client(...) is EPHEMERAL (in-memory) in modern chromadb -
        # the old chroma_db_dir setting is ignored, so the vector index vanished on
        # every restart and recall silently fell back to JSON keyword search.
        # PersistentClient writes the index to disk so semantic recall survives.
        self._chroma_client = None
        self._collection = None
        if CHROMA_AVAILABLE:
            try:
                chroma_dir = self.data_dir / "chroma_db"
                chroma_dir.mkdir(parents=True, exist_ok=True)
                self._chroma_client = chromadb.PersistentClient(path=str(chroma_dir))

                # Get or create collection
                self._collection = self._chroma_client.get_or_create_collection(
                    name="jarvis_memory",
                    metadata={"description": "JARVIS long-term memory"}
                )
                print(f"OK: Long-term memory initialized (persistent: {chroma_dir})")
            except Exception as e:
                print(f"WARN: ChromaDB initialization failed: {e}")
        
        # Conversation threads storage (JSON file)
        self._threads_file = self.data_dir / "conversation_threads.json"
        self._threads: Dict[str, ConversationThread] = {}
        self._active_thread_id: Optional[str] = None
        self._load_threads()

        # One-time backfill: index any JSON-backup memories that aren't yet in the
        # (previously ephemeral) vector store, so historical memories become
        # semantically recallable after the persistence fix.
        self._backfill_vector_store()

    def _backfill_vector_store(self) -> None:
        """Add memories present in memories.json but missing from the vector store."""
        if not (self._collection and self._embedding_model):
            return
        json_file = self.data_dir / "memories.json"
        if not json_file.exists():
            return
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                memories = json.load(f)
            if not memories:
                return
            existing = set(self._collection.get().get("ids", []) or [])
            added = 0
            for mem in memories:
                mid = mem.get("id")
                if not mid or mid in existing:
                    continue
                content = mem.get("content", "")
                emb = self._get_embedding(content)
                if not emb:
                    continue
                meta = mem.get("metadata", {}) or {}
                self._collection.add(
                    ids=[mid],
                    embeddings=[emb],
                    documents=[content],
                    metadatas=[{
                        "memory_type": mem.get("memory_type", "unknown"),
                        "timestamp": mem.get("timestamp", datetime.now().isoformat()),
                        "importance": mem.get("importance", 1.0),
                        **{k: v for k, v in meta.items() if isinstance(v, (str, int, float, bool))},
                    }],
                )
                added += 1
            if added:
                print(f"OK: Backfilled {added} memories into the vector store")
        except Exception as e:
            print(f"WARN: Vector store backfill skipped: {e}")
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding vector for text."""
        if self._embedding_model:
            try:
                embedding = self._embedding_model.encode(text)
                # Convert numpy array to list if needed
                if hasattr(embedding, 'tolist'):
                    embedding = embedding.tolist()
                return embedding
            except Exception as e:
                print(f"WARN: Embedding generation failed: {e}")
        return None
    
    def store(
        self,
        memory_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 1.0,
        memory_id: Optional[str] = None
    ) -> str:
        """
        Store a memory.
        
        Args:
            memory_type: Type of memory ("fact", "preference", "event", etc.)
            content: The content to store
            metadata: Additional metadata
            importance: Importance score (0.0-2.0)
            memory_id: Optional specific ID
        
        Returns:
            Memory ID
        """
        memory_id = memory_id or str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Get embedding
        embedding = self._get_embedding(content)
        
        # Create entry
        entry = MemoryEntry(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            timestamp=timestamp,
            metadata=metadata or {},
            importance=importance,
            embedding=embedding
        )
        
        # Store in ChromaDB if available
        if self._collection and embedding:
            try:
                self._collection.add(
                    ids=[memory_id],
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[{
                        "memory_type": memory_type,
                        "timestamp": timestamp.isoformat(),
                        "importance": importance,
                        **(metadata or {})
                    }]
                )
            except Exception as e:
                print(f"WARN: ChromaDB storage failed: {e}")
        
        # Also save to JSON backup
        self._save_to_json(entry)
        
        return memory_id
    
    def _save_to_json(self, entry: MemoryEntry) -> None:
        """Save memory entry to JSON file as backup."""
        json_file = self.data_dir / "memories.json"
        
        try:
            # Load existing
            memories = []
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    memories = json.load(f)
            
            # Add new entry
            memories.append(entry.to_dict())
            
            # Save
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(memories, f, indent=2, default=str)
        except Exception as e:
            print(f"WARN: JSON backup failed: {e}")
    
    def recall(
        self,
        query: str,
        k: int = 5,
        memory_type: Optional[str] = None,
        min_importance: float = 0.0
    ) -> List[MemoryEntry]:
        """
        Search memories using hybrid retrieval: semantic (vector) + keyword search
        fused by Reciprocal Rank Fusion, with an optional cross-encoder rerank.

        Hybrid catches both meaning ("car trouble" ~ "engine won't start") and exact
        terms (names, IDs, error codes) that pure vector search misses. Falls back
        gracefully to whichever signal is available.

        Disable hybrid with env DEEP_HYBRID_RECALL=0. Enable cross-encoder rerank
        with DEEP_RERANK=1 (downloads a small model on first use).
        """
        hybrid = os.getenv("DEEP_HYBRID_RECALL", "1") not in ("0", "false", "False")

        if not hybrid:
            results = self._semantic_recall(query, k, memory_type, min_importance)
            if not results:
                results = self._search_json_fallback(query, k, memory_type)
            return results[:k]

        # Pull a wider candidate pool from each signal, then fuse.
        fetch_k = max(k * 4, 20)
        semantic = self._semantic_recall(query, fetch_k, memory_type, min_importance)
        keyword = self._search_json_fallback(query, fetch_k, memory_type)

        fused = self._rrf_fuse(semantic, keyword)
        # Importance filter (keyword path doesn't enforce it)
        fused = [e for e in fused if e.importance >= min_importance]

        if not fused:
            return (semantic or keyword)[:k]

        # Optional precision rerank over the fused candidates
        ranked = self._rerank(query, fused)
        return ranked[:k]

    def _semantic_recall(
        self,
        query: str,
        k: int,
        memory_type: Optional[str] = None,
        min_importance: float = 0.0
    ) -> List[MemoryEntry]:
        """Pure vector similarity search via ChromaDB. Returns rank-ordered entries."""
        results = []
        if self._collection:
            try:
                query_embedding = self._get_embedding(query)
                if query_embedding:
                    where_filter = {"memory_type": memory_type} if memory_type else None
                    chroma_results = self._collection.query(
                        query_embeddings=[query_embedding],
                        n_results=k,
                        where=where_filter
                    )
                    if chroma_results and chroma_results['ids']:
                        for i, memory_id in enumerate(chroma_results['ids'][0]):
                            metadata = chroma_results['metadatas'][0][i] if chroma_results['metadatas'] else {}
                            if metadata.get('importance', 1.0) >= min_importance:
                                entry = MemoryEntry(
                                    id=memory_id,
                                    content=chroma_results['documents'][0][i],
                                    memory_type=metadata.get('memory_type', 'unknown'),
                                    timestamp=datetime.fromisoformat(metadata.get('timestamp', datetime.now().isoformat())),
                                    metadata={kk: v for kk, v in metadata.items() if kk not in ['memory_type', 'timestamp', 'importance']},
                                    importance=metadata.get('importance', 1.0),
                                    embedding=chroma_results['embeddings'][0][i] if chroma_results.get('embeddings') else None
                                )
                                results.append(entry)
            except Exception as e:
                print(f"WARN: Semantic search failed: {e}")
        return results

    @staticmethod
    def _rrf_fuse(*ranked_lists: List[MemoryEntry], k_const: int = 60) -> List[MemoryEntry]:
        """Reciprocal Rank Fusion: combine multiple ranked lists into one.

        score(d) = sum over lists of 1 / (k_const + rank_d). Robust, score-free,
        and the standard way to merge lexical + semantic rankings.
        """
        scores: Dict[str, float] = {}
        entries: Dict[str, MemoryEntry] = {}
        for ranked in ranked_lists:
            for rank, entry in enumerate(ranked):
                scores[entry.id] = scores.get(entry.id, 0.0) + 1.0 / (k_const + rank)
                entries.setdefault(entry.id, entry)
        ordered_ids = sorted(scores, key=scores.get, reverse=True)
        return [entries[i] for i in ordered_ids]

    def _rerank(self, query: str, entries: List[MemoryEntry]) -> List[MemoryEntry]:
        """Optionally reorder candidates with a cross-encoder for higher precision."""
        if os.getenv("DEEP_RERANK", "0") in ("0", "false", "False"):
            return entries
        if not CROSS_ENCODER_AVAILABLE or not entries:
            return entries
        try:
            if self._reranker is None:
                self._reranker = CrossEncoder(self._reranker_name)
            pairs = [(query, e.content) for e in entries]
            scores = self._reranker.predict(pairs)
            order = sorted(range(len(entries)), key=lambda i: scores[i], reverse=True)
            return [entries[i] for i in order]
        except Exception as e:
            print(f"WARN: Rerank failed, using fused order: {e}")
            return entries
    
    def _search_json_fallback(
        self,
        query: str,
        k: int,
        memory_type: Optional[str] = None
    ) -> List[MemoryEntry]:
        """Fallback search on JSON file."""
        json_file = self.data_dir / "memories.json"
        
        if not json_file.exists():
            return []
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                memories = json.load(f)
            
            # Simple keyword matching
            query_words = set(query.lower().split())
            scored = []
            
            for mem in memories:
                if memory_type and mem.get('memory_type') != memory_type:
                    continue
                
                content = mem.get('content', '').lower()
                score = sum(1 for word in query_words if word in content)
                
                if score > 0:
                    scored.append((score, mem))
            
            # Sort by score
            scored.sort(key=lambda x: x[0], reverse=True)
            
            return [MemoryEntry.from_dict(m) for _, m in scored[:k]]
            
        except Exception as e:
            print(f"WARN: JSON search failed: {e}")
            return []
    
    def get_fact(self, key: str) -> Optional[str]:
        """Get a specific fact by key."""
        results = self.recall(key, k=1, memory_type="fact")
        if results:
            return results[0].content
        return None
    
    def store_fact(self, key: str, value: str, importance: float = 1.5) -> str:
        """Store a simple fact."""
        return self.store(
            memory_type="fact",
            content=f"{key}: {value}",
            metadata={"key": key, "value": value},
            importance=importance
        )
    
    def store_preference(self, category: str, preference: str, importance: float = 1.5) -> str:
        """Store user preference."""
        return self.store(
            memory_type="preference",
            content=f"User preference - {category}: {preference}",
            metadata={"category": category, "preference": preference},
            importance=importance
        )
    
    def get_preferences(self, category: Optional[str] = None) -> List[MemoryEntry]:
        """Get user preferences."""
        where_filter = {"memory_type": "preference"}
        if category:
            where_filter["category"] = category
        
        return self.recall("preference", k=20, memory_type="preference")
    
    # ==================== CONVERSATION THREADS ====================
    
    def _load_threads(self) -> None:
        """Load conversation threads from disk."""
        if self._threads_file.exists():
            try:
                with open(self._threads_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for thread_id, thread_data in data.items():
                    thread = ConversationThread(
                        id=thread_data["id"],
                        title=thread_data["title"],
                        created_at=datetime.fromisoformat(thread_data["created_at"]),
                        updated_at=datetime.fromisoformat(thread_data["updated_at"]),
                        entries=thread_data.get("entries", []),
                        summary=thread_data.get("summary"),
                        is_active=thread_data.get("is_active", True)
                    )
                    self._threads[thread_id] = thread
                    
            except Exception as e:
                print(f"WARN: Failed to load threads: {e}")
    
    def _save_threads(self) -> None:
        """Save conversation threads to disk."""
        try:
            data = {}
            for thread_id, thread in self._threads.items():
                data[thread_id] = {
                    "id": thread.id,
                    "title": thread.title,
                    "created_at": thread.created_at.isoformat(),
                    "updated_at": thread.updated_at.isoformat(),
                    "entries": thread.entries,
                    "summary": thread.summary,
                    "is_active": thread.is_active
                }
            
            with open(self._threads_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"WARN: Failed to save threads: {e}")
    
    def start_conversation_thread(self, title: str) -> str:
        """Start a new conversation thread."""
        thread_id = str(uuid.uuid4())
        now = datetime.now()
        
        thread = ConversationThread(
            id=thread_id,
            title=title,
            created_at=now,
            updated_at=now
        )
        
        self._threads[thread_id] = thread
        self._active_thread_id = thread_id
        self._save_threads()
        
        print(f"OK: Started conversation thread: {title}")
        return thread_id
    
    def add_to_thread(
        self,
        content: str,
        role: str = "assistant",
        thread_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """Add entry to conversation thread."""
        thread_id = thread_id or self._active_thread_id
        
        if not thread_id or thread_id not in self._threads:
            # Auto-create thread
            thread_id = self.start_conversation_thread("Auto Thread")
        
        thread = self._threads[thread_id]
        thread.add_entry(role, content, metadata)
        self._save_threads()
    
    def get_thread(self, thread_id: str) -> Optional[ConversationThread]:
        """Get conversation thread by ID."""
        return self._threads.get(thread_id)
    
    def get_active_thread(self) -> Optional[ConversationThread]:
        """Get currently active thread."""
        if self._active_thread_id:
            return self._threads.get(self._active_thread_id)
        return None
    
    def list_threads(self, active_only: bool = False) -> List[ConversationThread]:
        """List all conversation threads."""
        threads = list(self._threads.values())
        if active_only:
            threads = [t for t in threads if t.is_active]
        return sorted(threads, key=lambda t: t.updated_at, reverse=True)
    
    def switch_thread(self, thread_id: str) -> bool:
        """Switch to different conversation thread."""
        if thread_id in self._threads:
            self._active_thread_id = thread_id
            print(f"OK: Switched to thread: {self._threads[thread_id].title}")
            return True
        return False
    
    def close_thread(self, thread_id: str, summary: Optional[str] = None) -> None:
        """Close conversation thread."""
        if thread_id in self._threads:
            thread = self._threads[thread_id]
            thread.is_active = False
            if summary:
                thread.summary = summary
            self._save_threads()
            print(f"OK: Closed thread: {thread.title}")
    
    def get_thread_context(self, thread_id: Optional[str] = None, n_recent: int = 10) -> str:
        """Get thread context for LLM prompt."""
        thread_id = thread_id or self._active_thread_id
        
        if not thread_id or thread_id not in self._threads:
            return ""
        
        thread = self._threads[thread_id]
        
        # Get recent entries
        recent_entries = thread.entries[-n_recent:] if len(thread.entries) > n_recent else thread.entries
        
        # Format as conversation history
        context = f"\n--- Conversation Thread: {thread.title} ---\n"
        
        for entry in recent_entries:
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            context += f"{role.upper()}: {content}\n"
        
        context += "--- End of Thread Context ---\n"
        
        return context
    
    # ==================== MEMORY MANAGEMENT ====================
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        # Remove from ChromaDB
        if self._collection:
            try:
                self._collection.delete(ids=[memory_id])
            except Exception as e:
                print(f"WARN: Failed to delete from ChromaDB: {e}")
        
        # Remove from JSON backup
        json_file = self.data_dir / "memories.json"
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    memories = json.load(f)
                
                memories = [m for m in memories if m.get("id") != memory_id]
                
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(memories, f, indent=2, default=str)
                
                return True
            except Exception as e:
                print(f"WARN: Failed to delete from JSON: {e}")
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        stats = {
            "total_memories": 0,
            "by_type": {},
            "conversation_threads": len(self._threads),
            "active_threads": sum(1 for t in self._threads.values() if t.is_active),
            "storage_backend": "unknown"
        }
        
        # Count from ChromaDB
        if self._collection:
            try:
                all_memories = self._collection.get()
                if all_memories and all_memories['metadatas']:
                    stats["total_memories"] = len(all_memories['metadatas'])
                    stats["storage_backend"] = "chroma"
                    
                    # Count by type
                    for metadata in all_memories['metadatas']:
                        mem_type = metadata.get('memory_type', 'unknown')
                        stats["by_type"][mem_type] = stats["by_type"].get(mem_type, 0) + 1
            except Exception as e:
                print(f"WARN: Failed to get ChromaDB stats: {e}")
        
        # Fallback to JSON
        if stats["total_memories"] == 0:
            json_file = self.data_dir / "memories.json"
            if json_file.exists():
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        memories = json.load(f)
                    stats["total_memories"] = len(memories)
                    stats["storage_backend"] = "json"
                except:
                    pass
        
        return stats
    
    def export_memories(self, output_file: str) -> bool:
        """Export all memories to file."""
        try:
            # Collect all memories
            all_memories = []
            
            # From ChromaDB
            if self._collection:
                try:
                    results = self._collection.get()
                    if results and results['ids']:
                        for i, memory_id in enumerate(results['ids']):
                            entry = MemoryEntry(
                                id=memory_id,
                                content=results['documents'][i],
                                memory_type=results['metadatas'][i].get('memory_type', 'unknown'),
                                timestamp=datetime.fromisoformat(results['metadatas'][i].get('timestamp', datetime.now().isoformat())),
                                metadata={k: v for k, v in results['metadatas'][i].items() if k not in ['memory_type', 'timestamp']},
                                importance=results['metadatas'][i].get('importance', 1.0)
                            )
                            all_memories.append(entry.to_dict())
                except Exception as e:
                    print(f"WARN: Failed to export from ChromaDB: {e}")
            
            # From JSON
            if not all_memories:
                json_file = self.data_dir / "memories.json"
                if json_file.exists():
                    with open(json_file, 'r', encoding='utf-8') as f:
                        all_memories = json.load(f)
            
            # Export
            export_data = {
                "export_date": datetime.now().isoformat(),
                "total_memories": len(all_memories),
                "memories": all_memories
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            print(f"OK: Exported {len(all_memories)} memories to {output_file}")
            return True
            
        except Exception as e:
            print(f"ERROR: Export failed: {e}")
            return False


# Integration helper class
class MemoryEnhancedJARVIS:
    """
    Wrapper that adds long-term memory to JARVIS.
    
    Usage:
        jarvis = MemoryEnhancedJARVIS(base_jarvis_instance)
        jarvis.remember("User likes dark mode")
        jarvis.recall_relevant("interface preferences")
    """
    
    def __init__(self, jarvis_instance):
        self.jarvis = jarvis_instance
        self.ltm = LongTermMemory()
        self._setup_hooks()
    
    def _setup_hooks(self):
        """Hook into JARVIS conversation flow."""
        # Store every user message and response
        original_process = self.jarvis._process_with_ai
        
        def enhanced_process(user_text):
            # Store user input
            self.ltm.add_to_thread(
                content=user_text,
                role="user",
                metadata={"type": "user_input"}
            )
            
            # Call original
            result = original_process(user_text)
            
            # Store response
            # (Would need to capture response - depends on JARVIS implementation)
            
            return result
        
        self.jarvis._process_with_ai = enhanced_process
    
    def remember(self, fact: str, importance: float = 1.0):
        """Store a fact."""
        return self.ltm.store("fact", fact, importance=importance)
    
    def recall_relevant(self, query: str, k: int = 5) -> List[str]:
        """Recall relevant memories."""
        results = self.ltm.recall(query, k=k)
        return [r.content for r in results]


# Demo
if __name__ == "__main__":
    print("="*60)
    print("Long-Term Memory System Demo")
    print("="*60)
    print()
    
    # Initialize
    ltm = LongTermMemory()
    
    # Store some facts
    print("Storing memories...")
    ltm.store_fact("favorite_color", "blue")
    ltm.store_fact("name", "Aryan")
    ltm.store_preference("interface", "dark mode")
    ltm.store("event", "Had meeting with team about Project Alpha", importance=1.5)
    
    # Recall
    print("\nRecalling relevant memories...")
    results = ltm.recall("What does the user like?", k=5)
    
    for r in results:
        print(f"  - [{r.memory_type}] {r.content[:60]}...")
    
    # Thread demo
    print("\nConversation thread demo...")
    thread_id = ltm.start_conversation_thread("Project Alpha Planning")
    ltm.add_to_thread("We need to decide on the tech stack", role="assistant")
    ltm.add_to_thread("Let's use Python and FastAPI", role="user")
    ltm.add_to_thread("Great choice! I'll document this.", role="assistant")
    
    # Get context
    context = ltm.get_thread_context(thread_id, n_recent=3)
    print(context)
    
    # Stats
    print("\nMemory Statistics:")
    stats = ltm.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nOK: Demo complete!")
