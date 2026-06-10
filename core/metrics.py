"""In-process observability metrics for DEEP.

Lightweight, dependency-free counters for the chat pipeline so the fallback
chain and provider performance can be tuned. Single asyncio process, so a plain
dict is sufficient; a lock guards the rare cross-thread access (executors).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any, Dict


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._started = time.time()
        self.chat_total = 0
        self.chat_failed = 0
        self.tokens_total = 0
        # Per-provider rollups: {provider: {count, tokens, latency_ms_sum, errors, last_latency_ms}}
        self._providers: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"count": 0, "tokens": 0, "latency_ms_sum": 0.0, "errors": 0, "last_latency_ms": 0.0}
        )
        self.rate_limited = 0
        self.unauthorized = 0

    def record_chat(self, model: str, tokens: int, latency_ms: float, ok: bool = True) -> None:
        with self._lock:
            self.chat_total += 1
            if not ok:
                self.chat_failed += 1
            self.tokens_total += max(0, int(tokens))
            p = self._providers[model or "unknown"]
            p["count"] += 1
            p["tokens"] += max(0, int(tokens))
            p["latency_ms_sum"] += max(0.0, float(latency_ms))
            p["last_latency_ms"] = float(latency_ms)

    def record_provider_error(self, provider: str) -> None:
        with self._lock:
            self._providers[provider or "unknown"]["errors"] += 1

    def record_rate_limited(self) -> None:
        with self._lock:
            self.rate_limited += 1

    def record_unauthorized(self) -> None:
        with self._lock:
            self.unauthorized += 1

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            providers = {}
            for name, p in self._providers.items():
                count = p["count"] or 1
                providers[name] = {
                    "count": int(p["count"]),
                    "tokens": int(p["tokens"]),
                    "errors": int(p["errors"]),
                    "avg_latency_ms": round(p["latency_ms_sum"] / count, 1),
                    "last_latency_ms": round(p["last_latency_ms"], 1),
                }
            return {
                "uptime_seconds": round(time.time() - self._started, 1),
                "chat_total": self.chat_total,
                "chat_failed": self.chat_failed,
                "tokens_total": self.tokens_total,
                "rate_limited": self.rate_limited,
                "unauthorized": self.unauthorized,
                "providers": providers,
            }


# Module-level singleton used across the server.
metrics = Metrics()
