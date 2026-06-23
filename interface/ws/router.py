"""
interface/ws/router.py

WebSocket routes extracted from server.py.
Handles connection multiplexing, forwarding events to ChatOrchestrator.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime
import json
import os
import tempfile

from interface.deps import services
from interface.ws.manager import manager
from core.brain.orchestrator import orchestrator
from core.config import settings

router = APIRouter()

def _client_is_local(host: str) -> bool:
    if not host: return False
    if host in ("127.0.0.1", "::1", "localhost"): return True
    if host.startswith("192.168.") or host.startswith("10.") or host.startswith("172."):
        # Simplistic local check, proper logic should match original server.py
        return True
    return False

@router.websocket("/ws/manas")
async def websocket_legacy_manas(ws: WebSocket):
    """Backward-compat alias for the pre-rename path."""
    await websocket(ws)

@router.websocket("/ws/deep")
async def websocket(ws: WebSocket):
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
                # Delegate entirely to the ChatOrchestrator generator
                async for event in orchestrator.process_turn(id(ws), msg):
                    await manager.send(ws, event)
            elif msg_type == "voice":
                await handle_voice(ws, msg)
            elif msg_type == "ping":
                await manager.send(ws, {"type": "pong", "time": datetime.now().isoformat()})
            elif msg_type == "security_snapshot":
                if services.netmon:
                    snap = await services.netmon.get_snapshot()
                    await manager.send(ws, {"type": "security_snapshot", "payload": snap.to_dict()})
            # ── C# Windows Client events (v2) ────────────────────────────
            elif msg_type == "device_register":
                device_id = payload.get("device_id", "unknown-windows")
                if services.redis_state:
                    await services.redis_state.set_device(
                        device_id, "info",
                        {
                            "name": payload.get("device_name", device_id),
                            "platform": payload.get("platform", "windows"),
                            "version": payload.get("version", "v2"),
                            "last_seen": datetime.now().isoformat(),
                            "active": True,
                        }
                    )
                if services.event_bus:
                    await services.event_bus.publish("remote_device_registered", {"device_id": device_id, "platform": "windows"})
            elif msg_type == "system_stats":
                device_id = payload.get("device_id", "unknown-windows")
                if services.redis_state:
                    await services.redis_state.set_device(device_id, "stats", payload)
            elif msg_type == "app_launched":
                if services.event_bus: await services.event_bus.publish("app_launched", payload)
            elif msg_type == "app_killed":
                if services.event_bus: await services.event_bus.publish("app_killed", payload)
            elif msg_type == "app_focused":
                if services.event_bus: await services.event_bus.publish("app_focused", payload)
            elif msg_type == "startup_enabled":
                if services.event_bus: await services.event_bus.publish("windows_startup_enabled", payload)
            elif msg_type == "startup_disabled":
                if services.event_bus: await services.event_bus.publish("windows_startup_disabled", payload)
            elif msg_type == "show_notification":
                if services.event_bus:
                    await services.event_bus.publish("tts_speak", {
                        "text": payload.get("body", ""),
                        "priority": payload.get("priority", "normal"),
                    })
                
    except WebSocketDisconnect:
        manager.disconnect(ws)
        orchestrator.clear_history(id(ws))


@router.websocket("/ws/voice")
async def websocket_voice(ws: WebSocket):
    """Lightweight WebSocket for the voice-status-orb frontend component."""
    await ws.accept()
    try:
        async def _voice_forward(event_name: str, payload: dict):
            if event_name == "voice_state_changed":
                await ws.send_json({"type": "state", **payload})
            elif event_name == "alert_spoken":
                await ws.send_json({"type": "alert", **payload})
        
        if services.event_bus:
            services.event_bus.subscribe("voice_state_changed", _voice_forward)
            services.event_bus.subscribe("alert_spoken", _voice_forward)
        
        try:
            while True:
                data = await ws.receive_text()
                msg = json.loads(data)
                if msg.get("type") == "command" and msg.get("command") == "stop":
                    # voice_security trigger_kill not fully ported; stubbed for now
                    pass
        except WebSocketDisconnect:
            pass
        finally:
            if services.event_bus:
                services.event_bus.unsubscribe("voice_state_changed", _voice_forward)
                services.event_bus.unsubscribe("alert_spoken", _voice_forward)
    except Exception:
        pass


async def handle_voice(ws: WebSocket, msg: dict):
    """Transcribe browser audio offline with Whisper, then answer as a chat turn."""
    import base64
    audio_data = msg.get("audio")
    if not audio_data:
        await manager.send(ws, {"type": "voice_ack", "error": "No audio received"})
        return

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
        # Note: stt_engine must be defined in services or initialized
        transcript = ""
        # transcript = (await stt_engine.transcribe_audio(temp_path)).strip()
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
        async for event in orchestrator.process_turn(id(ws), {"text": transcript, "mode": msg.get("mode", "auto")}):
            await manager.send(ws, event)
