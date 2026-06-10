# DEEP Web Interface

**DEEP** is now a web-first JARVIS-class AI assistant with a HUD-style interface.

## Quick Start

### Recommended (Windows)
```bat
start_deep.bat
```
Starts the main server (`interface\server.py`) on **port 7768** plus the
science-engine HUD on port 8000.

### Manual
```bash
cd C:\Users\Aryan\Aryan_Private\DEEP
python interface\server.py
```

## Web Interface

Once started, open your browser to:
- **Main UI:** http://127.0.0.1:7768/ai
- **Health:** http://127.0.0.1:7768/api/health

### Features
- **JARVIS HUD UI** - Animated sci-fi interface with system vitals
- **AI Chat** - WebSocket streaming responses
- **System Monitoring** - CPU, memory, disk gauges in real-time
- **Component Health** - Brain, Ollama, ChromaDB status
- **Command Input** - Central command bar with quick links

### Keyboard Shortcuts
- `Enter` - Send command
- `Ctrl+C` (in terminal) - Stop server

## Configuration

The server binds to `127.0.0.1:7768` (see the bottom of `interface/server.py`).
Key `.env` settings:

```env
OLLAMA_MODEL=llama3.2
CHAT_PROVIDER_ORDER=groq,gemini,claude,ollama
DEEP_API_KEY=choose-a-strong-secret      # required for remote (non-loopback) access
DEEP_REQUIRE_REMOTE_AUTH=true
DEEP_CORS_ORIGINS=*
DEEP_RATE_LIMIT_PER_MIN=240
```

## Architecture

```
start_deep.bat
    ↓
python interface/server.py (FastAPI + uvicorn, port 7768)
    ↓
├─ WebSocket /ws/deep   (streaming AI responses + voice)
├─ REST API /api/*      (health, security, research, predictive, knowledge, science)
├─ POST /api/transcribe (offline Whisper STT)
└─ Static files interface/static/ (HUD interface at /ai)
```

## Requirements

```bash
pip install uvicorn fastapi aiofiles websockets python-dotenv
```

Or use the existing requirements:
```bash
pip install -r requirements.txt
```

## Voice Output (Optional)

For voice output in the web interface, the system supports:
- **Edge TTS** (free, default) - Microsoft's neural voices
- **ElevenLabs** (requires paid API key) - Premium voice quality

Configure in `.env`:
```
ELEVENLABS_API_KEY=your_key_here  # Optional
EDGE_TTS_VOICE=en-US-GuyNeural
VOICE_PERSONALITY=jarvis
```

## Troubleshooting

### Port already in use
Edit the `uvicorn.run(...)` call at the bottom of `interface/server.py` to use a
different port, or stop the process already bound to 7768.

### Module not found
```bash
# Make sure you're in the DEEP directory
pip install -r requirements.txt
```

### WebSocket not connecting
- Check firewall settings and that port 7768 is free
- The endpoint is `/ws/deep`
- For remote access, append `?key=YOUR_DEEP_API_KEY` to the WS URL
