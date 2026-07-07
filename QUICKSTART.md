# 🤖 DEEP JARVIS - Quick Start Guide

**Your personal AI companion is ready!** This guide will get you up and running in minutes.

---

## 📦 What's Been Built

You now have a **JARVIS-class personal AI** with:

### ✅ Core Features (Ready to Use)
1. **🎙️ Voice Interface** - Speak naturally, get spoken responses
2. **🧠 AI Brain** - Ollama (offline) + Claude (cloud) hybrid
3. **💾 Persistent Memory** - Remembers conversations across sessions
4. **🔒 Cybersecurity** - Real-time network monitoring & intrusion detection
5. **📰 Global News** - Tech, AI, science, world news briefings
6. **⚡ Task Automation** - Submit complex tasks, DEEP executes autonomously
7. **🎭 JARVIS Personality** - Cinematic, witty, proactive dialogue
8. **🌐 System Control** - Control your computer, browser, media, files

---

## 🚀 Getting Started (5 Minutes)

### Step 1: Install Dependencies

```bash
cd DEEP

# Install all required packages
pip install -r requirements.txt

# Additional: Install Tesseract OCR for vision features (optional)
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
# macOS: brew install tesseract
# Linux: sudo apt install tesseract-ocr
```

### Step 2: Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit .env with your settings:
# - Add your Claude API key (optional, for cloud mode)
# - Configure Ollama (runs locally, no API key needed)
# - Add NewsAPI key for better news (free at newsapi.org)
```

### Step 3: Start Ollama (Local AI)

```bash
# Install Ollama from https://ollama.ai

# Pull the recommended model
ollama pull llama3.2

# Verify it's running
ollama list
```

### Step 4: Launch DEEP (web-first)

DEEP runs as a FastAPI + WebSocket server. The HUD/chat UI, voice, and all
subsystems are served from the browser.

**Recommended (Windows):**
```bat
start_deep.bat
```
This launches the main server (`interface\server.py`) on **port 5174** and the
science-engine HUD on port 8000.

**Manual:**
```bash
python interface\server.py
```

Then open:
- **Main UI:** http://127.0.0.1:5174/ai
- **Health:** http://127.0.0.1:5174/api/health

The WebSocket endpoint is `/ws/deep`. Voice input is transcribed offline with
Whisper via `/api/transcribe` (or the `voice` WS message).

---

### Remote access & security

Local browser requests (`127.0.0.1`) are always trusted. When you expose DEEP
off-device (LAN / Tailscale via `network/remote_access.py`), remote clients must
present your `DEEP_API_KEY`. Configure in `.env`:

```env
DEEP_API_KEY=choose-a-strong-secret          # required for remote access
DEEP_REQUIRE_REMOTE_AUTH=true                 # set false to disable (not advised)
DEEP_CORS_ORIGINS=*                           # comma-separated allowlist
DEEP_RATE_LIMIT_PER_MIN=240                   # 0 disables rate limiting
```

Remote clients pass the key via the `X-DEEP-Key` header, `?key=` query param, or
a `deep_key` cookie. The WebSocket accepts `?key=` as well.

---

## 💬 First Commands to Try

### 🎙️ Voice Commands (if voice enabled)
Just say:
- `"jarvis"` - Wake word activation
- `"What's the news?"` - Get news briefing
- `"Research blockchain in healthcare"` - Autonomous research
- `"Start security monitoring"` - Cybersecurity protection

### ⌨️ Text Commands
```
news                    # Get immediate news briefing
research AI trends      # Plan autonomous research task
status                  # System status
quit                    # Exit
```

### 🤖 AI Interaction Examples
```
You> Good morning DEEP
DEEP> Good morning, Aryan. Ready to conquer the day?

You> What's in the tech news?
DEEP> [Provides curated tech briefing with JARVIS personality]

You> Research quantum computing applications
DEEP> [Plans multi-step research task, executes autonomously]

You> How's my system looking?
DEEP> [System diagnostics with cinematic flair]
```

---

## 🔧 Configuration Options

### `.env` File Settings

```env
# AI Providers
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
CLAUDE_API_KEY=sk-ant-... (optional)
CLAUDE_MODEL=claude-3-5-sonnet-latest

# News (get free key at newsapi.org)
NEWSAPI_KEY=your_key_here

# Voice
WHISPER_MODEL=base
TTS_RATE=175

# Security
ENABLE_SYSTEM_TOOLS=true
```

---

## 📱 Multi-Device Setup (Advanced)

### Future Steps (Phase 2):
1. **Web Server Mode**: `python web/server.py`
2. **Access from Phone**: Open `http://YOUR_IP:5000`
3. **Sync Server**: Coming in next update

---

## 🎯 Daily Usage Workflow

### Morning Routine
```bash
# 8:00 AM - Automatic news briefing (if enabled)
# Or manually: start the server and open the UI
start_deep.bat

# In the UI, ask: "What's my briefing?"
# DEEP delivers tech, AI, science, world news
```

### Study/Work Sessions
```
You> Research [your topic]
DEEP> Plans and executes research autonomously

You> Summarize this PDF
DEEP> Processes document, provides summary

You> Take notes on this
DEEP> Saves to knowledge base
```

### Evening Wind-down
```
You> What's the security status?
DEEP> All quiet on the digital front, sir.

You> Any news I missed?
DEEP> Evening briefing delivered.
```

---

## 🛠️ Troubleshooting

### Issue: "Porcupine not found"
**Solution**: 
```bash
pip install pvporcupine
# Get free key at https://console.picovoice.ai/
```

### Issue: "Ollama unreachable"
**Solution**:
```bash
# Make sure Ollama is running
ollama serve

# Or pull the model again
ollama pull llama3.2
```

### Issue: Voice not working
**Solution**:
- Check microphone permissions in the browser
- Confirm Whisper is installed (`pip install -U openai-whisper`)
- Test transcription directly via `POST /api/transcribe`

### Issue: News not loading
**Solution**:
- RSS feeds work without API key (built-in)
- Add NewsAPI key for more sources (free tier: 100 req/day)

---

## 📚 Available Tools (What DEEP Can Do)

### Information & News
- `get_news_briefing` - Global news across all categories
- `search_news` - Find specific topics in news
- `research_topic` - Autonomous deep research
- `get_ai_news` - Latest AI headlines

### System Control
- `get_system_status` - CPU, memory, disk usage
- `set_volume` - Control system volume
- `set_brightness` - Adjust screen brightness
- `launch_app` - Start applications
- `media_control` - Play/pause/next for media

### File Operations
- `read_file` - Read documents
- `write_file` - Save files
- `list_dir` - Browse workspace

### Security
- `start_security_monitoring` - Begin network/system monitoring
- `get_security_status` - Check security state
- `scan_ports` - Check open ports on devices
- `audit_system` - Security audit

### Automation
- `submit_task` - Autonomous multi-step execution
- `get_task_status` - Check running tasks
- `save_knowledge` - Remember information

---

## 🌟 Pro Tips

### 1. **Wake Word Hands-Free**
With wake word enabled, just say **"jarvis"** anywhere in the room:
```
You: "jarvis"
DEEP: "At your service, sir."
You: "What's the news?"
DEEP: [Delivers briefing]
```

### 2. **Autonomous Research**
Instead of manual searching:
```
You> Research the latest AI breakthroughs and summarize for my blog
DEEP> [Plans 4-step task, executes web search, fetches articles, 
        synthesizes findings, formats summary]
```

### 3. **Proactive Alerts**
DEEP can alert you automatically:
- Morning briefings (8am, 12pm, 6pm)
- Security threats detected
- Task completions

### 4. **Memory Across Sessions**
DEEP remembers:
- Previous conversations
- Saved knowledge
- Your preferences
- Research findings

### 5. **Offline-First**
Even without internet:
- Voice works (Whisper offline)
- AI works (Ollama local)
- TTS works (pyttsx3)
- Only news/cloud features disabled

---

## 🎓 For Students - Special Features

### Study Assist
```
You> Find research papers on neural networks
DEEP> Searches arXiv, Google Scholar, summarizes findings

You> Explain quantum entanglement simply
DEEP> Provides tailored explanation

You> Remind me about my deadline tomorrow
DEEP> Schedules reminder
```

### Productivity
- Task automation for repetitive research
- Document summarization
- Note-taking and knowledge management
- Deadline tracking

---

## 🗺️ Roadmap - What's Coming

### Phase 2 (Next 2 Weeks)
- [ ] Mobile web interface (access from phone)
- [ ] Multi-device sync (laptop + phone + tablet)
- [ ] Calendar integration (Google/Outlook)
- [ ] Email triage and drafting

### Phase 3 (Month 2)
- [ ] Smart home control (lights, thermostat)
- [ ] Vision capabilities (OCR, object recognition)
- [ ] Advanced voice synthesis (custom voice)
- [ ] Autonomous agents (coding, shopping, travel)

### Phase 4 (Month 3)
- [ ] Continuous learning from interactions
- [ ] Predictive suggestions
- [ ] Multi-language support
- [ ] Advanced security threat detection

---

## 📞 Getting Help

### Logs
```bash
# Server log (written by start_deep.bat)
type ..\logs\server_autostart.log
```

### Check Components
```python
# Verify the server module imports cleanly
python -c "import interface.server; print('Server OK')"
python -c "from core.config import Settings; print('Config OK')"
```

### Live debug feeds
- Event bus: http://127.0.0.1:5174/debug/events
- Health: http://127.0.0.1:5174/api/health

### Logs
Logs are printed to console. Check for:
- `[ERROR]` - Something broke
- `[WARNING]` - Minor issues
- `[INFO]` - Normal operation

---

## 🎉 Success Checklist

After setup, verify everything works:

- [ ] `start_deep.bat` starts the server without errors
- [ ] http://127.0.0.1:5174/ai loads the HUD
- [ ] AI responds with JARVIS personality ("As you wish", "Right away")
- [ ] Voice works (if enabled): "Testing" → spoken response
- [ ] Wake word works (if configured): Say "jarvis" → activation
- [ ] Security monitoring starts: `start_security_monitoring`
- [ ] Research task submits: `research AI trends`

---

## 💡 Remember

> "The future is already here - it's just not evenly distributed." 
> 
> **DEEP JARVIS** distributes that future to **your** devices, Aryan.

**Your AI companion is ready. At your service, sir.** 🎩🤖

---

## 🚀 Quick Launch Commands

```bash
# Recommended (Windows): main server + science HUD
start_deep.bat

# Manual launch of the main server
python interface\server.py

# Then open the UI
#   http://127.0.0.1:5174/ai
```

**Ready to begin?** Run `start_deep.bat`, open http://127.0.0.1:5174/ai, and say hello to DEEP! 🚀
