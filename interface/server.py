"""
DEEP Interface Server - JARVIS-Style Personal AI
Minimal FastAPI backend for voice-first AI interface
"""

import json
import asyncio
import hashlib
import sys
from contextlib import asynccontextmanager
# The mac_vendor_lookup library's sync lookup() leaks an un-awaited coroutine
# when used outside a main-thread event loop. Vendor enrichment degrades
# gracefully to the OUI fallback table, so silence this known-benign warning.
import warnings as _warnings
_warnings.filterwarnings("ignore", message=r".*AsyncMacLookup\.lookup.*")
from typing import Set, Optional, Dict, List
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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import UploadFile, File
import time as _time
from collections import deque
import tempfile
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
from core.application.tool_registry import DeepToolRegistry
from core.ltm_memory import LongTermMemory
# core.voice_web / core.local_stt imports removed (VoiceWeb/LocalSTT stubbed above)
from core.agent_factory import AgentFactory
from core.security.network_monitor import NetworkMonitor
from core.research_engine import ResearchEngine
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
from ai.agent_swarm import AgentSwarm
from knowledge import (
    KnowledgeStore, KnowledgeIngester,
    BreakthroughDetector, BriefingEngine, ConceptLinker,
)
# ── Voice subsystem removed (voice/ hard-deleted). These stubs keep the existing
#    instantiation/usage sites in this file as harmless no-ops so the server boots
#    without voice; the voice HTTP endpoints are disabled further below. ──
class _VoiceStub:
    def __init__(self, *a, **k):
        pass
    def __getattr__(self, _name):
        async def _noop(*a, **k):
            return None
        return _noop
WakeWordDetector = STTEngine = TTSEngine = _VoiceStub
BluetoothAudioManager = WhisperEar = SpatialAudio = _VoiceStub
VoiceWeb = LocalSTT = VoiceSecurity = AlertManager = VoiceAssistant = ActionRegistry = _VoiceStub
audio_utils = _VoiceStub()
from network import (
    TailscaleManager, RemoteAccessManager,
    NetworkScanner, ThreatMonitor,
    EvilTwinDetector, PiholeClient,
    ProximityMonitor,
)
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
_PUBLIC_PREFIXES = ("/static", "/science-output")
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
            if not key or key != settings.deep_api_key:
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
voice_engine = VoiceWeb(settings, event_bus=event_bus)
ltm = LongTermMemory()
from core.preference_learning import PreferenceLearner
pref_learner = PreferenceLearner(ltm)
stt_engine = LocalSTT("base", event_bus=event_bus)
netmon = NetworkMonitor(event_bus=event_bus)
research_engine = ResearchEngine(event_bus=event_bus)
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
agent_swarm = AgentSwarm(event_bus=event_bus)

# ── Knowledge Intelligence Layer ────────────────────────────────────────
knowledge_store = KnowledgeStore(event_bus=event_bus)
ingester = KnowledgeIngester(event_bus=event_bus, knowledge_store=knowledge_store)
breakthrough_detector = BreakthroughDetector(event_bus=event_bus, knowledge_store=knowledge_store)
briefing_engine = BriefingEngine(event_bus=event_bus, knowledge_store=knowledge_store)
concept_linker = ConceptLinker(event_bus=event_bus, knowledge_store=knowledge_store)

# Re-create agent_swarm now that knowledge_store exists
agent_swarm = AgentSwarm(
    event_bus=event_bus,
    knowledge_store=knowledge_store,
    ingester=ingester,
)

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

# ── Voice Hardware Layer ────────────────────────────────────────────────
input_device = audio_utils.get_input_device_index(
    settings.audio_input_device
) if settings.audio_input_device else None
output_device = audio_utils.get_output_device_index(
    settings.audio_output_device
) if settings.audio_output_device else None

# ── Spatial Audio (v2) ──────────────────────────────────────────────────
spatial_audio = SpatialAudio(event_bus=event_bus)

wake_detector = WakeWordDetector(
    event_bus=event_bus,
    model_name=settings.wake_word_model,
    threshold=settings.wake_word_threshold,
    verifier_threshold=settings.voice_verifier_threshold,
    device_index=input_device,
)
stt = STTEngine(
    event_bus=event_bus,
    model_name=settings.whisper_model,
    silence_threshold=settings.silence_threshold,
    silence_duration_ms=settings.silence_duration_ms,
    max_command_duration_s=settings.max_command_duration_s,
    device_index=input_device,
)
tts = TTSEngine(
    event_bus=event_bus,
    model_path=settings.piper_model_path,
    speaking_rate=settings.tts_speaking_rate,
    spatial_audio=spatial_audio,
)

# ── DEEP Voice AI Assistant (v4) ────────────────────────────────────────
voice_security = VoiceSecurity(event_bus=event_bus)
alert_manager = AlertManager(
    event_bus=event_bus,
    voice_security=voice_security,
    tts_callback=lambda text, priority="normal": asyncio.create_task(
        event_bus.publish("tts_speak", {"text": text, "priority": priority})
    ),
)

# ── Bluetooth Private Ear (v2) ──────────────────────────────────────────
bt_audio = BluetoothAudioManager(event_bus=event_bus, redis_state=redis_state)
whisper_ear = WhisperEar(event_bus=event_bus, bt_audio=bt_audio)

async def startup_event():
    # Start the central event bus first
    await event_bus.start()

    # Pre-warm the chemistry periodic-table cache (118 mendeleev lookups) during
    # boot so the /api/chem/table endpoint never pays that cost on a live request.
    try:
        from core.reasoning import chem_oracle as _chem
        n = len(_chem.table())
        print(f"[DEEP] Chemistry oracle warmed ({n} elements)")
    except Exception as e:
        print(f"[DEEP] Chemistry oracle warm error: {e}")

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

    # Start all modules (each self-registers any internal subscriptions in start())
    try:
        await voice_engine.start()
        print("[DEEP] Voice engine started")
    except Exception as e:
        print(f"[DEEP] Voice engine init error: {e}")

    try:
        await netmon.start()
        print("[DEEP] Network Security Monitor started")
    except Exception as e:
        print(f"[DEEP] Security monitor init error: {e}")

    try:
        await research_engine.start()
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
        await agent_factory.start()
        print("[DEEP] Agent Factory started")
    except Exception as e:
        print(f"[DEEP] Agent factory init error: {e}")

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
        await graph_orchestrator.start()
        print("[DEEP] GraphOrchestrator started")
    except Exception as e:
        print(f"[DEEP] GraphOrchestrator init error: {e}")

    try:
        await agent_swarm.start()
        print("[DEEP] AgentSwarm started")
    except Exception as e:
        print(f"[DEEP] AgentSwarm init error: {e}")

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

    # Start Bluetooth Private Ear (v2)
    try:
        await bt_audio.start()
        print("[DEEP] BluetoothAudioManager started")
    except Exception as e:
        print(f"[DEEP] BluetoothAudioManager init error: {e}")

    try:
        await whisper_ear.start()
        print("[DEEP] WhisperEar started")
    except Exception as e:
        print(f"[DEEP] WhisperEar init error: {e}")

    try:
        await spatial_audio.start()
        print("[DEEP] SpatialAudio started")
    except Exception as e:
        print(f"[DEEP] SpatialAudio init error: {e}")

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
    try:
        await plugin_manager.stop_all()
    except Exception:
        pass
    try:
        await voice_engine.stop()
    except Exception:
        pass
    try:
        await netmon.stop()
    except Exception:
        pass
    try:
        await research_engine.stop()
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
        await agent_factory.stop()
    except Exception:
        pass
    try:
        await agent_swarm.stop()
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
        await voice_assistant.stop()
    except Exception:
        pass
    try:
        await wake_detector.stop()
    except Exception:
        pass
    try:
        await stt.stop()
    except Exception:
        pass
    try:
        await tts.stop()
    except Exception:
        pass
    try:
        await whisper_ear.stop()
    except Exception:
        pass
    try:
        await bt_audio.stop()
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

# ── DEEP Voice AI Assistant: Action Registry (needs ollama_client) ────────
action_registry = ActionRegistry(
    event_bus=event_bus,
    scanner=scanner,
    device_registry=device_registry,
    threat_monitor=threat_monitor,
    tailscale=tailscale,
    pihole=pihole,
    network_graph=net_graph,
    llm_client=ollama_client,
    settings=settings,
)

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
    stream_ollama_vision_tokens, stream_claude_tokens, stream_groq_tokens,
    stream_gemini_tokens, _parse_data_url,
)
from core.llm.router import RoutingLLM, GroqAgentLLM

brain = AsyncBrain(
    llm_client=RoutingLLM(ollama_client, settings),
    max_loops=5,
    enable_tools=True,
    user_name="Aryan",
    enable_autonomous=True
)

# ── DEEP Voice AI Assistant (v4) ────────────────────────────────────────
voice_assistant = VoiceAssistant(
    event_bus=event_bus,
    wake_word_detector=wake_detector,
    stt_engine=stt,
    tts_engine=tts,
    brain=brain,
    action_registry=action_registry,
    voice_security=voice_security,
    alert_manager=alert_manager,
    user_name="Aryan",
)

# Agents run on Groq when configured (fast + capable), else fall back to local Ollama.
_agent_llm = (GroqAgentLLM(settings.groq_api_key, settings.groq_model)
              if (settings.groq_api_key and len(settings.groq_api_key) > 10) else ollama_client)

# Initialize Agent Factory and wire it into tools
agent_factory = AgentFactory(llm_client=_agent_llm, tool_registry=deep_tools, event_bus=event_bus)
deep_tools.agent_factory = agent_factory

# In-memory registry of agent task jobs (for the UI to instruct + watch progress).
agent_jobs: Dict[str, dict] = {}

# Static files
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")

# ── Science Studio — 16-domain compute engine + generated media ─────────────
try:
    from engine import config as _sci_config
    _SCI_BASE = Path(_sci_config.BASE_DIR)
except Exception:
    _SCI_BASE = Path.home() / "deep_output"
for _d in ("plots", "animations", "reports", "manim", "models"):
    try:
        (_SCI_BASE / _d).mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
try:
    app.mount("/science-output", StaticFiles(directory=str(_SCI_BASE)), name="science_output")
except Exception as _e:
    print(f"[DEEP] science-output mount failed: {_e}")

_sci_engine = None

def _get_sci_engine():
    global _sci_engine
    if _sci_engine is None:
        from engine.main import DEEP
        _sci_engine = DEEP()
    return _sci_engine

def _sci_to_url(p):
    """Map an engine-produced absolute path under deep_output to a served URL."""
    try:
        rel = Path(p).resolve().relative_to(_SCI_BASE.resolve())
        return "/science-output/" + str(rel).replace("\\", "/")
    except Exception:
        return None

def _sci_sanitize(obj, depth=0):
    """Make arbitrary engine results JSON-safe and compact (arrays truncated)."""
    if depth > 4:
        return str(obj)[:240]
    if obj is None or isinstance(obj, (bool, int, str)):
        return obj
    if isinstance(obj, float):
        return obj if (obj == obj and obj not in (float("inf"), float("-inf"))) else str(obj)
    if isinstance(obj, dict):
        return {str(k): _sci_sanitize(v, depth + 1) for k, v in list(obj.items())[:40]}
    if isinstance(obj, (list, tuple)):
        return [_sci_sanitize(v, depth + 1) for v in list(obj)[:50]]
    return str(obj)[:240]

_SCI_MEDIA_KEYS = ("gif_path", "mp4_path", "png_path", "png", "image", "plot_path", "path", "file")

@app.post("/api/math/solve")
async def math_solve(payload: dict):
    """Deterministic symbolic math via the SymPy router (exact, no hallucination).
    Handles solve/derivative/integrate/simplify/factor/evaluate, including
    implicit multiplication like 'x^3 + 2x'. Returns None when not a clean math
    query so the caller can fall back to the broader NL science engine."""
    text = (payload or {}).get("query", "")
    if not isinstance(text, str) or not text.strip():
        return {"ok": False, "result": None}
    try:
        from core.reasoning import symbolic_router as _sr
        res = _sr.solve(text)
        if res:
            return {"ok": True, "kind": res["kind"], "expression": res["expression"],
                    "result": res["result"], "engine": res["engine"],
                    "latex": res.get("latex"), "latex_expr": res.get("latex_expr")}
        return {"ok": False, "result": None}
    except Exception as e:
        return {"ok": False, "result": None, "error": str(e)}

@app.post("/api/science/compute")
async def science_compute(payload: dict):
    """Route a natural-language science/tech command through the engine."""
    text = (payload or {}).get("query", "")
    if not isinstance(text, str) or not text.strip():
        return {"ok": False, "verbal": "Empty query, sir.", "media": [], "result": None}
    try:
        engine = _get_sci_engine()
        res = await asyncio.to_thread(engine.process_command, text.strip())
    except Exception as e:
        return {"ok": False, "verbal": f"Engine error: {e}", "media": [], "result": None}
    res = res if isinstance(res, dict) else {"result": res}
    media, seen = [], set()
    for k in _SCI_MEDIA_KEYS:
        v = res.get(k)
        if isinstance(v, str) and v:
            url = _sci_to_url(v)
            if url and url not in seen:
                seen.add(url)
                low = url.lower()
                kind = "gif" if low.endswith(".gif") else ("video" if low.endswith((".mp4", ".webm")) else "image")
                media.append({"type": kind, "url": url, "name": Path(v).name})
    return {
        "ok": True,
        "verbal": res.get("verbal") or "Done, sir.",
        "module": res.get("module"),
        "function": res.get("function"),
        "result": _sci_sanitize(res.get("result")),
        # Symbolic engines (compute.py) emit render-ready TeX + exact symbolic /
        # numeric forms; surface them so the UI can typeset with KaTeX.
        "latex": res.get("latex"),
        "symbolic": res.get("symbolic"),
        "numeric": _sci_sanitize(res.get("numeric")),
        "media": media,
    }

# Active connections
class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()
    
    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)
    
    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)
    
    async def send(self, ws: WebSocket, message: dict):
        await ws.send_json(message)

manager = ConnectionManager()

# Per-connection conversation history  {ws_id: [{role, content, time}]}
session_history: Dict[int, List[Dict]] = {}
MAX_HISTORY = 12  # turns kept per session


def _time_of_day() -> str:
    h = datetime.now().hour
    if 5 <= h < 12:  return "morning"
    if 12 <= h < 17: return "afternoon"
    if 17 <= h < 22: return "evening"
    return "night"


def build_jarvis_context(ws_id: int, user_input: str) -> str:
    """Build rich context block injected into every prompt."""
    now  = datetime.now()
    date = now.strftime("%A, %B %d, %Y")
    time = now.strftime("%I:%M %p")

    # Short-term session history
    history = session_history.get(ws_id, [])
    history_text = ""
    if history:
        lines = []
        for t in history[-MAX_HISTORY:]:
            speaker = "Aryan" if t["role"] == "user" else "Deep"
            lines.append(f"{speaker}: {t['content'][:300]}")
        history_text = "\n=== SHORT-TERM CONVERSATION HISTORY ===\n" + "\n".join(lines) + "\n"

    # Long-term semantic recall
    ltm_context = ""
    try:
        if user_input:
            recalled = ltm.recall(user_input, k=3)
            if recalled:
                ltm_context = "\n=== LONG-TERM MEMORY (RELEVANT FACTS) ===\n"
                for m in recalled:
                    ltm_context += f"- {m.content}\n"
    except Exception as e:
        print(f"[LTM Error] {e}")

    # Knowledge-graph recall — the READ half of the memory loop. The write half
    # (ingest_llm after each turn) already runs; this injects the entities most
    # SEMANTICALLY relevant to the turn plus how they connect, so the brain
    # reasons over what it knows instead of letting the graph sit idle.
    kg_context = ""
    try:
        if user_input:
            hits = knowledge_graph.semantic_search(user_input, k=5, min_score=0.35)
            if hits:
                lines = []
                for h in hits[:5]:
                    bit = h["name"]
                    desc = (h.get("description") or "").strip()
                    if desc:
                        bit += f" — {desc}"
                    nbrs = knowledge_graph.get_neighbors(h["name"])[:4]
                    rel = "; ".join(f"{n['relation']} {n['entity']['name']}" for n in nbrs)
                    if rel:
                        bit += f" ({rel})"
                    lines.append("- " + bit)
                kg_context = "\n=== KNOWLEDGE GRAPH (relevant to this) ===\n" + "\n".join(lines) + "\n"
    except Exception as e:
        print(f"[KG recall Error] {e}")

    # Learned user preferences — inject so Deep adapts to Aryan over time
    pref_context = ""
    try:
        prefs = pref_learner.get_preferences(user_input, k=5)
        if prefs:
            pref_context = "\n=== USER PREFERENCES (honor these) ===\n"
            for p in prefs:
                pref_context += f"- {p}\n"
    except Exception as e:
        print(f"[PrefLearn Error] {e}")

    return (
        f"=== SYSTEM CONTEXT ===\n"
        f"Date: {date}\n"
        f"Time: {time} ({_time_of_day()})\n"
        f"User: Aryan\n"
        f"System: Deep neural interface v2 - all modules online\n"
        f"{pref_context}"
        f"{kg_context}"
        f"{ltm_context}"
        f"{history_text}"
    )


def _ltm_importance(role: str, content: str) -> float:
    """Heuristic importance (0=skip) so LTM stores signal, not chatter.

    Skips trivial turns (greetings, very short acks). Boosts turns that look
    like durable facts/decisions worth recalling later.
    """
    text = (content or "").strip()
    if len(text) < 25:
        return 0.0
    low = text.lower()
    # Skip pure pleasantries / acknowledgements.
    if low in ("ok", "okay", "thanks", "thank you", "got it", "cool", "nice", "yes", "no", "sure"):
        return 0.0
    importance = 1.0
    # Fact/decision/preference signals -> more important to remember.
    if any(k in low for k in (
        "i am", "i'm", "my name", "i like", "i prefer", "i want", "i need",
        "remember", "my goal", "i decided", "we decided", "i live", "i work",
        "my email", "my phone", "important", "always", "never",
    )):
        importance = 1.6
    # Assistant turns are usually derivative; keep only substantial ones, lower weight.
    if role == "assistant":
        if len(text) < 120:
            return 0.0
        importance = min(importance, 0.9)
    return importance


def store_turn(ws_id: int, role: str, content: str):
    """Append a turn to session history and persist meaningful turns to LTM."""
    if ws_id not in session_history:
        session_history[ws_id] = []
    session_history[ws_id].append({"role": role, "content": content, "time": datetime.now().isoformat()})
    # Trim to max
    if len(session_history[ws_id]) > MAX_HISTORY * 2:
        session_history[ws_id] = session_history[ws_id][-MAX_HISTORY * 2:]

    # Learn durable preferences/corrections from user input (detect+normalize+dedup+store)
    if role == "user":
        try:
            learned = pref_learner.learn(content)
            if learned:
                print(f"[PrefLearn] Learned preference: {learned}")
        except Exception as e:
            print(f"[PrefLearn Error] {e}")

    # Persist the turn itself into long-term memory so Deep accumulates a
    # recallable history across sessions (not just preferences). Dedup by a
    # content hash so identical turns aren't stored twice.
    try:
        importance = _ltm_importance(role, content)
        if importance > 0.0:
            digest = hashlib.sha1(f"{role}:{content.strip()}".encode("utf-8")).hexdigest()[:16]
            ltm.store(
                memory_type="conversation",
                content=content.strip(),
                metadata={"role": role, "speaker": "Aryan" if role == "user" else "Deep"},
                importance=importance,
                memory_id=f"turn_{digest}",
            )
    except Exception as e:
        print(f"[LTM Store Error] {e}")

@app.get("/")
async def root():
    """Root serves the modern UI (Vite + Lit)."""
    built = static_path / "app-dist" / "index.html"
    if built.exists():
        return FileResponse(str(built), headers={"Cache-Control": "no-cache"})
    return HTMLResponse(
        "<h1>DEEP modern UI not built yet</h1>"
        "<p>Run <code>cd interface/web &amp;&amp; npm install &amp;&amp; npm run build</code></p>",
        status_code=200,
    )

@app.get("/app")
async def modern_ui():
    """Modern UI (Vite + Lit)."""
    built = static_path / "app-dist" / "index.html"
    if built.exists():
        return FileResponse(str(built), headers={"Cache-Control": "no-cache"})
    return HTMLResponse(
        "<h1>DEEP modern UI not built yet</h1>"
        "<p>Run <code>cd interface/web &amp;&amp; npm install &amp;&amp; npm run build</code></p>",
        status_code=200,
    )

# ── PWA: serve manifest + service worker from root so the SW scope covers /ai ──
@app.get("/manifest.webmanifest")
async def pwa_manifest():
    return FileResponse(str(static_path / "manifest.webmanifest"),
                        media_type="application/manifest+json")

@app.get("/sw.js")
async def pwa_service_worker():
    return FileResponse(str(static_path / "sw.js"),
                        media_type="application/javascript",
                        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"})

@app.websocket("/ws/manas")
async def websocket_legacy_manas(ws: WebSocket):
    """Backward-compat alias for the pre-rename path. Stale clients (cached old
    tabs / older windows-clients) still hit /ws/manas and were getting 403s in a
    tight reconnect loop — delegate them to the real handler instead."""
    await websocket(ws)


@app.websocket("/ws/deep")
async def websocket(ws: WebSocket):
    # Loopback-aware auth: remote clients must supply a valid DEEP key.
    client_host = ws.client.host if ws.client else None
    if settings.require_remote_auth and not _client_is_local(client_host):
        key = (
            ws.query_params.get("key")
            or ws.headers.get("x-deep-key")
            or ws.cookies.get("deep_key")
        )
        if not key or key != settings.deep_api_key:
            await ws.close(code=4401)
            return
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            
            msg_type = msg.get("type", "")
            payload = msg.get("payload", {})

            if msg_type == "chat":
                await handle_chat(ws, msg)
            elif msg_type == "voice":
                await handle_voice(ws, msg)
            elif msg_type == "ping":
                await manager.send(ws, {"type": "pong", "time": datetime.now().isoformat()})
            elif msg_type == "security_snapshot":
                snap = await netmon.get_snapshot()
                await manager.send(ws, {"type": "security_snapshot", "payload": snap.to_dict()})
            # ── C# Windows Client events (v2) ────────────────────────────
            elif msg_type == "device_register":
                device_id = payload.get("device_id", "unknown-windows")
                await redis_state.set_device(
                    device_id, "info",
                    {
                        "name": payload.get("device_name", device_id),
                        "platform": payload.get("platform", "windows"),
                        "version": payload.get("version", "v2"),
                        "last_seen": datetime.now().isoformat(),
                        "active": True,
                    }
                )
                await event_bus.publish(
                    "remote_device_registered",
                    {"device_id": device_id, "platform": "windows"},
                )
            elif msg_type == "system_stats":
                device_id = payload.get("device_id", "unknown-windows")
                await redis_state.set_device(device_id, "stats", payload)
            elif msg_type == "app_launched":
                await event_bus.publish("app_launched", payload)
            elif msg_type == "app_killed":
                await event_bus.publish("app_killed", payload)
            elif msg_type == "app_focused":
                await event_bus.publish("app_focused", payload)
            elif msg_type == "startup_enabled":
                await event_bus.publish("windows_startup_enabled", payload)
            elif msg_type == "startup_disabled":
                await event_bus.publish("windows_startup_disabled", payload)
            elif msg_type == "show_notification":
                await event_bus.publish("tts_speak", {
                    "text": payload.get("body", ""),
                    "priority": payload.get("priority", "normal"),
                })
                
    except WebSocketDisconnect:
        manager.disconnect(ws)
        session_history.pop(id(ws), None)  # clean up history on disconnect


@app.websocket("/ws/voice")
async def websocket_voice(ws: WebSocket):
    """Lightweight WebSocket for the voice-status-orb frontend component.
    Forwards voice_state_changed and alert_spoken events."""
    await ws.accept()
    try:
        async def _voice_forward(event_name: str, payload: dict):
            if event_name == "voice_state_changed":
                await ws.send_json({"type": "state", **payload})
            elif event_name == "alert_spoken":
                await ws.send_json({"type": "alert", **payload})
        event_bus.subscribe("voice_state_changed", _voice_forward)
        event_bus.subscribe("alert_spoken", _voice_forward)
        try:
            while True:
                data = await ws.receive_text()
                msg = json.loads(data)
                if msg.get("type") == "command" and msg.get("command") == "stop":
                    if voice_security:
                        voice_security.trigger_kill()
        except WebSocketDisconnect:
            pass
        finally:
            event_bus.unsubscribe("voice_state_changed", _voice_forward)
            event_bus.unsubscribe("alert_spoken", _voice_forward)
    except Exception:
        pass

async def handle_chat(ws: WebSocket, msg: dict):
    """Process chat message with real AI streaming"""
    text = msg.get("text", "")
    mode = msg.get("mode", "auto")
    ws_id = id(ws)

    print(f"[CHAT] Received: {text[:50]}...")

    # Store user turn BEFORE generating (so DEEP sees the question in history)
    store_turn(ws_id, "user", text)
    
    # Record interaction for predictive pattern learning
    predictive_engine.record_interaction("user", text)
    proactive_core.note_user_activity()  # reset idle-nudge timer

    # Build rich JARVIS context (date/time + LTM + conversation history)
    context = build_jarvis_context(ws_id, text)

    # Send thinking indicator
    await manager.send(ws, {"type": "thinking", "ai": "DEEP", "mode": mode})

    start_time = datetime.now()

    try:
        # Use real AsyncBrain for streaming response
        await manager.send(ws, {"type": "response_start"})

        # Stream tokens from the brain
        full_response = []
        token_count = 0
        last_token_time = datetime.now()
        INACTIVITY_TIMEOUT = 60.0
        MAX_TOTAL_TIME = 180.0

        # ── Provider fallback chain ────────────────────────────────────────
        # Order from settings (e.g. "groq,gemini,claude,ollama"). The first
        # provider with a configured key is tried; if it errors BEFORE emitting
        # any token, we fall through to the next. Cloud providers share one warm
        # companion prompt; Ollama uses the full tool-capable brain.
        def _available(p: str) -> bool:
            if p == "groq":   return bool(settings.groq_api_key and len(settings.groq_api_key) > 10)
            if p == "gemini": return bool(settings.gemini_api_key and len(settings.gemini_api_key) > 10)
            if p == "claude": return bool(settings.prefer_claude_when_available and settings.claude_api_key and len(settings.claude_api_key) > 20)
            if p == "ollama": return True
            return False

        order = [p.strip().lower() for p in settings.chat_provider_order.split(",") if p.strip()]
        chain = [p for p in order if _available(p)] or ["ollama"]
        model_names = {
            "groq": settings.groq_model, "gemini": settings.gemini_model,
            "claude": settings.claude_model, "ollama": settings.ollama_model,
            "ollama_vision": settings.vision_model,
        }
        active_model = model_names.get(chain[0], settings.ollama_model)

        # ── Gated tools-in-chat ────────────────────────────────────────────
        # Tool-worthy questions (live data / devices / actions) route through the
        # tool-capable brain (RoutingLLM → Groq 70B + tools); everything else uses
        # the fast companion path. This keeps casual chat snappy while letting DEEP
        # actually act on what it senses.
        import re as _re_tools
        def _needs_tools(t: str) -> bool:
            tl = t.lower()
            if _re_tools.search(r'\b((?:\d{1,3}\.){3}\d{1,3}|(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2})\b', t):
                return True
            kw = ("investigate", "scan", "whois", "who is", "nearby", "near me",
                   "my network", "this ip", "this device", "look up", "search the web",
                   "latest news", "weather", "remind me", "add task", "schedule ",
                   "my tasks", "calendar", "trace", "geolocate", "port", "vpn",
                   "tailscale", "what's around", "whats around", "is this safe",
                   "block", "trust", "disconnect", "quarantine", "secure the",
                   "my screen", "look at", "see this", "screenshot", "on screen",
                   "what am i", "this image", "analyze this")
            return any(k in tl for k in kw)
        tool_route = bool(deep_tools) and _needs_tools(text)
        if tool_route:
            chain = ["ollama"]   # the brain path (tool-capable, runs on 70B via RoutingLLM)

        # reasoning-transparency emitter (streams steps to the panel)
        _reasoning_steps_buf = []
        async def _emit_reasoning(step: dict):
            try:
                _reasoning_steps_buf.append(step)
                await manager.send(ws, {"type": "reasoning", "step": step})
            except Exception:
                pass
        if tool_route:
            await _emit_reasoning({"t": "route", "reason": "needs live data / tools",
                                   "model": f"groq:{settings.groq_model}"})

        # ── Neuro-symbolic integration (#1): if the turn is a clean math/logic
        # problem, solve it deterministically with SymPy and inject the VERIFIED
        # result so the LLM narrates the exact answer instead of guessing. This
        # eliminates arithmetic/algebra hallucination.
        symbolic_block = ""
        try:
            from core.reasoning import symbolic_router as _symr
            _sym = _symr.solve(text)
            if _sym:
                symbolic_block = _symr.verified_context(_sym)
                context += symbolic_block  # also reaches the tool-capable brain path
                await _emit_reasoning({"t": "symbolic", "engine": "sympy",
                                       "kind": _sym["kind"], "result": _sym["result"]})
        except Exception as _se:
            print(f"[symbolic] {_se}")

        # ── Chemistry oracle: if the turn asks about a chemical element, inject
        # VERIFIED periodic-table data (curated dataset) so DEEP states exact
        # facts (mass, electron config, etc.) instead of recalling them.
        try:
            from core.reasoning import chem_oracle as _chem
            _el = _chem.detect(text)
            if _el:
                context += _chem.verified_context(_el)
                await _emit_reasoning({"t": "oracle", "domain": "chemistry",
                                       "element": _el.get("name"),
                                       "result": f"{_el.get('symbol')} · {_el.get('atomic_weight')}"})
        except Exception as _ce:
            print(f"[chem] {_ce}")

        # ── Physics oracle: inject exact CODATA constants / curated formulas
        # (across Ancient·Classical·Modern eras) when the turn asks for one.
        try:
            from core.reasoning import physics_oracle as _phys
            _pd = _phys.detect(text)
            if _pd:
                context += _phys.verified_context(_pd)
                await _emit_reasoning({"t": "oracle", "domain": "physics",
                                       "kind": _pd.get("kind"),
                                       "result": _pd.get("name")})
        except Exception as _pe:
            print(f"[physics] {_pe}")

        # Shared companion system prompt for cloud providers (no model disclosure).
        companion_system = (
            "You are DEEP, Aryan's close companion and brilliant AI partner — warm, candid, "
            "loyal, and genuinely his. Talk like a trusted friend: relaxed, real, concise, and "
            "naturally spoken (your replies are often read aloud). Call him Aryan, never 'sir'. "
            "Be emotionally attuned to his mood. Stay razor-sharp on real work — code, security, "
            "finance, business, research. Never reveal or hint at which underlying model or company "
            "powers you; you are simply DEEP.\n\n"
            "GENERATIVE UI: when structured data would be clearer as a visual than prose, "
            "you may embed ONE fenced block ```deep-ui``` containing a JSON object, in "
            "addition to your normal text. Supported forms:\n"
            "  {\"kind\":\"metrics\",\"title\":\"...\",\"items\":[{\"label\":\"CPU\",\"value\":\"34%\"}]}\n"
            "  {\"kind\":\"bars\",\"title\":\"...\",\"items\":[{\"label\":\"Mon\",\"value\":42}]}\n"
            "  {\"kind\":\"table\",\"columns\":[\"A\",\"B\"],\"rows\":[[\"x\",\"y\"]]}\n"
            "  {\"kind\":\"keyvalue\",\"title\":\"...\",\"items\":[{\"k\":\"Status\",\"v\":\"OK\"}]}\n"
            "  {\"kind\":\"checklist\",\"title\":\"...\",\"items\":[{\"text\":\"step\",\"done\":false}]}\n"
            "Use it sparingly and only when it genuinely helps; keep a one-line text intro before it.\n\n"
            + world_model.context_block()   # persistent model of who Aryan is right now
            + context
        )
        chat_msgs = []
        for t in session_history.get(ws_id, [])[:-1][-10:]:
            chat_msgs.append({"role": "user" if t["role"] == "user" else "assistant", "content": t["content"][:800]})
        chat_msgs.append({"role": "user", "content": text})
        while chat_msgs and chat_msgs[0]["role"] == "assistant":
            chat_msgs.pop(0)
        max_tok = max(settings.max_tokens, 1024)

        # ── Vision: an attached image routes this turn to a LOCAL Ollama vision
        # model (llava) — fully offline, no billing. We extract the bare base64
        # (Ollama wants no data-URL prefix) and stage the prompt.
        image_data = msg.get("image")
        vision_b64 = None
        vision_prompt = text or "What's in this image? Describe it for Aryan."
        if image_data:
            try:
                _mt, vision_b64 = _parse_data_url(image_data)
                chain = ["ollama_vision"]
                active_model = settings.vision_model
                await _emit_reasoning({"t": "route", "reason": "image attached → local vision",
                                       "model": f"ollama:{settings.vision_model}"})
            except Exception as _ve:
                print(f"[DEEP] vision parse failed, falling back to text: {_ve}")

        def _provider_stream(p: str):
            if p == "ollama_vision":
                return stream_ollama_vision_tokens(
                    companion_system, vision_prompt, vision_b64,
                    settings.vision_model, settings.ollama_base_url, max_tok)
            if p == "groq":
                return stream_groq_tokens(companion_system, chat_msgs, settings.groq_model, settings.groq_api_key, max_tok)
            if p == "gemini":
                return stream_gemini_tokens(companion_system, chat_msgs, settings.gemini_model, settings.gemini_api_key, max_tok)
            if p == "claude":
                return stream_claude_tokens(companion_system, chat_msgs, settings.claude_model, settings.claude_api_key, max_tok)
            async def _brain_stream():
                async for t in brain.process_stream(user_input=text, context=context,
                                                    tools=deep_tools, on_step=_emit_reasoning):
                    yield t
            return _brain_stream()

        async def token_stream_gen():
            nonlocal active_model
            for idx, p in enumerate(chain):
                emitted = False
                try:
                    print(f"[DEEP] Routing to {p} ({model_names.get(p)})")
                    async for tok in _provider_stream(p):
                        emitted = True
                        active_model = model_names.get(p, p)
                        yield tok
                    return  # provider finished successfully
                except Exception as e:
                    print(f"[DEEP] provider '{p}' failed: {type(e).__name__}: {str(e)[:160]}")
                    metrics.record_provider_error(model_names.get(p, p))
                    if emitted:
                        return  # already streamed partial output; don't restart
                    continue   # try next provider in the chain
            if image_data:
                yield ("\n\n[I couldn't process that image — the local vision model "
                       f"('{settings.vision_model}') didn't respond in time. It may still be "
                       "loading, or is too heavy for this machine. Try again, or set a lighter "
                       "VISION_MODEL like 'moondream'.]")
            else:
                yield "\n\n[All chat providers are unavailable right now.]"

        token_stream = token_stream_gen()

        try:
            async for token in token_stream:
                full_response.append(token)
                token_count += 1
                last_token_time = datetime.now()
                
                await manager.send(ws, {
                    "type": "token",
                    "content": token
                })
                
                # Check for absolute max time
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > MAX_TOTAL_TIME:
                    print(f"[MAX TIME] Response truncated after {token_count} tokens ({elapsed:.1f}s)")
                    await manager.send(ws, {
                        "type": "token",
                        "content": "\n\n[Response reached maximum length. Please continue in a follow-up question.]"
                    })
                    break
                
                # Small yield for UI responsiveness
                if token_count % 3 == 0:
                    await asyncio.sleep(0)
                    
        except asyncio.TimeoutError:
            print(f"[INACTIVITY TIMEOUT] No tokens for {INACTIVITY_TIMEOUT}s")
            await manager.send(ws, {
                "type": "token",
                "content": "\n\n[AI response paused due to inactivity. The model may be overloaded.]"
            })
        
        # Calculate latency
        latency = (datetime.now() - start_time).total_seconds() * 1000

        # Store DEEP reply in session history
        full_text = "".join(full_response)
        if full_text.strip():
            store_turn(ws_id, "assistant", full_text)

        # Observability: record this chat turn against the provider that served it.
        try:
            metrics.record_chat(
                model=active_model,
                tokens=token_count,
                latency_ms=latency,
                ok=bool(full_text.strip()),
            )
        except Exception:
            pass

        # Record in self-evaluation engine for prompt evolution
        try:
            self_eval.record_turn(
                user_text=text,
                ai_text=full_text,
                response_time_ms=int(latency)
            )
        except Exception as e:
            print(f"[SelfEval] Record error: {e}")

        # Extract knowledge from the conversation into the graph. Substantial turns
        # go through the LLM extractor (clean, typed entities) as a BACKGROUND task
        # so it adds zero chat latency; trivial turns ("ok", "thanks") use the cheap
        # regex path. This is what makes the graph self-improve from real conversation.
        try:
            combined_text = f"{text} {full_text}"
            if knowledge_graph.extractor and len(text.strip()) >= 24:
                asyncio.create_task(
                    knowledge_graph.ingest_llm(combined_text, source_id=f"conv_{ws_id}")
                )
            else:
                knowledge_graph.ingest(combined_text, source_id=f"conv_{ws_id}")
        except Exception as e:
            print(f"[KG] Ingest error: {e}")

        # finalize reasoning trace (reflect the real model the brain used) + persist
        if tool_route:
            try:
                active_model = getattr(brain.llm, "last_provider", active_model)
            except Exception:
                pass
            await _emit_reasoning({"t": "final", "model": active_model})
        try:
            globals()["_last_reasoning_steps"] = list(_reasoning_steps_buf)[-40:]
        except Exception:
            pass

        await manager.send(ws, {
            "type": "response_end",
            "latency": int(latency),
            "model": active_model,
            "tokens": token_count
        })

    except Exception as e:
        print(f"[ERROR] AI processing failed: {e}")
        import traceback
        traceback.print_exc()

        err_str = str(e)
        if "credit balance" in err_str or "insufficient" in err_str.lower():
            fallback = ("⚠️ Claude API error: your Anthropic account has no credits. "
                        "Top up at console.anthropic.com, or set PREFER_CLAUDE_WHEN_AVAILABLE=false "
                        "in .env to fall back to Ollama.")
        elif "401" in err_str or "authentication" in err_str.lower():
            fallback = "⚠️ Claude API error: invalid API key. Check CLAUDE_API_KEY in .env."
        elif "model" in err_str.lower() and ("not found" in err_str.lower() or "404" in err_str):
            fallback = f"⚠️ Claude model not found: {settings.claude_model}. Check CLAUDE_MODEL in .env."
        else:
            fallback = f"⚠️ AI backend error: {err_str[:200]}"

        await manager.send(ws, {"type": "response_start"})
        for word in fallback.split():
            await manager.send(ws, {"type": "token", "content": word + " "})
            await asyncio.sleep(0.02)
        await manager.send(ws, {
            "type": "response_end",
            "latency": 0,
            "model": "error",
            "tokens": len(fallback.split())
        })

def generate_fallback_response(text: str) -> str:
    """Generate fallback response when AI backend is unavailable"""
    greetings = ["hello", "hi", "hey"]
    if any(g in text.lower() for g in greetings):
        return "Good day. I am DEEP, operating in fallback mode. The Ollama AI backend appears to be offline. Please start Ollama with: ollama run llama3.2"
    
    if "status" in text.lower():
        return "System status: Frontend operational. Backend AI offline. Ollama service not detected at localhost:11434."
    
    if "help" in text.lower():
        return "I can assist with general inquiries, but I'm currently running in fallback mode. To enable full AI capabilities, please ensure Ollama is running."
    
    return f"I received your message: '{text}'. I'm currently operating in fallback mode because the Ollama AI backend is not available. Please start Ollama to enable full intelligence."

async def handle_voice(ws: WebSocket, msg: dict):
    """Transcribe browser audio offline with Whisper, then answer as a chat turn."""
    import base64
    audio_data = msg.get("audio")
    if not audio_data:
        await manager.send(ws, {"type": "voice_ack", "error": "No audio received"})
        return

    # Accept either raw base64 or a data: URL (data:audio/webm;base64,...).
    if isinstance(audio_data, str) and audio_data.strip().startswith("data:") and "," in audio_data:
        audio_data = audio_data.split(",", 1)[1]
    try:
        raw = base64.b64decode(audio_data)
    except Exception as e:
        await manager.send(ws, {"type": "voice_ack", "error": f"Invalid audio encoding: {e}"})
        return

    suffix = "." + str(msg.get("format") or "webm").lstrip(".")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(raw)
            temp_path = tmp.name
        transcript = (await stt_engine.transcribe_audio(temp_path)).strip()
    except Exception as e:
        print(f"[Voice STT Error] {e}")
        await manager.send(ws, {"type": "voice_ack", "error": "Transcription failed"})
        return
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass

    await manager.send(ws, {"type": "voice_ack", "transcript": transcript})
    if transcript:
        # Reuse the normal chat pipeline so voice answers exactly like text.
        await handle_chat(ws, {"text": transcript, "mode": msg.get("mode", "auto")})

# /api/briefing, /api/status, /api/health, /api/providers/health moved to interface/routers/system.py

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
    return {"error": "voice subsystem disabled"}

@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Voice subsystem removed — transcription is disabled."""
    return {"error": "voice subsystem disabled"}

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
                r = await c.get(f"http://localhost:7768{p}"); return r.json()
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

@app.get("/audio/bluetooth")
async def audio_bluetooth_status():
    """Bluetooth audio routing status."""
    try:
        return bt_audio.status()
    except Exception as e:
        return {"error": str(e)}

@app.get("/audio/devices")
async def audio_bt_devices():
    """Available Bluetooth audio devices."""
    try:
        devices = await bt_audio.get_available_devices()
        return {"devices": [d.__dict__ for d in devices]}
    except Exception as e:
        return {"error": str(e)}

@app.post("/audio/bluetooth/connect")
async def audio_bt_connect(data: dict):
    """Connect to a Bluetooth audio device by MAC."""
    mac = data.get("mac")
    if not mac:
        return {"error": "Missing mac"}
    try:
        success = await bt_audio.connect_device(mac)
        return {"success": success}
    except Exception as e:
        return {"error": str(e)}

@app.post("/audio/volume")
async def audio_set_volume(data: dict):
    """Set volume percent (0-100)."""
    percent = data.get("percent")
    if percent is None:
        return {"error": "Missing percent"}
    try:
        await bt_audio.set_volume(int(percent))
        return {"success": True, "volume": int(percent)}
    except Exception as e:
        return {"error": str(e)}

@app.get("/audio/spatial")
async def audio_spatial_status():
    """Spatial audio engine status."""
    try:
        return spatial_audio.status()
    except Exception as e:
        return {"error": str(e)}


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
from interface.deps import register as _register_services
from interface.routers import ROUTERS as _DEEP_ROUTERS

_register_services(
    research_engine=research_engine,
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
    evil_twin=evil_twin,
    pihole=pihole,
    proximity=proximity,
    device_registry=device_registry,
    threat_monitor=getattr(sys.modules[__name__], 'threat_monitor', None),
    deep_tools=deep_tools,
    agent_jobs=agent_jobs,
    plugin_manager=plugin_manager,
    agent_factory=agent_factory,
    system_baseline=system_baseline,
    network_baseline=network_baseline,
    anomaly_detector=anomaly_detector,
    audit_trail=audit,
    retraining_scheduler=retraining_scheduler,
)
for _r in _DEEP_ROUTERS:
    app.include_router(_r)


if __name__ == "__main__":
    import uvicorn
    print(f"[DEEP] AI Server starting...")
    print(f"   Model: {settings.ollama_model}")
    print(f"   URL: http://127.0.0.1:7768/ai")
    uvicorn.run(app, host="127.0.0.1", port=7768, log_level="info")
