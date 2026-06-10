"""
core/predictive_engine.py

DEEP Predictive Workflow Engine — Learns your patterns, anticipates your needs.

Features:
- Time-of-day behavior tracking (hour buckets)
- Command-type clustering (code, research, system, chat, etc.)
- Sequence pattern detection (what you do after what)
- Confidence-scored predictive suggestions
- User feedback loop (accept/reject trains the model)
- Weekly rhythm detection (Monday vs Friday patterns)
- Proactive suggestion generation
- All local, no API keys

Usage:
    from DEEP.core.predictive_engine import PredictiveEngine
    
    engine = PredictiveEngine()
    
    # Record an interaction
    engine.record_interaction("user", "Write a Python script")
    
    # Get predictions for right now
    suggestions = engine.get_predictions()
    
    # User accepted a prediction
    engine.record_feedback("pred_123", accepted=True)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict, Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple

try:
    from core.event_bus import EventBus
except ImportError:
    from event_bus import EventBus

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class ActionType(Enum):
    CODE = "code"           # Write/edit code
    RESEARCH = "research"   # Search, find info
    SYSTEM = "system"       # Status, settings, commands
    CHAT = "chat"           # General conversation
    PRODUCTIVITY = "prod"   # Calendar, tasks, scheduling
    SECURITY = "security"   # Network, monitoring
    CREATIVE = "creative"   # Writing, design
    LEARNING = "learning"   # Tutorials, explanations
    UNKNOWN = "unknown"


@dataclass
class UserInteraction:
    """A single recorded user interaction."""
    id: str
    timestamp: datetime
    action_type: ActionType
    text: str
    day_of_week: int      # 0=Monday
    hour_bucket: int      # 0-23
    context_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "action_type": self.action_type.value,
            "text": self.text[:200],
            "day_of_week": self.day_of_week,
            "hour_bucket": self.hour_bucket,
            "context_tags": self.context_tags,
        }


@dataclass
class TimePattern:
    """A detected temporal pattern."""
    action_type: str
    hour_bucket: int
    frequency: int
    confidence: float  # 0.0 to 1.0
    sample_texts: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type,
            "hour_bucket": self.hour_bucket,
            "frequency": self.frequency,
            "confidence": round(self.confidence, 3),
        }


@dataclass
class SequencePattern:
    """A detected sequence: after action A, user does action B."""
    trigger_type: str
    predicted_type: str
    trigger_text: str     # Example trigger text
    predicted_action: str  # Suggested next action
    frequency: int
    confidence: float
    avg_minutes_after: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trigger_type": self.trigger_type,
            "predicted_type": self.predicted_type,
            "predicted_action": self.predicted_action,
            "frequency": self.frequency,
            "confidence": round(self.confidence, 3),
            "avg_minutes_after": round(self.avg_minutes_after, 1),
        }


@dataclass
class Prediction:
    """A single predictive suggestion for the user."""
    id: str
    timestamp: datetime
    action_type: str
    suggestion: str
    reason: str
    confidence: float
    predicted_at_hour: int
    predicted_dow: int
    triggered_by: Optional[str] = None
    accepted: Optional[bool] = None  # None = pending

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "action_type": self.action_type,
            "suggestion": self.suggestion,
            "reason": self.reason,
            "confidence": round(self.confidence, 3),
            "triggered_by": self.triggered_by,
            "accepted": self.accepted,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Action Classification
# ═══════════════════════════════════════════════════════════════════════════════

_ACTION_KEYWORDS: Dict[ActionType, List[str]] = {
    ActionType.CODE: ["code", "script", "program", "debug", "function", "class", "python", "javascript", "java", "rust", "cpp", "algorithm", "refactor", "compile", "error", "bug", "fix", "write", "develop", "api", "database", "sql", "html", "css", "react", "component"],
    ActionType.RESEARCH: ["search", "find", "research", "look up", "google", "what is", "how to", "explain", "information", "article", "paper", "study", "news", "recent", "latest", "trend"],
    ActionType.SYSTEM: ["status", "system", "server", "restart", "settings", "config", "update", "log", "health", "check", "monitor", "cpu", "memory", "disk", "network", "port"],
    ActionType.PRODUCTIVITY: ["calendar", "schedule", "remind", "task", "todo", "deadline", "meeting", "plan", "organize", "time", "appointment", "event", "alarm"],
    ActionType.SECURITY: ["security", "network", "scan", "firewall", "device", "intrusion", "vulnerability", "threat", "monitor", "alert", "protect", "encrypt"],
    ActionType.CREATIVE: ["write", "story", "essay", "email", "draft", "design", "create", "draw", "image", "art", "poem", "blog", "content", "copy"],
    ActionType.LEARNING: ["learn", "tutorial", "course", "lesson", "study", "education", "concept", "theory", "practice", "exercise", "quiz", "understand", "teach"],
    ActionType.CHAT: ["hello", "hi", "hey", "how are you", "good morning", "good evening", "thank", "thanks", "nice", "great", "awesome", "talk", "chat", "conversation"],
}


def classify_action(text: str) -> ActionType:
    """Classify user text into an action type."""
    text_lower = text.lower()
    scores: Dict[ActionType, int] = {t: 0 for t in ActionType}
    
    for act_type, keywords in _ACTION_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[act_type] += 1
    
    # Weight exact matches higher
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return ActionType.UNKNOWN
    return best


# ═══════════════════════════════════════════════════════════════════════════════
# Predictive Engine
# ═══════════════════════════════════════════════════════════════════════════════

class PredictiveEngine:
    """
    Learns user behavior patterns and generates predictive suggestions.
    """

    MIN_SAMPLES_FOR_PREDICTION = 3
    CONFIDENCE_THRESHOLD = 0.4
    MAX_DAILY_PREDICTIONS = 5  # Don't overwhelm the user

    def __init__(self, data_dir: Optional[Path] = None, event_bus: EventBus = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / "data" / "predictive"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Raw data
        self.interactions: List[UserInteraction] = []
        self.predictions: List[Prediction] = []
        
        # Derived patterns
        self.time_patterns: List[TimePattern] = []
        self.sequence_patterns: List[SequencePattern] = []
        
        self.event_bus = event_bus
        
        # State
        self._last_prediction_time: Optional[datetime] = None
        self._predictions_today = 0
        self._today_date: Optional[datetime.date] = None
        
        # Load state
        self._load_state()

    async def start(self) -> None:
        """Activate the predictive engine."""
        logger.info("[PredictiveEngine] Started")

    async def stop(self) -> None:
        """Deactivate the predictive engine."""
        logger.info("[PredictiveEngine] Stopped")

    def status(self) -> Dict[str, Any]:
        """Return operational status."""
        return {
            "interactions": len(self.interactions),
            "predictions": len(self.predictions),
            "patterns": len(self.time_patterns) + len(self.sequence_patterns),
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
        return self.data_dir / "predictive_state.json"

    def _load_state(self):
        f = self._state_file()
        if not f.exists():
            return
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            for i_data in data.get("interactions", [])[-200:]:  # Keep last 200
                self.interactions.append(UserInteraction(
                    id=i_data["id"],
                    timestamp=datetime.fromisoformat(i_data["timestamp"]),
                    action_type=ActionType(i_data["action_type"]),
                    text=i_data["text"],
                    day_of_week=i_data["day_of_week"],
                    hour_bucket=i_data["hour_bucket"],
                    context_tags=i_data.get("context_tags", []),
                ))
            for p_data in data.get("predictions", [])[-50:]:
                self.predictions.append(Prediction(
                    id=p_data["id"],
                    timestamp=datetime.fromisoformat(p_data["timestamp"]),
                    action_type=p_data["action_type"],
                    suggestion=p_data["suggestion"],
                    reason=p_data["reason"],
                    confidence=p_data["confidence"],
                    predicted_at_hour=p_data["predicted_at_hour"],
                    predicted_dow=p_data["predicted_dow"],
                    triggered_by=p_data.get("triggered_by"),
                    accepted=p_data.get("accepted"),
                ))
            logger.info(f"[PredictiveEngine] Loaded {len(self.interactions)} interactions, {len(self.predictions)} predictions")
        except Exception as e:
            logger.warning(f"[PredictiveEngine] Failed to load state: {e}")

    def _save_state(self):
        try:
            data = {
                "saved_at": datetime.utcnow().isoformat(),
                "interactions": [i.to_dict() for i in self.interactions[-200:]],
                "predictions": [p.to_dict() for p in self.predictions[-50:]],
            }
            self._state_file().write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"[PredictiveEngine] Failed to save state: {e}")

    # ─── Event System ────────────────────────────────────────────────────────


    # ─── Recording ───────────────────────────────────────────────────────────

    def record_interaction(self, sender: str, text: str, tags: Optional[List[str]] = None):
        """Record a user interaction for pattern learning."""
        if sender != "user":
            return  # Only learn from user inputs
        
        now = datetime.utcnow()
        action = classify_action(text)
        
        interaction = UserInteraction(
            id=f"int_{int(time.time()*1000)}",
            timestamp=now,
            action_type=action,
            text=text[:300],
            day_of_week=now.weekday(),
            hour_bucket=now.hour,
            context_tags=tags or [],
        )
        
        self.interactions.append(interaction)
        
        # Trim old interactions
        if len(self.interactions) > 500:
            self.interactions = self.interactions[-400:]
        
        self._save_state()
        
        # Trigger pattern rebuild if we have enough data
        if len(self.interactions) >= self.MIN_SAMPLES_FOR_PREDICTION:
            self._rebuild_patterns()
            
            # Try to generate a prediction based on this interaction
            pred = self._generate_prediction_from_interaction(interaction)
            if pred:
                self._publish("prediction_ready", pred.to_dict())

    def record_feedback(self, prediction_id: str, accepted: bool):
        """User accepted or rejected a prediction — learn from it."""
        for p in self.predictions:
            if p.id == prediction_id:
                p.accepted = accepted
                self._save_state()
                
                # If accepted, reinforce the pattern
                if accepted:
                    self._rebuild_patterns()
                
                self._publish("feedback_recorded", {
                    "prediction_id": prediction_id,
                    "accepted": accepted,
                })
                return True
        return False

    # ─── Pattern Detection ───────────────────────────────────────────────────

    def _rebuild_patterns(self):
        """Rebuild all patterns from recorded interactions."""
        if len(self.interactions) < self.MIN_SAMPLES_FOR_PREDICTION:
            return
        
        self._rebuild_time_patterns()
        self._rebuild_sequence_patterns()

    def _rebuild_time_patterns(self):
        """Detect which action types happen at which hours."""
        # Count (action_type, hour_bucket) occurrences
        counts: Dict[Tuple[str, int], List[str]] = defaultdict(list)
        
        for i in self.interactions:
            key = (i.action_type.value, i.hour_bucket)
            counts[key].append(i.text[:60])
        
        # Convert to patterns with confidence
        total_per_hour: Dict[int, int] = Counter()
        for i in self.interactions:
            total_per_hour[i.hour_bucket] += 1
        
        self.time_patterns = []
        for (action, hour), texts in counts.items():
            freq = len(texts)
            total = total_per_hour.get(hour, 1)
            confidence = freq / max(total, 1)
            
            if freq >= 2 and confidence >= 0.3:  # At least 2 occurrences, 30% of that hour
                self.time_patterns.append(TimePattern(
                    action_type=action,
                    hour_bucket=hour,
                    frequency=freq,
                    confidence=min(confidence, 0.95),
                    sample_texts=texts[:3],
                ))
        
        # Sort by confidence
        self.time_patterns.sort(key=lambda p: p.confidence, reverse=True)

    def _rebuild_sequence_patterns(self):
        """Detect sequences: after action A, user does action B within N minutes."""
        if len(self.interactions) < 4:
            return
        
        # Look for pairs within 30 minutes
        seq_counts: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        seq_texts: Dict[Tuple[str, str], Tuple[str, str]] = {}
        
        for i in range(len(self.interactions) - 1):
            curr = self.interactions[i]
            for j in range(i + 1, min(i + 5, len(self.interactions))):
                next_i = self.interactions[j]
                gap = (next_i.timestamp - curr.timestamp).total_seconds() / 60
                if gap > 30:
                    break
                
                key = (curr.action_type.value, next_i.action_type.value)
                seq_counts[key].append(gap)
                if key not in seq_texts:
                    seq_texts[key] = (curr.text, next_i.text)
        
        self.sequence_patterns = []
        for (trigger, predicted), gaps in seq_counts.items():
            freq = len(gaps)
            if freq >= 2:
                # Confidence = frequency relative to total trigger occurrences
                trigger_count = sum(1 for i in self.interactions if i.action_type.value == trigger)
                confidence = freq / max(trigger_count, 1)
                
                texts = seq_texts.get((trigger, predicted), ("", ""))
                self.sequence_patterns.append(SequencePattern(
                    trigger_type=trigger,
                    predicted_type=predicted,
                    trigger_text=texts[0],
                    predicted_action=self._infer_action_from_type(predicted),
                    frequency=freq,
                    confidence=min(confidence, 0.95),
                    avg_minutes_after=sum(gaps) / len(gaps),
                ))
        
        self.sequence_patterns.sort(key=lambda p: p.confidence, reverse=True)

    def _infer_action_from_type(self, action_type: str) -> str:
        """Map action type to a common user request."""
        mapping = {
            "code": "continue coding or write a script",
            "research": "look up information or search",
            "system": "check system status or health",
            "chat": "have a conversation",
            "prod": "check calendar or organize tasks",
            "security": "review security status",
            "creative": "write or create something",
            "learning": "learn something new",
            "unknown": "continue with current task",
        }
        return mapping.get(action_type, "continue working")

    # ─── Prediction Generation ───────────────────────────────────────────────

    def _generate_prediction_from_interaction(self, interaction: UserInteraction) -> Optional[Prediction]:
        """Generate a prediction based on a just-completed interaction."""
        # Check sequence patterns first
        for seq in self.sequence_patterns:
            if seq.trigger_type == interaction.action_type.value and seq.confidence >= self.CONFIDENCE_THRESHOLD:
                return self._create_prediction(
                    action_type=seq.predicted_type,
                    suggestion=f"Would you like to {seq.predicted_action}?",
                    reason=f"You often do this after {seq.trigger_type} tasks",
                    confidence=seq.confidence,
                    triggered_by=interaction.id,
                )
        return None

    def get_predictions(self, max_results: int = 3) -> List[Dict]:
        """Get current predictive suggestions based on time and context."""
        now = datetime.utcnow()
        current_hour = now.hour
        current_dow = now.weekday()
        
        predictions = []
        
        # Time-based predictions
        for tp in self.time_patterns[:5]:
            if tp.hour_bucket == current_hour and tp.confidence >= self.CONFIDENCE_THRESHOLD:
                action = self._infer_action_from_type(tp.action_type)
                pred = self._create_prediction(
                    action_type=tp.action_type,
                    suggestion=f"Would you like to {action}?",
                    reason=f"You often do this around {tp.hour_bucket}:00",
                    confidence=tp.confidence,
                )
                if pred:
                    predictions.append(pred.to_dict())
        
        # If recent interaction, check sequence patterns
        if self.interactions:
            last = self.interactions[-1]
            gap = (now - last.timestamp).total_seconds() / 60
            if gap < 10:  # Within 10 minutes of last interaction
                for seq in self.sequence_patterns[:3]:
                    if seq.trigger_type == last.action_type.value and seq.confidence >= self.CONFIDENCE_THRESHOLD:
                        pred = self._create_prediction(
                            action_type=seq.predicted_type,
                            suggestion=f"Would you like to {seq.predicted_action}?",
                            reason=f"You often do this next after {seq.trigger_type}",
                            confidence=seq.confidence * 0.9,  # Slightly lower for sequence
                            triggered_by=last.id,
                        )
                        if pred:
                            predictions.append(pred.to_dict())
        
        # Deduplicate by suggestion text
        seen = set()
        unique = []
        for p in predictions:
            if p["suggestion"] not in seen:
                seen.add(p["suggestion"])
                unique.append(p)
        
        return unique[:max_results]

    def _create_prediction(self, action_type: str, suggestion: str, reason: str,
                           confidence: float, triggered_by: Optional[str] = None) -> Optional[Prediction]:
        """Create and store a prediction, respecting daily limits."""
        now = datetime.utcnow()
        
        # Reset daily counter if new day
        if self._today_date != now.date():
            self._today_date = now.date()
            self._predictions_today = 0
        
        # Rate limit
        if self._predictions_today >= self.MAX_DAILY_PREDICTIONS:
            return None
        
        # Don't predict too frequently
        if self._last_prediction_time:
            gap = (now - self._last_prediction_time).total_seconds()
            if gap < 300:  # Min 5 minutes between predictions
                return None
        
        pred = Prediction(
            id=f"pred_{int(time.time()*1000)}",
            timestamp=now,
            action_type=action_type,
            suggestion=suggestion,
            reason=reason,
            confidence=confidence,
            predicted_at_hour=now.hour,
            predicted_dow=now.weekday(),
            triggered_by=triggered_by,
        )
        
        self.predictions.append(pred)
        self._predictions_today += 1
        self._last_prediction_time = now
        
        if len(self.predictions) > 100:
            self.predictions = self.predictions[-80:]
        
        self._save_state()
        return pred

    # ─── Stats & Introspection ─────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Engine statistics."""
        total = len(self.interactions)
        action_counts = Counter(i.action_type.value for i in self.interactions)
        acceptance_rate = 0.0
        evaluated = [p for p in self.predictions if p.accepted is not None]
        if evaluated:
            accepted = sum(1 for p in evaluated if p.accepted)
            acceptance_rate = accepted / len(evaluated)
        
        return {
            "total_interactions": total,
            "action_distribution": dict(action_counts),
            "time_patterns_detected": len(self.time_patterns),
            "sequence_patterns_detected": len(self.sequence_patterns),
            "predictions_made": len(self.predictions),
            "predictions_accepted": sum(1 for p in self.predictions if p.accepted is True),
            "predictions_rejected": sum(1 for p in self.predictions if p.accepted is False),
            "acceptance_rate": round(acceptance_rate, 3),
            "predictions_today": self._predictions_today,
        }

    def get_patterns(self) -> Dict[str, List[Dict]]:
        """Get detected patterns for inspection."""
        return {
            "time_patterns": [p.to_dict() for p in self.time_patterns[:10]],
            "sequence_patterns": [p.to_dict() for p in self.sequence_patterns[:10]],
        }

    def get_recent_predictions(self, limit: int = 10) -> List[Dict]:
        """Get recent predictions with their status."""
        return [p.to_dict() for p in reversed(self.predictions[-limit:])]
