"""
core/infrastructure/degradation.py

Graceful degradation strategies for when components fail.
Ensures the system remains functional even with partial outages.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

from ..domain.interfaces import LLMClient, MemoryRepository
from ..health import ComponentHealth, ComponentStatus

logger = logging.getLogger(__name__)


class DegradationLevel(Enum):
    FULL = "full"           # All features available
    REDUCED = "reduced"     # Some features disabled
    MINIMAL = "minimal"     # Core features only
    OFFLINE = "offline"     # Local-only, no external services


@dataclass
class SystemCapabilities:
    """Current system capabilities based on component health."""
    level: DegradationLevel
    llm_available: bool
    memory_available: bool
    tools_available: bool
    streaming_available: bool
    voice_available: bool
    web_available: bool
    
    disabled_features: List[str]
    warnings: List[str]
    
    @property
    def is_functional(self) -> bool:
        """Can the system process basic chat?"""
        return self.llm_available
    
    def to_dict(self) -> Dict:
        return {
            "level": self.level.value,
            "functional": self.is_functional,
            "features": {
                "llm": self.llm_available,
                "memory": self.memory_available,
                "tools": self.tools_available,
                "streaming": self.streaming_available,
                "voice": self.voice_available,
                "web": self.web_available,
            },
            "disabled": self.disabled_features,
            "warnings": self.warnings
        }


class DegradationManager:
    """
    Manages graceful degradation based on component health.
    
    When components fail, the system degrades gracefully rather than
    crashing completely. Users see a "degraded mode" message but
    can still use core features.
    """
    
    def __init__(self):
        self._llm_fallbacks: List[LLMClient] = []
        self._memory_fallback: Optional[MemoryRepository] = None
        self._current_level = DegradationLevel.FULL
    
    def register_llm_fallbacks(self, fallbacks: List[LLMClient]):
        """Register fallback LLM clients in priority order."""
        self._llm_fallbacks = fallbacks
    
    def register_memory_fallback(self, fallback: MemoryRepository):
        """Register fallback memory (e.g., simple in-memory cache)."""
        self._memory_fallback = fallback
    
    def assess_capabilities(
        self,
        primary_llm: Optional[LLMClient],
        primary_memory: Optional[MemoryRepository],
        health_results: Dict[str, ComponentHealth]
    ) -> SystemCapabilities:
        """
        Assess current system capabilities based on health checks.
        
        Returns capabilities with appropriate degradation level.
        """
        warnings = []
        disabled = []
        
        # Check LLM
        llm_available = False
        llm_health = health_results.get("ollama") or health_results.get("claude")
        
        if llm_health and llm_health.status == ComponentStatus.OK:
            llm_available = True
        elif primary_llm and primary_llm.is_available:
            llm_available = True
            warnings.append("LLM health check uncertain but responding")
        else:
            # Try fallbacks
            for fallback in self._llm_fallbacks:
                if fallback.is_available:
                    llm_available = True
                    warnings.append(f"Using fallback LLM: {fallback.model_name}")
                    break
            
            if not llm_available:
                disabled.extend(["chat", "research", "code_generation"])
                warnings.append("CRITICAL: No LLM available")
        
        # Check Memory
        memory_available = False
        memory_health = health_results.get("chromadb")
        
        if memory_health and memory_health.status == ComponentStatus.OK:
            memory_available = True
        elif primary_memory:
            try:
                # Quick test
                primary_memory.recall("test", k=1)
                memory_available = True
            except:
                pass
        
        if not memory_available and self._memory_fallback:
            memory_available = True
            warnings.append("Using fallback memory (limited context)")
        elif not memory_available:
            disabled.append("long_term_memory")
            warnings.append("Memory unavailable - conversations won't persist")
        
        # Check system resources
        memory_health = health_results.get("memory")
        if memory_health and memory_health.status == ComponentStatus.FAILED:
            disabled.extend(["streaming", "voice", "large_context"])
            warnings.append("Memory critically low - using minimal mode")
        
        # Determine level
        if not llm_available:
            level = DegradationLevel.OFFLINE
        elif disabled:
            if "long_term_memory" in disabled or "streaming" in disabled:
                level = DegradationLevel.REDUCED
            else:
                level = DegradationLevel.MINIMAL
        else:
            level = DegradationLevel.FULL
        
        self._current_level = level
        
        return SystemCapabilities(
            level=level,
            llm_available=llm_available,
            memory_available=memory_available,
            tools_available=level in (DegradationLevel.FULL, DegradationLevel.REDUCED),
            streaming_available=level in (DegradationLevel.FULL, DegradationLevel.REDUCED) and "streaming" not in disabled,
            voice_available=level == DegradationLevel.FULL and "voice" not in disabled,
            web_available=level != DegradationLevel.OFFLINE,
            disabled_features=disabled,
            warnings=warnings
        )
    
    def get_fallback_message(self, capabilities: SystemCapabilities) -> Optional[str]:
        """Get user-facing message about degradation."""
        if capabilities.level == DegradationLevel.FULL:
            return None
        
        if capabilities.level == DegradationLevel.OFFLINE:
            return (
                "⚠️ **SYSTEM OFFLINE**\n\n"
                "DEEP is currently unable to connect to any AI backend.\n"
                "Please check:\n"
                "- Ollama is running (ollama serve)\n"
                "- Or configure a Claude API key in .env\n\n"
                "Some offline features may still be available."
            )
        
        if capabilities.warnings:
            msg = f"⚠️ Running in {capabilities.level.value.upper()} mode\n\n"
            msg += "Warnings:\n"
            for w in capabilities.warnings[:3]:  # Show max 3
                msg += f"- {w}\n"
            
            if capabilities.disabled_features:
                msg += f"\nDisabled: {', '.join(capabilities.disabled_features[:3])}"
            
            return msg
        
        return None


class FallbackMemoryRepository(MemoryRepository):
    """
    In-memory fallback memory when ChromaDB fails.
    
    Provides basic functionality without vector search.
    Uses simple keyword matching instead of semantic search.
    """
    
    def __init__(self, max_items: int = 100):
        self._memories: List[Dict] = []
        self._max_items = max_items
    
    def store(self, entry) -> bool:
        """Store in simple list (no embeddings)."""
        data = {
            "id": entry.id,
            "content": entry.content,
            "type": entry.memory_type,
            "timestamp": entry.timestamp,
            "metadata": entry.metadata
        }
        self._memories.append(data)
        
        # Trim if needed
        if len(self._memories) > self._max_items:
            self._memories = self._memories[-self._max_items:]
        
        return True
    
    def recall(self, query: str, k: int = 5):
        """Simple keyword matching fallback."""
        query_words = set(query.lower().split())
        scored = []
        
        for mem in self._memories:
            content_words = set(mem["content"].lower().split())
            overlap = len(query_words & content_words)
            if overlap > 0:
                scored.append((overlap, mem))
        
        # Sort by score (overlap count), return top k
        scored.sort(reverse=True)
        
        # Convert back to MemoryEntry-like objects
        from ..domain.models import MemoryEntry
        from datetime import datetime
        
        results = []
        for _, data in scored[:k]:
            results.append(MemoryEntry(
                id=data["id"],
                content=data["content"],
                memory_type=data["type"],
                timestamp=data.get("timestamp", datetime.utcnow())
            ))
        
        return results
    
    def get_conversation_context(self, query: str, max_tokens: int = 2000) -> str:
        """Get context from recent memories."""
        memories = self.recall(query, k=3)
        if not memories:
            return ""
        
        context_parts = []
        current_tokens = 0
        
        for mem in memories:
            text = f"[{mem.memory_type}] {mem.content}\n"
            # Rough token estimate
            tokens = len(text.split())
            if current_tokens + tokens > max_tokens:
                break
            context_parts.append(text)
            current_tokens += tokens
        
        return "\n".join(context_parts)


class CachedResponseProvider:
    """
    Provides cached responses for common queries when LLM is down.
    
    Acts as a last-resort fallback for basic functionality.
    """
    
    _COMMON_RESPONSES = {
        "hello": "Greetings! I'm DEEP, your AI assistant. How may I help you today?",
        "help": "I can help with: research, coding, analysis, system status, and general questions. What would you like to do?",
        "status": "I'm currently operating in offline mode with limited functionality. Full services will resume when connection is restored.",
        "who are you": "I'm DEEP, a JARVIS-class AI assistant built for Aryan. I'm currently running in degraded mode due to connectivity issues.",
    }
    
    @classmethod
    def get_response(cls, query: str) -> Optional[str]:
        """Get cached response for common queries."""
        query_lower = query.lower().strip()
        
        # Direct match
        if query_lower in cls._COMMON_RESPONSES:
            return cls._COMMON_RESPONSES[query_lower]
        
        # Partial match
        for key, response in cls._COMMON_RESPONSES.items():
            if key in query_lower or query_lower in key:
                return response
        
        return None
    
    @classmethod
    def get_offline_message(cls) -> str:
        """Generic offline mode message."""
        return (
            "I'm currently operating in offline mode.\n\n"
            "I can respond to basic greetings and common questions, "
            "but advanced features like research, code generation, and "
            "complex analysis require connection to an AI backend.\n\n"
            "Please check that Ollama is running or configure an API key."
        )
