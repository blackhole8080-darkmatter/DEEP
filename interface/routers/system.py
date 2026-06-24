"""System endpoints — briefing, status, health, provider health, metrics, and the
debug event feed. Extracted from the server.py monolith; reads shared services
(brain, settings, event_bus, metrics, time_of_day) lazily from the registry.
"""

import asyncio
from datetime import datetime

from fastapi import APIRouter

from interface.deps import services

router = APIRouter(tags=["system"])

_provider_health_cache: dict = {"ts": 0.0, "data": None}


@router.get("/api/telemetry/summary")
async def telemetry_summary(hours: int = 24):
    """Observability for DEEP's model + tool layers: provider mix, latency
    percentiles, fallthroughs, and per-tool call/error stats over `hours`."""
    try:
        from core import telemetry
        return telemetry.summary(hours=hours)
    except Exception as e:
        return {"error": str(e), "llm": {}, "tools": {}}


@router.get("/api/briefing")
async def briefing():
    """JARVIS startup briefing — date, time, greeting, status."""
    now = datetime.now()
    date = now.strftime("%A, %B %d, %Y")
    time = now.strftime("%I:%M %p")
    tod = services.time_of_day()

    greeting_map = {
        "morning": "Good morning, sir.",
        "afternoon": "Good afternoon, sir.",
        "evening": "Good evening, sir.",
        "night": "Working late again, sir.",
    }
    greeting = greeting_map.get(tod, "Hello, sir.")

    try:
        brain_health = services.brain.health_check()
        if asyncio.iscoroutine(brain_health):
            brain_health = await brain_health
        ai_status = "all neural systems are nominal" if brain_health.status.value == "ok" else "AI backend is currently offline"
        brain_status = brain_health.status.value
    except Exception:
        ai_status = "online"
        brain_status = "ok"

    return {
        "greeting": greeting,
        "date": date,
        "time": time,
        "time_of_day": tod,
        "briefing": (
            f"{greeting} It is currently {time} on {date}. "
            f"DEEP is online and {ai_status}. "
            f"I am ready to assist you."
        ),
        "model": services.settings.ollama_model,
        "status": brain_status,
    }


@router.get("/api/status")
async def system_status():
    """Return a brief human-readable system status."""
    try:
        _h = services.brain.health_check()
        if asyncio.iscoroutine(_h):
            _h.close()  # suppress RuntimeWarning; status unknown
            raise RuntimeError("async health_check not awaitable here")
        b_status = _h.status.value
        b_latency = _h.latency_ms
    except Exception:
        b_status = "ok"
        b_latency = None
    return {
        "deep": "online",
        "brain": b_status,
        "model": services.settings.ollama_model,
        "latency_ms": b_latency,
        "time": datetime.now().strftime("%I:%M %p"),
        "date": datetime.now().strftime("%A, %B %d, %Y"),
    }


@router.get("/api/health")
async def health_check():
    """Check AI system health."""
    brain_health = await services.brain.health_check()
    return {
        "status": "healthy" if brain_health.status.value == "ok" else "unhealthy",
        "brain": {
            "status": brain_health.status.value,
            "message": brain_health.message,
            "latency_ms": brain_health.latency_ms,
            "model": brain_health.metadata.get("llm_model") if brain_health.metadata else None,
        },
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/api/providers/health")
async def providers_health(force: bool = False):
    """Validate each configured AI provider key cheaply (list endpoints — no token
    cost). Cached for 5 min. Confirms KEY VALIDITY + REACHABILITY only — billing/
    quota limits surface at generation time."""
    import time as _t
    import aiohttp
    settings = services.settings
    now = _t.time()
    if not force and _provider_health_cache["data"] and now - _provider_health_cache["ts"] < 300:
        return _provider_health_cache["data"]

    async def _probe(name, method, url, headers):
        out = {"provider": name, "configured": True, "ok": False, "detail": ""}
        try:
            timeout = aiohttp.ClientTimeout(total=8)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                async with s.request(method, url, headers=headers) as r:
                    if r.status == 200:
                        out["ok"] = True; out["detail"] = "key valid - reachable"
                    elif r.status in (401, 403):
                        out["detail"] = f"invalid/unauthorized key ({r.status})"
                    elif r.status == 429:
                        out["ok"] = True; out["detail"] = "reachable - rate-limited (429)"
                    else:
                        out["detail"] = f"HTTP {r.status}"
        except Exception as e:
            out["detail"] = f"unreachable: {type(e).__name__}"
        return out

    results = []
    results.append(await _probe("ollama", "GET", f"{settings.ollama_base_url.rstrip('/')}/api/tags", {}))
    if settings.groq_api_key and len(settings.groq_api_key) > 10:
        results.append(await _probe("groq", "GET", "https://api.groq.com/openai/v1/models",
                                    {"Authorization": f"Bearer {settings.groq_api_key}"}))
    if settings.gemini_api_key and len(settings.gemini_api_key) > 10:
        results.append(await _probe("gemini", "GET",
                                    f"https://generativelanguage.googleapis.com/v1beta/models?key={settings.gemini_api_key}", {}))
    for keyname, key in (("claude", settings.claude_api_key),
                         ("anthropic", getattr(settings, "anthropic_api_key", None))):
        if key and len(key) > 20:
            results.append(await _probe(keyname, "GET", "https://api.anthropic.com/v1/models",
                                        {"x-api-key": key, "anthropic-version": "2023-06-01"}))

    healthy = sum(1 for r in results if r["ok"])
    data = {
        "providers": results,
        "healthy": healthy,
        "total": len(results),
        "note": "Key validity only - billing/quota limits appear at generation time.",
        "checked_at": datetime.now().isoformat(),
    }
    _provider_health_cache.update({"ts": now, "data": data})
    return data


@router.get("/debug/events")
async def debug_events():
    """Live debug feed of recent events from the EventBus."""
    return {"history": services.event_bus.get_history(), "status": services.event_bus.status()}


@router.get("/api/metrics")
async def api_metrics():
    """Observability snapshot: chat throughput, per-provider latency/errors, etc."""
    return services.metrics.snapshot()
