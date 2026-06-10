"""
ai/threat/threat_classifier.py

Live inference component that runs the trained threat model in DEEP and triggers alerts.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from core.config import Settings
except ImportError:
    from config import Settings

from ai.threat.feature_extractor import ThreatFeatureExtractor, ThreatFeatureVector
from ai.threat.threat_dataset import ThreatDatasetBuilder, ThreatLabel
from ai.threat.threat_model import ThreatClassifierNet, ThreatModelTrainer

logger = logging.getLogger(__name__)


@dataclass
class ThreatPrediction:
    threat_type: str = ""
    confidence: float = 0.0
    all_probabilities: dict = field(default_factory=dict)
    feature_vector: list = field(default_factory=list)
    timestamp: str = ""
    acted_on: bool = False


class ThreatClassifier:
    """Runs inference and integrates with EventBus for real-time threat classification."""

    def __init__(
        self,
        event_bus: Any,
        redis_state: Any,
        network_baseline: Any,
        system_baseline: Optional[Any] = None,
    ) -> None:
        self.event_bus = event_bus
        self.redis_state = redis_state
        self.network_baseline = network_baseline
        self.system_baseline = system_baseline
        self.settings = Settings()

        self._model_path = getattr(self.settings, "threat_model_path", "ai/models/threat_classifier.pt")
        self._scaler_path = getattr(self.settings, "threat_scaler_path", "ai/models/threat_scaler.pkl")
        self._retrain_interval_days = int(getattr(self.settings, "threat_retrain_interval_days", 7))
        self._confidence_threshold = float(getattr(self.settings, "threat_confidence_threshold", 0.7))
        self._model_epochs = int(getattr(self.settings, "threat_model_epochs", 50))
        self._min_samples = int(getattr(self.settings, "min_threat_samples", 50))

        self._feature_extractor = ThreatFeatureExtractor(network_baseline)
        self._model: Optional[ThreatClassifierNet] = None
        self._trainer: Optional[ThreatModelTrainer] = None
        self._started = False
        self._retrain_task: Optional[asyncio.Task] = None
        self._training_check_task: Optional[asyncio.Task] = None
        self._recent_predictions: List[ThreatPrediction] = []
        self._predictions_today = 0
        self._threats_classified_today = 0
        self._last_prediction: Optional[str] = None

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._started:
            return
        self._started = True

        Path("logs/threat").mkdir(parents=True, exist_ok=True)

        await self._load_model_if_exists()

        # Subscribe to network flows for real-time classification
        self.event_bus.subscribe("network_flow_recorded", self._on_flow_recorded)
        # Subscribe to raw threat detections for labelled training samples
        self.event_bus.subscribe("threat_raw_detected", self._on_threat_raw)
        # Subscribe to anomaly events for immediate classification
        self.event_bus.subscribe("anomaly_detected", self._on_anomaly)
        # Subscribe to model trained events
        self.event_bus.subscribe("threat_model_trained", self._on_model_trained)

        # Start periodic retraining
        self._retrain_task = asyncio.create_task(self._training_check_loop())
        logger.info("[ThreatClassifier] Started")

    async def stop(self) -> None:
        self._started = False
        for task in (self._retrain_task, self._training_check_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        for event in ("network_flow_recorded", "threat_raw_detected", "anomaly_detected", "threat_model_trained"):
            try:
                self.event_bus.unsubscribe(event, getattr(self, f"_on_{event.replace('_detected', '').replace('_recorded', '').replace('_trained', '')}"))
            except Exception:
                pass
        logger.info("[ThreatClassifier] Stopped")

    # ── Model I/O ────────────────────────────────────────────────────────

    async def _load_model_if_exists(self) -> None:
        if not TORCH_AVAILABLE:
            logger.warning("[ThreatClassifier] PyTorch unavailable — model inference disabled")
            return
        if os.path.exists(self._model_path):
            try:
                self._model = ThreatClassifierNet()
                self._trainer = ThreatModelTrainer(self._model)
                self._trainer.load(self._model_path)
                logger.info(f"[ThreatClassifier] Loaded model from {self._model_path}")
            except Exception as exc:
                logger.warning(f"[ThreatClassifier] Failed to load model: {exc}")
        else:
            logger.info("[ThreatClassifier] No model yet — will train when enough data available")

    # ── Event handlers ───────────────────────────────────────────────────

    async def _on_flow_recorded(self, event_name: str, payload: dict) -> None:
        """Called for every network_flow_recorded event."""
        if not self._started or self._model is None or self._trainer is None:
            return
        try:
            await self._classify_flow_payload(payload)
        except Exception as exc:
            logger.debug(f"[ThreatClassifier] Flow classification error: {exc}")

    async def _on_threat_raw(self, event_name: str, payload: dict) -> None:
        """Called when threat_monitor detects a raw threat — use as labelled sample."""
        logger.info(f"[ThreatClassifier] Received raw threat: {payload.get('threat_type', 'unknown')}")
        # The dataset builder will pick this up from the audit log on next retrain

    async def _on_anomaly(self, event_name: str, payload: dict) -> None:
        """Anomalies trigger immediate classification of latest flow."""
        if not self._started or self._model is None:
            return
        # Anomaly already detected — classify immediately for threat type
        logger.debug("[ThreatClassifier] Anomaly detected — will classify next flow")

    async def _on_model_trained(self, event_name: str, payload: dict) -> None:
        """Reload model after training."""
        await self._load_model_if_exists()

    # ── Classification ───────────────────────────────────────────────────

    async def _classify_flow_payload(self, payload: dict) -> None:
        from ai.anomaly.network_baseline import NetworkFlowSnapshot
        flow_snap = NetworkFlowSnapshot(**{k: v for k, v in payload.items() if hasattr(NetworkFlowSnapshot, k)})

        sys_snap = None
        if self.system_baseline:
            sys_snap = await self._get_latest_system_snapshot()

        vec = await self._feature_extractor.extract(flow_snap, sys_snap)
        pred = self._classify(vec)

        self._predictions_today += 1
        self._last_prediction = pred.timestamp

        if pred.threat_type != "NORMAL" and pred.confidence >= self._confidence_threshold:
            self._threats_classified_today += 1
            await self._handle_threat_prediction(pred)

    def _classify(self, vec: ThreatFeatureVector) -> ThreatPrediction:
        if self._trainer is None or self._model is None or self._trainer.scaler is None:
            return ThreatPrediction(
                threat_type="unknown",
                confidence=0.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        X = self._trainer.scaler.transform(vec.features.reshape(1, -1))
        self._model.eval()
        with torch.no_grad():
            inputs = torch.FloatTensor(X).to(self._trainer.device)
            outputs = self._model(inputs)
            probs = torch.softmax(outputs, dim=1).cpu().numpy()[0]

        idx = int(np.argmax(probs))
        confidence = float(probs[idx])
        threat_type = ThreatLabel(idx).name
        all_probs = {ThreatLabel(i).name: float(p) for i, p in enumerate(probs)}

        return ThreatPrediction(
            threat_type=threat_type,
            confidence=confidence,
            all_probabilities=all_probs,
            feature_vector=vec.features.tolist(),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    async def _handle_threat_prediction(self, pred: ThreatPrediction) -> None:
        # Deduplication: skip if same threat type within 30s
        now = datetime.now(timezone.utc)
        for recent in self._recent_predictions[-10:]:
            try:
                recent_dt = datetime.fromisoformat(recent.timestamp.replace("Z", "+00:00"))
                if recent.threat_type == pred.threat_type and (now - recent_dt).total_seconds() < 30:
                    return  # deduplicate
            except Exception:
                pass

        self._recent_predictions.append(pred)
        if len(self._recent_predictions) > 100:
            self._recent_predictions.pop(0)

        await self.event_bus.publish("threat_classified", {
            "threat_type": pred.threat_type,
            "confidence": pred.confidence,
            "probabilities": pred.all_probabilities,
            "source": "neural_classifier",
            "timestamp": pred.timestamp,
        })

        await self.redis_state.set_global("latest_threat_classification", {
            "threat_type": pred.threat_type,
            "confidence": pred.confidence,
            "timestamp": pred.timestamp,
        })

        if pred.confidence >= 0.85:
            await self.event_bus.publish("tts_speak", {
                "text": f"Neural classifier: {pred.threat_type.replace('_', ' ')} detected with {pred.confidence*100:.0f} percent confidence.",
                "priority": "urgent",
            })

    async def _get_latest_system_snapshot(self) -> Optional[Any]:
        try:
            history = await self.system_baseline.get_snapshot_history(hours_back=1)
            return history[0] if history else None
        except Exception:
            return None

    # ── Training ─────────────────────────────────────────────────────────

    async def train_model(self) -> dict[str, Any]:
        """Train the threat classifier on accumulated data."""
        await self.event_bus.publish("threat_model_training_started", {})
        logger.info("[ThreatClassifier] Starting model training...")

        if not TORCH_AVAILABLE or not SKLEARN_AVAILABLE:
            return {"error": "PyTorch or sklearn unavailable"}

        builder = ThreatDatasetBuilder(self.network_baseline, str(self.settings.anomaly_db_path))
        dataset = await builder.build_dataset()

        if len(dataset.X) < self._min_samples:
            msg = f"Insufficient data: {len(dataset.X)} < {self._min_samples}"
            logger.info(f"[ThreatClassifier] {msg}")
            await self.event_bus.publish("threat_model_training_skipped", {
                "reason": "insufficient_data",
                "have": len(dataset.X),
                "need": self._min_samples,
            })
            return {"error": msg, "samples": len(dataset.X)}

        X_train, X_test, y_train, y_test = train_test_split(
            dataset.X, dataset.y, test_size=0.2, stratify=dataset.y, random_state=42
        )

        model = ThreatClassifierNet()
        trainer = ThreatModelTrainer(model)
        history = trainer.train(
            X_train, y_train,
            X_test=X_test, y_test=y_test,
            epochs=self._model_epochs, batch_size=32, learning_rate=0.001,
        )

        eval_results = trainer.evaluate(X_test, y_test)

        # Save model + scaler
        Path(self._model_path).parent.mkdir(parents=True, exist_ok=True)
        trainer.save(self._model_path, self._scaler_path)

        self._model = model
        self._trainer = trainer

        # Save training report
        report_path = Path("logs/threat") / f"train_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "eval": eval_results,
                "history": history,
                "dataset_stats": {
                    "n_normal": dataset.n_normal,
                    "n_real_threats": dataset.n_real_threats,
                    "n_synthetic": dataset.n_synthetic,
                    "class_distribution": dataset.class_distribution,
                },
            }, f, indent=2, default=str)

        await self.event_bus.publish("threat_model_trained", {
            "accuracy": eval_results.get("accuracy"),
            "report_path": str(report_path),
            "n_samples": len(dataset.X),
        })

        logger.info(
            f"[ThreatClassifier] Trained: accuracy={eval_results.get('accuracy', 'N/A'):.3f}, "
            f"samples={len(dataset.X)}"
        )
        return eval_results

    async def _training_check_loop(self) -> None:
        """Periodically retrain the model."""
        while self._started:
            try:
                await asyncio.sleep(self._retrain_interval_days * 86400)
                if self._started:
                    await self.train_model()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning(f"[ThreatClassifier] Training check error: {exc}")

    # ── Public API ─────────────────────────────────────────────────────────

    async def get_recent_predictions(self, n: int = 20) -> List[dict]:
        return [
            {
                "threat_type": p.threat_type,
                "confidence": p.confidence,
                "timestamp": p.timestamp,
            }
            for p in self._recent_predictions[-n:]
        ]

    def status(self) -> dict[str, Any]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return {
            "model_ready": self._model is not None and self._trainer is not None,
            "model_path": self._model_path,
            "scaler_path": self._scaler_path,
            "confidence_threshold": self._confidence_threshold,
            "predictions_today": self._predictions_today,
            "threats_classified_today": self._threats_classified_today,
            "last_prediction": self._last_prediction,
            "torch_available": TORCH_AVAILABLE,
            "sklearn_available": SKLEARN_AVAILABLE,
        }
