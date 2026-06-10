# deep/config.py — DEEP Engineering Bible Configuration (Section 2)
import os, pathlib

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ── IDENTITY ─────────────────────────────────────────────────────────────
DEEP_NAME        = 'DEEP'
CREATOR_NAME      = 'Aryan'
ADDRESS_AS        = 'sir'
BOOT_MESSAGE      = 'DEEP online. All 16 intelligence domains active. Ready, sir.'
SHUTDOWN_MESSAGE  = 'Shutting down, sir. Saving memory state.'

# ── PATHS ────────────────────────────────────────────────────────────────
BASE_DIR          = pathlib.Path.home() / 'deep_output'
PLOTS_DIR         = BASE_DIR / 'plots'
ANIM_DIR          = BASE_DIR / 'animations'
MANIM_DIR         = BASE_DIR / 'manim'
REPORTS_DIR       = BASE_DIR / 'reports'
MODELS_DIR        = BASE_DIR / 'models'
LOGS_DIR          = BASE_DIR / 'logs'
NOTES_DIR         = BASE_DIR / 'notes'
MEMORY_DIR        = BASE_DIR / 'memory'

# ── LLM ──────────────────────────────────────────────────────────────────
ONLINE_MODE       = False
OLLAMA_MODEL      = 'llama3'
OLLAMA_URL        = 'http://localhost:11434'
CLAUDE_MODEL      = 'claude-sonnet-4-20250514'
CLAUDE_API_KEY    = os.getenv('ANTHROPIC_API_KEY')
MAX_HISTORY       = 10
MAX_TOKENS        = 4096
TEMPERATURE       = 0.7

# ── VOICE ────────────────────────────────────────────────────────────────
VOICE_ENABLED     = True
WAKE_WORD         = 'deep'
WAKE_SENSITIVITY  = 0.5
PORCUPINE_KEY     = os.getenv('PORCUPINE_API_KEY')
WHISPER_MODEL     = 'base.en'
TTS_ENGINE        = 'pyttsx3'
PIPER_MODEL       = 'en_US-ryan-medium'
ELEVENLABS_KEY    = os.getenv('ELEVENLABS_API_KEY')
ELEVENLABS_VOICE  = 'Adam'
TTS_RATE          = 160
TTS_VOLUME        = 1.0

# ── STT ──────────────────────────────────────────────────────────────────
STT_ENGINE        = 'whisper'
DEEPGRAM_KEY      = os.getenv('DEEPGRAM_API_KEY')
DEEPGRAM_MODEL    = 'nova-2'
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS    = 1

# ── MEMORY ───────────────────────────────────────────────────────────────
MEMORY_BACKEND    = 'local'
CHROMA_PERSIST    = str(MEMORY_DIR / 'chromadb')
SQLITE_PATH       = str(MEMORY_DIR / 'deep_memory.db')
SUPABASE_URL      = os.getenv('SUPABASE_URL')
SUPABASE_KEY      = os.getenv('SUPABASE_KEY')
MEMORY_TOP_K      = 5

# ── SCIENCE ──────────────────────────────────────────────────────────────
DEFAULT_PRECISION = 50
SYMPY_SIMPLIFY    = True
PLOT_DPI          = 300
PLOT_THEME        = 'dark'
ANIMATION_FPS     = 30
ANIMATION_DPI     = 150
MANIM_QUALITY     = 'medium_quality'

# ── ML / AI ──────────────────────────────────────────────────────────────
DEVICE            = 'auto'
MODELS_CACHE      = str(MODELS_DIR)
LAZY_LOAD_MODELS  = True
HF_CACHE          = str(MODELS_DIR / 'huggingface')

# ── ROBOTICS ─────────────────────────────────────────────────────────────
ROS2_ENABLED      = False
PYBULLET_GUI      = False
ROBOT_SIM_DT      = 0.01

# ── QUANTUM COMPUTING ────────────────────────────────────────────────────
QUANTUM_BACKEND   = 'statevector'
IBM_TOKEN         = os.getenv('IBM_QUANTUM_TOKEN')
QASM_SHOTS        = 1024

# ── CYBERSECURITY ────────────────────────────────────────────────────────
SCAN_TIMEOUT      = 2.0
LOG_ALL_COMMANDS  = True
ANOMALY_THRESHOLD = 3

# ── CLOUD ────────────────────────────────────────────────────────────────
FASTAPI_HOST      = '0.0.0.0'
FASTAPI_PORT      = 8000
REDIS_URL         = os.getenv('REDIS_URL', 'redis://localhost:6379')

# ── HUD ──────────────────────────────────────────────────────────────────
HUD_ENABLED       = True
HUD_UPDATE_MS     = 2000
HUD_BG_COLOR      = '#0D0D1A'
HUD_ACCENT_1      = '#00FFFF'
HUD_ACCENT_2      = '#FF00FF'
HUD_ACCENT_3      = '#FF6B9D'

VERBAL_FORMAT     = '{summary}'

for d in [BASE_DIR, PLOTS_DIR, ANIM_DIR, MANIM_DIR, REPORTS_DIR,
          MODELS_DIR, LOGS_DIR, NOTES_DIR, MEMORY_DIR]:
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
