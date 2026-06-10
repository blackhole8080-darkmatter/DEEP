"""
config.py

Central configuration for DEEP.

- Reads environment variables from `.env` (via python-dotenv).
- Exposes a single `Settings` dataclass used by all modules.
- Keeps Claude (online) optional: if CLAUDE_API_KEY is missing, the system
  will still work fully offline using Ollama.
"""

from __future__ import annotations

import os
import socket
import sys
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv


# Load environment variables from .env if present.
# This is safe to call even if .env doesn't exist.
load_dotenv()


def _get_env(name: str, default: str) -> str:
    """Read a required-ish environment variable with a fallback default."""
    value = os.getenv(name)
    return value if value is not None and value != "" else default


def _get_env_opt(name: str) -> Optional[str]:
    """Read an optional environment variable (returns None if missing/empty)."""
    value = os.getenv(name)
    return value if value is not None and value != "" else None


@dataclass(frozen=True, slots=True)
class Settings:
    """
    Settings for DEEP.

    Keep defaults conservative so DEEP works out-of-the-box for local/offline mode.
    """

    # ----------------------------
    # LLMs / inference providers (Multi-LLM Support)
    # ----------------------------
    ollama_base_url: str = _get_env("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = _get_env("OLLAMA_MODEL", "llama3.2")

    # OpenAI (GPT-4, GPT-3.5)
    openai_api_key: Optional[str] = _get_env_opt("OPENAI_API_KEY")
    openai_model: str = _get_env("OPENAI_MODEL", "gpt-4")

    # Claude (Anthropic) — accept either CLAUDE_API_KEY or the standard ANTHROPIC_API_KEY
    claude_api_key: Optional[str] = _get_env_opt("CLAUDE_API_KEY") or _get_env_opt("ANTHROPIC_API_KEY")
    claude_model: str = _get_env("CLAUDE_MODEL", "claude-3-5-sonnet-latest")

    # Gemini (Google) — free tier at aistudio.google.com
    gemini_api_key: Optional[str] = _get_env_opt("GEMINI_API_KEY")
    gemini_model: str = _get_env("GEMINI_MODEL", "gemini-2.0-flash")

    # Groq — free tier at console.groq.com (OpenAI-compatible, very fast)
    groq_api_key: Optional[str] = _get_env_opt("GROQ_API_KEY")
    groq_model: str = _get_env("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Interactive chat provider fallback chain (first configured one wins, then
    # falls through on error). Comma-separated: groq, gemini, claude, ollama.
    chat_provider_order: str = _get_env("CHAT_PROVIDER_ORDER", "groq,gemini,claude,ollama")

    # Smart routing: auto-select best model for task
    smart_llm_routing: bool = _get_env("SMART_LLM_ROUTING", "true").strip().lower() in {"1", "true", "yes", "y"}

    # When true, try Claude first if configured; otherwise fall back to Ollama.
    prefer_claude_when_available: bool = (
        _get_env("PREFER_CLAUDE_WHEN_AVAILABLE", "false").strip().lower() in {"1", "true", "yes", "y"}
    )

    # Basic generation controls (you can tweak later).
    temperature: float = float(_get_env("TEMPERATURE", "0.2"))
    max_tokens: int = int(_get_env("MAX_TOKENS", "512"))

    # Chat token budgets. Simple turns stay tight (fast, cheap); complex turns
    # (code, analysis, long reasoning) get a much larger ceiling so the strong
    # 70B model isn't truncated mid-answer. RoutingLLM no longer hard-caps at 1024.
    # Local vision model (Ollama) for image inputs — fully offline, no billing.
    # Cloud vision (Claude/Gemini) is used only if explicitly preferred + keyed.
    vision_model: str = _get_env("VISION_MODEL", "moondream")
    chat_max_tokens: int = int(_get_env("CHAT_MAX_TOKENS", "1536"))
    chat_max_tokens_complex: int = int(_get_env("CHAT_MAX_TOKENS_COMPLEX", "4096"))
    # Per-provider retry on transient failures (timeouts / 429 / 5xx) before
    # falling through to the next provider in the chain.
    llm_retry_attempts: int = int(_get_env("LLM_RETRY_ATTEMPTS", "1"))
    llm_retry_backoff_s: float = float(_get_env("LLM_RETRY_BACKOFF_S", "0.8"))

    # ----------------------------
    # Persistent memory (ChromaDB)
    # ----------------------------
    chroma_dir: str = _get_env("CHROMA_DIR", "data/chroma")
    chroma_collection: str = _get_env("CHROMA_COLLECTION", "deep_memory")

    # How much context to pull from RAG (rough heuristic for starter).
    rag_top_k: int = int(_get_env("RAG_TOP_K", "4"))

    # ----------------------------
    # Voice (Whisper STT + Premium TTS)
    # ----------------------------
    whisper_model: str = _get_env("WHISPER_MODEL", "base")

    # Recording duration for a simple starter implementation (seconds).
    # For more advanced wake-word/streaming later.
    voice_listen_seconds: int = int(_get_env("VOICE_LISTEN_SECONDS", "5"))

    # Speech output settings (legacy pyttsx3).
    tts_rate: int = int(_get_env("TTS_RATE", "175"))
    tts_volume: float = float(_get_env("TTS_VOLUME", "1.0"))
    tts_voice_name: Optional[str] = _get_env_opt("TTS_VOICE_NAME")

    # --- ElevenLabs Premium TTS ---
    elevenlabs_api_key: Optional[str] = _get_env_opt("ELEVENLABS_API_KEY")
    elevenlabs_voice: str = _get_env("ELEVENLABS_VOICE", "jarvis")  # requires paid plan for full API access
    elevenlabs_stability: float = float(_get_env("ELEVENLABS_STABILITY", "0.5"))
    elevenlabs_similarity_boost: float = float(_get_env("ELEVENLABS_SIMILARITY_BOOST", "0.75"))

    # --- Edge TTS (Free neural fallback) ---
    edge_tts_voice: str = _get_env("EDGE_TTS_VOICE", "en-US-GuyNeural")
    edge_tts_rate: str = _get_env("EDGE_TTS_RATE", "+0%")  # -50% to +100%

    # Voice personality mode
    voice_personality: str = _get_env("VOICE_PERSONALITY", "jarvis")  # jarvis, friday, professional, casual
    voice_sound_effects: bool = _get_env("VOICE_SOUND_EFFECTS", "true").strip().lower() in {"1", "true", "yes", "y"}

    # ----------------------------
    # System / tools
    # ----------------------------
    # If you want to restrict dangerous commands, implement allow-lists later.
    enable_system_tools: bool = (
        _get_env("ENABLE_SYSTEM_TOOLS", "true").strip().lower() in {"1", "true", "yes", "y"}
    )

    # ----------------------------
    # Security & Cybersecurity
    # ----------------------------
    deep_password: str = _get_env("DEEP_PASSWORD", "deep2026")
    deep_api_key: str = _get_env("DEEP_API_KEY", "nx-default-key")
    deep_secret_key: str = _get_env("DEEP_SECRET_KEY", "deep-super-secret-12345")
    cyber_scan_timeout: int = int(_get_env("CYBER_SCAN_TIMEOUT", "15"))

    # ----------------------------
    # Web server hardening (v3)
    # ----------------------------
    # Loopback (127.0.0.1) requests are always trusted so the local browser UI
    # stays frictionless. Non-loopback requests (LAN / Tailscale remote access)
    # must present a valid DEEP_API_KEY when this is enabled.
    require_remote_auth: bool = (
        _get_env("DEEP_REQUIRE_REMOTE_AUTH", "true").strip().lower() in {"1", "true", "yes", "y"}
    )
    # Comma-separated CORS allowlist. "*" allows any origin (no credentials).
    cors_allow_origins: str = _get_env("DEEP_CORS_ORIGINS", "*")
    # Sliding-window per-client request cap. 0 disables rate limiting.
    rate_limit_per_min: int = int(_get_env("DEEP_RATE_LIMIT_PER_MIN", "240"))

    # ----------------------------
    # Integrations
    # ----------------------------
    brave_api_key: Optional[str] = _get_env_opt("BRAVE_API_KEY")
    home_assistant_token: Optional[str] = _get_env_opt("HOME_ASSISTANT_TOKEN")
    home_assistant_url: str = _get_env("HOME_ASSISTANT_URL", "http://homeassistant.local:8123")

    # ----------------------------
    # Offline mode (strict)
    # ----------------------------
    # When enabled: use Ollama-only + local memory; disable Claude and outbound features.
    offline_mode: bool = _get_env("DEEP_OFFLINE", "false").strip().lower() in {"1", "true", "yes", "y"}

    # ----------------------------
    # AI Neural Network Layer
    # ----------------------------
    # Pattern memory SQLite database
    pattern_memory_db_path: str = _get_env("PATTERN_MEMORY_DB_PATH", "data/pattern_memory.db")

    # Intent classification model persistence
    intent_model_path: str = _get_env("INTENT_MODEL_PATH", "data/intent_model.pkl")
    intent_max_features: int = int(_get_env("INTENT_MAX_FEATURES", "500"))

    # Intent categories for the classifier (must match Pipeline SEED_DATA keys)
    intent_categories: tuple[str, ...] = (
        "system_control", "information_query", "creative_task",
        "conversation", "network_action", "research_task",
        "planning_task", "multi_step_execution",
    )

    # ── Intent retraining pipeline ─────────────────────────────────────────
    retrain_interval_days: int = int(_get_env("RETRAIN_INTERVAL_DAYS", "7"))
    retrain_time: str = _get_env("RETRAIN_TIME", "03:00")
    retrain_sample_trigger: int = int(_get_env("RETRAIN_SAMPLE_TRIGGER", "200"))
    min_training_samples: int = int(_get_env("MIN_TRAINING_SAMPLES", "50"))
    min_accuracy_improvement: float = float(_get_env("MIN_ACCURACY_IMPROVEMENT", "0.02"))
    retrain_log_dir: str = _get_env("RETRAIN_LOG_DIR", "logs/retraining")

    # Skill routing table: intent -> module name
    skill_routes: dict[str, str] = field(default_factory=lambda: {
        "system_control": "skills.system_control",
        "information_query": "skills.information_query",
        "creative_task": "skills.creative_task",
        "conversation": "skills.conversation",
        "network_action": "skills.network_action",
        "research_task": "skills.research_task",
        "planning_task": "skills.planning_task",
        "multi_step_execution": "skills.multi_step_execution",
    })

    # Pipeline confidence threshold for direct skill routing vs LangGraph escalation
    pipeline_confidence_threshold: float = float(_get_env("PIPELINE_CONFIDENCE_THRESHOLD", "0.65"))

    # Minimum quality score before LLM reasoning is retried
    min_quality_score: float = float(_get_env("MIN_QUALITY_SCORE", "0.50"))

    # Tool invocation timeout (seconds)
    tool_timeout_seconds: int = int(_get_env("TOOL_TIMEOUT_SECONDS", "10"))

    # Swarm agent timeout and concurrency limits
    swarm_agent_timeout_seconds: int = int(_get_env("SWARM_AGENT_TIMEOUT_SECONDS", "30"))
    swarm_max_parallel: int = int(_get_env("SWARM_MAX_PARALLEL", "4"))

    # User-facing assistant name (persona). Internal class/module names stay "Deep*".
    assistant_name: str = _get_env("ASSISTANT_NAME", "Deep")

    # System prompt injected into every LangGraph LLM call
    deep_system_prompt: str = _get_env(
        "DEEP_SYSTEM_PROMPT",
        (
            "You are Deep, an intelligent personal AI assistant built for Aryan. "
            "You are helpful, accurate, and concise, with a dry, understated wit. "
            "You are proactive: surface what matters before being asked. "
            "You have access to tools via [TOOL:skill_name:params] markers."
        ),
    )

    # OpenAI API key (used as LLM fallback in GraphOrchestrator)
    openai_api_key: Optional[str] = _get_env_opt("OPENAI_API_KEY")

    # ----------------------------
    # Knowledge Intelligence Layer
    # ----------------------------
    # ChromaDB path for the knowledge store
    knowledge_db_path: str = _get_env("KNOWLEDGE_DB_PATH", "data/chroma_research")

    # Ingestion schedule and sources
    ingest_interval_hours: int = int(_get_env("INGEST_INTERVAL_HOURS", "6"))
    ingest_domains: tuple[str, ...] = (
        "ai_ml", "physics", "cybersecurity", "space", "robotics", "quantum",
    )
    ingest_sources: dict[str, Any] = field(default_factory=lambda: {
        "arxiv": {
            "enabled": True,
            "feeds": [
                "https://arxiv.org/rss/cs.AI",
                "https://arxiv.org/rss/cs.LG",
                "https://arxiv.org/rss/cs.RO",
                "https://arxiv.org/rss/cs.CR",
                "https://arxiv.org/rss/physics",
                "https://arxiv.org/rss/quant-ph",
                "https://arxiv.org/rss/math",
                "https://arxiv.org/rss/astro-ph",
            ],
        },
        "pubmed": {
            "enabled": True,
            "queries": [
                "neural interface",
                "CRISPR 2024",
                "quantum computing",
                "protein structure prediction",
            ],
        },
        "nvd": {"enabled": True},
        "nasa_ads": {
            "enabled": False,  # requires API key
            "queries": ["star formation"],
        },
    })

    # PubMed default query terms
    pubmed_queries: tuple[str, ...] = (
        "neural interface", "CRISPR 2024", "quantum computing",
        "protein structure prediction",
    )

    # NASA ADS API key (optional)
    nasa_ads_key: Optional[str] = _get_env_opt("NASA_ADS_KEY")

    # Breakthrough detection
    high_signal_words: tuple[str, ...] = (
        "first demonstration", "surpasses human", "world record",
        "breakthrough", "novel approach", "outperforms",
        "state-of-the-art", "exceeds", "first ever", "previously impossible",
    )
    high_impact_sources: tuple[str, ...] = (
        "Nature", "Science", "Cell", "NeurIPS", "ICML", "ICLR",
        "CVPR", "ACL", "IEEE", "PNAS", "Physical Review Letters", "The Lancet",
    )
    breakthrough_threshold: float = float(_get_env("BREAKTHROUGH_THRESHOLD", "0.72"))

    # Briefing schedule
    briefing_time: str = _get_env("BRIEFING_TIME", "06:00")

    # Concept explanation depth prompts
    # ----------------------------
    # Voice Hardware Layer
    # ----------------------------
    # Wake word detection
    wake_word_model: str = _get_env("WAKE_WORD_MODEL", "deep_custom")
    wake_word_threshold: float = float(_get_env("WAKE_WORD_THRESHOLD", "0.5"))
    voice_verifier_threshold: float = float(_get_env("VOICE_VERIFIER_THRESHOLD", "0.6"))
    wake_word_training_dir: str = _get_env("WAKE_WORD_TRAINING_DIR", "voice/training/samples")
    wake_word_model_dir: str = _get_env("WAKE_WORD_MODEL_DIR", "voice/models")

    # Whisper STT
    whisper_model: str = _get_env("WHISPER_MODEL", "base")
    silence_threshold: int = int(_get_env("SILENCE_THRESHOLD", "300"))
    silence_duration_ms: int = int(_get_env("SILENCE_DURATION_MS", "1000"))
    max_command_duration_s: float = float(_get_env("MAX_COMMAND_DURATION_S", "10.0"))

    # Piper TTS
    piper_model_path: str = _get_env(
        "PIPER_MODEL_PATH", "voice/models/en_US-lessac-medium.onnx"
    )
    tts_speaking_rate: float = float(_get_env("TTS_SPEAKING_RATE", "1.0"))
    tts_sentence_silence: float = float(_get_env("TTS_SENTENCE_SILENCE", "0.05"))

    # Audio I/O
    audio_input_device: Optional[str] = _get_env_opt("AUDIO_INPUT_DEVICE")
    audio_output_device: Optional[str] = _get_env_opt("AUDIO_OUTPUT_DEVICE")

    # ----------------------------
    # Tailscale VPN (v2)
    # ----------------------------
    tailscale_bin_path: str = _get_env(
        "TAILSCALE_BIN_PATH",
        "C:/Program Files/Tailscale/tailscale.exe" if sys.platform == "win32" else "/usr/bin/tailscale",
    )
    tailscale_poll_interval_s: int = int(_get_env("TAILSCALE_POLL_INTERVAL_S", "30"))

    # ----------------------------
    # Redis shared state (v2)
    # ----------------------------
    redis_url: str = _get_env("REDIS_URL", "redis://localhost:6379")
    redis_sync_interval_s: int = int(_get_env("REDIS_SYNC_INTERVAL_S", "5"))

    # ----------------------------
    # Device identity (v2)
    # ----------------------------
    deep_device_id: str = _get_env("DEEP_DEVICE_ID", socket.gethostname())
    deep_device_name: str = _get_env("DEEP_DEVICE_NAME", socket.gethostname())
    deep_instance_id: str = _get_env("DEEP_INSTANCE_ID", "deep-main")
    conversation_history_max: int = int(_get_env("CONVERSATION_HISTORY_MAX", "20"))

    # ----------------------------
    # Network scanning & security (v2)
    # ----------------------------
    network_cidr: str = _get_env("NETWORK_CIDR", "192.168.1.0/24")
    known_devices: dict[str, str] = field(default_factory=dict)
    scan_interval_s: int = int(_get_env("SCAN_INTERVAL_S", "60"))
    deep_scan_interval_s: int = int(_get_env("DEEP_SCAN_INTERVAL_S", "300"))
    monitor_interface: str | None = _get_env_opt("MONITOR_INTERFACE")
    port_scan_threshold: int = int(_get_env("PORT_SCAN_THRESHOLD", "15"))
    port_scan_window_s: int = int(_get_env("PORT_SCAN_WINDOW_S", "10"))
    deauth_threshold: int = int(_get_env("DEAUTH_THRESHOLD", "5"))
    home_ssid: str = _get_env("HOME_SSID", "")
    home_bssid: str = _get_env("HOME_BSSID", "")
    pihole_url: str = _get_env("PIHOLE_URL", "http://pi.hole")
    pihole_api_token: str = _get_env("PIHOLE_API_TOKEN", "")
    pihole_poll_interval_s: int = int(_get_env("PIHOLE_POLL_INTERVAL_S", "30"))
    wifi_scan_interval_s: int = int(_get_env("WIFI_SCAN_INTERVAL_S", "120"))
    suspicious_domain_patterns: tuple[str, ...] = (
        "malware", "botnet", "c2", "command-and-control",
        "tor-exit", "cryptominer", "phishing",
    )

    # ----------------------------
    # Passive proximity monitor (v2)
    # ----------------------------
    known_bt_devices: dict[str, str] = field(default_factory=dict)
    proximity_signal_threshold: int = int(_get_env("PROXIMITY_SIGNAL_THRESHOLD", "-80"))
    persistence_threshold: int = int(_get_env("PERSISTENCE_THRESHOLD", "5"))
    bt_close_threshold: int = int(_get_env("BT_CLOSE_THRESHOLD", "-60"))
    bt_absence_alert_minutes: int = int(_get_env("BT_ABSENCE_ALERT_MINUTES", "60"))
    pattern_analysis_interval_s: int = int(_get_env("PATTERN_ANALYSIS_INTERVAL_S", "300"))
    night_hours: tuple[int, ...] = (23, 0, 1, 2, 3, 4)
    cluster_threshold: int = int(_get_env("CLUSTER_THRESHOLD", "8"))
    wifi_proximity_scan_s: int = int(_get_env("WIFI_PROXIMITY_SCAN_S", "60"))
    bt_proximity_scan_s: int = int(_get_env("BT_PROXIMITY_SCAN_S", "45"))

    # ----------------------------
    # Bluetooth private ear & spatial audio (v2)
    # ----------------------------
    preferred_bt_audio_devices: list[str] = field(default_factory=list)
    bt_audio_poll_s: int = int(_get_env("BT_AUDIO_POLL_S", "15"))
    spatial_audio_enabled: bool = _get_env("SPATIAL_AUDIO_ENABLED", "true").strip().lower() in {"1", "true", "yes", "y"}
    spatial_event_pan_map: dict[str, float] = field(default_factory=lambda: {
        "security_alert": 1.0,
        "unknown_device_detected": 1.0,
        "threat_detected": 1.0,
        "breakthrough_detected": -1.0,
        "briefing_ready": 0.0,
        "system_stats": -1.0,
        "tts_speak": 0.0,
        "deep_response": 0.0,
    })

    # ----------------------------
    # Immutable audit trail (v2)
    # ----------------------------
    audit_db_path: str = _get_env("AUDIT_DB_PATH", "logs/audit/deep_audit.db")
    audit_integrity_check_interval_s: int = int(_get_env("AUDIT_INTEGRITY_CHECK_INTERVAL_S", "3600"))
    audit_export_dir: str = _get_env("AUDIT_EXPORT_DIR", "logs/sessions")

    # ----------------------------
    # Explanation depth prompts (knowledge layer)
    # ----------------------------
    explanation_depth_prompts: dict[str, str] = field(default_factory=lambda: {
        "accessible": (
            "Explain clearly for a curious non-specialist. Use analogies."
        ),
        "undergraduate": (
            "Assume solid physics/math background. Define jargon."
        ),
        "graduate": (
            "Assume graduate-level knowledge. Use precise terminology. "
            "Mention current open questions."
        ),
        "research": (
            "Assume active researcher. Be rigorous. Cite specific results "
            "from the provided papers. Discuss what remains unsolved."
        ),
    })

    # ----------------------------
    # Anomaly detection (v3)
    # ----------------------------
    anomaly_db_path: str = _get_env("ANOMALY_DB_PATH", "logs/anomaly/deep_anomaly.db")
    anomaly_model_path: str = _get_env("ANOMALY_MODEL_PATH", "ai/models/anomaly_models.pkl")
    baseline_sample_interval_s: int = int(_get_env("BASELINE_SAMPLE_INTERVAL_S", "30"))
    baseline_history_days: int = int(_get_env("BASELINE_HISTORY_DAYS", "30"))
    min_baseline_samples: int = int(_get_env("MIN_BASELINE_SAMPLES", "10"))
    anomaly_contamination: float = float(_get_env("ANOMALY_CONTAMINATION", "0.05"))
    anomaly_z_threshold: float = float(_get_env("ANOMALY_Z_THRESHOLD", "3.0"))
    anomaly_check_interval_s: int = int(_get_env("ANOMALY_CHECK_INTERVAL_S", "60"))
    anomaly_model_refresh_days: int = int(_get_env("ANOMALY_MODEL_REFRESH_DAYS", "7"))

    # ----------------------------
    # Threat classifier neural net (v3)
    # ----------------------------
    threat_model_path: str = _get_env("THREAT_MODEL_PATH", "ai/models/threat_classifier.pt")
    threat_scaler_path: str = _get_env("THREAT_SCALER_PATH", "ai/models/threat_scaler.pkl")
    threat_retrain_interval_days: int = int(_get_env("THREAT_RETRAIN_INTERVAL_DAYS", "7"))
    threat_confidence_threshold: float = float(_get_env("THREAT_CONFIDENCE_THRESHOLD", "0.7"))
    threat_model_epochs: int = int(_get_env("THREAT_MODEL_EPOCHS", "50"))
    min_threat_samples: int = int(_get_env("MIN_THREAT_SAMPLES", "50"))
    synthetic_samples_per_class: int = int(_get_env("SYNTHETIC_SAMPLES_PER_CLASS", "100"))
