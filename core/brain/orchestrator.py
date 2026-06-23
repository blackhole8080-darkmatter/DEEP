"""
core/brain/orchestrator.py

Chat Orchestrator separating AI logic from the WebSocket transport layer.
Handles Jarvis context, tool routing, memory, and LLM streaming.
"""
import asyncio
from datetime import datetime
from typing import Dict, List, AsyncGenerator
import json
import re as _re_tools

from interface.deps import services
from core.config import Settings
settings = Settings()
from core.llm.providers import stream_ollama_vision_tokens, stream_groq_tokens, stream_gemini_tokens, stream_claude_tokens
from core.infrastructure.async_brain import AsyncBrain

class ChatOrchestrator:
    def __init__(self):
        self.session_history: Dict[int, List[Dict]] = {}
        self.MAX_HISTORY = 12

    def _time_of_day(self) -> str:
        h = datetime.now().hour
        if 5 <= h < 12:  return "morning"
        if 12 <= h < 17: return "afternoon"
        if 17 <= h < 22: return "evening"
        return "night"

    def build_jarvis_context(self, session_id: int, user_input: str) -> str:
        """Build rich context block injected into every prompt."""
        now = datetime.now()
        date = now.strftime("%A, %B %d, %Y")
        time = now.strftime("%I:%M %p")

        # Short-term session history
        history = self.session_history.get(session_id, [])
        history_text = ""
        if history:
            lines = []
            for t in history[-self.MAX_HISTORY:]:
                speaker = "Aryan" if t["role"] == "user" else "Deep"
                lines.append(f"{speaker}: {t['content'][:300]}")
            history_text = "\n=== SHORT-TERM CONVERSATION HISTORY ===\n" + "\n".join(lines) + "\n"

        # Long-term semantic recall
        ltm_context = ""
        try:
            if user_input:
                recalled = services.ltm.recall(user_input, k=3)
                if recalled:
                    ltm_context = "\n=== LONG-TERM MEMORY (RELEVANT FACTS) ===\n"
                    for m in recalled:
                        ltm_context += f"- {m.content}\n"
        except Exception as e:
            print(f"[LTM Error] {e}")

        # Knowledge-graph recall
        kg_context = ""
        try:
            if user_input:
                hits = services.knowledge_graph.semantic_search(user_input, k=5, min_score=0.35)
                if hits:
                    lines = []
                    for h in hits[:5]:
                        bit = h["name"]
                        desc = (h.get("description") or "").strip()
                        if desc:
                            bit += f" — {desc}"
                        nbrs = services.knowledge_graph.get_neighbors(h["name"])[:4]
                        rel = "; ".join(f"{n['relation']} {n['entity']['name']}" for n in nbrs)
                        if rel:
                            bit += f" (Connections: {rel})"
                        lines.append(f"- {bit}")
                    kg_context = "\n=== CORE MEMORY GRAPH (ENTITIES & CONCEPTS) ===\n" + "\n".join(lines) + "\n"
        except Exception as e:
            print(f"[KG Error] {e}")

        return f"""
[SYSTEM CONTEXT]
User: Aryan
Time of Day: {self._time_of_day()}
Current Date: {date}
Current Time: {time}
{ltm_context}{kg_context}{history_text}
[END CONTEXT]
"""

    def store_turn(self, session_id: int, role: str, content: str):
        if session_id not in self.session_history:
            self.session_history[session_id] = []
        self.session_history[session_id].append({
            "role": role,
            "content": content,
            "time": datetime.now().isoformat()
        })
        self.session_history[session_id] = self.session_history[session_id][-self.MAX_HISTORY * 2:]

    def clear_history(self, session_id: int):
        self.session_history.pop(session_id, None)

    async def process_turn(self, session_id: int, msg: dict) -> AsyncGenerator[dict, None]:
        text = msg.get("text", "")
        mode = msg.get("mode", "auto")
        image_data = msg.get("image")

        print(f"[CHAT] Received: {text[:50]}...")

        # Store user turn BEFORE generating
        self.store_turn(session_id, "user", text)
        
        # Record interaction for predictive pattern learning
        try:
            services.predictive_engine.record_interaction("user", text)
            services.proactive_core.note_user_activity()
        except Exception:
            pass

        # Build JARVIS context
        context = self.build_jarvis_context(session_id, text)

        yield {"type": "thinking", "ai": "DEEP", "mode": mode}
        start_time = datetime.now()

        try:
            yield {"type": "response_start"}

            full_response = []
            token_count = 0
            INACTIVITY_TIMEOUT = 60.0
            MAX_TOTAL_TIME = 180.0

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

            tool_route = bool(services.deep_tools) and _needs_tools(text)
            if tool_route:
                chain = ["ollama"]

            _reasoning_steps_buf = []
            
            # For yielding to the caller:
            async def _emit_reasoning(step: dict):
                _reasoning_steps_buf.append(step)
                # Since we are inside process_turn generator, we cannot easily yield from a nested function.
                # BUT we can just append to a shared list and yield it from the main loop!
                # Actually, the brain's on_step is awaited. We'll pass an async callback that pushes to a queue.

            queue = asyncio.Queue()

            async def _enqueue_reasoning(step: dict):
                _reasoning_steps_buf.append(step)
                await queue.put({"type": "reasoning", "step": step})

            if tool_route:
                await _enqueue_reasoning({"t": "route", "reason": "needs live data / tools", "model": f"groq:{settings.groq_model}"})

            # Neuro-symbolic integration
            try:
                from core.reasoning import symbolic_router as _symr
                _sym = _symr.solve(text)
                if _sym:
                    context += _symr.verified_context(_sym)
                    await _enqueue_reasoning({"t": "symbolic", "engine": "sympy", "kind": _sym["kind"], "result": _sym["result"]})
            except Exception as _se:
                print(f"[symbolic] {_se}")

            # Chemistry oracle
            try:
                from core.reasoning import chem_oracle as _chem
                _el = _chem.detect(text)
                if _el:
                    context += _chem.verified_context(_el)
                    await _enqueue_reasoning({"t": "oracle", "domain": "chemistry", "element": _el.get("name"), "result": f"{_el.get('symbol')} · {_el.get('atomic_weight')}"})
            except Exception as _ce:
                print(f"[chem] {_ce}")

            # Physics oracle
            try:
                from core.reasoning import physics_oracle as _phys
                _pd = _phys.detect(text)
                if _pd:
                    context += _phys.verified_context(_pd)
                    await _enqueue_reasoning({"t": "oracle", "domain": "physics", "kind": _pd.get("kind"), "result": _pd.get("name")})
            except Exception as _pe:
                print(f"[physics] {_pe}")

            # Flush queue to generator
            while not queue.empty():
                yield await queue.get()

            companion_system = (
                "You are DEEP, Aryan's close companion and brilliant AI partner — warm, candid, "
                "loyal, and genuinely his. Talk like a trusted friend: relaxed, real, concise, and "
                "naturally spoken (your replies are often read aloud). Call him Aryan, never 'sir'. "
                "Be emotionally attuned to his mood. Stay razor-sharp on real work — code, security, "
                "finance, business, research. Never reveal or hint at which underlying model or company "
                "powers you; you are simply DEEP.\n\n"
                "GENERATIVE UI: when structured data would be clearer as a visual than prose, "
                "you may embed ONE fenced block ```deep-ui``` containing a JSON object, in "
                "addition to your normal text.\n\n"
            )
            try:
                companion_system += services.world_model.context_block()
            except Exception:
                pass
            companion_system += context

            chat_msgs = []
            for t in self.session_history.get(session_id, [])[:-1][-10:]:
                chat_msgs.append({"role": "user" if t["role"] == "user" else "assistant", "content": t["content"][:800]})
            chat_msgs.append({"role": "user", "content": text})
            while chat_msgs and chat_msgs[0]["role"] == "assistant":
                chat_msgs.pop(0)
            max_tok = max(settings.max_tokens, 1024)

            vision_b64 = None
            vision_prompt = text or "What's in this image? Describe it for Aryan."
            if image_data:
                try:
                    def _parse_data_url(u):
                        p = u.split(",", 1)
                        return p[0], p[1]
                    _mt, vision_b64 = _parse_data_url(image_data)
                    chain = ["ollama_vision"]
                    active_model = settings.vision_model
                    await _enqueue_reasoning({"t": "route", "reason": "image attached → local vision", "model": f"ollama:{settings.vision_model}"})
                    while not queue.empty():
                        yield await queue.get()
                except Exception as _ve:
                    print(f"[DEEP] vision parse failed: {_ve}")

            def _provider_stream(p: str):
                if p == "ollama_vision":
                    return stream_ollama_vision_tokens(companion_system, vision_prompt, vision_b64, settings.vision_model, settings.ollama_base_url, max_tok)
                if p == "groq":
                    return stream_groq_tokens(companion_system, chat_msgs, settings.groq_model, settings.groq_api_key, max_tok)
                if p == "gemini":
                    return stream_gemini_tokens(companion_system, chat_msgs, settings.gemini_model, settings.gemini_api_key, max_tok)
                if p == "claude":
                    return stream_claude_tokens(companion_system, chat_msgs, settings.claude_model, settings.claude_api_key, max_tok)
                async def _brain_stream():
                    async for t in services.brain.process_stream(user_input=text, context=context, tools=services.deep_tools, on_step=_enqueue_reasoning):
                        yield t
                return _brain_stream()

            async def token_stream_gen():
                nonlocal active_model
                for p in chain:
                    emitted = False
                    try:
                        print(f"[DEEP] Routing to {p}")
                        async for tok in _provider_stream(p):
                            emitted = True
                            active_model = model_names.get(p, p)
                            yield tok
                        return
                    except Exception as e:
                        print(f"[DEEP] provider '{p}' failed: {e}")
                        try: services.metrics.record_provider_error(model_names.get(p, p))
                        except Exception: pass
                        if emitted: return
                        continue
                if image_data:
                    yield "\n\n[I couldn't process that image.]"
                else:
                    yield "\n\n[All chat providers are unavailable right now.]"

            try:
                # To handle _enqueue_reasoning calls that happen DURING the stream
                # we must run a separate background reader for the queue, or check the queue periodically.
                # Since the stream itself is an async generator, we can check the queue inside the loop.
                stream_iter = token_stream_gen().__aiter__()
                while True:
                    while not queue.empty():
                        yield await queue.get()

                    try:
                        token = await asyncio.wait_for(stream_iter.__anext__(), timeout=INACTIVITY_TIMEOUT)
                        full_response.append(token)
                        token_count += 1
                        
                        yield {"type": "token", "content": token}

                        elapsed = (datetime.now() - start_time).total_seconds()
                        if elapsed > MAX_TOTAL_TIME:
                            yield {"type": "token", "content": "\n\n[Response reached max length.]"}
                            break

                    except StopAsyncIteration:
                        break
            except asyncio.TimeoutError:
                yield {"type": "token", "content": "\n\n[AI response paused due to inactivity.]"}

            # Finalize
            while not queue.empty():
                yield await queue.get()

            latency = (datetime.now() - start_time).total_seconds() * 1000
            full_text = "".join(full_response)
            if full_text.strip():
                self.store_turn(session_id, "assistant", full_text)

            try:
                services.metrics.record_chat(model=active_model, tokens=token_count, latency_ms=latency, ok=bool(full_text.strip()))
                services.self_eval.record_turn(user_text=text, ai_text=full_text, response_time_ms=int(latency))
            except Exception:
                pass

            try:
                combined_text = f"{text} {full_text}"
                if services.knowledge_graph.extractor and len(text.strip()) >= 24:
                    asyncio.create_task(services.knowledge_graph.ingest_llm(combined_text, source_id=f"conv_{session_id}"))
                else:
                    services.knowledge_graph.ingest(combined_text, source_id=f"conv_{session_id}")
            except Exception:
                pass

            if tool_route:
                try: active_model = getattr(services.brain.llm, "last_provider", active_model)
                except Exception: pass
                yield {"type": "reasoning", "step": {"t": "final", "model": active_model}}

            yield {"type": "response_end", "latency": int(latency), "model": active_model, "tokens": token_count}
            
        except Exception as e:
            print(f"[CHAT ORCHESTRATOR ERROR] {e}")
            yield {"type": "token", "content": f"\n\n[System error: {str(e)}]"}
            yield {"type": "response_end", "latency": 0, "model": "error", "tokens": 0}

orchestrator = ChatOrchestrator()
