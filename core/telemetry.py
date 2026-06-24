"""Telemetry — DEEP's observability layer for its model + orchestration tiers.

Records every LLM call (which provider/model actually served it, latency,
success, fallthroughs) and every tool invocation (name, duration, ok/error)
to a small SQLite store, and exposes an aggregated summary. This turns DEEP's
model-routing and tool-calling from a black box into something inspectable —
the data already flows through RoutingLLM/DeepToolRegistry, we just keep it.

Writes are cheap and best-effort: a failure to record never breaks a request.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "telemetry.db"
_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None

# Approximate USD per 1K tokens (input, output), keyed by provider. These are
# rough published rates for FinOps *estimates* — token counts themselves are
# also estimated (~4 chars/token) since the streaming path exposes no usage
# object. Treat the cost column as an order-of-magnitude guide, not billing.
_PRICING = {
    "groq":   (0.00059, 0.00079),   # llama-3.3-70b ballpark
    "gemini": (0.00035, 0.00105),   # flash-ish
    "claude": (0.003,   0.015),     # sonnet ballpark
    "openai": (0.0025,  0.01),
    "ollama": (0.0,     0.0),       # local = free
}


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token) for cost approximation."""
    return max(0, len(text or "") // 4)


def _cost(provider: str, tokens_in: int, tokens_out: int) -> float:
    pin, pout = _PRICING.get(provider, (0.0, 0.0))
    return round((tokens_in / 1000.0) * pin + (tokens_out / 1000.0) * pout, 6)


def _db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute(
            "CREATE TABLE IF NOT EXISTS llm_calls ("
            "ts REAL, provider TEXT, model TEXT, latency_ms REAL, ok INTEGER, "
            "fallthroughs INTEGER, note TEXT, tokens_in INTEGER DEFAULT 0, "
            "tokens_out INTEGER DEFAULT 0, cost REAL DEFAULT 0)"
        )
        _conn.execute(
            "CREATE TABLE IF NOT EXISTS tool_calls ("
            "ts REAL, name TEXT, duration_ms REAL, ok INTEGER, error TEXT)"
        )
        # Migrate older DBs that predate the token/cost columns.
        for col, decl in (("tokens_in", "INTEGER DEFAULT 0"),
                          ("tokens_out", "INTEGER DEFAULT 0"),
                          ("cost", "REAL DEFAULT 0")):
            try:
                _conn.execute(f"ALTER TABLE llm_calls ADD COLUMN {col} {decl}")
            except Exception:
                pass  # column already exists
        _conn.commit()
    return _conn


def record_llm(provider: str, model: str, latency_ms: Optional[float] = None,
               ok: bool = True, fallthroughs: int = 0, note: str = "",
               tokens_in: int = 0, tokens_out: int = 0) -> None:
    try:
        cost = _cost(provider, tokens_in, tokens_out)
        with _lock:
            _db().execute(
                "INSERT INTO llm_calls VALUES (?,?,?,?,?,?,?,?,?,?)",
                (time.time(), provider, model, latency_ms, int(ok), fallthroughs,
                 note, tokens_in, tokens_out, cost),
            )
            _db().commit()
    except Exception:
        pass  # observability must never break the request it observes


def record_tool(name: str, duration_ms: float, ok: bool = True, error: str = "") -> None:
    try:
        with _lock:
            _db().execute(
                "INSERT INTO tool_calls VALUES (?,?,?,?,?)",
                (time.time(), name, duration_ms, int(ok), error[:300]),
            )
            _db().commit()
    except Exception:
        pass


def _pct(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    i = min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1))))
    return round(s[i], 1)


def summary(hours: int = 24) -> Dict[str, Any]:
    """Aggregated view of the model + tool layers over the last `hours`."""
    cutoff = time.time() - hours * 3600
    try:
        with _lock:
            db = _db()
            llm = db.execute(
                "SELECT provider, model, latency_ms, ok, fallthroughs, tokens_in, tokens_out, cost "
                "FROM llm_calls WHERE ts >= ?",
                (cutoff,),
            ).fetchall()
            tools = db.execute(
                "SELECT name, duration_ms, ok FROM tool_calls WHERE ts >= ?",
                (cutoff,),
            ).fetchall()
    except Exception as e:
        return {"error": str(e), "llm": {}, "tools": {}}

    # ── LLM layer ────────────────────────────────────────────────────────────
    providers: Dict[str, Dict[str, Any]] = {}
    latencies: List[float] = []
    llm_ok = 0
    total_fallthroughs = 0
    total_tokens = 0
    total_cost = 0.0
    for provider, model, latency, ok, ft, tin, tout, cost in llm:
        key = f"{provider}:{model}" if model else provider
        p = providers.setdefault(key, {"calls": 0, "ok": 0, "lat": [], "tokens": 0, "cost": 0.0})
        p["calls"] += 1
        p["ok"] += int(ok or 0)
        p["tokens"] += int((tin or 0) + (tout or 0))
        p["cost"] += float(cost or 0.0)
        if latency is not None:
            p["lat"].append(latency); latencies.append(latency)
        llm_ok += int(ok or 0)
        total_fallthroughs += int(ft or 0)
        total_tokens += int((tin or 0) + (tout or 0))
        total_cost += float(cost or 0.0)
    provider_mix = [
        {"provider": k, "calls": v["calls"], "ok": v["ok"],
         "p50_ms": _pct(v["lat"], 50), "p95_ms": _pct(v["lat"], 95),
         "tokens": v["tokens"], "cost": round(v["cost"], 4)}
        for k, v in sorted(providers.items(), key=lambda kv: -kv[1]["calls"])
    ]

    # ── Tool layer ───────────────────────────────────────────────────────────
    tool_stats: Dict[str, Dict[str, Any]] = {}
    for name, dur, ok in tools:
        t = tool_stats.setdefault(name, {"calls": 0, "errors": 0, "dur": []})
        t["calls"] += 1
        if not ok:
            t["errors"] += 1
        if dur is not None:
            t["dur"].append(dur)
    tool_rows = [
        {"name": k, "calls": v["calls"], "errors": v["errors"],
         "p50_ms": _pct(v["dur"], 50), "p95_ms": _pct(v["dur"], 95)}
        for k, v in sorted(tool_stats.items(), key=lambda kv: -kv[1]["calls"])
    ]

    return {
        "window_hours": hours,
        "llm": {
            "total_calls": len(llm),
            "ok": llm_ok,
            "fallthroughs": total_fallthroughs,
            "p50_ms": _pct(latencies, 50),
            "p95_ms": _pct(latencies, 95),
            "est_tokens": total_tokens,
            "est_cost_usd": round(total_cost, 4),
            "providers": provider_mix,
        },
        "tools": {
            "total_calls": len(tools),
            "errors": sum(t["errors"] for t in tool_stats.values()),
            "by_tool": tool_rows,
        },
    }
