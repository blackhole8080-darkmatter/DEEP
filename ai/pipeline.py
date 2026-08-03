"""
deep/ai/pipeline.py

Fast synchronous pipeline (target < 200 ms per command) that:
    1. Classifies user intent
    2. Detects emotional state (mood)
    3. Routes to the correct skill module or escalates to LangGraph

Subscribes to EventBus "user_command" events on startup and calls
process() for each incoming command.

Architecture:
    DeepPipeline ──► IntentClassifier ──► MoodDetector ──► SkillRouter
                            │                     │               │
                            ▼                     ▼               ▼
                    intent + confidence      mood features     routed event
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Optional heavy imports with graceful degradation ────────────────────────

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import SGDClassifier
    from sklearn.pipeline import Pipeline as SklearnPipeline
    from sklearn.exceptions import NotFittedError
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not installed — intent classification uses keyword fallback")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("librosa not installed — mood detection falls back to text-only")

try:
    from core.config import Settings
except ImportError:
    from config import Settings

try:
    from core.event_bus import EventBus
except ImportError:
    from event_bus import EventBus


# ═══════════════════════════════════════════════════════════════════════════════
# Seed Training Data (minimum 20 examples per category)
# ═══════════════════════════════════════════════════════════════════════════════

SEED_DATA: Dict[str, List[str]] = {
    "system_control": [
        "turn off the lights",
        "turn on the lights",
        "lock the door",
        "unlock the door",
        "set the thermostat to 22 degrees",
        "increase brightness",
        "decrease volume",
        "mute the speakers",
        "open the blinds",
        "close the curtains",
        "shut down the computer",
        "restart the router",
        "check system status",
        "enable do not disturb",
        "disable notifications",
        "set a timer for 5 minutes",
        "turn on night mode",
        "activate security mode",
        "run a speed test",
        "check disk space",
        "update system",
    ],
    "information_query": [
        "what is the weather today",
        "what time is it",
        "who is the president of the united states",
        "how tall is mount everest",
        "what is the capital of japan",
        "when is the next solar eclipse",
        "how does photosynthesis work",
        "what is the speed of light",
        "explain quantum computing",
        "who wrote hamlet",
        "what is the stock price of apple",
        "how do I make a martini",
        "what is the meaning of life",
        "tell me about the roman empire",
        "how far is the moon",
        "what is blockchain",
        "what is the best programming language",
        "who invented the telephone",
        "what is the population of india",
        "what is the boiling point of water",
    ],
    "creative_task": [
        "write a poem about the ocean",
        "generate a python script for sorting",
        "create a logo description",
        "compose a haiku about spring",
        "write an email to my boss",
        "draft a short story about a robot",
        "design a database schema",
        "help me brainstorm startup ideas",
        "write a song lyric",
        "generate a recipe for pasta",
        "create a workout routine",
        "write a to-do list",
        "help me with my resume",
        "write a shell script",
        "create a presentation outline",
        "generate a crossword puzzle",
        "write a thank you note",
        "create a character for dnd",
        "help me plan a dinner party",
        "write a birthday card message",
    ],
    "conversation": [
        "how are you doing",
        "what is your name",
        "tell me a joke",
        "good morning",
        "good night",
        "nice to meet you",
        "thank you",
        "I appreciate your help",
        "what is new",
        "how was your day",
        "do you like music",
        "what are you thinking about",
        "that is funny",
        "can you hear me",
        "I feel lonely",
        "tell me something interesting",
        "what do you think about ai",
        "do you have dreams",
        "are you sentient",
        "what is your favourite colour",
    ],
    "network_action": [
        "scan the network",
        "check connected devices",
        "show me the router logs",
        "is anyone on the guest wifi",
        "block this mac address",
        "allow this device on the network",
        "run a vulnerability scan",
        "check firewall rules",
        "ping google",
        "what is my ip address",
        "trace route to example.com",
        "check dns settings",
        "monitor network traffic",
        "disconnect unknown devices",
        "show network topology",
        "run a bandwidth test",
        "check port status",
        "enable guest network",
        "disable remote access",
        "show dhcp leases",
    ],
    "research_task": [
        "research quantum computing",
        "find papers on neural networks",
        "what is the latest in fusion energy",
        "summarise this article",
        "compare react and vue",
        "find documentation for docker",
        "what are the best practices for rest apis",
        "research renewable energy trends",
        "find case studies on agile methodology",
        "what is the state of the art in computer vision",
        "compare different database architectures",
        "find recent news on ai regulation",
        "research history of the internet",
        "summarise the theory of relativity",
        "find statistics on climate change",
        "research electric vehicle batteries",
        "compare cloud providers aws azure gcp",
        "what are the latest web frameworks",
        "find tutorials on machine learning",
        "research space exploration milestones",
    ],
    "planning_task": [
        "plan my week",
        "schedule a meeting for tomorrow at 2pm",
        "remind me to call mum at 5",
        "create a project timeline",
        "what is on my calendar today",
        "set a reminder for my dentist appointment",
        "help me prioritise my tasks",
        "block time for deep work",
        "plan a trip to japan",
        "create a budget for next month",
        "set up a study schedule",
        "plan meals for the week",
        "create a reading list",
        "schedule exercise sessions",
        "plan a team offsite",
        "create a milestone map",
        "set quarterly goals",
        "plan a renovation timeline",
        "build a habit tracker",
        "schedule a daily standup",
    ],
    "multi_step_execution": [
        "find the weather and then set the thermostat accordingly",
        "turn on the lights and play jazz music",
        "check my email and then create tasks for each",
        "find a restaurant and then call to book",
        "download the file and then extract it",
        "scan the network and then run a security check",
        "find the best route and then send it to my phone",
        "order groceries and then set reminders for delivery",
        "compile the code and then run the tests",
        "search for flights and then compare prices",
        "take a screenshot and then upload it",
        "convert this pdf to text and then summarise it",
        "find a recipe and then add ingredients to shopping list",
        "check disk space and then clean up old files",
        "monitor cpu usage and then alert me if it spikes",
        "find my keys and then unlock the door",
        "scan documents and then organise them by date",
        "fetch the news and then read the headlines aloud",
        "analyse the log file and then generate a report",
        "sync my calendar and then send invites",
    ],
    "explain_concept": [
        "explain quantum entanglement",
        "what is CRISPR",
        "how does backpropagation work",
        "explain transformer attention",
        "what is a black hole",
        "explain photosynthesis",
        "what is blockchain technology",
        "explain neural networks simply",
        "what is dark matter",
        "explain genetic engineering",
        "what is reinforcement learning",
        "explain quantum superposition",
        "what is the Higgs boson",
        "explain natural language processing",
        "what is graphene",
        "explain computer vision",
        "what is mRNA vaccine technology",
        "explain federated learning",
        "what is topological quantum computing",
        "explain protein folding",
    ],
    "find_paper": [
        "find papers on protein folding",
        "latest research on room temperature superconductors",
        "papers about large language models",
        "find research on quantum error correction",
        "recent papers on autonomous driving",
        "find studies about climate tipping points",
        "papers on brain-computer interfaces",
        "latest work on diffusion models",
        "find research on cancer immunotherapy",
        "papers about topological insulators",
        "recent publications on gene editing",
        "find papers on gravitational waves",
        "research about renewable energy storage",
        "latest papers on explainable AI",
        "find studies on microbiome health",
        "papers about fusion reactor progress",
        "research on synthetic biology",
        "find papers on meta-learning",
        "latest work on photonic computing",
        "papers about exoplanet detection",
    ],
    "track_field": [
        "what is happening in robotics",
        "summarise AI research this week",
        "latest developments in quantum computing",
        "what is new in cybersecurity",
        "track progress in fusion energy",
        "what is happening in space exploration",
        "latest neuroscience breakthroughs",
        "what is new in materials science",
        "track climate science updates",
        "latest in computational biology",
        "what is happening in nanotechnology",
        "track progress in battery technology",
        "latest developments in gene therapy",
        "what is new in astrophysics",
        "track machine learning trends",
        "latest in computer architecture",
        "what is happening in oceanography",
        "track progress in carbon capture",
        "latest in epidemiology research",
        "what is new in cognitive science",
    ],
    "cross_domain_query": [
        "how does neuroscience relate to AI",
        "connection between quantum physics and computing",
        "how does biology inform robotics",
        "relationship between climate and economics",
        "how does linguistics connect to machine learning",
        "link between materials science and energy",
        "how does psychology inform interface design",
        "connection between astronomy and navigation",
        "how does immunology relate to cancer treatment",
        "relationship between topology and physics",
        "how does philosophy inform AI ethics",
        "connection between oceanography and climate",
        "how does archaeology use satellite imaging",
        "link between genetics and anthropology",
        "how does acoustics connect to marine biology",
        "relationship between graph theory and networks",
        "how does ecology inform urban planning",
        "connection between number theory and cryptography",
        "how does thermodynamics relate to computing",
        "relationship between optics and telecommunications",
    ],
    "daily_briefing": [
        "morning briefing",
        "what did I miss",
        "science update",
        "daily research summary",
        "catch me up on science",
        "morning science briefing",
        "what is new in research",
        "today's science headlines",
        "brief me on latest papers",
        "science news summary",
        "what happened in science today",
        "research roundup",
        "academic news briefing",
        "tech and science update",
        "morning knowledge feed",
        "latest breakthroughs briefing",
        "science digest",
        "paper of the day",
        "research highlights",
        "what is trending in science",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# Result dataclass
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Immutable result from running the full pipeline."""

    intent: str
    confidence: float
    mood: str
    routed_to: str
    duration_ms: float


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 1 — IntentClassifier
# ═══════════════════════════════════════════════════════════════════════════════

class IntentClassifier:
    """
    sklearn text-classification pipeline.
    Falls back to keyword-based classification if scikit-learn is unavailable.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model_path = getattr(settings, "intent_model_path", "data/intent_model.pkl")
        self._pipeline: Optional[Any] = None
        self._intent_categories = self._resolve_categories()
        self._lock = asyncio.Lock()

    def _resolve_categories(self) -> List[str]:
        """Return intent category list from config or default seed keys."""
        cats = getattr(self.settings, "intent_categories", None)
        if cats:
            return list(cats)
        return list(SEED_DATA.keys())

    # ── Training / Loading ─────────────────────────────────────────────────

    async def load_or_train(self) -> None:
        """Load persisted model, or train on seed data if missing."""
        if not SKLEARN_AVAILABLE:
            logger.info("[IntentClassifier] scikit-learn unavailable — using keyword fallback")
            return

        if os.path.exists(self.model_path):
            try:
                import joblib
                self._pipeline = joblib.load(self.model_path)
                logger.info(f"[IntentClassifier] Loaded model from {self.model_path}")
                return
            except Exception as e:
                logger.warning(f"[IntentClassifier] Failed to load model: {e} — retraining")

        # Train on seed data
        X: List[str] = []
        y: List[str] = []
        for intent, examples in SEED_DATA.items():
            X.extend(examples)
            y.extend([intent] * len(examples))

        self._pipeline = SklearnPipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=500)),
            ("clf", SGDClassifier(loss="log_loss", max_iter=1000, tol=1e-3, random_state=42)),
        ])
        self._pipeline.fit(X, y)

        Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
        import joblib
        joblib.dump(self._pipeline, self.model_path)
        logger.info(f"[IntentClassifier] Trained and saved model to {self.model_path}")

    async def classify(self, text: str) -> Tuple[str, float]:
        """Classify text → (intent, confidence).  Confidence is in [0, 1]."""
        text = text.strip().lower()
        if not text:
            return ("unknown", 0.0)

        if not SKLEARN_AVAILABLE or self._pipeline is None:
            return self._keyword_classify(text)

        async with self._lock:
            try:
                probs = self._pipeline.predict_proba([text])[0]
                idx = probs.argmax()
                intent = self._pipeline.classes_[idx]
                confidence = float(probs[idx])
                return (intent, confidence)
            except NotFittedError:
                return self._keyword_classify(text)
            except Exception as e:
                logger.warning(f"[IntentClassifier] predict error: {e}")
                return self._keyword_classify(text)

    def _keyword_classify(self, text: str) -> Tuple[str, float]:
        """Fallback keyword-based classification."""
        scores: Dict[str, int] = {}
        for intent, examples in SEED_DATA.items():
            score = sum(1 for ex in examples if any(tok in text for tok in ex.lower().split()))
            scores[intent] = score
        if not scores or max(scores.values()) == 0:
            return ("unknown", 0.0)
        best = max(scores, key=scores.get)
        return (best, min(0.6, max(0.3, scores[best] / 5.0)))

    async def retrain(self, new_examples: Dict[str, List[str]]) -> None:
        """Re-fit the model with new training examples and persist."""
        if not SKLEARN_AVAILABLE:
            logger.warning("[IntentClassifier] Cannot retrain — scikit-learn unavailable")
            return

        X: List[str] = []
        y: List[str] = []
        # Merge seed + new
        for intent, examples in {**SEED_DATA, **new_examples}.items():
            X.extend(examples)
            y.extend([intent] * len(examples))

        new_model = SklearnPipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=500)),
            ("clf", SGDClassifier(loss="log_loss", max_iter=1000, tol=1e-3, random_state=42)),
        ])
        new_model.fit(X, y)

        async with self._lock:
            self._pipeline = new_model

        Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
        import joblib
        joblib.dump(self._pipeline, self.model_path)
        logger.info(f"[IntentClassifier] Retrained and saved ({len(X)} examples)")

    async def hot_swap(self, new_model: Any) -> None:
        """Thread-safe replacement of the live model."""
        async with self._lock:
            self._pipeline = new_model
        logger.info("[IntentClassifier] Model hot-swapped live")


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 2 — MoodDetector
# ═══════════════════════════════════════════════════════════════════════════════

class MoodDetector:
    """
    Detects user emotional state from audio features (librosa) or
    from text sentiment (word-list fallback).
    Publishes "mood_update" events via the EventBus.
    """

    # Simple word-list fallback (text-only path)
    POSITIVE_WORDS = {
        "good", "great", "awesome", "excellent", "happy", "excited",
        "love", "fantastic", "wonderful", "amazing", "perfect", "nice",
        "pleased", "delighted", "cheerful", "joyful", "optimistic",
    }
    NEGATIVE_WORDS = {
        "bad", "terrible", "awful", "sad", "angry", "frustrated",
        "hate", "worried", "stressed", "annoyed", "upset", "depressed",
        "disappointed", "exhausted", "irritated", "anxious", "tired",
    }

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    # ── Audio path ────────────────────────────────────────────────────────

    def classify_audio(self, audio_array) -> Tuple[str, Dict[str, float]]:
        """
        Extract acoustic mood features from a numpy audio array.
        Returns (mood_label, feature_dict).
        """
        if not NUMPY_AVAILABLE or not LIBROSA_AVAILABLE:
            logger.warning("[MoodDetector] Audio analysis unavailable — use classify_text()")
            return ("neutral", {"energy": 0.5, "speech_rate": 0.0, "pitch_variance": 0.0})

        try:
            sr = 16000  # assumed; caller should pass sr if different
            # Energy = RMS amplitude, normalised 0-1
            rms = librosa.feature.rms(y=audio_array)[0]
            energy = float(min(1.0, rms.mean() * 10))  # rough normalisation

            # Speech rate proxy = zero crossing rate mean
            zcr = librosa.feature.zero_crossing_rate(audio_array)[0]
            speech_rate = float(zcr.mean())

            # Pitch variance = std of fundamental frequency (F0)
            f0 = librosa.yin(audio_array, fmin=50, fmax=300, sr=sr)
            pitch_variance = float(f0.std()) if len(f0) > 1 else 0.0

            features = {
                "energy": round(energy, 4),
                "speech_rate": round(speech_rate, 4),
                "pitch_variance": round(pitch_variance, 4),
            }

            mood = self._features_to_mood(energy, speech_rate, pitch_variance)
            return (mood, features)
        except Exception as e:
            logger.warning(f"[MoodDetector] Audio analysis error: {e}")
            return ("neutral", {"energy": 0.5, "speech_rate": 0.0, "pitch_variance": 0.0})

    def _features_to_mood(self, energy: float, speech_rate: float, pitch_variance: float) -> str:
        """Map acoustic features to a mood label."""
        if energy > 0.7 and pitch_variance > 30:
            return "energetic"
        if energy < 0.3 and speech_rate < 0.01:
            return "tired"
        if pitch_variance > 40 and energy > 0.5:
            return "stressed"
        if energy > 0.5 and speech_rate > 0.02:
            return "focused"
        if energy > 0.6 and pitch_variance < 20:
            return "calm"
        return "neutral"

    # ── Text fallback ─────────────────────────────────────────────────────

    def classify_text(self, text: str) -> Tuple[str, Dict[str, float]]:
        """
        Classify mood from text using a simple positive/negative/neutral
        word list. Maps to calm/stressed/focused/neutral.
        """
        text_lower = text.lower()
        pos = sum(1 for w in self.POSITIVE_WORDS if w in text_lower)
        neg = sum(1 for w in self.NEGATIVE_WORDS if w in text_lower)

        features = {
            "positive_words": pos,
            "negative_words": neg,
            "text_length": len(text.split()),
        }

        if pos > neg and pos >= 2:
            return ("calm", features)
        if neg > pos and neg >= 2:
            return ("stressed", features)
        if "?" in text or "help" in text_lower or "how" in text_lower:
            return ("focused", features)
        return ("neutral", features)


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 3 — SkillRouter
# ═══════════════════════════════════════════════════════════════════════════════

class SkillRouter:
    """
    Routes the classified intent to a skill module.
    Publishes either "routed_command" (high confidence) or
    "escalate_to_graph" (low confidence) on the EventBus.
    """

    def __init__(self, event_bus: EventBus, settings: Settings) -> None:
        self.event_bus = event_bus
        self.settings = settings

    def _resolve_routes(self) -> Dict[str, str]:
        """Return skill routing table from config or sensible defaults."""
        routes = getattr(self.settings, "skill_routes", None)
        if routes:
            return dict(routes)
        return {
            "system_control": "skills.system_control",
            "information_query": "skills.information_query",
            "creative_task": "skills.creative_task",
            "conversation": "skills.conversation",
            "network_action": "skills.network_action",
            "research_task": "skills.research_task",
            "planning_task": "skills.planning_task",
            "multi_step_execution": "skills.multi_step_execution",
            "explain_concept": "skills.explain_concept",
            "find_paper": "skills.find_paper",
            "track_field": "skills.track_field",
            "cross_domain_query": "skills.cross_domain_query",
            "daily_briefing": "skills.daily_briefing",
        }

    def attach_context(
        self,
        intent: str,
        confidence: float,
        mood: str,
        command: str,
    ) -> Dict[str, Any]:
        """Build the routed payload dict."""
        routes = self._resolve_routes()
        skill_module = routes.get(intent, "skills.general")
        return {
            "intent": intent,
            "confidence": round(confidence, 4),
            "mood": mood,
            "command": command,
            "skill_module": skill_module,
            "timestamp": datetime.now().isoformat(),
        }

    async def publish_decision(self, payload: Dict[str, Any]) -> None:
        """
        Compare confidence against threshold and publish the appropriate
        event on the EventBus.
        """
        threshold = getattr(self.settings, "pipeline_confidence_threshold", 0.65)
        confidence = payload.get("confidence", 0.0)

        if confidence >= threshold:
            await self.event_bus.publish("routed_command", payload)
            logger.debug(f"[SkillRouter] routed_command → {payload['skill_module']} "
                         f"(conf={confidence:.2f})")
        else:
            await self.event_bus.publish("escalate_to_graph", payload)
            logger.debug(f"[SkillRouter] escalate_to_graph (conf={confidence:.2f} < "
                         f"{threshold})")


# ═══════════════════════════════════════════════════════════════════════════════
# DeepPipeline — orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class DeepPipeline:
    """
    Orchestrates the three-stage pipeline:
        IntentClassifier → MoodDetector → SkillRouter

    On startup subscribes to "user_command" events on the EventBus.
    """

    def __init__(
        self,
        event_bus: EventBus,
        pattern_memory,
        redis_state=None,
    ) -> None:
        self.event_bus = event_bus
        self.pattern_memory = pattern_memory
        self.redis_state = redis_state
        self.settings = Settings()

        self.intent_classifier = IntentClassifier(self.settings)
        self.mood_detector = MoodDetector(event_bus)
        self.skill_router = SkillRouter(event_bus, self.settings)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Load/train intent model and subscribe to EventBus."""
        await self.intent_classifier.load_or_train()
        self.event_bus.subscribe("user_command", self._on_user_command)
        logger.info("[DeepPipeline] Started — listening for user_command events")

    async def stop(self) -> None:
        """Unsubscribe from events."""
        # EventBus currently has no unsubscribe for wildcard-style,
        # but we can note the shutdown.
        logger.info("[DeepPipeline] Stopped")

    def status(self) -> Dict[str, Any]:
        """Return operational status."""
        return {
            "sklearn_available": SKLEARN_AVAILABLE,
            "librosa_available": LIBROSA_AVAILABLE,
            "intent_model_loaded": self.intent_classifier._pipeline is not None,
        }

    # ── EventBus handler ──────────────────────────────────────────────────

    async def _on_user_command(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Called for every 'user_command' event from the bus."""
        text = payload.get("text", "")
        source = payload.get("source", "microphone")
        await self.process(text, source=source)

    # ── Main entry point ──────────────────────────────────────────────────

    async def process(
        self,
        command_text: str,
        audio_array=None,
        source: str = "microphone",
    ) -> PipelineResult:
        """
        Run the full pipeline synchronously (target < 200 ms).

        Args:
            command_text: Transcribed or typed user input.
            audio_array: Optional numpy audio array for mood detection.
            source: Where the command came from (e.g. "microphone", "chat", "api").

        Returns:
            PipelineResult with intent, confidence, mood, routed_to,
            and execution duration.
        """
        t0 = time.perf_counter()

        # Stage 1 — Intent Classification
        intent, confidence = await self.intent_classifier.classify(command_text)

        # Stage 2 — Mood Detection
        if audio_array is not None:
            mood, mood_features = self.mood_detector.classify_audio(audio_array)
        else:
            mood, mood_features = self.mood_detector.classify_text(command_text)

        # Publish mood update so PatternMemory can pick it up
        if self.event_bus:
            try:
                await self.event_bus.publish("mood_update", {
                    "mood": mood,
                    **mood_features,
                })
            except Exception as e:
                logger.warning(f"[DeepPipeline] mood_update publish error: {e}")

        # Sync mood to Redis shared state (v2)
        if self.redis_state:
            try:
                await self.redis_state.set_global(
                    "mood",
                    {"mood": mood, "timestamp": datetime.now().isoformat()},
                    broadcast=True,
                )
            except Exception as e:
                logger.debug(f"[DeepPipeline] Redis mood sync error: {e}")

        # Stage 3 — Skill Routing
        routed_payload = self.skill_router.attach_context(
            intent=intent,
            confidence=confidence,
            mood=mood,
            command=command_text,
        )
        await self.skill_router.publish_decision(routed_payload)

        duration_ms = (time.perf_counter() - t0) * 1000

        # Log interaction (fire-and-forget; don't block response)
        asyncio.create_task(
            self.pattern_memory.log_interaction(
                intent=intent,
                command=command_text,
                response="",  # will be filled later by graph / skill result
                mood=mood,
                quality_score=confidence,
                source=source,
            )
        )

        result = PipelineResult(
            intent=intent,
            confidence=round(confidence, 4),
            mood=mood,
            routed_to=routed_payload.get("skill_module", "unknown"),
            duration_ms=round(duration_ms, 2),
        )

        logger.info(
            f"[DeepPipeline] {command_text[:40]!r} → intent={intent} "
            f"(conf={confidence:.2f}), mood={mood}, routed_to={result.routed_to}, "
            f"took={duration_ms:.1f}ms"
        )
        return result
