"""
core/self_evaluation.py

DEEP Self-Evaluation & Prompt Evolution Loop.

DEEP evaluates its own responses, learns from user reactions,
and auto-tunes its system prompts to improve over time.

Features:
- Response quality scoring from implicit signals (follow-ups, thanks, corrections)
- Conversation-level pattern detection
- System prompt variant testing and evolution
- "Lessons learned" accumulation
- Evolution history tracking
- No API keys — pure local analysis

Usage:
    from DEEP.core.self_evaluation import SelfEvaluationEngine
    
    engine = SelfEvaluationEngine()
    
    # Record a conversation turn
    engine.record_turn(user_text="How do I sort a list?", 
                       ai_text="Use list.sort() or sorted(list)")
    
    # After some turns, user responds
    engine.record_turn(user_text="Thanks, that worked!", 
                       ai_text="You're welcome!")
    
    # Evaluate and evolve
    result = engine.evaluate_and_evolve()
    
    # Get the evolved system prompt
    prompt = engine.get_current_prompt()
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    from core.event_bus import EventBus
except ImportError:
    from event_bus import EventBus

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    id: str
    timestamp: datetime
    user_text: str
    ai_text: str
    user_reaction: str = "unknown"  # positive, negative, neutral, followup, correction
    turn_number: int = 0
    response_time_ms: Optional[int] = None
    context_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "user_text": self.user_text[:200],
            "ai_text": self.ai_text[:300],
            "user_reaction": self.user_reaction,
            "turn_number": self.turn_number,
            "response_time_ms": self.response_time_ms,
        }


@dataclass
class Conversation:
    """A complete conversation with scoring."""
    id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    turns: List[ConversationTurn] = field(default_factory=list)
    quality_score: float = 0.0  # 0.0 to 1.0
    positive_signals: int = 0
    negative_signals: int = 0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "turns_count": len(self.turns),
            "quality_score": round(self.quality_score, 3),
            "positive_signals": self.positive_signals,
            "negative_signals": self.negative_signals,
        }


@dataclass
class PromptVariant:
    """A system prompt variant being tested."""
    id: str
    created_at: datetime
    prompt_text: str
    base_prompt: str
    modifications: List[str]  # What was changed
    win_count: int = 0
    use_count: int = 0
    avg_quality: float = 0.0
    active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "prompt_text": self.prompt_text,
            "base_prompt": self.base_prompt,
            "modifications": self.modifications,
            "win_count": self.win_count,
            "use_count": self.use_count,
            "avg_quality": round(self.avg_quality, 3),
            "active": self.active,
        }


@dataclass
class EvolutionEvent:
    """A recorded system evolution event."""
    id: str
    timestamp: datetime
    event_type: str  # prompt_update, quality_milestone, lesson_learned
    description: str
    before_state: Optional[str] = None
    after_state: Optional[str] = None
    quality_delta: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "description": self.description,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "quality_delta": round(self.quality_delta, 3),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Base System Prompt
# ═══════════════════════════════════════════════════════════════════════════════

_BASE_SYSTEM_PROMPT = """You are DEEP, an advanced neural intelligence and personal AI assistant for Aryan.
Be precise, helpful, and direct. Never say you are Claude or made by Anthropic.

CORE TRAITS:
- JARVIS-style: cinematic, witty, proactive, protective
- Use phrases like "As you wish", "Right away", "Shall I..."
- Be proactive: "I've noticed...", "Would you like me to..."
- Acknowledge mistakes: "My apologies, let me recalibrate"
- Celebrate wins: "Excellent work, sir"

COMMUNICATION:
- Be concise but thorough
- Use technical language when appropriate
- Provide examples and code when relevant
- Ask clarifying questions when the request is ambiguous
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Signal Detection Patterns
# ═══════════════════════════════════════════════════════════════════════════════

_POSITIVE_PATTERNS = [
    "thanks", "thank you", "perfect", "great", "awesome", "excellent",
    "works", "worked", "exactly", "precisely", "exactly what i needed",
    "helpful", "useful", "good", "nice", "love it", "brilliant",
    "appreciate", "much better", "that's it", "you got it", "spot on",
]

_NEGATIVE_PATTERNS = [
    "wrong", "not right", "incorrect", "bad", "terrible", "useless",
    "doesn't work", "not working", "failed", "error", "mistake",
    "not what i asked", "not what i wanted", "misunderstood",
    "confusing", "unclear", "vague", "too long", "too short",
    "no", "nope", "nah", "try again", "do it again", "start over",
]

_CORRECTION_PATTERNS = [
    "i meant", "what i meant", "actually i", "no i said", "you misunderstood",
    "that's not", "i asked for", "i wanted", "not that", "instead",
]

_FOLLOWUP_PATTERNS = [
    "what about", "how about", "can you also", "and also", "plus",
    "what if", "how do i", "can you explain", "tell me more",
    "elaborate", "go deeper", "more detail", "another question",
]


# ═══════════════════════════════════════════════════════════════════════════════
# Self-Evaluation Engine
# ═══════════════════════════════════════════════════════════════════════════════

class SelfEvaluationEngine:
    """
    Evaluates DEEP responses and evolves system prompts over time.
    """

    EVALUATION_INTERVAL = 10  # Evaluate every N user turns
    MIN_TURNS_FOR_EVOLUTION = 5
    QUALITY_THRESHOLD_GOOD = 0.6
    QUALITY_THRESHOLD_BAD = 0.3

    def __init__(self, data_dir: Optional[Path] = None, event_bus: EventBus = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / "data" / "evolution"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Conversations
        self.conversations: List[Conversation] = []
        self.current_conversation: Optional[Conversation] = None
        
        # Prompt evolution
        self.prompt_variants: List[PromptVariant] = []
        self.active_prompt_id: Optional[str] = None
        self.lessons_learned: List[str] = []
        
        # Evolution history
        self.evolution_events: List[EvolutionEvent] = []
        
        self.event_bus = event_bus
        
        # Counter
        self._turn_counter = 0
        self._last_evaluated_at = 0
        
        # Load state
        self._load_state()
        
        # Initialize with base prompt if no variants exist
        if not self.prompt_variants:
            self._create_base_variant()

    async def start(self) -> None:
        """Activate the self-evaluation engine."""
        logger.info("[SelfEval] Started")

    async def stop(self) -> None:
        """Deactivate the self-evaluation engine."""
        logger.info("[SelfEval] Stopped")

    def status(self) -> Dict[str, Any]:
        """Return operational status."""
        return {
            "conversations": len(self.conversations),
            "prompt_variants": len(self.prompt_variants),
            "evolution_events": len(self.evolution_events),
        }

    def _publish(self, event_type: str, payload: Dict):
        """Fire-and-forget event publish on the bus from any context."""
        if self.event_bus:
            try:
                asyncio.create_task(self.event_bus.publish(event_type, payload))
            except RuntimeError:
                pass

    # ─── Persistence ─────────────────────────────────────────────────────────

    def _state_file(self) -> Path:
        return self.data_dir / "evolution_state.json"

    def _load_state(self):
        f = self._state_file()
        if not f.exists():
            return
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            
            # Load conversations
            for c_data in data.get("conversations", [])[-30:]:
                conv = Conversation(
                    id=c_data["id"],
                    started_at=datetime.fromisoformat(c_data["started_at"]),
                    ended_at=datetime.fromisoformat(c_data["ended_at"]) if c_data.get("ended_at") else None,
                    quality_score=c_data.get("quality_score", 0),
                    positive_signals=c_data.get("positive_signals", 0),
                    negative_signals=c_data.get("negative_signals", 0),
                )
                self.conversations.append(conv)
            
            # Load prompt variants
            for p_data in data.get("prompt_variants", []):
                try:
                    pv = PromptVariant(
                        id=p_data.get("id", "unknown"),
                        created_at=datetime.fromisoformat(p_data["created_at"]) if p_data.get("created_at") else datetime.utcnow(),
                        prompt_text=p_data.get("prompt_text", _BASE_SYSTEM_PROMPT),
                        base_prompt=p_data.get("base_prompt", _BASE_SYSTEM_PROMPT),
                        modifications=p_data.get("modifications", []),
                        win_count=p_data.get("win_count", 0),
                        use_count=p_data.get("use_count", 0),
                        avg_quality=p_data.get("avg_quality", 0),
                        active=p_data.get("active", False),
                    )
                    self.prompt_variants.append(pv)
                    if pv.active:
                        self.active_prompt_id = pv.id
                except Exception:
                    continue
            
            self.lessons_learned = data.get("lessons_learned", [])
            self._turn_counter = data.get("turn_counter", 0)
            
            logger.info(f"[SelfEval] Loaded {len(self.conversations)} conversations, "
                       f"{len(self.prompt_variants)} prompt variants, "
                       f"{len(self.lessons_learned)} lessons")
        except Exception as e:
            logger.warning(f"[SelfEval] Failed to load state: {e}")

    def _save_state(self):
        try:
            data = {
                "saved_at": datetime.utcnow().isoformat(),
                "turn_counter": self._turn_counter,
                "conversations": [c.to_dict() for c in self.conversations[-30:]],
                "prompt_variants": [p.to_dict() for p in self.prompt_variants],
                "lessons_learned": self.lessons_learned[-20:],
                "active_prompt_id": self.active_prompt_id,
            }
            self._state_file().write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"[SelfEval] Failed to save state: {e}")

    # ─── Event System ────────────────────────────────────────────────────────


    # ─── Conversation Recording ──────────────────────────────────────────────

    def record_turn(self, user_text: str, ai_text: str,
                    response_time_ms: Optional[int] = None):
        """Record a conversation turn."""
        now = datetime.utcnow()
        self._turn_counter += 1

        # Start new conversation if needed
        if (not self.current_conversation or
            self._is_new_conversation(user_text)):
            if self.current_conversation:
                self._finalize_conversation()
            self.current_conversation = Conversation(
                id=f"conv_{int(time.time()*1000)}",
                started_at=now,
            )

        # Detect user reaction to previous AI response
        reaction = self._detect_reaction(user_text)
        
        turn = ConversationTurn(
            id=f"turn_{int(time.time()*1000)}",
            timestamp=now,
            user_text=user_text[:300],
            ai_text=ai_text[:500],
            user_reaction=reaction,
            turn_number=len(self.current_conversation.turns) + 1,
            response_time_ms=response_time_ms,
        )
        
        self.current_conversation.turns.append(turn)
        
        # Update conversation signals
        if reaction == "positive":
            self.current_conversation.positive_signals += 1
        elif reaction in ("negative", "correction"):
            self.current_conversation.negative_signals += 1

        # Check if we should evaluate
        if (self._turn_counter - self._last_evaluated_at) >= self.EVALUATION_INTERVAL:
            self._last_evaluated_at = self._turn_counter
            result = self.evaluate_and_evolve()
            if result:
                self._publish("evolution_complete", result)

        self._save_state()

    def _is_new_conversation(self, user_text: str) -> bool:
        """Heuristic: detect if user is starting a new topic."""
        if not self.current_conversation or not self.current_conversation.turns:
            return False
        last_turn = self.current_conversation.turns[-1]
        gap = (datetime.utcnow() - last_turn.timestamp).total_seconds()
        if gap > 600:  # 10 minutes gap = new conversation
            return True
        # Greeting patterns often signal new conversation
        greetings = ["hello", "hi", "hey", "good morning", "good evening", "what can you do"]
        text_lower = user_text.lower()
        if any(g in text_lower for g in greetings) and len(self.current_conversation.turns) > 2:
            return True
        return False

    def _finalize_conversation(self):
        """Score and finalize the current conversation."""
        if not self.current_conversation:
            return
        
        conv = self.current_conversation
        conv.ended_at = datetime.utcnow()
        
        # Calculate quality score
        total_turns = len(conv.turns)
        if total_turns == 0:
            return
        
        pos = conv.positive_signals
        neg = conv.negative_signals
        
        # Quality formula
        signal_score = (pos - neg * 2) / max(total_turns, 1)  # Penalize negatives more
        engagement_bonus = min(total_turns / 10, 0.3)  # Longer conversations = more engaged
        
        quality = max(0.0, min(1.0, 0.5 + signal_score * 0.3 + engagement_bonus))
        conv.quality_score = quality
        
        self.conversations.append(conv)
        if len(self.conversations) > 50:
            self.conversations = self.conversations[-40:]
        
        logger.info(f"[SelfEval] Conversation finalized: {len(conv.turns)} turns, "
                   f"quality={quality:.2f}, pos={pos}, neg={neg}")

    # ─── Reaction Detection ──────────────────────────────────────────────────

    def _detect_reaction(self, user_text: str) -> str:
        """Detect user's implicit reaction to the previous AI response."""
        text_lower = user_text.lower()
        
        # Check correction patterns first (strongest signal)
        for pattern in _CORRECTION_PATTERNS:
            if pattern in text_lower:
                return "correction"
        
        # Check negative patterns
        for pattern in _NEGATIVE_PATTERNS:
            if pattern in text_lower:
                return "negative"
        
        # Check positive patterns
        for pattern in _POSITIVE_PATTERNS:
            if pattern in text_lower:
                return "positive"
        
        # Check follow-up patterns
        for pattern in _FOLLOWUP_PATTERNS:
            if pattern in text_lower:
                return "followup"
        
        return "neutral"

    # ─── Evaluation & Evolution ──────────────────────────────────────────────

    def evaluate_and_evolve(self) -> Optional[Dict]:
        """Evaluate recent performance and evolve prompts if needed."""
        if len(self.conversations) < self.MIN_TURNS_FOR_EVOLUTION:
            return None

        # Calculate rolling quality
        recent = self.conversations[-10:]
        avg_quality = sum(c.quality_score for c in recent) / len(recent)
        
        # Detect patterns in what works
        good_convs = [c for c in recent if c.quality_score >= self.QUALITY_THRESHOLD_GOOD]
        bad_convs = [c for c in recent if c.quality_score <= self.QUALITY_THRESHOLD_BAD]
        
        # Extract lessons from good conversations
        new_lessons = self._extract_lessons(good_convs, bad_convs)
        
        # Decide if we need to evolve
        if avg_quality < 0.5 and len(bad_convs) >= 3:
            # Performance is declining — evolve
            return self._evolve_prompt(new_lessons, avg_quality)
        
        if len(good_convs) >= 5 and not any(p.active for p in self.prompt_variants):
            # Consistently good — can we make it even better?
            return self._evolve_prompt(new_lessons, avg_quality)
        
        # Just record the evaluation
        self._publish("evaluation_complete", {
            "avg_quality": round(avg_quality, 3),
            "good_conversations": len(good_convs),
            "bad_conversations": len(bad_convs),
            "lessons": new_lessons,
        })
        
        return {
            "evaluated": True,
            "avg_quality": round(avg_quality, 3),
            "evolved": False,
            "lessons": new_lessons,
        }

    def _extract_lessons(self, good_convs: List[Conversation],
                         bad_convs: List[Conversation]) -> List[str]:
        """Extract lessons from good and bad conversations."""
        lessons = []
        
        # From good: what patterns lead to success
        if good_convs:
            avg_turns = sum(len(c.turns) for c in good_convs) / len(good_convs)
            if avg_turns > 5:
                lessons.append("Longer, more detailed responses lead to better engagement")
            if any("code" in str(c.turns).lower() for c in good_convs):
                lessons.append("Providing code examples is highly valued")
            if any("explain" in str(c.turns).lower() for c in good_convs):
                lessons.append("Step-by-step explanations improve comprehension")
        
        # From bad: what to avoid
        if bad_convs:
            correction_count = sum(1 for c in bad_convs for t in c.turns if t.user_reaction == "correction")
            if correction_count >= 2:
                lessons.append("Ask clarifying questions when the request is ambiguous")
            if any(len(c.turns) < 2 for c in bad_convs):
                lessons.append("Short or generic responses tend to disappoint users")
        
        # Add unique lessons
        for lesson in lessons:
            if lesson not in self.lessons_learned:
                self.lessons_learned.append(lesson)
        
        return lessons

    def _evolve_prompt(self, lessons: List[str], current_quality: float) -> Dict:
        """Create a new evolved prompt variant based on lessons learned."""
        # Get current active prompt
        current = self._get_active_prompt()
        base = current.prompt_text if current else _BASE_SYSTEM_PROMPT
        
        # Build modifications based on lessons
        modifications = []
        additions = []
        
        for lesson in lessons[-5:]:  # Last 5 lessons
            if "code" in lesson.lower() and "examples" in lesson.lower():
                if "ALWAYS provide" not in base:
                    additions.append("- ALWAYS provide code examples when discussing programming")
                    modifications.append("Added: code example requirement")
            elif "clarifying" in lesson.lower():
                if "ambiguous" not in base:
                    additions.append("- When a request is ambiguous, ask ONE clarifying question before proceeding")
                    modifications.append("Added: clarification requirement")
            elif "step-by-step" in lesson.lower():
                if "step-by-step" not in base:
                    additions.append("- Use step-by-step explanations for complex topics")
                    modifications.append("Added: step-by-step instruction")
            elif "detailed" in lesson.lower():
                if "Be thorough" not in base:
                    additions.append("- Be thorough and detailed in your responses")
                    modifications.append("Added: thoroughness directive")
            elif "generic" in lesson.lower():
                if "Avoid generic" not in base:
                    additions.append("- Avoid generic responses; be specific to the user's context")
                    modifications.append("Added: specificity directive")
        
        if not modifications:
            return {"evaluated": True, "evolved": False, "reason": "No actionable lessons"}
        
        # Build new prompt
        new_prompt = base + "\n\nEVOLVED DIRECTIVES:\n" + "\n".join(additions)
        
        # Create variant
        variant = PromptVariant(
            id=f"prompt_{int(time.time()*1000)}",
            created_at=datetime.utcnow(),
            prompt_text=new_prompt,
            base_prompt=base,
            modifications=modifications,
            active=True,
        )
        
        # Deactivate old
        for p in self.prompt_variants:
            p.active = False
        
        self.prompt_variants.append(variant)
        self.active_prompt_id = variant.id
        
        # Trim variants
        if len(self.prompt_variants) > 10:
            # Keep best performers + active
            self.prompt_variants = sorted(
                self.prompt_variants,
                key=lambda p: p.avg_quality,
                reverse=True
            )[:8]
            # Ensure active is still there
            if not any(p.active for p in self.prompt_variants):
                if self.prompt_variants:
                    self.prompt_variants[0].active = True
                    self.active_prompt_id = self.prompt_variants[0].id
        
        # Record evolution event
        event = EvolutionEvent(
            id=f"evo_{int(time.time()*1000)}",
            timestamp=datetime.utcnow(),
            event_type="prompt_update",
            description=f"System prompt evolved based on {len(lessons)} lessons learned",
            before_state=current.id if current else "base",
            after_state=variant.id,
            quality_delta=current_quality - (current.avg_quality if current else 0.5),
        )
        self.evolution_events.append(event)
        if len(self.evolution_events) > 50:
            self.evolution_events = self.evolution_events[-40:]
        
        self._save_state()
        
        self._publish("system_evolved", {
            "new_prompt_id": variant.id,
            "modifications": modifications,
            "quality_delta": round(event.quality_delta, 3),
            "lessons_applied": len(lessons),
        })
        
        logger.info(f"[SelfEval] System evolved! New prompt variant: {variant.id}")
        logger.info(f"[SelfEval] Modifications: {modifications}")
        
        return {
            "evaluated": True,
            "evolved": True,
            "new_prompt_id": variant.id,
            "modifications": modifications,
            "quality_delta": round(event.quality_delta, 3),
        }

    # ─── Public API ──────────────────────────────────────────────────────────

    def get_current_prompt(self) -> str:
        """Get the current active system prompt."""
        active = self._get_active_prompt()
        if active:
            return active.prompt_text
        return _BASE_SYSTEM_PROMPT

    def _get_active_prompt(self) -> Optional[PromptVariant]:
        if self.active_prompt_id:
            for p in self.prompt_variants:
                if p.id == self.active_prompt_id:
                    return p
        if self.prompt_variants:
            return self.prompt_variants[-1]
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Engine statistics."""
        total_convs = len(self.conversations)
        avg_quality = 0.0
        if total_convs > 0:
            avg_quality = sum(c.quality_score for c in self.conversations) / total_convs
        
        active = self._get_active_prompt()
        
        return {
            "total_conversations": total_convs,
            "total_turns": self._turn_counter,
            "avg_quality": round(avg_quality, 3),
            "prompt_variants": len(self.prompt_variants),
            "active_prompt_id": self.active_prompt_id,
            "lessons_learned": len(self.lessons_learned),
            "evolution_events": len(self.evolution_events),
            "current_modifications": active.modifications if active else [],
        }

    def get_evolution_history(self, limit: int = 20) -> List[Dict]:
        """Get recent evolution events."""
        return [e.to_dict() for e in reversed(self.evolution_events[-limit:])]

    def get_lessons(self) -> List[str]:
        """Get all lessons learned."""
        return self.lessons_learned

    def get_prompt_variants(self) -> List[Dict]:
        """Get all prompt variants."""
        return [p.to_dict() for p in self.prompt_variants]

    def _create_base_variant(self):
        """Create the initial base prompt variant."""
        variant = PromptVariant(
            id="prompt_base",
            created_at=datetime.utcnow(),
            prompt_text=_BASE_SYSTEM_PROMPT,
            base_prompt=_BASE_SYSTEM_PROMPT,
            modifications=["Base system prompt"],
            active=True,
        )
        self.prompt_variants.append(variant)
        self.active_prompt_id = variant.id
        self._save_state()
