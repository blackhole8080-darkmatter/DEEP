"""
ai/retraining/trainer.py

Retrains the intent classifier on extracted real data and evaluates improvement.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import SGDClassifier
    from sklearn.metrics import classification_report
    from sklearn.model_selection import StratifiedShuffleSplit
    from sklearn.pipeline import Pipeline as SklearnPipeline
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

try:
    from core.config import Settings
except ImportError:
    from config import Settings

logger = logging.getLogger(__name__)


@dataclass
class RetrainingResult:
    success: bool = False
    old_accuracy: float = 0.0
    new_accuracy: float = 0.0
    improvement: float = 0.0
    samples_used: int = 0
    by_intent_accuracy: dict[str, float] = None  # type: ignore[assignment]
    model_path: str = ""
    timestamp: str = ""
    deployed: bool = False

    def __post_init__(self):
        if self.by_intent_accuracy is None:
            self.by_intent_accuracy = {}


class IntentRetrainer:
    """Retrains and hot-swaps the intent classifier."""

    def __init__(self, pipeline: Any, event_bus: Any) -> None:
        self.pipeline = pipeline
        self.event_bus = event_bus
        self.settings = Settings()
        self.model_path = getattr(self.settings, "intent_model_path", "data/intent_model.pkl")
        self.max_features = int(getattr(self.settings, "intent_max_features", 500))
        self.min_improvement = float(getattr(self.settings, "min_accuracy_improvement", 0.02))
        self.retrain_log_dir = Path(getattr(self.settings, "retrain_log_dir", "logs/retraining"))

    async def retrain(
        self,
        dataset: Any,
        deploy_if_better: bool = True,
    ) -> RetrainingResult:
        """Retrain classifier and optionally hot-swap if improved."""
        result = RetrainingResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        if not SKLEARN_AVAILABLE:
            logger.warning("[IntentRetrainer] scikit-learn unavailable — cannot retrain")
            return result

        samples = getattr(dataset, "samples", [])
        if not samples:
            logger.warning("[IntentRetrainer] Empty dataset — skipping retrain")
            return result

        X = [s.command for s in samples]
        y = [s.intent for s in samples]
        result.samples_used = len(samples)

        # Step 1 — Stratified split
        if len(set(y)) < 2:
            logger.warning("[IntentRetrainer] Only one intent class — cannot stratify")
            return result

        sss = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        train_idx, test_idx = next(sss.split(X, y))
        X_train = [X[i] for i in train_idx]
        y_train = [y[i] for i in train_idx]
        X_test = [X[i] for i in test_idx]
        y_test = [y[i] for i in test_idx]

        # Step 2 — Benchmark current model
        old_accuracy = await self._evaluate_current_model(X_test, y_test)
        result.old_accuracy = old_accuracy

        # Step 3 — Train new model
        new_model = SklearnPipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=self.max_features,
                sublinear_tf=True,
            )),
            ("clf", SGDClassifier(
                loss="modified_huber",
                alpha=0.001,
                max_iter=1000,
                class_weight="balanced",
                random_state=42,
            )),
        ])
        new_model.fit(X_train, y_train)

        # Step 4 — Evaluate new model
        new_accuracy = new_model.score(X_test, y_test)
        result.new_accuracy = new_accuracy

        y_pred = new_model.predict(X_test)
        report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
        result.by_intent_accuracy = {
            intent: round(report.get(intent, {}).get("f1-score", 0.0), 4)
            for intent in set(y_test)
        }

        # Save full report
        self.retrain_log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.retrain_log_dir / f"retrain_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": result.timestamp,
                "old_accuracy": old_accuracy,
                "new_accuracy": new_accuracy,
                "improvement": new_accuracy - old_accuracy,
                "samples_used": len(samples),
                "by_intent_accuracy": result.by_intent_accuracy,
                "classification_report": report,
            }, f, indent=2, default=str)

        # Step 5 — Deploy decision
        improvement = new_accuracy - old_accuracy
        result.improvement = round(improvement, 4)
        result.success = True

        if deploy_if_better and improvement >= self.min_improvement:
            await self._hot_swap_model(new_model)
            result.deployed = True
            result.model_path = str(self.model_path)
            logger.info(
                f"[IntentRetrainer] Model deployed. "
                f"Accuracy: {old_accuracy:.3f} → {new_accuracy:.3f} "
                f"(+{improvement:.3f})"
            )
            if self.event_bus:
                await self.event_bus.publish("intent_model_updated", {
                    "old_accuracy": old_accuracy,
                    "new_accuracy": new_accuracy,
                    "improvement": improvement,
                    "samples_used": len(samples),
                    "timestamp": result.timestamp,
                })
                await self.event_bus.publish("tts_speak", {
                    "text": f"Intent classifier updated. Accuracy improved by {improvement*100:.1f} percent.",
                    "priority": "normal",
                })
        elif improvement < 0:
            result.deployed = False
            logger.warning(
                f"[IntentRetrainer] New model worse than current — not deploying. "
                f"Delta: {improvement:.3f}"
            )
            if self.event_bus:
                await self.event_bus.publish("retrain_rejected", {
                    "reason": "accuracy_regression",
                    "old_accuracy": old_accuracy,
                    "new_accuracy": new_accuracy,
                })
        else:
            result.deployed = False
            logger.info(
                f"[IntentRetrainer] Improvement {improvement:.3f} below threshold "
                f"({self.min_improvement}) — keeping current model"
            )

        return result

    async def _evaluate_current_model(self, X_test: list, y_test: list) -> float:
        """Benchmark the current live model on test set."""
        correct = 0
        for text, true_intent in zip(X_test, y_test):
            try:
                # classify() is now async
                predicted, _ = await self.pipeline.intent_classifier.classify(text)
                if predicted == true_intent:
                    correct += 1
            except Exception as exc:
                logger.debug(f"Current model eval error: {exc}")
        return correct / len(y_test) if y_test else 0.0

    async def _hot_swap_model(self, new_model: Any) -> None:
        """Atomically replace persisted model and live pipeline reference."""
        if not JOBLIB_AVAILABLE:
            logger.error("[IntentRetrainer] joblib not available — cannot persist model")
            return

        temp_path = str(self.model_path) + ".new"
        joblib.dump(new_model, temp_path)
        os.replace(temp_path, self.model_path)

        # Thread-safe swap via the classifier's lock
        await self.pipeline.intent_classifier.hot_swap(new_model)

        logger.info(f"[IntentRetrainer] Model hot-swapped at {datetime.now(timezone.utc).isoformat()}")

    async def evaluate_only(self, dataset: Any) -> dict[str, Any]:
        """Run evaluation without training or deploying."""
        if not SKLEARN_AVAILABLE:
            return {"error": "scikit-learn unavailable"}

        samples = getattr(dataset, "samples", [])
        if not samples:
            return {"error": "empty dataset"}

        X = [s.command for s in samples]
        y = [s.intent for s in samples]

        sss = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        train_idx, test_idx = next(sss.split(X, y))
        X_test = [X[i] for i in test_idx]
        y_test = [y[i] for i in test_idx]

        old_accuracy = await self._evaluate_current_model(X_test, y_test)

        X_train = [X[i] for i in train_idx]
        y_train = [y[i] for i in train_idx]

        new_model = SklearnPipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=self.max_features, sublinear_tf=True)),
            ("clf", SGDClassifier(loss="modified_huber", alpha=0.001, max_iter=1000, class_weight="balanced", random_state=42)),
        ])
        new_model.fit(X_train, y_train)
        new_accuracy = new_model.score(X_test, y_test)

        return {
            "old_accuracy": round(old_accuracy, 4),
            "new_accuracy": round(new_accuracy, 4),
            "improvement": round(new_accuracy - old_accuracy, 4),
            "samples_used": len(samples),
        }
