@echo off
REM DEEP server launcher — starts the FastAPI/WebSocket server.
REM Logs to ..\logs\server_autostart.log
cd /d C:\Users\Aryan\Aryan_Private\DEEP
REM Force UTF-8 so emoji/unicode print() calls (e.g. in core/ltm_memory.py) don't
REM crash startup when stdout is redirected to a cp1252-encoded log file.
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
REM Disable agent self-critique pass: it adds LLM calls that blow past Groq's
REM free-tier 12k TPM limit (429s). Remove this line if agents move off Groq.
set DEEP_AGENT_REFLECTION=0
REM Auto-start the Engineering-Bible engine HUD on :8000 (separate from the
REM main server on :7768). Runs in the background; lazy-loads science deps.
start "DEEP-HUD" /b cmd /c "python -m engine.hud >> ""C:\Users\Aryan\Aryan_Private\logs\engine_hud.log"" 2>&1"
python interface\server.py >> "C:\Users\Aryan\Aryan_Private\logs\server_autostart.log" 2>&1
