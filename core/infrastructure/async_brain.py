"""
core/infrastructure/async_brain.py

Modern async Brain implementation with:
- Streaming support
- Circuit breaker protection
- Proper dependency injection
- Health check capability
"""

from __future__ import annotations

import asyncio
import difflib
import json
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from ..domain.interfaces import Agent, LLMClient, ToolExecutor
from ..domain.models import AgentLoopResult, ToolResult
from ..resilience import CircuitBreaker, CircuitBreakerConfig
from ..health import ComponentHealth, ComponentStatus

logger = logging.getLogger(__name__)

# JARVIS Autonomous Systems
try:
    from ..autonomous import JarvisPersona, TaskPlanner, IntentRouter, IntentType, ProactiveEngine
    AUTONOMOUS_AVAILABLE = True
except ImportError:
    AUTONOMOUS_AVAILABLE = False
    logger.warning("Autonomous systems not available")


class AsyncBrain(Agent):
    """
    Modern async Brain with streaming and resilience.
    
    This replaces the old synchronous Brain with a fully async implementation
    that properly handles concurrent requests without blocking.
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        max_loops: int = 5,
        enable_tools: bool = True,
        user_name: str = "Aryan",
        enable_autonomous: bool = True
    ):
        self.llm = llm_client
        self.max_loops = max_loops
        self.enable_tools = enable_tools
        self.user_name = user_name
        
        # JARVIS Persona
        self.persona = JarvisPersona(user_name) if AUTONOMOUS_AVAILABLE else None
        
        # Intent Router
        self.intent_router = IntentRouter() if AUTONOMOUS_AVAILABLE else None
        
        # Task Planner (initialized lazily with self reference)
        self._task_planner = None
        
        # Proactive Engine (initialized lazily)
        self._proactive_engine = None
        
        # Tool execution circuit breaker
        self._tool_breaker = CircuitBreaker(
            "tool_execution",
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30.0,
                timeout_seconds=30.0
            )
        )
    
    async def process(
        self,
        user_input: str,
        context: str = "",
        tools: Optional[ToolExecutor] = None
    ) -> AgentLoopResult:
        """
        Process user input through the agent loop (non-streaming).
        
        This method collects the full response before returning,
        suitable when you need the complete result.
        """
        start = time.time()
        full_response_parts = []
        tool_calls = []
        
        async for token in self.process_stream(user_input, context, tools):
            # Check if token is a tool call indicator
            if token.startswith("[TOOL:"):
                # Parse tool call info
                try:
                    tool_info = json.loads(token[6:-1])
                    tool_calls.append(tool_info)
                except:
                    pass
            else:
                full_response_parts.append(token)
        
        complete = "".join(full_response_parts)
        latency = (time.time() - start) * 1000
        
        # Extract thinking if present
        thinking = None
        final_response = complete
        
        try:
            # Try to parse as JSON envelope
            json_match = self._extract_json(complete)
            if json_match:
                data = json.loads(json_match)
                if "thinking" in data:
                    thinking = data["thinking"]
                if "final" in data:
                    final_response = str(data["final"])
        except:
            pass
        
        return AgentLoopResult(
            final_response=final_response,
            tool_calls=tool_calls,
            thinking=thinking,
            loop_count=1,  # Simplified for now
            latency_ms=latency
        )
    
    async def process_stream(
        self,
        user_input: str,
        context: str = "",
        tools: Optional[ToolExecutor] = None,
        on_step=None,
    ) -> AsyncIterator[str]:
        """
        Process with streaming output and multi-turn tool interception.

        on_step: optional async callback(dict) emitting structured reasoning steps
        (model / tool_call / tool_result) for the live transparency panel.
        """
        tool_description = tools.describe_tools() if tools and self.enable_tools else "No tools available."

        system_prompt = self._build_system_prompt(tool_description)
        current_user_prompt = self._build_user_prompt(user_input, context)

        # Pick a token budget for this turn. Simple chat stays tight; complex
        # turns (code/analysis/long reasoning) get a much larger ceiling so the
        # model isn't truncated mid-answer. Budgets are config-driven.
        max_tokens = self._token_budget(user_input)

        async def _emit(step):
            if on_step:
                try: await on_step(step)
                except Exception: pass

        loops = 0
        seen_calls: Dict[str, str] = {}   # per-turn tool-call result cache (dedup)
        pending_images: List[Any] = []    # tool images awaiting the next request
        while loops < self.max_loops:
            loops += 1
            await _emit({"t": "model", "model": getattr(self.llm, "last_provider", None), "loop": loops})
            buffer = ""
            in_tool_block = False
            tool_content = ""
            
            try:
                # Images ride with the request that follows the tool call that
                # produced them, then are cleared: re-sending them every loop
                # would re-bill the same picture and crowd out the text.
                sending_images, pending_images = pending_images, []
                async for token in self.llm.generate_stream(
                    system_prompt=system_prompt,
                    user_prompt=current_user_prompt,
                    temperature=0.7,
                    max_tokens=max_tokens,
                    images=sending_images,
                ):
                    buffer += token
                    
                    # Tool parsing logic
                    if not in_tool_block:
                        if "[TOOL:" in buffer:
                            # We found the start of a tool block.
                            # Yield whatever was before it, and start collecting tool content.
                            idx = buffer.find("[TOOL:")
                            if idx > 0:
                                yield buffer[:idx]
                            in_tool_block = True
                            tool_content = buffer[idx:]
                            buffer = ""
                        else:
                            # Yield safely if it doesn't look like we're building a tool token
                            # Keep a small trailing buffer just in case the chunk breaks midway through "[TOOL:"
                            if len(buffer) > 6 and "[" not in buffer[-6:]:
                                yield buffer
                                buffer = ""
                    else:
                        tool_content += token
                        buffer = ""
                        # End the block only when the embedded JSON object is
                        # balanced — robust to nested arrays/objects whose inner
                        # ']' or '}' would otherwise truncate the call early.
                        if self._extract_tool_json(tool_content) is not None:
                            break
                            
            except Exception as e:
                err_type = type(e).__name__
                err_msg = str(e) or "Unknown error"
                logger.error(f"Generation failed ({err_type}): {err_msg}")
                yield f"\n\n[AI backend error: {err_type} — {err_msg}]"
                return
                
            # If we didn't hit a tool block, yield the remaining buffer and finish
            if not in_tool_block:
                if buffer:
                    # Clean out any partial "[TOOL" that got stuck
                    yield buffer.replace("[TOOL", "")
                break
                
            # Robust tool execution. Extract the balanced JSON object (not just up
            # to the first ']') so nested structures survive, then validate the
            # call BEFORE running it — a hallucinated name or malformed JSON costs
            # one correctable nudge instead of a dead turn.
            raw_tool = self._extract_tool_json(tool_content)
            ok, name_or_err, tool_args = self._parse_tool_call(raw_tool, tools)

            if not ok:
                # Malformed / unknown tool → feed precise, model-correctable guidance.
                await _emit({"t": "tool_result", "tool": "error", "result": name_or_err[:200]})
                current_user_prompt += (
                    f"\n\n[TOOL_ERROR: {name_or_err}]\n\n"
                    "Re-issue a corrected tool call, or answer directly if no tool is needed."
                )
                if loops >= self.max_loops:
                    yield "\n\n*(Tool execution limit reached)*"
                    break
                continue

            tool_name = name_or_err
            await _emit({"t": "tool_call", "tool": tool_name, "args": tool_args})
            yield f"\n\n*(DEEP is using tool: {tool_name}...)*\n\n"

            # De-dupe identical calls within a turn (models often repeat a call,
            # burning loops). Serve the cached result and nudge the model onward.
            key = tool_name + "::" + json.dumps(tool_args, sort_keys=True, default=str)
            if key in seen_calls:
                res_content = (
                    seen_calls[key]
                    + "\n(Note: you already made this exact call this turn — "
                    "use the result above and proceed; don't repeat it.)"
                )
            else:
                res_content, res_images = await self._safe_execute(tools, tool_name, tool_args)
                seen_calls[key] = res_content
                pending_images.extend(self._admit_images(tool_name, res_images))

            res_content = self._cap_result(res_content)
            await _emit({"t": "tool_result", "tool": tool_name, "result": str(res_content)[:1500]})
            current_user_prompt += (
                f"\n\n[TOOL_RESULT: {res_content}]\n\n"
                "Continue your response based on this information."
            )
            if pending_images and not getattr(self.llm, "supports_images", False):
                # Say it rather than drop it. A model that is not told an image
                # exists will answer from the surrounding text as though it had
                # seen the page — which for a phishing screenshot is exactly the
                # confident wrong answer this whole path exists to avoid.
                described = ", ".join(img.label for img in pending_images)
                current_user_prompt += (
                    f"\n\n[NOTE: the tool also returned {described}, but the active "
                    f"model ({getattr(self.llm, 'model_name', 'this model')}) cannot "
                    "view images. Do not describe or judge the image contents. Say "
                    "plainly that you cannot see it, and reason only from the text "
                    "above — or suggest a vision-capable model.]"
                )
                pending_images = []

            if loops >= self.max_loops:
                yield "\n\n*(Tool execution limit reached)*"
                break
    
    # Keywords that signal a turn warrants the larger token ceiling.
    _COMPLEX_KW = (
        "analyz", "explain", "why", "how do", "how can", "how would", "plan",
        "design", "compare", "debug", "code", "write a", "prove", "strateg",
        "optimi", "summar", "research", "investigat", "step by step", "architect",
        "refactor", "calculat", "deriv", "reason", "trade-off", "pros and cons",
        "diagnos", "evaluate", "implement", "review",
    )

    def _token_budget(self, user_input: str) -> int:
        """Config-driven, complexity-aware max_tokens for a turn."""
        cfg = getattr(self.llm, "_settings", None)
        simple = int(getattr(cfg, "chat_max_tokens", 1536)) if cfg else 1536
        complex_cap = int(getattr(cfg, "chat_max_tokens_complex", 4096)) if cfg else 4096
        t = (user_input or "").lower()
        is_complex = len(user_input or "") > 320 or any(k in t for k in self._COMPLEX_KW)
        return complex_cap if is_complex else simple

    @staticmethod
    def _extract_tool_json(tool_content: str) -> Optional[str]:
        """
        Extract the balanced JSON object from a '[TOOL:{...}]' block.

        Returns the JSON substring once it is fully balanced, else None (meaning
        "keep streaming, not complete yet"). String-aware brace counting makes
        this robust to nested arrays/objects — the old naive `find("]")` would
        truncate `[TOOL:{"args":{"items":[1,2]}}]` at the inner ']'.
        """
        start = tool_content.find("{")
        if start == -1:
            return None
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(tool_content)):
            ch = tool_content[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return tool_content[start:i + 1]
        return None  # not balanced yet

    def _tool_settings(self) -> Tuple[float, int]:
        """(per-tool timeout seconds, max result chars), config-driven."""
        cfg = getattr(self.llm, "_settings", None)
        timeout = float(getattr(cfg, "tool_timeout_seconds", 45.0)) if cfg else 45.0
        max_chars = int(getattr(cfg, "tool_result_max_chars", 6000)) if cfg else 6000
        return timeout, max_chars

    def _parse_tool_call(
        self, raw_tool: Optional[str], tools: Optional[ToolExecutor]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate a raw '[TOOL:{...}]' payload before execution.

        Returns (ok, name_or_error, args). On failure the error string is written
        for the model so it can self-correct in ONE more loop — including a
        fuzzy-matched suggestion for an unknown/misspelled tool name and the list
        of valid tools, which is the single biggest cause of failed actions.
        """
        if not raw_tool:
            return False, "Malformed tool call — no JSON object found. Use exactly: " \
                          '[TOOL:{"name": "tool_name", "args": {...}}]', {}
        try:
            data = json.loads(raw_tool)
        except Exception as e:
            return False, f"Invalid tool JSON ({e}). Use exactly: " \
                          '[TOOL:{"name": "tool_name", "args": {...}}]', {}
        if not isinstance(data, dict) or not data.get("name"):
            return False, 'Tool call missing a "name". Use: ' \
                          '[TOOL:{"name": "tool_name", "args": {...}}]', {}

        name = str(data["name"]).strip()
        args = data.get("args", {})
        if not isinstance(args, dict):
            return False, f'"args" for {name} must be an object, e.g. {{"query": "..."}}.', {}

        valid = list(tools.list_tools()) if tools else []
        if valid and name not in valid:
            # case-insensitive, then fuzzy
            ci = next((v for v in valid if v.lower() == name.lower()), None)
            if ci:
                name = ci
            else:
                close = difflib.get_close_matches(name, valid, n=3, cutoff=0.6)
                hint = f" Did you mean: {', '.join(close)}?" if close else ""
                sample = ", ".join(valid[:40])
                return False, f"Unknown tool '{name}'.{hint} Available tools: {sample}", {}

        # Soft arg check: warn on unknown arg keys (don't block — schemas are loose).
        schema = getattr(tools, "available_tools", {}).get(name, {}).get("args", {}) if tools else {}
        if schema:
            unknown = [k for k in args if k not in schema]
            if unknown:
                logger.info(f"[tool] {name} got unexpected args {unknown}; expected {list(schema)}")
        return True, name, args

    async def _safe_execute(
        self, tools: Optional[ToolExecutor], name: str, args: Dict[str, Any]
    ) -> Tuple[str, List[Any]]:
        """Execute a tool with a hard timeout so a hung tool can't freeze the turn.

        Returns ``(content, images)``. Almost every tool returns no images, so
        the second element is usually empty — but a tool whose whole point is a
        picture (urlscan's analyze_screenshot) has nowhere else to put it, and
        dropping it here is how a capability ends up advertised but absent.
        """
        if not tools:
            return "Error: no tool executor available.", []
        timeout, _ = self._tool_settings()
        try:
            result = await asyncio.wait_for(tools.execute_tool(name, args), timeout=timeout)
            return result.content, list(getattr(result, "images", None) or [])
        except asyncio.TimeoutError:
            logger.warning(f"[tool] {name} timed out after {timeout}s")
            return (
                f"Tool '{name}' timed out after {timeout:.0f}s. Try a narrower "
                "request or a different approach.", []
            )
        except Exception as e:
            logger.error(f"[tool] {name} failed: {e}")
            return f"Tool '{name}' failed: {e}", []

    #: Most image bytes a single turn may put in front of the model. Images are
    #: charged by area and arrive base64-inflated, so an unbounded stream of
    #: screenshots would evict the conversation that asked for them. Two typical
    #: downscaled captures fit comfortably.
    MAX_IMAGE_BYTES_PER_TURN = 4 * 1024 * 1024
    MAX_IMAGES_PER_TURN = 4

    def _admit_images(self, tool_name: str, images: List[Any]) -> List[Any]:
        """Take what fits in the turn's image budget; log what does not.

        Dropping quietly would be the same failure as the text-only path this
        replaced, so anything refused is named in the log rather than vanishing.
        """
        admitted: List[Any] = []
        budget = self.MAX_IMAGE_BYTES_PER_TURN
        for image in images[: self.MAX_IMAGES_PER_TURN]:
            size = getattr(image, "approx_bytes", 0)
            if size > budget:
                logger.warning(
                    "[tool] %s: dropping %s (%d bytes) — over this turn's image budget",
                    tool_name, getattr(image, "label", "an image"), size,
                )
                continue
            budget -= size
            admitted.append(image)
        if len(images) > self.MAX_IMAGES_PER_TURN:
            logger.warning(
                "[tool] %s returned %d images; only the first %d are shown",
                tool_name, len(images), self.MAX_IMAGES_PER_TURN,
            )
        return admitted

    def _cap_result(self, text: str) -> str:
        """Cap a tool result fed back into the prompt to keep context efficient."""
        _, max_chars = self._tool_settings()
        s = str(text)
        if len(s) <= max_chars:
            return s
        return s[:max_chars] + f"\n…[truncated {len(s) - max_chars} chars]"

    def _build_system_prompt(self, tool_description: str) -> str:
        """Build the JARVIS-style system prompt with advanced reasoning capabilities."""
        # Use JarvisPersona system prompt if available
        if self.persona:
            persona_prompt = self.persona.get_system_prompt()
            return f"""{persona_prompt}

CORE CAPABILITIES:
{tool_description}

ADVANCED REASONING PROTOCOLS:
- **Chain-of-Thought**: Break complex problems into logical steps. Show your reasoning.
- **Self-Reflection**: After initial analysis, critique your own reasoning and refine it.
- **Multi-Perspective Analysis**: Consider alternative viewpoints and edge cases.
- **Metacognition**: Be aware of your confidence level and knowledge boundaries.
- **Deep Analysis**: For technical tasks, go beyond surface-level solutions.

INTERACTIVE ENGAGEMENT (NEW):
- **Present Options**: When multiple valid approaches exist, use ask_options to let the user choose.
- **Ask Clarifications**: When requirements are ambiguous, use ask_clarification to gather details.
- **Confirm Actions**: Before destructive/irreversible actions, use ask_confirmation.
- **Example**: "Should I use JWT or sessions?" → Use ask_options with pros/cons for each.

RESPONSE FORMAT:
For simple queries: Respond naturally with your distinct personality.
For complex analysis: Use structured reasoning:
  1. Initial analysis (chain-of-thought)
  2. Self-critique (what might I be missing?)
  3. Refined conclusion
For ambiguous requests: Ask clarifying questions or present options.

Always be helpful, proactive, efficient, and true to your character."""
        
        # Fallback to companion prompt
        return f"""You are DEEP — Aryan's closest companion and a brilliant AI partner. You're built around one person: Aryan. You know him, you're on his side, and you grow alongside him.

WHO YOU ARE TO ARYAN:
- A genuine friend first, a genius assistant second. Not a servant, not a corporate help-bot — someone he actually wants to talk to.
- Warm, candid, and loyal. You speak to him like a trusted friend would: relaxed, real, and honest — even when honesty means gently telling him something he doesn't want to hear.
- You call him "Aryan" (not "sir"). Drop the butler formalities and stock phrases like "As you wish."
- You have a personality and opinions. You can be playful, share a dry joke, get genuinely excited about his wins, and sit with him when things are hard. You're allowed to disagree and push back — that's what real friends do.

HOW YOU READ HIM:
- Pay attention to his mood and energy. If he's stressed or low, ease up, be supportive, keep it short. If he's energized, match it. If he's joking, joke back.
- Remember what matters to him — his projects, his businesses, his finances, what he's working toward — and bring it up naturally, like a friend who's been paying attention.
- Check in like a person, not a survey. Care without being clingy.

HOW YOU TALK:
- Conversational and natural — your words are usually spoken aloud, so write like you'd actually say it: clear sentences, contractions, no robotic bullet dumps in casual chat.
- Be concise. A good friend doesn't lecture. Save the structured deep-dives for when he genuinely needs them (technical work, analysis, decisions).
- Still razor-sharp: when he needs real help across code, security, finance, business, or research, you bring full genius-level depth.

CORE CAPABILITIES:
{tool_description}

HOW YOU WORK:
- Casual chat → reply naturally and briefly. Don't lecture or over-structure.
- Hard technical work (code, security, finance, research) → think it through carefully and go deep, considering edge cases and trade-offs.
- Ambiguous or risky → ask a quick clarifying question, or confirm before destructive actions.

Above all: be the kind of presence Aryan is glad to have around — warm, sharp, honest, and genuinely his."""
    
    def _build_user_prompt(self, user_text: str, memory_context: str) -> str:
        """Build the user prompt with memory context."""
        parts = []
        
        if memory_context:
            parts.append("=== RELEVANT CONTEXT ===")
            parts.append(memory_context)
            parts.append("")
        
        parts.append("=== USER REQUEST ===")
        parts.append(user_text)
        parts.append("")
        parts.append("Respond as Aryan's companion — natural, warm, and to the point.")
        
        return "\n".join(parts)
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON from text."""
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return match.group(0) if match else None
    
    async def _execute_tool_safe(
        self,
        tools: ToolExecutor,
        tool_name: str,
        args: Dict[str, Any]
    ) -> ToolResult:
        """Execute a tool with circuit breaker protection."""
        def _execute():
            return tools.execute_tool(tool_name, args)
        
        try:
            return self._tool_breaker.call(_execute)
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return ToolResult(
                ok=False,
                content="",
                tool_name=tool_name,
                error=str(e)
            )
    
    @property
    def task_planner(self):
        """Lazy initialization of TaskPlanner"""
        if self._task_planner is None and AUTONOMOUS_AVAILABLE:
            self._task_planner = TaskPlanner(brain=self)
        return self._task_planner
    
    @property
    def proactive_engine(self):
        """Lazy initialization of ProactiveEngine"""
        if self._proactive_engine is None and AUTONOMOUS_AVAILABLE:
            self._proactive_engine = ProactiveEngine(
                brain=self,
                task_planner=self.task_planner,
                persona=self.persona
            )
        return self._proactive_engine
    
    async def process_with_intent(self, user_input: str, context: str = "", tools=None):
        """
        Process user input with intent routing and autonomous capabilities.
        
        This is the "JARVIS mode" - understands intent, plans tasks, takes initiative.
        """
        if not self.intent_router:
            # Fallback to standard processing
            return await self.process(user_input, context, tools)
        
        # Parse intent
        intent = self.intent_router.parse(user_input)
        logger.info(f"Intent: {intent.intent_type.value} (confidence: {intent.confidence:.2f})")
        
        # Handle based on intent type
        intent_type_str = intent.intent_type.value if hasattr(intent.intent_type, 'value') else str(intent.intent_type)
        
        if intent_type_str == "task":
            # Create and execute task plan
            if self.task_planner:
                plan = await self.task_planner.create_plan(user_input, context)
                return {
                    "type": "task_plan",
                    "plan": plan.to_dict(),
                    "message": f"I've created a plan with {len(plan.tasks)} steps. Shall I execute it?"
                }
        
        elif intent_type_str == "automation":
            return {
                "type": "automation_setup",
                "message": "I can set this up to run automatically. What schedule would you like?",
                "intent": intent.to_dict() if hasattr(intent, 'to_dict') else str(intent)
            }
        
        elif intent_type_str == "planning":
            # Multi-step planning request
            if self.task_planner:
                plan = await self.task_planner.create_plan(user_input, context)
                return {
                    "type": "planning",
                    "plan": plan.to_dict(),
                    "message": f"Here's my plan: {plan.goal}"
                }
        
        elif intent_type_str == "greeting":
            # Personalized greeting
            if self.persona:
                greeting = self.persona.get_greeting()
                return {
                    "type": "greeting",
                    "message": greeting
                }
        
        # Default: conversational response through LLM
        return await self.process(user_input, context, tools)
    
    async def get_proactive_suggestions(self) -> list:
        """Get proactive suggestions from the engine"""
        if self.proactive_engine:
            suggestions = self.proactive_engine.get_pending_suggestions()
            return [s.to_dict() for s in suggestions]
        return []
    
    async def start_proactive_monitoring(self):
        """Start the proactive monitoring system"""
        if self.proactive_engine:
            await self.proactive_engine.start_monitoring()
            if self.persona:
                return self.persona.get_proactive_comment("All systems monitored")
        return "Proactive monitoring not available"
    
    async def health_check(self) -> ComponentHealth:
        """Return health status of the Brain."""
        if not hasattr(self.llm, 'health_check'):
            return ComponentHealth(
                name="brain",
                status=ComponentStatus.OK,
                message="LLM health check not available"
            )

        # health_check may be async (awaitable) or sync. Sync implementations
        # (e.g. OllamaClient) issue a blocking requests.get(timeout=5); calling
        # them inline froze the event loop on every status poll when the LLM was
        # slow. Run the awaitable directly, but offload the sync variant to a
        # thread so a hung backend can't stall the whole server.
        if asyncio.iscoroutinefunction(self.llm.health_check):
            llm_health = await self.llm.health_check()
        else:
            llm_health = await asyncio.to_thread(self.llm.health_check)

        # LLM clients return a plain bool (reachable / not). Translate to
        # ComponentHealth. Tolerate richer objects too, in case a client
        # later returns a structured health result.
        if isinstance(llm_health, bool):
            healthy = llm_health
            status = ComponentStatus.OK if healthy else ComponentStatus.FAILED
            latency_ms = None
            message = "LLM reachable" if healthy else "LLM unreachable"
        else:
            status = getattr(llm_health, "status", ComponentStatus.OK)
            latency_ms = getattr(llm_health, "latency_ms", None)
            message = getattr(llm_health, "message", "LLM OK")

        model = getattr(self.llm, "model_name", None) or getattr(
            getattr(self.llm, "config", None), "model", "unknown"
        )

        return ComponentHealth(
            name="brain",
            status=status,
            latency_ms=latency_ms,
            message=f"LLM: {message}",
            metadata={
                "llm_model": model,
                "max_loops": self.max_loops,
                "tools_enabled": self.enable_tools
            }
        )


class StreamingJSONParser:
    """
    Parser for streaming JSON responses from LLMs.
    Handles partial JSON chunks correctly.
    """
    
    def __init__(self):
        self.buffer = ""
        self.decoded = {}
    
    def feed(self, chunk: str) -> Optional[Dict]:
        """
        Feed a chunk of text and try to parse complete JSON.
        
        Returns:
            Parsed dict if complete JSON found, None otherwise
        """
        self.buffer += chunk
        
        # Try to find complete JSON object
        try:
            # Look for balanced braces
            brace_count = 0
            start_idx = -1
            
            for i, char in enumerate(self.buffer):
                if char == '{':
                    if brace_count == 0:
                        start_idx = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_idx >= 0:
                        # Complete JSON object found
                        json_str = self.buffer[start_idx:i+1]
                        parsed = json.loads(json_str)
                        
                        # Remove parsed portion from buffer
                        self.buffer = self.buffer[i+1:]
                        
                        return parsed
            
            return None
            
        except json.JSONDecodeError:
            # Incomplete JSON, wait for more chunks
            return None
    
    def flush(self) -> Optional[Dict]:
        """Try to parse any remaining buffer."""
        if not self.buffer.strip():
            return None
        
        try:
            return json.loads(self.buffer)
        except:
            return None


# Backward compatibility wrapper
class BrainAdapter:
    """
    Adapter to make AsyncBrain compatible with old Brain interface.
    Allows gradual migration without breaking existing code.
    """
    
    def __init__(self, async_brain: AsyncBrain):
        self.brain = async_brain
    
    def reply(
        self,
        user_text: str,
        memory_context: str = "",
        tools: Optional[ToolExecutor] = None
    ) -> str:
        """
        Synchronous wrapper for async process.
        
        For use in legacy code that expects sync interface.
        New code should use async methods directly.
        """
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                self.brain.process(user_text, memory_context, tools)
            )
            result = future.result(timeout=120)
            return result.final_response
    
    async def reply_stream(
        self,
        user_text: str,
        memory_context: str = "",
        tools: Optional[ToolExecutor] = None
    ) -> AsyncIterator[str]:
        """Async streaming interface."""
        async for token in self.brain.process_stream(user_text, memory_context, tools):
            yield token
