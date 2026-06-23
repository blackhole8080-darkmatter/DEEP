

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
