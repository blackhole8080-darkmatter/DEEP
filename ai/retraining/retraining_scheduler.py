"""
ai/retraining/retraining_scheduler.py

Runs the intent classifier retraining pipeline automatically on a schedule.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from core.config import Settings
except ImportError:
    from config import Settings

logger = logging.getLogger(__name__)


class RetrainingScheduler:
    """Automatically retrains the intent classifier on a schedule or trigger."""

    def __init__(
        self,
        event_bus: Any,
        pattern_memory: Any,
        pipeline: Any,
        redis_state: Any,
    ) -> None:
        self.event_bus = event_bus
        self.pattern_memory = pattern_memory
        self.pipeline = pipeline
        self.redis_state = redis_state
        self.settings = Settings()

        self.interval_days = int(getattr(self.settings, "retrain_interval_days", 7))
        self.retrain_time = getattr(self.settings, "retrain_time", "03:00")
        self.sample_trigger = int(getattr(self.settings, "retrain_sample_trigger", 200))
        self.min_training_samples = int(getattr(self.settings, "min_training_samples", 50))
        self.retrain_log_dir = Path(getattr(self.settings, "retrain_log_dir", "logs/retraining"))

        self._started = False
        self._task: Optional[asyncio.Task] = None
        self._new_samples_since_retrain = 0
        self._total_retrains = 0
        self._last_result: Optional[dict] = None
        self._last_retrain: Optional[str] = None
        self._next_scheduled: Optional[str] = None

    async def start(self) -> None:
        """Start the scheduler: subscribe to events and launch scheduled task."""
        if self._started:
            return

        self._started = True
        self.retrain_log_dir.mkdir(parents=True, exist_ok=True)

        # Subscribe to manual trigger
        self.event_bus.subscribe("retrain_now", self._on_retrain_now)

        # Subscribe to user commands to count new samples
        self.event_bus.subscribe("user_command", self._on_user_command)

        # Launch scheduled retraining loop
        self._task = asyncio.create_task(self._scheduled_loop())
        logger.info("[RetrainingScheduler] Started")

    async def stop(self) -> None:
        """Stop the scheduler and clean up."""
        self._started = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        try:
            self.event_bus.unsubscribe("retrain_now", self._on_retrain_now)
        except Exception:
            pass
        try:
            self.event_bus.unsubscribe("user_command", self._on_user_command)
        except Exception:
            pass

        logger.info("[RetrainingScheduler] Stopped")

    async def _scheduled_loop(self) -> None:
        """Sleep until the next scheduled retrain time, then run."""
        while self._started:
            try:
                now = datetime.now(timezone.utc)
                target = self._parse_retrain_time(now)
                if target <= now:
                    target += timedelta(days=self.interval_days)

                self._next_scheduled = target.isoformat()
                sleep_seconds = (target - now).total_seconds()
                logger.debug(f"[RetrainingScheduler] Next retrain at {target.isoformat()}")
                await asyncio.wait_for(asyncio.sleep(sleep_seconds), timeout=sleep_seconds + 60)

                if self._started:
                    await self._run_retraining_cycle(trigger="scheduled")
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning(f"[RetrainingScheduler] Scheduled loop error: {exc}")
                await asyncio.sleep(3600)  # Retry in 1 hour on error

    def _parse_retrain_time(self, reference: datetime) -> datetime:
        """Parse RETRAIN_TIME (e.g. '03:00') into a datetime on the reference day."""
        try:
            hour, minute = map(int, self.retrain_time.split(":"))
        except ValueError:
            hour, minute = 3, 0
        return reference.replace(hour=hour, minute=minute, second=0, microsecond=0)

    async def _on_retrain_now(self, event_name: str, payload: dict) -> None:
        """Handle manual retrain trigger."""
        source = payload.get("source", "manual")
        logger.info(f"[RetrainingScheduler] Manual retrain triggered (source={source})")
        await self._run_retraining_cycle(trigger="manual")

    async def _on_user_command(self, event_name: str, payload: dict) -> None:
        """Count new commands since last retrain."""
        self._new_samples_since_retrain += 1
        if self._new_samples_since_retrain >= self.sample_trigger:
            logger.info(
                f"[RetrainingScheduler] Sample threshold reached "
                f"({self._new_samples_since_retrain}/{self.sample_trigger}) — triggering retrain"
            )
            await self._run_retraining_cycle(trigger="threshold")
            self._new_samples_since_retrain = 0

    async def _run_retraining_cycle(self, trigger: str = "scheduled") -> None:
        """Run one full retraining cycle."""
        if not self._started:
            return

        await self.event_bus.publish("retraining_started", {"trigger": trigger})
        logger.info(f"[RetrainingScheduler] Starting retraining cycle (trigger={trigger})")

        try:
            from ai.retraining.data_extractor import TrainingDataExtractor
            from ai.retraining.trainer import IntentRetrainer

            extractor = TrainingDataExtractor(self.pattern_memory)
            dataset = await extractor.extract()

            if dataset.total < self.min_training_samples:
                logger.info(
                    f"[RetrainingScheduler] Not enough samples yet "
                    f"({dataset.total}/{self.min_training_samples})"
                )
                await self.event_bus.publish("retraining_skipped", {
                    "reason": "insufficient_samples",
                    "have": dataset.total,
                    "need": self.min_training_samples,
                })
                return

            retrainer = IntentRetrainer(self.pipeline, self.event_bus)
            result = await retrainer.retrain(dataset)

            self._total_retrains += 1
            self._last_retrain = datetime.now(timezone.utc).isoformat()
            self._last_result = {
                "old_accuracy": result.old_accuracy,
                "new_accuracy": result.new_accuracy,
                "improvement": result.improvement,
                "deployed": result.deployed,
                "samples_used": result.samples_used,
            }

            if self.redis_state:
                try:
                    await self.redis_state.set_global("last_retrain_result", self._last_result)
                except Exception as exc:
                    logger.debug(f"Redis set_global error: {exc}")

            await self._save_retrain_log(result, dataset, trigger)

        except Exception as exc:
            logger.error(f"[RetrainingScheduler] Retraining cycle failed: {exc}")
            await self.event_bus.publish("retraining_failed", {"error": str(exc)})

    async def _save_retrain_log(self, result: Any, dataset: Any, trigger: str) -> None:
        """Persist retrain result to JSON log."""
        log_path = self.retrain_log_dir / f"retrain_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        content = {
            "result": {
                "success": result.success,
                "old_accuracy": result.old_accuracy,
                "new_accuracy": result.new_accuracy,
                "improvement": result.improvement,
                "samples_used": result.samples_used,
                "deployed": result.deployed,
                "model_path": result.model_path,
                "timestamp": result.timestamp,
            },
            "dataset_stats": {
                "total": dataset.total,
                "real_samples": dataset.real_samples,
                "seed_supplements": dataset.seed_supplements,
                "date_range": dataset.date_range,
                "by_intent": {k: len(v) for k, v in dataset.by_intent.items()},
            },
            "trigger": trigger,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "deep_version": "v3",
        }
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, default=str)

    async def trigger_manual(self) -> None:
        """Manual trigger for retraining."""
        await self.event_bus.publish("retrain_now", {"source": "manual"})

    def status(self) -> dict[str, Any]:
        """Return current scheduler status."""
        return {
            "last_retrain": self._last_retrain,
            "next_scheduled": self._next_scheduled,
            "new_samples_since_retrain": self._new_samples_since_retrain,
            "total_retrains": self._total_retrains,
            "last_accuracy": self._last_result.get("new_accuracy") if self._last_result else None,
            "last_improvement": self._last_result.get("improvement") if self._last_result else None,
        }
