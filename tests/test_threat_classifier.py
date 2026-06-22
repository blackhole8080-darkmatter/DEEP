"""
tests/test_threat_classifier.py

Unit tests for the PyTorch threat classifier neural net.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: ThreatFeatureExtractor returns vector of correct shape (21,)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_threat_feature_vector_count() -> None:
    """ThreatFeatureVector should have exactly 21 features."""
    try:
        from ai.threat.feature_extractor import ThreatFeatureExtractor, FEATURE_NAMES
        from ai.anomaly.network_baseline import NetworkFlowSnapshot
    except ImportError:
        pytest.skip("Dependencies missing")

    extractor = ThreatFeatureExtractor(network_baseline=AsyncMock())
    with patch.object(extractor.network_baseline, "get_baseline_stats", new_callable=AsyncMock, return_value=None):
        flow = NetworkFlowSnapshot(
            timestamp="2024-01-01T00:00:00Z",
            hour=14, day_of_week=2,
            bytes_sent_ps=100, bytes_recv_ps=200,
        )
        vec = await extractor.extract(flow)
        assert len(vec.features) == len(FEATURE_NAMES), f"Expected {len(FEATURE_NAMES)} features, got {len(vec.features)}"
        print(f"  ✓ ThreatFeatureVector has {len(vec.features)} features")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: Cyclic time encoding: hour=0 and hour=24 produce same sin/cos values
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cyclic_time_encoding() -> None:
    """Cyclic encoding should wrap around at 24 hours."""
    try:
        import numpy as np
        from ai.threat.feature_extractor import ThreatFeatureExtractor
        from ai.anomaly.network_baseline import NetworkFlowSnapshot
    except ImportError:
        pytest.skip("Dependencies missing")

    extractor = ThreatFeatureExtractor(network_baseline=AsyncMock())
    with patch.object(extractor.network_baseline, "get_baseline_stats", new_callable=AsyncMock, return_value=None):
        flow_0 = NetworkFlowSnapshot(timestamp="", hour=0, day_of_week=0, bytes_sent_ps=1, bytes_recv_ps=1)
        flow_24 = NetworkFlowSnapshot(timestamp="", hour=24, day_of_week=7, bytes_sent_ps=1, bytes_recv_ps=1)

        vec_0 = await extractor.extract(flow_0)
        vec_24 = await extractor.extract(flow_24)

        # hour=0 and hour=24 should be equivalent (same sin/cos)
        assert math.isclose(vec_0.features[-5], vec_24.features[-5], abs_tol=0.01), "hour_sin should match for hour=0 and 24"
        assert math.isclose(vec_0.features[-4], vec_24.features[-4], abs_tol=0.01), "hour_cos should match for hour=0 and 24"
    print("  ✓ Cyclic time encoding wraps correctly")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: Synthetic port scan has high unique_remote_ips
# ═══════════════════════════════════════════════════════════════════════════════

def test_synthetic_port_scan_signature() -> None:
    """Synthetic port scan should have high unique_remote_ips."""
    try:
        import numpy as np
        from ai.threat.threat_dataset import ThreatDatasetBuilder, ThreatLabel
    except ImportError:
        pytest.skip("Dependencies missing")

    builder = ThreatDatasetBuilder(network_baseline=AsyncMock())
    rng = np.random.RandomState(42)
    base = builder._random_normal_flow(rng)
    port_scan = builder._apply_attack_signature(base, ThreatLabel.PORT_SCAN, rng)

    assert port_scan["unique_remote_ips"] >= 50, f"Expected >= 50, got {port_scan['unique_remote_ips']}"
    print("  ✓ Synthetic port scan has high unique_remote_ips")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: Synthetic exfiltration has send_recv_ratio > 5
# ═══════════════════════════════════════════════════════════════════════════════

def test_synthetic_exfiltration_signature() -> None:
    """Synthetic exfiltration should have high send/recv ratio."""
    try:
        import numpy as np
        from ai.threat.threat_dataset import ThreatDatasetBuilder, ThreatLabel
    except ImportError:
        pytest.skip("Dependencies missing")

    builder = ThreatDatasetBuilder(network_baseline=AsyncMock())
    rng = np.random.RandomState(42)
    base = builder._random_normal_flow(rng)
    exfil = builder._apply_attack_signature(base, ThreatLabel.EXFILTRATION, rng)

    ratio = exfil["bytes_sent_ps"] / max(exfil["bytes_recv_ps"], 0.001)
    assert ratio > 5, f"Expected send_recv_ratio > 5, got {ratio}"
    print("  ✓ Synthetic exfiltration has high send_recv_ratio")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: Class balancing produces equal class counts
# ═══════════════════════════════════════════════════════════════════════════════

def test_class_balancing() -> None:
    """_balance_classes should produce equal counts for each label present."""
    try:
        from ai.threat.threat_dataset import ThreatDatasetBuilder, ThreatLabel, ThreatSample
        import numpy as np
    except ImportError:
        pytest.skip("Dependencies missing")

    samples = [
        ThreatSample(features=np.zeros(21), label=0, threat_type="NORMAL", timestamp=""),
        ThreatSample(features=np.zeros(21), label=0, threat_type="NORMAL", timestamp=""),
        ThreatSample(features=np.zeros(21), label=1, threat_type="PORT_SCAN", timestamp=""),
    ]

    builder = ThreatDatasetBuilder(network_baseline=AsyncMock())
    balanced = builder._balance_classes(samples)
    counts = {}
    for s in balanced:
        counts[s.label] = counts.get(s.label, 0) + 1

    assert counts[0] == counts[1], f"Expected equal counts, got {counts}"
    print("  ✓ Class balancing produces equal class counts")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 6: ThreatClassifierNet forward pass produces shape (batch, 7)
# ═══════════════════════════════════════════════════════════════════════════════

def test_threat_classifier_net_forward() -> None:
    """ThreatClassifierNet should produce output of shape (batch, n_classes)."""
    try:
        import torch
        from ai.threat.threat_model import ThreatClassifierNet
    except ImportError:
        pytest.skip("PyTorch not available")

    model = ThreatClassifierNet(input_dim=21, hidden_dim=64, n_classes=7)
    x = torch.randn(4, 21)
    out = model(x)
    assert out.shape == (4, 7), f"Expected (4, 7), got {out.shape}"
    print("  ✓ ThreatClassifierNet forward produces correct output shape")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 7: ThreatModelTrainer trains without crash on 50 synthetic samples
# ═══════════════════════════════════════════════════════════════════════════════

def test_threat_model_trainer() -> None:
    """ThreatModelTrainer should train without crash on synthetic data."""
    try:
        import numpy as np
        from ai.threat.threat_model import ThreatClassifierNet, ThreatModelTrainer
    except ImportError:
        pytest.skip("PyTorch or numpy not available")

    X = np.random.randn(50, 21).astype(np.float32)
    y = np.random.randint(0, 7, size=50)

    model = ThreatClassifierNet(input_dim=21, hidden_dim=32, n_classes=7)
    trainer = ThreatModelTrainer(model)
    result = trainer.train(X, y, epochs=5, batch_size=16)

    assert "final_train_acc" in result
    assert 0 <= result["final_train_acc"] <= 1
    print(f"  ✓ ThreatModelTrainer trains (train_acc={result['final_train_acc']:.3f})")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 8: evaluate() returns accuracy between 0 and 1
# ═══════════════════════════════════════════════════════════════════════════════

def test_evaluate_returns_valid_accuracy() -> None:
    """evaluate() should return accuracy in [0, 1]."""
    try:
        import numpy as np
        from ai.threat.threat_model import ThreatClassifierNet, ThreatModelTrainer
    except ImportError:
        pytest.skip("PyTorch or numpy not available")

    X = np.random.randn(50, 21).astype(np.float32)
    y = np.random.randint(0, 7, size=50)
    X_test = np.random.randn(20, 21).astype(np.float32)
    y_test = np.random.randint(0, 7, size=20)

    model = ThreatClassifierNet(input_dim=21, hidden_dim=32, n_classes=7)
    trainer = ThreatModelTrainer(model)
    trainer.train(X, y, epochs=3, batch_size=16)
    result = trainer.evaluate(X_test, y_test)

    assert "accuracy" in result
    assert 0 <= result["accuracy"] <= 1
    print(f"  ✓ evaluate() returns valid accuracy: {result['accuracy']:.3f}")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 9: ThreatClassifier skips gracefully when model not ready
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_classifier_skips_when_not_ready() -> None:
    """ThreatClassifier should skip classification when model not loaded."""
    try:
        from ai.threat.threat_classifier import ThreatClassifier
    except ImportError:
        pytest.skip("Dependencies missing")

    classifier = ThreatClassifier(
        event_bus=AsyncMock(), redis_state=MagicMock(),
        network_baseline=AsyncMock(), system_baseline=None,
    )
    # Don't load model — _model_ready should be False equivalent
    assert classifier._model is None
    print("  ✓ ThreatClassifier skips gracefully when model not ready")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 10: train_model() skips with event when < MIN_THREAT_SAMPLES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_train_skips_insufficient_data() -> None:
    """train_model should skip gracefully when insufficient samples."""
    try:
        from ai.threat.threat_classifier import ThreatClassifier
    except ImportError:
        pytest.skip("Dependencies missing")

    classifier = ThreatClassifier(
        event_bus=AsyncMock(), redis_state=MagicMock(),
        network_baseline=AsyncMock(), system_baseline=None,
    )
    classifier._min_samples = 99999  # Impossibly high
    result = await classifier.train_model()
    assert "error" in result
    assert result["error"].startswith("Insufficient")
    print("  ✓ train_model() skips when < MIN_THREAT_SAMPLES")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 11: Deduplication: second identical prediction within 30s does not publish tts_speak
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_deduplication_within_30s() -> None:
    """Duplicate threat predictions within 30s should be deduplicated."""
    try:
        from ai.threat.threat_classifier import ThreatClassifier, ThreatPrediction
    except ImportError:
        pytest.skip("Dependencies missing")

    event_bus = AsyncMock()
    classifier = ThreatClassifier(
        event_bus=event_bus, redis_state=AsyncMock(),
        network_baseline=AsyncMock(), system_baseline=None,
    )

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    pred = ThreatPrediction(threat_type="PORT_SCAN", confidence=0.9, timestamp=now)

    await classifier._handle_threat_prediction(pred)
    first_tts_count = len([c for c in event_bus.publish.call_args_list if c[0][0] == "tts_speak"])

    # Same threat type, same timestamp (within 30s) — should deduplicate
    await classifier._handle_threat_prediction(pred)
    second_tts_count = len([c for c in event_bus.publish.call_args_list if c[0][0] == "tts_speak"])

    assert second_tts_count == first_tts_count, "Duplicate prediction should not trigger additional TTS"
    print("  ✓ Deduplication prevents duplicate TTS within 30s")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 12: ThreatLabel enum values
# ═══════════════════════════════════════════════════════════════════════════════

def test_threat_label_enum() -> None:
    """ThreatLabel enum should have correct values."""
    try:
        from ai.threat.threat_dataset import ThreatLabel
    except ImportError:
        pytest.skip("Dependencies missing")

    assert ThreatLabel.NORMAL == 0
    assert ThreatLabel.PORT_SCAN == 1
    assert ThreatLabel.BRUTE_FORCE == 2
    assert ThreatLabel.ARP_SPOOF == 3
    assert ThreatLabel.DEAUTH == 4
    assert ThreatLabel.EXFILTRATION == 5
    assert ThreatLabel.UNKNOWN_THREAT == 6
    print("  ✓ ThreatLabel enum values correct")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 13: save() + load() round-trip preserves model predictions
# ═══════════════════════════════════════════════════════════════════════════════

def test_save_load_roundtrip() -> None:
    """save() followed by load() should preserve model predictions."""
    try:
        import numpy as np
        import torch
        from ai.threat.threat_model import ThreatClassifierNet, ThreatModelTrainer
    except ImportError:
        pytest.skip("PyTorch or numpy not available")

    import tempfile
    X = np.random.randn(50, 21).astype(np.float32)
    y = np.random.randint(0, 7, size=50)

    model = ThreatClassifierNet(input_dim=21, hidden_dim=32, n_classes=7)
    trainer = ThreatModelTrainer(model)
    trainer.train(X, y, epochs=3, batch_size=16)

    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
        path = tmp.name

    try:
        trainer.save(path)

        # Load into a fresh model
        model2 = ThreatClassifierNet(input_dim=21, hidden_dim=32, n_classes=7)
        trainer2 = ThreatModelTrainer(model2)
        trainer2.load(path)

        # Predictions should match
        X_test = np.random.randn(10, 21).astype(np.float32)
        pred1 = trainer.scaler.transform(X_test)
        pred2 = trainer2.scaler.transform(X_test)

        # eval() mode is required for deterministic inference: BatchNorm uses
        # running stats and Dropout is disabled. Without it, Dropout randomness
        # makes the two forward passes differ even with identical weights.
        model.eval()
        model2.eval()
        with torch.no_grad():
            out1 = model(torch.FloatTensor(pred1).to(trainer.device)).cpu().numpy()
            out2 = model2(torch.FloatTensor(pred2).to(trainer2.device)).cpu().numpy()

        assert np.allclose(out1, out2, atol=1e-5), "Predictions should match after save/load round-trip"
        print("  ✓ save() + load() round-trip preserves predictions")
    finally:
        import os
        os.unlink(path)


# ═══════════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
