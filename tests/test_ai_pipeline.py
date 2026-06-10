"""
tests/test_ai_pipeline.py

Validation suite for the AI Neural Network Layer.

Run:
    python tests/test_ai_pipeline.py
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# ── Ensure DEEP root is importable ──────────────────────────────────────
DEEP_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(DEEP_ROOT))

# ── Optional dependency checks ────────────────────────────────────────────

try:
    import sklearn
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("WARNING: scikit-learn not installed — intent classifier tests skipped")

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False
    print("WARNING: aiosqlite not installed — PatternMemory tests skipped")

# ── Imports ───────────────────────────────────────────────────────────────

from core.event_bus import EventBus
from ai.pipeline import (
    DeepPipeline,
    IntentClassifier,
    MoodDetector,
    SkillRouter,
    PipelineResult,
    SEED_DATA,
)
from ai.pattern_memory import PatternMemory


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

async def _make_bus() -> EventBus:
    bus = EventBus()
    await bus.start()
    return bus


def _make_mock_settings(**overrides) -> MagicMock:
    """Build a Settings mock with sensible defaults."""
    settings = MagicMock()
    settings.ollama_base_url = "http://localhost:11434"
    settings.ollama_model = "llama3.2"
    settings.temperature = 0.2
    settings.max_tokens = 512
    settings.offline_mode = True
    settings.openai_api_key = None
    settings.intent_model_path = overrides.get("intent_model_path", "data/intent_model.pkl")
    settings.intent_categories = overrides.get(
        "intent_categories",
        list(SEED_DATA.keys()),
    )
    settings.skill_routes = overrides.get("skill_routes", {
        "system_control": "skills.system_control",
        "information_query": "skills.information_query",
    })
    settings.pipeline_confidence_threshold = overrides.get(
        "pipeline_confidence_threshold", 0.65
    )
    return settings


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: IntentClassifier trains on seed data and classifies correctly
# ═══════════════════════════════════════════════════════════════════════════════

async def test_intent_classifier_trains_and_classifies():
    if not SKLEARN_AVAILABLE:
        print("  SKIP: scikit-learn unavailable")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "intent_model.pkl"
        settings = _make_mock_settings(intent_model_path=str(model_path))
        clf = IntentClassifier(settings)
        await clf.load_or_train()

        assert clf._pipeline is not None, "Model should be loaded or trained"

        intent, confidence = clf.classify("turn off the lights")
        assert intent == "system_control", (
            f"Expected 'system_control', got '{intent}' (confidence={confidence:.2f})"
        )
        assert confidence > 0.5, f"Confidence too low: {confidence}"
        assert model_path.exists(), "Model should be persisted to disk"

        # Verify reload works
        clf2 = IntentClassifier(settings)
        await clf2.load_or_train()
        assert clf2._pipeline is not None, "Reloaded model should not be None"

    print("  ✓ IntentClassifier trains on seed data and classifies correctly")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: MoodDetector text fallback returns a valid mood label
# ═══════════════════════════════════════════════════════════════════════════════

async def test_mood_detector_text_fallback():
    bus = await _make_bus()
    detector = MoodDetector(bus)

    # Positive text → calm
    mood, features = detector.classify_text("I feel great and happy today")
    assert mood in {"calm", "stressed", "focused", "neutral"}, f"Unexpected mood: {mood}"
    assert "positive_words" in features
    assert "negative_words" in features

    # Negative text → stressed
    mood2, _ = detector.classify_text("I am stressed and angry about this")
    assert mood2 in {"calm", "stressed", "focused", "neutral"}, f"Unexpected mood: {mood2}"

    # Question/help → focused
    mood3, _ = detector.classify_text("how do I fix this bug?")
    assert mood3 in {"calm", "stressed", "focused", "neutral"}, f"Unexpected mood: {mood3}"

    await bus.stop()
    print("  ✓ MoodDetector text fallback returns valid mood labels")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: pipeline.process() returns a PipelineResult with all fields populated
# ═══════════════════════════════════════════════════════════════════════════════

async def test_pipeline_process_returns_result():
    bus = await _make_bus()

    # PatternMemory needs aiosqlite — mock if unavailable
    if AIOSQLITE_AVAILABLE:
        db_path = Path(tempfile.mkdtemp()) / "test_pattern_memory.db"
        pattern_memory = PatternMemory(event_bus=bus, db_path=str(db_path))
        await pattern_memory.start()
    else:
        pattern_memory = MagicMock()

        async def _mock_log(**kwargs):
            pass

        async def _mock_ctx(n):
            return "(mock context)"

        async def _mock_pred(h, d):
            return None

        pattern_memory.log_interaction = _mock_log
        pattern_memory.get_recent_context = _mock_ctx
        pattern_memory.get_predicted_intent = _mock_pred

    pipeline = DeepPipeline(bus, pattern_memory)
    # Override settings to avoid config load issues in test env
    pipeline.settings = _make_mock_settings()
    pipeline.intent_classifier.settings = pipeline.settings
    pipeline.skill_router.settings = pipeline.settings

    # Subscribe to routed_command / escalate_to_graph so process() can fire
    routed_events: list = []
    escalated_events: list = []

    async def _on_routed(event_name: str, payload: dict):
        routed_events.append(payload)

    async def _on_escalated(event_name: str, payload: dict):
        escalated_events.append(payload)

    bus.subscribe("routed_command", _on_routed)
    bus.subscribe("escalate_to_graph", _on_escalated)

    # Train the classifier first so it produces real results
    if SKLEARN_AVAILABLE:
        await pipeline.intent_classifier.load_or_train()

    result = await pipeline.process("turn off the lights")

    assert isinstance(result, PipelineResult), f"Expected PipelineResult, got {type(result)}"
    assert result.intent != "", "Intent should not be empty"
    assert result.confidence > 0.0, "Confidence should be > 0"
    assert result.mood in {"calm", "stressed", "focused", "neutral", "energetic", "tired"}, (
        f"Unexpected mood: {result.mood}"
    )
    assert result.routed_to != "", "routed_to should not be empty"
    assert result.duration_ms >= 0.0, "duration_ms should be >= 0"

    if AIOSQLITE_AVAILABLE:
        await pattern_memory.stop()
    await bus.stop()
    print("  ✓ pipeline.process() returns a fully populated PipelineResult")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: Low-confidence result publishes "escalate_to_graph" not "routed_command"
# ═══════════════════════════════════════════════════════════════════════════════

async def test_low_confidence_escalates_to_graph():
    bus = await _make_bus()

    pattern_memory = MagicMock()

    async def _mock_log2(**kwargs):
        pass

    pattern_memory.log_interaction = _mock_log2

    pipeline = DeepPipeline(bus, pattern_memory)
    # Force a very high threshold so ANY classification will be "low confidence"
    pipeline.settings = _make_mock_settings(pipeline_confidence_threshold=0.99)
    pipeline.skill_router.settings = pipeline.settings

    escalated: list = []
    routed: list = []

    async def _on_esc(event_name: str, payload: dict):
        escalated.append(payload)

    async def _on_routed(event_name: str, payload: dict):
        routed.append(payload)

    bus.subscribe("escalate_to_graph", _on_esc)
    bus.subscribe("routed_command", _on_routed)

    # Train so we get a real (but low-confidence relative to 0.99) result
    if SKLEARN_AVAILABLE:
        await pipeline.intent_classifier.load_or_train()

    await pipeline.process("some completely unknown phrase that will not match anything")

    # Give the async publish a moment to fire
    await asyncio.sleep(0.05)

    assert len(escalated) >= 1, (
        f"Expected at least 1 escalate_to_graph event, got {len(escalated)}"
    )
    assert len(routed) == 0, (
        f"Expected 0 routed_command events, got {len(routed)}"
    )

    await bus.stop()
    print("  ✓ Low-confidence result publishes 'escalate_to_graph' not 'routed_command'")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: PatternMemory logs an interaction and retrieves it
# ═══════════════════════════════════════════════════════════════════════════════

async def test_pattern_memory_log_and_retrieve():
    if not AIOSQLITE_AVAILABLE:
        print("  SKIP: aiosqlite unavailable")
        return

    bus = await _make_bus()
    db_path = Path(tempfile.mkdtemp()) / "test_pm.db"
    pm = PatternMemory(event_bus=bus, db_path=str(db_path))
    await pm.start()

    # Log an interaction
    await pm.log_interaction(
        intent="system_control",
        command="turn off the lights",
        response="lights turned off",
        mood="calm",
        quality_score=0.85,
        source="microphone",
    )

    # Retrieve via get_recent_context
    ctx = await pm.get_recent_context(n=5)
    assert "system_control" in ctx, f"Context should contain the logged intent: {ctx}"
    assert "turn off the lights" in ctx, f"Context should contain the command: {ctx}"
    assert "lights turned off" in ctx, f"Context should contain the response: {ctx}"

    # Check status reflects the record
    status = pm.status()
    assert status["total_interactions"] >= 1, f"Expected >=1 interaction: {status}"

    await pm.stop()
    await bus.stop()
    print("  ✓ PatternMemory logs interaction and retrieves it via get_recent_context()")


# ═══════════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    print("Running AI Pipeline validation...\n")
    await test_intent_classifier_trains_and_classifies()
    await test_mood_detector_text_fallback()
    await test_pipeline_process_returns_result()
    await test_low_confidence_escalates_to_graph()
    await test_pattern_memory_log_and_retrieve()
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  All AI pipeline tests passed.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    asyncio.run(main())
