"""
deep/ai/graph_orchestrator.py

LangGraph-style async state machine implemented natively in Python.
Triggered by "escalate_to_graph" events from the Pipeline.

No langgraph library dependency — everything is a plain async method
walking an edge-map.  This keeps the layer fully inspectable and
lightweight.

Architecture:
    GraphState  (dataclass)  →  nodes mutate state in-place
    GraphOrchestrator.execute(payload) walks the edge map:
        context_retrieval → llm_reasoning → [tool_executor] →
        self_evaluator → [llm_reasoning retry] → response_formatter →
        memory_writeback → END

Each node is an async method returning the next edge name.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not installed — LLM calls in GraphOrchestrator will fail")

try:
    from core.config import Settings
except ImportError:
    from config import Settings

try:
    from core.event_bus import EventBus
except ImportError:
    from event_bus import EventBus


# ═══════════════════════════════════════════════════════════════════════════════
# GraphState
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GraphState:
    """Mutable container passed between graph nodes."""

    command: str = ""
    intent: str = ""
    mood: str = ""
    context: str = ""
    llm_response: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    quality_score: float = 0.0
    final_response: str = ""
    retry_count: int = 0
    node_trace: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# GraphOrchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class GraphOrchestrator:
    """
    Native async state-machine orchestrator.

    Triggered by "escalate_to_graph" events.
    Publishes "deep_response" when the graph reaches END.
    """

    def __init__(
        self,
        event_bus: EventBus,
        pattern_memory,
        knowledge_store=None,
        redis_state=None,
        device_registry=None,
    ) -> None:
        self.event_bus = event_bus
        self.pattern_memory = pattern_memory
        self.knowledge_store = knowledge_store
        self.redis_state = redis_state
        self.device_registry = device_registry
        self.settings = Settings()

        # Edge map: node name → (handler_method, next_node_name or conditional)
        # Conditional nodes return the next node name dynamically.
        self._edges: Dict[str, Any] = {
            "context_retrieval": self._node_context_retrieval,
            "llm_reasoning": self._node_llm_reasoning,
            "tool_gate": self._node_tool_gate,
            "tool_executor": self._node_tool_executor,
            "self_evaluator": self._node_self_evaluator,
            "response_formatter": self._node_response_formatter,
            "memory_writeback": self._node_memory_writeback,
        }

        # Async HTTP client (reused across calls)
        self._client: Optional[Any] = None
        if HTTPX_AVAILABLE:
            self._client = httpx.AsyncClient(timeout=60.0)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Subscribe to escalation events."""
        self.event_bus.subscribe("escalate_to_graph", self._on_escalate)
        logger.info("[GraphOrchestrator] Started — listening for escalate_to_graph")

    async def stop(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("[GraphOrchestrator] Stopped")

    def status(self) -> Dict[str, Any]:
        return {"client_ready": self._client is not None}

    # ── EventBus handler ──────────────────────────────────────────────────

    async def _on_escalate(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Entry point: the Pipeline fires this when confidence is low."""
        state = await self.execute(payload)
        logger.info(f"[GraphOrchestrator] Completed graph for: {state.command[:40]!r}")

    # ── Main executor ─────────────────────────────────────────────────────

    async def execute(self, payload: Dict[str, Any]) -> GraphState:
        """
        Walk the edge map starting at "context_retrieval" until END.

        Args:
            payload: dict from Pipeline (contains intent, confidence,
                     mood, command, etc.)

        Returns:
            Final GraphState after all nodes have run.
        """
        state = GraphState(
            command=payload.get("command", ""),
            intent=payload.get("intent", ""),
            mood=payload.get("mood", "neutral"),
        )

        current_node = "context_retrieval"
        while current_node != "END":
            handler = self._edges.get(current_node)
            if handler is None:
                logger.error(f"[GraphOrchestrator] Unknown node '{current_node}'")
                break

            state.node_trace.append(current_node)

            # Conditional nodes (tool_gate, self_evaluator) return the next node name
            if current_node in {"tool_gate", "self_evaluator"}:
                next_node = await handler(state)
                current_node = next_node
            else:
                await handler(state)
                # Deterministic fallback: use the hardcoded edge list
                current_node = self._next_node(current_node)

        state.node_trace.append("END")
        logger.info(f"[GraphOrchestrator] Trace: {' → '.join(state.node_trace)}")
        return state

    def _next_node(self, current: str) -> str:
        """Deterministic edges for non-conditional nodes."""
        deterministic = {
            "context_retrieval": "llm_reasoning",
            "llm_reasoning": "tool_gate",
            "tool_executor": "self_evaluator",
            "response_formatter": "memory_writeback",
            "memory_writeback": "END",
        }
        return deterministic.get(current, "END")

    # ── Node: Context Retrieval ─────────────────────────────────────────

    async def _node_context_retrieval(self, state: GraphState) -> None:
        """Pull recent context + predicted intent from PatternMemory."""
        recent_ctx = "(PatternMemory not available)"
        predicted = None
        try:
            recent_ctx = await self.pattern_memory.get_recent_context(n=10)
        except Exception as e:
            logger.warning(f"[GraphOrchestrator] get_recent_context error: {e}")

        try:
            now = time.localtime()
            predicted = await self.pattern_memory.get_predicted_intent(
                hour=now.tm_hour,
                day_of_week=now.tm_wday,
            )
        except Exception as e:
            logger.warning(f"[GraphOrchestrator] get_predicted_intent error: {e}")

        ctx_parts = [f"Recent context:\n{recent_ctx}"]
        if predicted:
            ctx_parts.append(f"Predicted intent for this time: {predicted}")

        # Load shared conversation history from Redis (all devices)
        if self.redis_state:
            try:
                history = await self.redis_state.get_conversation_history()
                if history:
                    ctx_parts.append("\nConversation history (all devices):")
                    for h in history[-6:]:
                        device_tag = h.get("device", "unknown")
                        role = h.get("role", "unknown")
                        content = h.get("content", "")[:120]
                        ctx_parts.append(f"[{device_tag}] {role}: {content}")
            except Exception as e:
                logger.debug(f"[GraphOrchestrator] Redis conversation history error: {e}")

        # Search knowledge_store for relevant papers
        if self.knowledge_store and self.knowledge_store._started:
            try:
                papers = await self.knowledge_store.search(state.command, n_results=3)
                if papers:
                    ctx_parts.append("\nRelevant research:")
                    for p in papers:
                        ctx_parts.append(
                            f"- {p.title} ({p.domain}): {p.abstract[:200]}"
                        )
            except Exception as e:
                logger.debug(f"[GraphOrchestrator] knowledge_store search error: {e}")

        state.context = "\n".join(ctx_parts)

    # ── Node: LLM Reasoning ─────────────────────────────────────────────

    async def _node_llm_reasoning(self, state: GraphState) -> None:
        """
        Call the LLM (Ollama → OpenAI fallback).
        Parse [TOOL:skill_name:params] markers from the response.
        """
        system_prompt = self._resolve_system_prompt()
        full_prompt = (
            f"{system_prompt}\n\n"
            f"{state.context}\n\n"
            f"Current mood: {state.mood}\n\n"
            f"User command: {state.command}\n\n"
            f"Respond naturally. If you need to call a tool, include exactly one line like:\n"
            f"  [TOOL:skill_name:{{'param':'value'}}]\n"
            f"Otherwise just answer directly."
        )

        raw_response = await self._call_llm(full_prompt)
        state.llm_response = raw_response

        # Parse tool markers
        state.tool_calls = self._parse_tool_calls(raw_response)

    def _resolve_system_prompt(self) -> str:
        """Return system prompt from config or built-in default."""
        return getattr(
            self.settings,
            "deep_system_prompt",
            (
                "You are DEEP, an intelligent personal AI assistant. "
                "You are helpful, accurate, and concise. "
                "You have access to tools via [TOOL:skill_name:params] markers."
            ),
        )

    async def _call_llm(self, prompt: str) -> str:
        """Primary: Ollama /api/generate.  Fallback: OpenAI gpt-4o-mini."""
        if not HTTPX_AVAILABLE:
            return "(httpx unavailable — no LLM response)"

        # --- Ollama ---
        ollama_url = getattr(self.settings, "ollama_base_url", "http://localhost:11434")
        ollama_model = getattr(self.settings, "ollama_model", "llama3.2")
        try:
            resp = await self._client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": getattr(self.settings, "temperature", 0.2),
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
        except Exception as e:
            logger.warning(f"[GraphOrchestrator] Ollama call failed: {e}")

        # --- OpenAI fallback (only if not offline and key present) ---
        if getattr(self.settings, "offline_mode", False):
            return "(Ollama unreachable and offline_mode is enabled)"

        openai_key = getattr(self.settings, "openai_api_key", None)
        if not openai_key:
            return "(Ollama unreachable and no OpenAI API key configured)"

        try:
            resp = await self._client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": self._resolve_system_prompt()},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": getattr(self.settings, "temperature", 0.2),
                    "max_tokens": getattr(self.settings, "max_tokens", 512),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"[GraphOrchestrator] OpenAI fallback failed: {e}")
            return "(LLM unavailable — both Ollama and OpenAI failed)"

    def _parse_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """Extract [TOOL:name:{json}] markers from LLM response."""
        pattern = re.compile(
            r"\[TOOL:(?P<name>[\w_]+):(?P<params>\{.*?\})\]"
        )
        calls = []
        for m in pattern.finditer(text):
            try:
                params = json.loads(m.group("params"))
            except json.JSONDecodeError:
                params = {"raw": m.group("params")}
            calls.append({"skill": m.group("name"), "params": params})
        return calls

    # ── Node: Tool Gate ─────────────────────────────────────────────────

    async def _node_tool_gate(self, state: GraphState) -> str:
        """Conditional: route to tool_executor if tools requested."""
        if state.tool_calls:
            return "tool_executor"
        return "self_evaluator"

    # ── Node: Tool Executor ───────────────────────────────────────────────

    async def _node_tool_executor(self, state: GraphState) -> None:
        """
        For each tool_call: publish "skill_invoke" and wait for
        "skill_result" with a timeout.
        """
        if not self.event_bus:
            state.llm_response += "\n(Tool execution skipped — EventBus unavailable)"
            return

        results: List[str] = []
        timeout = getattr(self.settings, "tool_timeout_seconds", 10)

        for call in state.tool_calls:
            skill = call.get("skill", "unknown")
            params = call.get("params", {})

            result_future = asyncio.get_event_loop().create_future()

            def _make_handler(fut):
                async def _handler(event_name: str, payload: dict):
                    if payload.get("skill") == skill:
                        if not fut.done():
                            fut.set_result(payload.get("result", "(no result)"))
                return _handler

            handler = _make_handler(result_future)
            self.event_bus.subscribe("skill_result", handler)

            await self.event_bus.publish("skill_invoke", {
                "skill": skill,
                "params": params,
            })

            try:
                result = await asyncio.wait_for(result_future, timeout=timeout)
                results.append(f"[{skill}] → {result}")
            except asyncio.TimeoutError:
                results.append(f"[{skill}] → (timeout after {timeout}s)")

            self.event_bus.unsubscribe("skill_result", handler)

        state.llm_response += "\n\nTool results:\n" + "\n".join(results)

    # ── Node: Self-Evaluator ────────────────────────────────────────────

    async def _node_self_evaluator(self, state: GraphState) -> str:
        """
        Score the response quality 0.0-1.0.
        If below threshold and retries left → loop back to llm_reasoning.
        """
        min_quality = getattr(self.settings, "min_quality_score", 0.5)

        prompt = (
            f"Rate this response 0.0-1.0 for relevance to the command.\n"
            f"Command: {state.command}\n"
            f"Response: {state.llm_response}\n"
            f"Reply with only a float."
        )
        raw = await self._call_llm(prompt)

        score = 0.0
        try:
            # Extract first float-like token
            match = re.search(r"([0-9]*\.?[0-9]+)", raw.replace(",", "."))
            if match:
                score = float(match.group(1))
                score = max(0.0, min(1.0, score))
        except Exception:
            score = 0.0

        state.quality_score = score
        logger.info(f"[GraphOrchestrator] Quality score: {score:.2f}")

        if score < min_quality and state.retry_count < 2:
            state.retry_count += 1
            state.context += (
                f"\n\n[SELF-EVAL FEEDBACK] Previous response scored {score:.2f}. "
                f"Please improve relevance to the command. Retry {state.retry_count}/2."
            )
            logger.info(f"[GraphOrchestrator] Retrying ({state.retry_count}/2)")
            return "llm_reasoning"

        return "response_formatter"

    # ── Node: Response Formatter ──────────────────────────────────────────

    async def _node_response_formatter(self, state: GraphState) -> None:
        """Adapt response tone based on detected mood."""
        mood = state.mood.lower()
        raw = state.llm_response.strip()

        if mood == "calm":
            state.final_response = raw
        elif mood == "focused":
            # Keep concise, preserve technical detail
            lines = [l for l in raw.splitlines() if l.strip()]
            state.final_response = "\n".join(lines[:6]) if len(lines) > 6 else raw
        elif mood == "stressed":
            # Shorten to 2 sentences max, warmer tone
            state.final_response = await self._rewrite_for_stressed(raw)
        elif mood == "tired":
            # Very short, no jargon
            state.final_response = await self._rewrite_for_tired(raw)
        elif mood == "energetic":
            # Can be longer and enthusiastic
            state.final_response = raw
        else:
            state.final_response = raw

    async def _rewrite_for_stressed(self, text: str) -> str:
        """Ask the LLM to rewrite for a stressed user."""
        prompt = (
            f"Rewrite this response for someone who is stressed. "
            f"Keep it to 2 sentences max, calm and supportive:\n\n{text}"
        )
        rewritten = await self._call_llm(prompt)
        return rewritten.strip() if rewritten.strip() else text

    async def _rewrite_for_tired(self, text: str) -> str:
        """Ask the LLM to rewrite for a tired user."""
        prompt = (
            f"Rewrite this response for someone who is tired. "
            f"Very short (1-2 sentences), no jargon:\n\n{text}"
        )
        rewritten = await self._call_llm(prompt)
        return rewritten.strip() if rewritten.strip() else text

    # ── Node: Memory Writeback ──────────────────────────────────────────

    async def _node_memory_writeback(self, state: GraphState) -> None:
        """Log the interaction and publish completion events."""
        try:
            await self.pattern_memory.log_interaction(
                intent=state.intent,
                command=state.command,
                response=state.final_response,
                mood=state.mood,
                quality_score=state.quality_score,
                source="graph_orchestrator",
            )
        except Exception as e:
            logger.warning(f"[GraphOrchestrator] Memory writeback error: {e}")

        # Sync to Redis shared state
        if self.redis_state and self.device_registry:
            try:
                from core.config import Settings
                settings = Settings()
                device_id = getattr(settings, "deep_device_id", "unknown")
                await self.redis_state.save_conversation_turn(
                    state.command,
                    state.final_response,
                    device_id,
                    state.mood,
                )
                await self.device_registry.mark_command(state.command)
            except Exception as e:
                logger.warning(f"[GraphOrchestrator] Redis sync error: {e}")

        # Publish the final response
        await self.event_bus.publish("deep_response", {
            "command": state.command,
            "response": state.final_response,
            "intent": state.intent,
            "mood": state.mood,
            "quality_score": state.quality_score,
            "node_trace": state.node_trace,
        })

        # Also publish graph_complete for downstream listeners
        await self.event_bus.publish("graph_complete", {
            "final_response": state.final_response,
            "node_trace": state.node_trace,
            "quality_score": state.quality_score,
        })
