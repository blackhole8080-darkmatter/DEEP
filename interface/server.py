"""
DEEP Interface Server - JARVIS-Style Personal AI
Minimal FastAPI backend for voice-first AI interface
"""

import json
import asyncio
import secrets
import sys
from contextlib import asynccontextmanager
# The mac_vendor_lookup library's sync lookup() leaks an un-awaited coroutine
# when used outside a main-thread event loop. Vendor enrichment degrades
# gracefully to the OUI fallback table, so silence this known-benign warning.
import warnings as _warnings
_warnings.filterwarnings("ignore", message=r".*AsyncMacLookup\.lookup.*")
from typing import Optional, Dict
from datetime import datetime
from pathlib import Path

# Force UTF-8 console output. On Windows the default console encoding is cp1252,
# which cannot encode emoji (🔮, ⚠️, ✓, …) used throughout DEEP' print/log
# statements — without this, the first emoji print crashes the whole server.
# Must run before any module that prints at import/init time.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import UploadFile, File
import time as _time
from collections import deque
import os

# Add parent to path for imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Anchor the working directory to the project root so the many relative paths
# (data/, .env, logs/, chroma, knowledge_graph/) resolve no matter where the
# process was launched from. This lets launchers/IDEs/preview tools start the
# server with any cwd (previously they had to cd into the DEEP folder first).
try:
    os.chdir(_PROJECT_ROOT)
except Exception:
    pass

from core.config import Settings
from core.metrics import metrics
from core.event_bus import EventBus
from core.infrastructure.async_brain import AsyncBrain
from core.multi_llm_router import OllamaClient, ProviderConfig, LLMProvider
from core import pending_actions
from core.tools.deep_registry import DeepToolRegistry
from core.ltm_memory import LongTermMemory
# core.voice_web / core.local_stt imports removed (VoiceWeb/LocalSTT stubbed above)
from core.security.network_monitor import NetworkMonitor
from core.alert_dispatcher import AlertDispatcher
from core.security.alert_correlator import AlertCorrelator
from core.security.security_timeline import SecurityTimeline
from core.predictive_engine import PredictiveEngine
from core.self_evaluation import SelfEvaluationEngine
from core.knowledge_graph import KnowledgeGraph
from core.plugin_manager import PluginManager
from ai.pattern_memory import PatternMemory
from ai.pipeline import DeepPipeline
from ai.graph_orchestrator import GraphOrchestrator
from ai.retraining import RetrainingScheduler
from ai.anomaly import SystemBaseline, NetworkBaseline, AnomalyDetector
from ai.threat import ThreatClassifier
from knowledge import (
    KnowledgeStore, KnowledgeIngester,
    BreakthroughDetector, BriefingEngine, ConceptLinker,
)
# ── Voice subsystem removed (voice/ was hard-deleted) ──────────────────────
# This file used to carry a _VoiceStub shim so ~12 orphaned instantiation sites
# kept "working" as async no-ops. Every one of those sites is gone now, and the
# stubs went with them — they were hiding /audio/* endpoints that returned
# un-awaited coroutines (HTTP 500) rather than admitting the feature was absent.
from network import (
    TailscaleManager, RemoteAccessManager,
    NetworkScanner, ThreatMonitor,
    EvilTwinDetector, PiholeClient,
    ProximityMonitor,
)
from interface.ws.manager import manager
from core.redis_state import RedisStateManager
from core.device_registry import DeviceRegistry
from core.audit_trail import AuditTrail
from core.session_manager import SessionManager
from core.network_topology_graph import get_network_graph
from core.network_graph_builder import NetworkGraphBuilder
from core.network_ai_analyst import NetworkAIAnalyst
# voice imports removed (ActionRegistry/VoiceSecurity/AlertManager/VoiceAssistant stubbed above)

@asynccontextmanager
async def lifespan(app: "FastAPI"):
    """Modern FastAPI lifespan (replaces the deprecated @app.on_event handlers).
    startup_event/shutdown_event are defined later in this module and resolved at
    call time — they run after the module is fully imported, so forward refs are safe."""
    await startup_event()
    try:
        yield
    finally:
        await shutdown_event()


app = FastAPI(title="DEEP", version="2.0", lifespan=lifespan)

# Central event bus — all inter-module communication routes through this
event_bus = EventBus()

# ── Immutable Audit Trail (v2) — instantiated first to capture everything ──
redis_state = RedisStateManager(event_bus=event_bus)  # needed by audit/session
audit = AuditTrail(event_bus=event_bus, redis_state=redis_state)
session_mgr = SessionManager(event_bus=event_bus, audit_trail=audit, redis_state=redis_state)

# Initialize AI Brain, Tools, Voice, Memory, Security, Research, Predictions, Self-Evaluation, Knowledge Graph, and Plugins
settings = Settings()

# ── Web server hardening (v3): CORS + loopback-aware auth + rate limiting ────
# Local browser (127.0.0.1) stays frictionless; remote (LAN/Tailscale) clients
# must present DEEP_API_KEY. UI bootstrap + PWA assets remain public so the
# login surface can load before a key is supplied.
_cors_origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_PUBLIC_PATHS = {"/", "/ai", "/manifest.webmanifest", "/sw.js", "/favicon.ico"}
_PUBLIC_PREFIXES = ("/static",)
_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", None}
_rate_buckets: Dict[str, deque] = {}


def _client_is_local(host: Optional[str]) -> bool:
    return host in _LOCAL_HOSTS


def _extract_deep_key(request: Request) -> Optional[str]:
    return (
        request.headers.get("x-deep-key")
        or request.query_params.get("key")
        or request.cookies.get("deep_key")
    )


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    client_host = request.client.host if request.client else None
    path = request.url.path

    # Sliding-window rate limit, per client IP. Loopback is trusted and exempt:
    # a single /ai load fans out to ~30-40 static assets in one burst, which
    # would otherwise rate-limit the app's own page loads/refreshes.
    if settings.rate_limit_per_min > 0 and not _client_is_local(client_host):
        now = _time.monotonic()
        bucket = _rate_buckets.setdefault(client_host or "?", deque())
        while bucket and now - bucket[0] > 60.0:
            bucket.popleft()
        if len(bucket) >= settings.rate_limit_per_min:
            metrics.record_rate_limited()
            return JSONResponse(
                status_code=429,
                content={"error": "rate_limited", "detail": "Too many requests; slow down."},
            )
        bucket.append(now)

    # Remote auth: loopback always trusted; remote needs a valid key.
    if settings.require_remote_auth and not _client_is_local(client_host):
        is_public = path in _PUBLIC_PATHS or any(path.startswith(p) for p in _PUBLIC_PREFIXES)
        if not is_public:
            key = _extract_deep_key(request)
            if not key or not secrets.compare_digest(key, settings.deep_api_key):
                metrics.record_unauthorized()
                return JSONResponse(
                    status_code=401,
                    content={"error": "unauthorized", "detail": "Valid DEEP key required for remote access."},
                )

    return await call_next(request)


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    """Return a clean JSON error instead of leaking stack traces to clients."""
    print(f"[DEEP] Unhandled error on {request.method} {request.url.path}: "
          f"{type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": "An internal error occurred."},
    )


deep_tools = DeepToolRegistry()
ltm = LongTermMemory()
from core.preference_learning import PreferenceLearner
pref_learner = PreferenceLearner(ltm)
netmon = NetworkMonitor(event_bus=event_bus)
predictive_engine = PredictiveEngine(event_bus=event_bus)
from core.proactive_core import ProactiveCore
# The polished proactive layer: rate-limited, quiet-hours-aware, fuses
# predictions + reminders + (later) goals/idle. Publishes `proactive_suggestion`
# on the bus, which the wildcard _ws_broadcast already forwards to the HUD.
# meta/memory are left None until those subsystems are actually populated.
proactive_core = ProactiveCore(event_bus=event_bus, predictive=predictive_engine)
self_eval = SelfEvaluationEngine(event_bus=event_bus)
knowledge_graph = KnowledgeGraph(event_bus=event_bus)
proactive_core.kg = knowledge_graph   # graph-derived inferences → proactive nudges
plugin_manager = PluginManager(event_bus=event_bus)

# ── AI Neural Network Layer ─────────────────────────────────────────────
pattern_memory = PatternMemory(event_bus=event_bus)
deep_pipeline = DeepPipeline(event_bus=event_bus, pattern_memory=pattern_memory, redis_state=redis_state)
retraining_scheduler = RetrainingScheduler(
    event_bus=event_bus,
    pattern_memory=pattern_memory,
    pipeline=deep_pipeline,
    redis_state=redis_state,
)
system_baseline = SystemBaseline(event_bus=event_bus, redis_state=redis_state)
network_baseline = NetworkBaseline(event_bus=event_bus, redis_state=redis_state)
anomaly_detector = AnomalyDetector(
    event_bus=event_bus,
    redis_state=redis_state,
    system_baseline=system_baseline,
    network_baseline=network_baseline,
)
threat_classifier = ThreatClassifier(
    event_bus=event_bus,
    redis_state=redis_state,
    network_baseline=network_baseline,
    system_baseline=system_baseline,
)
# Enriches anomaly_detected/threat_classified with MITRE ATT&CK + CVE context
# and republishes as `security_alert_correlated` (kept distinct from the
# existing device-level `security_alert` event) — see
# core/security/alert_correlator.py
alert_correlator = AlertCorrelator(event_bus=event_bus)
# Merges security_alert + security_alert_correlated into one severity-scored
# feed for the dashboard — see core/security/security_timeline.py
security_timeline = SecurityTimeline(event_bus=event_bus)
# Delivers the alerts that matter off the browser tab — desktop notification,
# optional webhook — severity-gated, deduplicated and rate-limited, because a
# console you have to be watching is a dashboard, not an alerting system.
# See core/alert_dispatcher.py
alert_dispatcher = AlertDispatcher(event_bus=event_bus)

# ── Knowledge Intelligence Layer ────────────────────────────────────────
knowledge_store = KnowledgeStore(event_bus=event_bus)
ingester = KnowledgeIngester(event_bus=event_bus, knowledge_store=knowledge_store)
breakthrough_detector = BreakthroughDetector(event_bus=event_bus, knowledge_store=knowledge_store)
briefing_engine = BriefingEngine(event_bus=event_bus, knowledge_store=knowledge_store)
concept_linker = ConceptLinker(event_bus=event_bus, knowledge_store=knowledge_store)


# ── Network Layer (v2) ──────────────────────────────────────────────────
tailscale = TailscaleManager(event_bus=event_bus)
remote_access = RemoteAccessManager(event_bus=event_bus, tailscale=tailscale)

# ── Network Scanning & Security (v2) ─────────────────────────────────────
scanner = NetworkScanner(event_bus=event_bus, redis_state=redis_state)
threat_monitor = ThreatMonitor(event_bus=event_bus, redis_state=redis_state)
evil_twin = EvilTwinDetector(event_bus=event_bus, redis_state=redis_state)
pihole = PiholeClient(event_bus=event_bus, redis_state=redis_state)

# ── Passive Proximity Monitor (v2) ─────────────────────────────────────────
proximity = ProximityMonitor(event_bus=event_bus, redis_state=redis_state)

# ── Unified Multi-Layer Network Graph (v3) ─────────────────────────────────
net_graph = get_network_graph()
net_graph_builder = NetworkGraphBuilder(event_bus=event_bus, graph=net_graph)

# ── Shared State Layer (v2) ───────────────────────────────────────────────
device_registry = DeviceRegistry(event_bus=event_bus, redis_state=redis_state)

# ── Graph Orchestrator (needs device_registry + knowledge_store) ──────────
graph_orchestrator = GraphOrchestrator(
    event_bus=event_bus, pattern_memory=pattern_memory,
    knowledge_store=knowledge_store,
    redis_state=redis_state,
    device_registry=device_registry,
)

# ── Voice hardware layer — REMOVED ──────────────────────────────────────
# The voice/ package was hard-deleted; what remained here were _VoiceStub
# instances (wake word, STT, TTS, spatial audio, Bluetooth ear) that no-op on
# every call. They are gone along with the /audio/* endpoints they served.
# Text-to-speech intent still flows over the `tts_speak` bus event, which the
# HUD can act on; nothing server-side synthesises audio any more.

async def startup_event():
    # Start the central event bus first
    await event_bus.start()

    # Surface the remote-access credential. When DEEP_API_KEY is unset, config
    # mints a random one and persists it to data/.deep_api_key — print it once
    # so remote access is actually usable without digging through the repo.
    if settings.require_remote_auth:
        if os.environ.get("DEEP_API_KEY"):
            print("[DEEP] Remote access: using DEEP_API_KEY from environment")
        else:
            print(f"[DEEP] Remote access key (auto-generated): {settings.deep_api_key}")
            print("[DEEP]   stored in data/.deep_api_key — set DEEP_API_KEY in .env to pin your own")
    else:
        print("[DEEP] ⚠  Remote auth DISABLED (DEEP_REQUIRE_REMOTE_AUTH=false) — API open to any reachable client")

    # Start Audit Trail FIRST — captures everything from boot
    try:
        await audit.start()
        print("[DEEP] AuditTrail started")
    except Exception as e:
        print(f"[DEEP] AuditTrail init error: {e}")

    try:
        await session_mgr.start()
        print("[DEEP] SessionManager started")
    except Exception as e:
        print(f"[DEEP] SessionManager init error: {e}")

    try:
        await netmon.start()
        print("[DEEP] Network Security Monitor started")
    except Exception as e:
        print(f"[DEEP] Security monitor init error: {e}")

    try:
        print("[DEEP] Research Engine started")
    except Exception as e:
        print(f"[DEEP] Research engine init error: {e}")

    try:
        await predictive_engine.start()
        print("[DEEP] Predictive Engine started")
    except Exception as e:
        print(f"[DEEP] Predictive engine init error: {e}")

    try:
        await self_eval.start()
        print("[DEEP] Self-Evaluation Engine started")
    except Exception as e:
        print(f"[DEEP] Self-evaluation init error: {e}")

    try:
        await knowledge_graph.start()
        print(f"[DEEP] Knowledge Graph started ({len(knowledge_graph.entities)} entities)")
    except Exception as e:
        print(f"[DEEP] Knowledge graph init error: {e}")

    try:
        print("[DEEP] Agent Factory started")
    except Exception as e:
        print(f"[DEEP] Agent factory init error: {e}")

    # Bridge external MCP servers into the brain's tool registry. Servers that
    # cannot start contribute nothing and say why — a missing capability, not a
    # failed boot — so this never guards the assistant coming up.
    try:
        from core.mcp import shared_bridge

        mcp_report = await shared_bridge().start()
        if mcp_report["tools_registered"]:
            print(f"[DEEP] MCP bridge: {mcp_report['tools_registered']} tool(s) from "
                  f"{len([s for s in mcp_report['servers'] if s.get('tools')])} server(s)")
        for entry in mcp_report["servers"]:
            if entry.get("skipped"):
                print(f"[DEEP] MCP {entry['id']} unavailable: {entry['skipped']}")
            elif entry.get("error"):
                print(f"[DEEP] MCP {entry['id']} failed to start: {entry['error']}")
    except Exception as e:
        print(f"[DEEP] MCP bridge init error: {e}")

    # Initialize Plugin Manager
    try:
        discovered = await plugin_manager.discover_plugins()
        await plugin_manager.init_all()
        await plugin_manager.start_all()

        # Let the brain's tool registry reach plugin-backed tools (e.g. scheduler)
        deep_tools.plugin_manager = plugin_manager

        # Register plugin API endpoints dynamically
        for endpoint in plugin_manager.get_all_endpoints():
            if endpoint.method == "GET":
                app.get(endpoint.path)(endpoint.handler)
            elif endpoint.method == "POST":
                app.post(endpoint.path)(endpoint.handler)
            elif endpoint.method == "PUT":
                app.put(endpoint.path)(endpoint.handler)
            elif endpoint.method == "DELETE":
                app.delete(endpoint.path)(endpoint.handler)
        
        print(f"[DEEP] Plugin Manager initialized ({len(discovered)} plugins)")
    except Exception as e:
        print(f"[DEEP] Plugin manager init error: {e}")

    # Start AI Neural Network Layer
    try:
        await pattern_memory.start()
        print("[DEEP] PatternMemory started")
    except Exception as e:
        print(f"[DEEP] PatternMemory init error: {e}")

    try:
        await deep_pipeline.start()
        print("[DEEP] DeepPipeline started")
    except Exception as e:
        print(f"[DEEP] DeepPipeline init error: {e}")

    try:
        await retraining_scheduler.start()
        print("[DEEP] RetrainingScheduler started")
    except Exception as e:
        print(f"[DEEP] RetrainingScheduler init error: {e}")

    try:
        await system_baseline.start()
        print("[DEEP] SystemBaseline started")
    except Exception as e:
        print(f"[DEEP] SystemBaseline init error: {e}")

    try:
        await network_baseline.start()
        print("[DEEP] NetworkBaseline started")
    except Exception as e:
        print(f"[DEEP] NetworkBaseline init error: {e}")

    try:
        await anomaly_detector.start()
        print("[DEEP] AnomalyDetector started")
    except Exception as e:
        print(f"[DEEP] AnomalyDetector init error: {e}")

    try:
        await threat_classifier.start()
        print("[DEEP] ThreatClassifier started")
    except Exception as e:
        print(f"[DEEP] ThreatClassifier init error: {e}")

    try:
        await alert_correlator.start()
        print("[DEEP] AlertCorrelator started")
    except Exception as e:
        print(f"[DEEP] AlertCorrelator init error: {e}")

    try:
        await security_timeline.start()
        print("[DEEP] SecurityTimeline started")
    except Exception as e:
        print(f"[DEEP] SecurityTimeline init error: {e}")

    try:
        await global_threat_watch.start()
        print("[DEEP] GlobalThreatWatch started")
    except Exception as e:
        print(f"[DEEP] GlobalThreatWatch init error: {e}")

    try:
        await alert_dispatcher.start()
        _live = ",".join(c["name"] for c in alert_dispatcher.status()["channels"]
                         if c.get("available"))
        print(f"[DEEP] AlertDispatcher started (floor="
              f"{alert_dispatcher.min_severity}, channels={_live or 'none'})")
    except Exception as e:
        print(f"[DEEP] AlertDispatcher init error: {e}")

    try:
        await graph_orchestrator.start()
        print("[DEEP] GraphOrchestrator started")
    except Exception as e:
        print(f"[DEEP] GraphOrchestrator init error: {e}")

    # Start Knowledge Intelligence Layer
    try:
        await knowledge_store.start()
        print("[DEEP] KnowledgeStore started")
    except Exception as e:
        print(f"[DEEP] KnowledgeStore init error: {e}")

    try:
        await ingester.start()
        print("[DEEP] KnowledgeIngester started")
    except Exception as e:
        print(f"[DEEP] KnowledgeIngester init error: {e}")

    try:
        await breakthrough_detector.start()
        print("[DEEP] BreakthroughDetector started")
    except Exception as e:
        print(f"[DEEP] BreakthroughDetector init error: {e}")

    try:
        await briefing_engine.start()
        print("[DEEP] BriefingEngine started")
    except Exception as e:
        print(f"[DEEP] BriefingEngine init error: {e}")

    try:
        await concept_linker.start()
        print("[DEEP] ConceptLinker started")
    except Exception as e:
        print(f"[DEEP] ConceptLinker init error: {e}")

    # Voice hardware/assistant startup removed (voice subsystem deleted).

    # Start Network Layer (v2)
    try:
        await tailscale.start()
        print("[DEEP] TailscaleManager started")
    except Exception as e:
        print(f"[DEEP] Tailscale init error: {e}")

    try:
        await remote_access.start()
        print("[DEEP] RemoteAccessManager started")
    except Exception as e:
        print(f"[DEEP] RemoteAccess init error: {e}")

    # Start Network Scanning & Security (v2)
    try:
        await scanner.start()
        print("[DEEP] NetworkScanner started")
    except Exception as e:
        print(f"[DEEP] NetworkScanner init error: {e}")

    try:
        await threat_monitor.start()
        print("[DEEP] ThreatMonitor started")
    except Exception as e:
        print(f"[DEEP] ThreatMonitor init error: {e}")

    try:
        await evil_twin.start()
        print("[DEEP] EvilTwinDetector started")
    except Exception as e:
        print(f"[DEEP] EvilTwinDetector init error: {e}")

    try:
        await pihole.start()
        print("[DEEP] PiholeClient started")
    except Exception as e:
        print(f"[DEEP] PiholeClient init error: {e}")

    try:
        await proximity.start()
        print("[DEEP] ProximityMonitor started")
    except Exception as e:
        print(f"[DEEP] ProximityMonitor init error: {e}")

    # Start Unified Network Graph (v3)
    try:
        await net_graph_builder.start()
        print("[DEEP] NetworkGraphBuilder started")
    except Exception as e:
        print(f"[DEEP] NetworkGraphBuilder init error: {e}")

    try:
        await net_ai_analyst.start()
        print("[DEEP] NetworkAIAnalyst started")
    except Exception as e:
        print(f"[DEEP] NetworkAIAnalyst init error: {e}")

    # Start Shared State Layer (v2)
    try:
        await redis_state.start()
        print("[DEEP] RedisStateManager started")
    except Exception as e:
        print(f"[DEEP] RedisState init error: {e}")

    try:
        await device_registry.start()
        print("[DEEP] DeviceRegistry started")
    except Exception as e:
        print(f"[DEEP] DeviceRegistry init error: {e}")

    # Announce DEEP is online
    await event_bus.publish("tts_speak", {
        "text": "DEEP online. All systems operational.",
        "priority": "urgent",
    })

    # Wire all bus events -> WebSocket broadcast via wildcard subscriber
    async def _ws_broadcast(event_name: str, payload: dict):
        if not manager.active:
            return
        type_map = {
            "security_alert": "security_alert",
            "security_alert_correlated": "security_alert_correlated",
            "topic_added": "research_event",
            "topic_removed": "research_event",
            "topic_scanned": "research_event",
            "briefing_ready": "research_event",
            "prediction_ready": "predictive_event",
            "feedback_recorded": "predictive_event",
            "evolution_complete": "evolution_event",
            "evaluation_complete": "evolution_event",
            "system_evolved": "evolution_event",
            "knowledge_added": "knowledge_event",
            "plugin_event": "plugin_event",
            "agent_created": "agent_event",
            "agent_terminated": "agent_event",
            "agent_task_start": "agent_event",
            "agent_task_complete": "agent_event",
            "agent_task_failed": "agent_event",
            "user_command": "user_command",
            "mood_update": "mood_update",
            "routed_command": "routed_command",
            "escalate_to_graph": "escalate_to_graph",
            "deep_response": "deep_response",
            "graph_complete": "graph_complete",
            "swarm_complete": "swarm_complete",
            "tts_complete": "tts_complete",
            "tts_error": "tts_error",
            "tts_interrupted": "tts_interrupted",
            "voice_state_changed": "voice_state_changed",
            "alert_spoken": "alert_spoken",
            "papers_ingested": "papers_ingested",
            "ingest_error": "ingest_error",
            "breakthrough_detected": "breakthrough_detected",
            "connection_found": "connection_found",
            "field_summary_ready": "field_summary_ready",
            "wake_word_detected": "wake_word_detected",
            "stt_listening": "stt_listening",
            "stt_processing": "stt_processing",
            "stt_complete": "stt_complete",
            "stt_failed": "stt_failed",
        }
        msg_type = type_map.get(event_name, event_name)
        msg = {"type": msg_type, "payload": payload}
        if event_name == "plugin_event":
            msg["plugin"] = payload.get("plugin")
            msg["event_type"] = payload.get("event_type")
        for ws in list(manager.active):
            try:
                await manager.send(ws, msg)
            except Exception:
                pass

    event_bus.subscribe("*", _ws_broadcast)

    # Approvals reach the HUD the moment a tool parks one. The queue is a
    # plain module with no bus dependency, so it exposes a hook instead; the
    # wildcard subscriber above forwards whatever we publish straight to the
    # WebSocket. Fire-and-forget: a tool must not fail because a browser is
    # not listening.
    def _approval_notify(event_name: str, payload: dict) -> None:
        try:
            asyncio.get_running_loop().create_task(event_bus.publish(event_name, payload))
        except RuntimeError:
            pass  # enqueued outside the loop (a test, a script) — poll picks it up

    pending_actions.set_notifier(_approval_notify)

    # Start the proactive layer (ProactiveCore: real rate-limiting/quiet-hours,
    # emits `proactive_suggestion` -> HUD alert cards). Replaces the old
    # proactive_loop() that faked alerts as raw chat tokens.
    asyncio.create_task(proactive_core.run())
    # Daily spoken briefing + anomaly correlation loops
    asyncio.create_task(_briefing_loop())
    asyncio.create_task(_correlation_loop())
    # Periodically synthesise the user world model from graph + recent chat
    asyncio.create_task(_world_model_loop())
    # Watch the personal-docs folder and ingest new/changed files
    asyncio.create_task(_docs_scan_loop())
    # Keep the hot intelligence feeds warm so the console never opens onto a
    # cold cache. Persistence means a restart usually costs no traffic at all.
    try:
        from core.intel.refresher import shared_refresher
        await shared_refresher().start()
    except Exception as exc:
        print(f"[DEEP] intel refresher failed to start: {exc}")


async def _briefing_loop():
    """Speak a morning briefing once per day at DEEP_BRIEFING_HOUR (local). Off if unset/<0."""
    import os
    from datetime import datetime
    try:
        hour = int(os.environ.get("DEEP_BRIEFING_HOUR", "-1"))
    except Exception:
        hour = -1
    if hour < 0:
        return  # disabled by default — opt in via env
    fired_on = None
    while True:
        try:
            now = datetime.now()
            if now.hour == hour and fired_on != now.date():
                fired_on = now.date()
                text = await _compose_briefing()
                await event_bus.publish("tts_speak", {"text": text, "priority": "normal"})
                await event_bus.publish("morning_briefing", {"text": text})
        except Exception:
            pass
        await asyncio.sleep(180)


async def _correlation_loop():
    """Correlate co-occurring suspicious signals into one reasoned alert."""
    seen = set()
    while True:
        await asyncio.sleep(45)
        try:
            hist = event_bus.get_history() if hasattr(event_bus, "get_history") else []
            import datetime as _dt
            cutoff = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(minutes=10)
            recent = []
            for h in hist:
                try:
                    if _dt.datetime.fromisoformat(h["timestamp"]) >= cutoff:
                        recent.append(h["event"])
                except Exception:
                    pass
            signals = {
                "new device": any("unknown_device" in e for e in recent),
                "unusual hour": any(e == "device_unusual_time" for e in recent),
                "open network": any("open_network" in e for e in recent),
                "tracker": any("tracker" in e for e in recent),
                "threat": any("threat" in e or "evil_twin" in e for e in recent),
            }
            hits = [k for k, v in signals.items() if v]
            if len(hits) >= 2:
                key = ",".join(sorted(hits))
                if key not in seen:
                    seen.add(key)
                    await event_bus.publish("correlated_alert", {
                        "signals": hits,
                        "summary": "Correlated activity: " + " + ".join(hits) + " within 10 minutes — possibly related.",
                    })
        except Exception:
            pass


async def shutdown_event():
    """Graceful shutdown: stop all modules then the event bus."""
    # Pooled aiohttp sessions. Neither of these was being closed, so every
    # shutdown leaked a connector: the intel layer's public-API session, and
    # the LLM client's (which /api/status opens via brain.health_check).
    try:
        from core.intel.refresher import shared_refresher
        await shared_refresher().stop()
    except Exception:
        pass
    try:
        from core.intel.http import shared_http
        await shared_http().close()
    except Exception:
        pass
    try:
        # Stops every bridged MCP subprocess and unregisters its tools.
        from core.mcp import shared_bridge
        await shared_bridge().aclose()
    except Exception:
        pass
    try:
        await ollama_client.close()
    except Exception:
        pass
    try:
        await plugin_manager.stop_all()
    except Exception:
        pass
    try:
        await netmon.stop()
    except Exception:
        pass
    
    try:
        await predictive_engine.stop()
    except Exception:
        pass
    try:
        await self_eval.stop()
    except Exception:
        pass
    try:
        await knowledge_graph.stop()
    except Exception:
        pass
    
    
    try:
        await graph_orchestrator.stop()
    except Exception:
        pass
    try:
        await anomaly_detector.stop()
    except Exception:
        pass
    try:
        await threat_classifier.stop()
    except Exception:
        pass
    try:
        await alert_correlator.stop()
    except Exception:
        pass
    try:
        await security_timeline.stop()
    except Exception:
        pass
    try:
        await alert_dispatcher.stop()
    except Exception:
        pass
    try:
        await global_threat_watch.stop()
    except Exception:
        pass
    try:
        await network_baseline.stop()
    except Exception:
        pass
    try:
        await system_baseline.stop()
    except Exception:
        pass
    try:
        await retraining_scheduler.stop()
    except Exception:
        pass
    try:
        await deep_pipeline.stop()
    except Exception:
        pass
    try:
        await pattern_memory.stop()
    except Exception:
        pass
    try:
        await concept_linker.stop()
    except Exception:
        pass
    try:
        await briefing_engine.stop()
    except Exception:
        pass
    try:
        await breakthrough_detector.stop()
    except Exception:
        pass
    try:
        await ingester.stop()
    except Exception:
        pass
    try:
        await knowledge_store.stop()
    except Exception:
        pass
    try:
        await proximity.stop()
    except Exception:
        pass
    try:
        await pihole.stop()
    except Exception:
        pass
    try:
        await evil_twin.stop()
    except Exception:
        pass
    try:
        await threat_monitor.stop()
    except Exception:
        pass
    try:
        await scanner.stop()
    except Exception:
        pass
    try:
        await device_registry.stop()
    except Exception:
        pass
    try:
        await redis_state.stop()
    except Exception:
        pass
    try:
        await remote_access.stop()
    except Exception:
        pass
    try:
        await tailscale.stop()
    except Exception:
        pass
    try:
        await net_ai_analyst.stop()
    except Exception:
        pass
    try:
        await net_graph_builder.stop()
    except Exception:
        pass
    # Stop SessionManager and AuditTrail LAST to capture shutdown events
    try:
        await session_mgr.end_session()
    except Exception:
        pass
    try:
        await audit.stop()
    except Exception:
        pass
    await event_bus.stop()
    print("[DEEP] Shutdown complete")

# (Retired) proactive_loop() — the old poller that faked alerts as chat tokens
# has been replaced by ProactiveCore (see proactive_core.run() in startup).

# Create Ollama client with ProviderConfig
ollama_config = ProviderConfig(
    provider=LLMProvider.OLLAMA,
    api_key=None,
    model=settings.ollama_model,
    base_url=settings.ollama_base_url,
    temperature=0.7,
    max_tokens=1024
)
ollama_client = OllamaClient(ollama_config)

# ── Network AI Analyst (needs ollama_client) ──────────────────────────────
net_ai_analyst = NetworkAIAnalyst(llm_client=ollama_client, event_bus=event_bus, graph=net_graph)

# ── Knowledge-graph LLM extractor ──────────────────────────────────────────
# Give the graph a real extractor (replaces the capitalized-word regex) using the
# local Ollama model at low temperature for clean, structured JSON. Decoupled:
# the graph only sees an async generate(system, user) callable.
async def _kg_llm_generate(system_prompt: str, user_prompt: str) -> str:
    out = ""
    async for tok in ollama_client.generate_stream(
        system_prompt, user_prompt, temperature=0.1, max_tokens=640
    ):
        out += tok
    return out

try:
    from core.entity_extractor import LLMEntityExtractor
    knowledge_graph.set_extractor(LLMEntityExtractor(_kg_llm_generate))
    print("[DEEP] Knowledge-graph LLM extractor wired (Ollama)")
except Exception as _kg_ex:
    print(f"[DEEP] KG extractor not wired: {_kg_ex}")

# ── User World Model ───────────────────────────────────────────────────────
# DEEP's persistent "what it knows about Aryan" — projects, people, priorities,
# focus, episodic summaries — synthesised from the knowledge graph + recent chat
# and injected into every system prompt.
from core.world_model import WorldModel
world_model = WorldModel()

# Bridges global threat intel (CISA KEV) into world_model: matches KEV
# vendor/product against known knowledge-graph entities so DEEP can connect
# "a CVE was disclosed today" to "you use that project" — see
# core/global_threat_watch.py
from core.intel_feeds import get_intel_feeds
from core.global_threat_watch import GlobalThreatWatch
global_threat_watch = GlobalThreatWatch(
    event_bus=event_bus,
    knowledge_graph=knowledge_graph,
    world_model=world_model,
    intel_feeds=get_intel_feeds(),
)

_wm_refreshing = False
async def _refresh_world_model():
    global _wm_refreshing
    if _wm_refreshing:
        return   # a synthesis is already running — skip overlapping LLM calls
    _wm_refreshing = True
    try:
        texts = []
        col = getattr(ltm, "_collection", None)
        if col is not None:
            res = col.get(where={"memory_type": "conversation"}, limit=14)
            texts = [t for t in (res.get("documents") or []) if t]
        await world_model.refresh(knowledge_graph, texts, _kg_llm_generate)
        print(f"[WorldModel] refreshed: {world_model.state.get('summary','')[:80]}")
    except Exception as e:
        print(f"[WorldModel] refresh error: {e}")
    finally:
        _wm_refreshing = False

async def _world_model_loop():
    await asyncio.sleep(45)              # let boot settle, then first synthesis
    await _refresh_world_model()
    while True:
        await asyncio.sleep(1800)        # re-synthesise every 30 min
        await _refresh_world_model()

# ── Personal Document RAG ──────────────────────────────────────────────────
# DEEP as a second brain over Aryan's own files: drop documents into the watch
# folder, they're chunked/embedded into memory and searchable with citations.
from core.personal_rag import PersonalRAG
personal_rag = PersonalRAG(ltm)

async def _docs_scan_loop():
    await asyncio.sleep(20)
    while True:
        try:
            res = personal_rag.scan()
            if res.get("files_ingested"):
                print(f"[PersonalRAG] ingested {res['files_ingested']} file(s), {res['chunks']} chunks")
                try:
                    await event_bus.publish("knowledge_ingested",
                                            {"source": "folder-scan", "chunks": res["chunks"]})
                except Exception:
                    pass
        except Exception as e:
            print(f"[PersonalRAG] scan error: {e}")
        await asyncio.sleep(120)   # re-scan the folder every 2 min

# /api/docs/* and /api/world/* moved to interface/routers/workspace.py

from core.llm.providers import (
    stream_ollama_vision_tokens,
)
from core.llm.router import RoutingLLM, GroqAgentLLM

brain = AsyncBrain(
    llm_client=RoutingLLM(ollama_client, settings),
    max_loops=5,
    enable_tools=True,
    user_name="Aryan",
    enable_autonomous=True
)


# Agents run on Groq when configured (fast + capable), else fall back to local Ollama.
_agent_llm = (GroqAgentLLM(settings.groq_api_key, settings.groq_model)
              if (settings.groq_api_key and len(settings.groq_api_key) > 10) else ollama_client)

# Initialize Agent Factory and wire it into tools

# In-memory registry of agent task jobs (for the UI to instruct + watch progress).
agent_jobs: Dict[str, dict] = {}

# Static files
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")


# ── SPA shell ────────────────────────────────────────────────────────────────
# Serve the built Lit app at / and /app. (Restored after a router refactor
# dropped these routes, which left / returning 404 and the UI blank.)
# no-cache on the HTML shell so upgrading clients always fetch the newest
# hashed assets; the /static/* assets stay immutable.
def _spa_index() -> FileResponse:
    built = static_path / "app-dist" / "index.html"
    if built.exists():
        return FileResponse(str(built), headers={"Cache-Control": "no-cache"})
    raise HTTPException(status_code=404, detail="UI not built — run `npm run build` in interface/web")

@app.get("/")
async def spa_root():
    return _spa_index()

@app.get("/app")
async def spa_app():
    return _spa_index()

# ── Science Studio — REMOVED ───────────────────────────────────────────────
# /api/science/compute, /api/math/solve and the /science-output media mount are
# gone. The compute engine behind them was archived (see archive/), so
# /api/science/compute answered `ok: true` while reporting "the science.compute
# module is not available" and /api/math/solve returned a null result. Their
# only frontend consumer, science-view.ts, shipped in no bundle. Deterministic
# math remains available to the chat path via core.reasoning.symbolic_router.

@app.post("/api/vision/screen")
async def vision_screen(payload: dict | None = None):
    """
    Screen awareness: capture the current screen, run it through the LOCAL vision
    model (moondream), and return DEEP's description. Fully offline; the question
    can be customised via {"q": "..."}.
    """
    payload = payload or {}
    question = payload.get("q") or "Describe what's on this screen for Aryan, concisely."
    try:
        from PIL import ImageGrab
        import io as _io, base64 as _b64
        img = ImageGrab.grab()
        w, h = img.size
        if max(w, h) > 1280:
            sc = 1280 / max(w, h)
            img = img.resize((int(w * sc), int(h * sc)))
        buf = _io.BytesIO(); img.convert("RGB").save(buf, "JPEG", quality=80)
        b64 = _b64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        return {"ok": False, "error": f"screen capture failed: {type(e).__name__}: {e}"}

    try:
        parts = []
        async for tok in stream_ollama_vision_tokens(
            "You are DEEP, describing Aryan's screen succinctly and usefully.",
            question, b64, settings.vision_model, settings.ollama_base_url, 256):
            parts.append(tok)
        text = "".join(parts).strip()
        try: await event_bus.publish("screen_observed", {"chars": len(text)})
        except Exception: pass
        return {"ok": True, "description": text, "model": settings.vision_model}
    except Exception as e:
        return {"ok": False, "error": f"vision failed: {type(e).__name__}: {e}"}

# /api/physics/* and /api/chem/* moved to interface/routers/reference.py

# /debug/events and /api/metrics moved to interface/routers/system.py

@app.get("/api/tts")
async def text_to_speech(text: str):
    """Voice subsystem removed — TTS is disabled."""
    raise HTTPException(status_code=503, detail="voice subsystem disabled")


@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Voice subsystem removed — transcription is disabled."""
    raise HTTPException(status_code=503, detail="voice subsystem disabled")

# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

# /api/security/{status,devices,events,acknowledge,trust,block} moved to interface/routers/security.py

# ── Research, Predictive, Evolution, and Knowledge-Graph endpoints have moved
#    to interface/routers/{research,predictive,evolution,knowledge_graph}.py and
#    are mounted via app.include_router(...) near the bottom of this file. ──


# ═══════════════════════════════════════════════════════════════════════════════
# PLUGIN MANAGER ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/plugins/stats")
async def plugin_stats():
    """Get plugin manager statistics."""
    try:
        return plugin_manager.get_stats()
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/plugins")
async def list_plugins():
    """List all loaded plugins."""
    try:
        return {"plugins": [p.to_dict() for p in plugin_manager.plugins.values()]}
    except Exception as e:
        return {"error": str(e)}






@app.post("/api/vision/analyze")
async def api_vision_analyze(data: dict):
    """Analyze an uploaded image (data-URL or base64) with local LLaVA vision."""
    img = (data or {}).get("image", "")
    q = (data or {}).get("question", "Describe this image in detail.")
    if not img:
        return {"error": "no image provided"}
    try:
        from core.integrations.vision_llava import llava_vision
        out = await llava_vision.analyze_image(img, q)
        return {"analysis": out}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/briefing/speak")
async def api_briefing_speak():
    """Compose a digest and speak it aloud (the morning-briefing voice)."""
    try:
        text = await _compose_briefing()
        await event_bus.publish("tts_speak", {"text": text, "priority": "normal"})
        return {"spoken": True, "text": text}
    except Exception as e:
        return {"error": str(e)}

async def _compose_briefing() -> str:
    """Build DEEP's spoken digest from briefing + research + security + sensing."""
    import httpx as _hx
    parts = []
    async with _hx.AsyncClient(timeout=8) as c:
        async def gj(p):
            try:
                r = await c.get(f"http://localhost:5174{p}"); return r.json()
            except Exception:
                return {}
        brief = await gj("/api/briefing")
        rs = await gj("/api/research/stats")
        sec = await gj("/api/security/status")
        known = await gj("/network/proximity/known")
    parts.append((brief.get("greeting") or "Good day, Aryan.").rstrip("."))
    bits = []
    if rs and rs.get("unread_findings"):
        bits.append(f"{rs['unread_findings']} new research findings")
    if sec and sec.get("summary"):
        s = sec["summary"]; susp = s.get("suspicious", 0)
        bits.append(f"{s.get('total', 0)} devices on your network" + (f", {susp} flagged" if susp else ", all clear"))
    if known and known.get("total_known"):
        bits.append(f"{known['total_known']} devices in my memory")
    if bits:
        parts.append("Here's your briefing. " + "; ".join(bits) + ".")
    else:
        parts.append("All systems nominal. Nothing needs your attention.")
    parts.append("I'm ready when you are.")
    return " ".join(parts)

# The HUD polls this every 15s (see deep-app.pollStatus) to drive the system
# health node, and core/api.ts exports a typed client for it — but no handler
# ever existed, so every poll 404'd into the catch branch and the indicator sat
# permanently on "warning". Only a live browser surfaces this; no test hit it.
_STATUS_CACHE = {"t": 0.0, "brain": "unknown"}


@app.get("/api/status")
async def api_status():
    """Cheap liveness summary for the HUD's system node."""
    import time as _t

    now = _t.time()
    # health_check can reach out to the LLM backend; cache so a 15s poll from
    # several tabs can't turn into a request storm against Ollama.
    if now - _STATUS_CACHE["t"] > 30:
        try:
            health = await asyncio.wait_for(brain.health_check(), timeout=5)
            status = getattr(health, "status", None)
            _STATUS_CACHE["brain"] = "ok" if getattr(status, "value", status) in ("ok", "OK") else "degraded"
        except Exception:
            _STATUS_CACHE["brain"] = "degraded"
        _STATUS_CACHE["t"] = now

    now_dt = datetime.now()
    return {
        "deep": "online",
        "brain": _STATUS_CACHE["brain"],
        "model": settings.ollama_model,
        "time": now_dt.strftime("%H:%M:%S"),
        "date": now_dt.strftime("%Y-%m-%d"),
    }


_vitals_cache = {"t": 0.0, "sent": 0, "recv": 0}
@app.get("/api/vitals")
async def api_vitals():
    """Live machine vitals (CPU / RAM / disk / network) for the orb's vitals ring."""
    import psutil, time as _t, os as _os
    try:
        cpu = psutil.cpu_percent(interval=None)
        vm = psutil.virtual_memory()
        try:
            disk = psutil.disk_usage(_os.environ.get("SystemDrive", "C:") + "\\").percent
        except Exception:
            disk = psutil.disk_usage("/").percent
        nio = psutil.net_io_counters()
        now = _t.time()
        prev = _vitals_cache
        sent_rate = recv_rate = 0.0
        if prev["t"]:
            dt = max(0.5, now - prev["t"])
            sent_rate = max(0.0, (nio.bytes_sent - prev["sent"]) / dt / 1e6)
            recv_rate = max(0.0, (nio.bytes_recv - prev["recv"]) / dt / 1e6)
        _vitals_cache.update({"t": now, "sent": nio.bytes_sent, "recv": nio.bytes_recv})
        return {
            "cpu": round(cpu, 1), "ram": round(vm.percent, 1), "disk": round(disk, 1),
            "ram_used_gb": round(vm.used / 1e9, 1), "ram_total_gb": round(vm.total / 1e9, 1),
            "net_sent_mbs": round(sent_rate, 2), "net_recv_mbs": round(recv_rate, 2),
            "cores": psutil.cpu_count(),
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/system/info")
async def api_system_info():
    """Rich machine profile: connected displays, GPU, battery, uptime, per-core
    CPU, OS — the precise hardware picture for the system monitor panel."""
    import psutil, platform, socket, time as _t
    info: dict = {}
    try:
        info["hostname"] = socket.gethostname()
        info["os"] = f"{platform.system()} {platform.release()}"
        info["arch"] = platform.machine()
        info["python"] = platform.python_version()
        info["boot_time"] = psutil.boot_time()
        info["uptime_s"] = int(_t.time() - psutil.boot_time())
        info["cpu_model"] = platform.processor() or "CPU"
        info["cores_physical"] = psutil.cpu_count(logical=False)
        info["cores_logical"] = psutil.cpu_count(logical=True)
        try:
            f = psutil.cpu_freq()
            info["cpu_freq_mhz"] = round(f.current) if f else None
        except Exception:
            info["cpu_freq_mhz"] = None
        info["per_core"] = psutil.cpu_percent(percpu=True, interval=0.2)
    except Exception as e:
        info["sys_error"] = str(e)

    # Battery
    try:
        b = psutil.sensors_battery()
        if b is not None:
            info["battery"] = {
                "percent": round(b.percent), "plugged": bool(b.power_plugged),
                "secs_left": (None if b.secsleft is None or b.secsleft < 0 else b.secsleft),
            }
    except Exception:
        pass

    # Connected displays / monitors (Windows via win32api, fallback to ctypes)
    displays = []
    try:
        import win32api
        for i, (h, _hdc, _rect) in enumerate(win32api.EnumDisplayMonitors()):
            mi = win32api.GetMonitorInfo(h)
            r = mi["Monitor"]
            displays.append({
                "name": mi.get("Device", f"DISPLAY{i+1}"),
                "width": r[2] - r[0], "height": r[3] - r[1],
                "x": r[0], "y": r[1],
                "primary": mi.get("Flags") == 1,
            })
    except Exception:
        try:
            import ctypes
            u = ctypes.windll.user32
            displays.append({"name": "DISPLAY1", "width": u.GetSystemMetrics(0),
                             "height": u.GetSystemMetrics(1), "x": 0, "y": 0, "primary": True})
        except Exception:
            pass
    info["displays"] = displays

    # GPU (best-effort via the existing system monitor)
    try:
        from engine.system_monitor import SystemMonitor  # type: ignore
        sm = SystemMonitor()
        if hasattr(sm, "_gpu"):
            info["gpu"] = sm._gpu()
    except Exception:
        info["gpu"] = None

    return info

@app.get("/api/reasoning/last")
async def api_reasoning_last():
    """Reasoning transparency: which model handled the last brain turn + steps."""
    provider = None
    try:
        provider = getattr(brain.llm, "last_provider", None)
    except Exception:
        pass
    return {
        "provider": provider,
        "chat_order": settings.chat_provider_order,
        "steps": list(globals().get("_last_reasoning_steps", [])),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# NETWORK / TAILSCALE ENDPOINTS (v2)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/network/tailscale")
async def network_tailscale_status():
    """Current Tailscale VPN status."""
    return tailscale.status()

@app.get("/network/remote")
async def network_remote_info():
    """Remote access information (URL, WS, QR code)."""
    return await remote_access.get_access_info()

@app.post("/network/vpn/up")
async def network_vpn_up():
    """Bring Tailscale VPN up."""
    success = await tailscale.connect()
    return {"success": success}

@app.post("/network/vpn/down")
async def network_vpn_down():
    """Bring Tailscale VPN down."""
    success = await tailscale.disconnect()
    return {"success": success}


# ═══════════════════════════════════════════════════════════════════════════════
# WINDOWS CLIENT ENDPOINTS (v2)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/windows/apps")
async def windows_apps():
    """Get running apps from C# Windows client (stored in Redis)."""
    try:
        from core.config import Settings
        device_id = getattr(Settings(), "deep_device_id", "unknown")
        apps = await redis_state.get_device(device_id, "running_apps", default=[])
        return {"apps": apps}
    except Exception as e:
        return {"error": str(e)}

@app.get("/windows/stats")
async def windows_stats():
    """Get latest Windows hardware stats from C# client via Redis."""
    try:
        from core.config import Settings
        device_id = getattr(Settings(), "deep_device_id", "unknown")
        stats = await redis_state.get_device(device_id, "stats", default={})
        return stats
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIO / BLUETOOTH ENDPOINTS (v2)
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT & SESSION ENDPOINTS (v2)
# ═══════════════════════════════════════════════════════════════════════════════

































































































@app.get("/ai/retraining/stats")
async def retraining_stats():
    """Return dataset statistics from PatternMemory."""
    try:
        from ai.retraining.data_extractor import TrainingDataExtractor
        extractor = TrainingDataExtractor(pattern_memory)
        return await extractor.get_dataset_stats()
    except Exception as e:
        return {"error": str(e)}


@app.post("/ai/retraining/trigger")
async def retraining_trigger():
    """Manually trigger an intent classifier retraining cycle."""
    try:
        await retraining_scheduler.trigger_manual()
        return {"success": True, "message": "Retraining triggered"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/ai/retraining/history")
async def retraining_history():
    """List all retraining log files with parsed contents."""
    try:
        log_dir = Path(getattr(settings, "retrain_log_dir", "logs/retraining"))
        if not log_dir.exists():
            return {"logs": []}
        logs = []
        for path in sorted(log_dir.glob("retrain_*.json"), reverse=True):
            try:
                logs.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                pass
        return {"logs": logs}
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# ANOMALY DETECTION ENDPOINTS (v3)
# ═══════════════════════════════════════════════════════════════════════════════









































# ── Threat classifier endpoints have moved to interface/routers/threat.py and
#    are mounted via app.include_router(...) below. ──


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER REGISTRATION — extracted endpoint groups (see interface/routers/)
# ═══════════════════════════════════════════════════════════════════════════════
from interface.deps import register as _register_services, services
from interface.routers import ROUTERS as _DEEP_ROUTERS

def _time_of_day():
    h = datetime.now().hour
    if h < 12: return "morning"
    elif h < 18: return "afternoon"
    else: return "evening"

_register_services(
    predictive_engine=predictive_engine,
    self_eval=self_eval,
    knowledge_graph=knowledge_graph,
    threat_classifier=threat_classifier,
    ltm=ltm,
    personal_rag=personal_rag,
    world_model=world_model,
    refresh_world_model=_refresh_world_model,
    settings=settings,
    brain=brain,
    event_bus=event_bus,
    metrics=metrics,
    time_of_day=_time_of_day,
    netmon=netmon,
    knowledge_store=knowledge_store,
    briefing_engine=briefing_engine,
    concept_linker=concept_linker,
    redis_state=redis_state,
    scanner=scanner,
    net_graph=net_graph,
    net_ai_analyst=net_ai_analyst,
    evil_twin=evil_twin,
    pihole=pihole,
    proximity=proximity,
    device_registry=device_registry,
    threat_monitor=getattr(sys.modules[__name__], 'threat_monitor', None),
    deep_tools=deep_tools,
    agent_jobs=agent_jobs,
    plugin_manager=plugin_manager,
    system_baseline=system_baseline,
    network_baseline=network_baseline,
    anomaly_detector=anomaly_detector,
    audit_trail=audit,
    session_manager=session_mgr,
    retraining_scheduler=retraining_scheduler,
    alert_correlator=alert_correlator,
    security_timeline=security_timeline,
    alert_dispatcher=alert_dispatcher,
    global_threat_watch=global_threat_watch,
)
# Give the LLM tool layer the same view of DEEP's own subsystems that the
# routers and the ops terminal have. core/tools/local_estate.py reads these
# through ctx.estate; without this the assistant can query public threat
# intelligence but not a single thing DEEP has actually observed here.
deep_tools.estate = services

for _r in _DEEP_ROUTERS:
    app.include_router(_r)

# Legacy threat-globe endpoints. Superseded by /api/intel/* (see
# interface/routers/intel.py); kept as thin async adapters so the existing
# frontend keeps working during the migration.
from core.services.threat_intel import (
    get_live_public_servers,
    get_live_threats,
    get_osint_details,
)


@app.get("/api/threats/live")
async def api_live_threats():
    return await get_live_threats()


@app.get("/api/threats/osint")
async def api_osint_details(ip: str):
    return await get_osint_details(ip)


@app.get("/api/servers/live")
async def api_live_servers():
    return await get_live_public_servers()

if __name__ == "__main__":
    import uvicorn
    print(f"[DEEP] AI Server starting...")
    print(f"   Model: {settings.ollama_model}")
    print(f"   URL: http://127.0.0.1:5174/ai")
    uvicorn.run(app, host="127.0.0.1", port=5174, log_level="info")
