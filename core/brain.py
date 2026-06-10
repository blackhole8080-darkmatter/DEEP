"""
brain.py

Optimized LLM orchestration for DEEP.
- Decoupled multi-turn tool loop.
- JSON-mode natively enforced for robust parsing.
- Dynamic tool routing independent of tool names.
"""

from __future__ import annotations

import asyncio
import json
import re
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional, Protocol

import requests

logger = logging.getLogger(__name__)

try:
    from .config import Settings
except ImportError:
    from config import Settings

try:
    from ..personality import get_personality
except ImportError:
    try:
        from personality import get_personality
    except ImportError:
        # Fallback if personality module not available
        def get_personality():
            return {"name": "DEEP", "style": "professional"}


class ToolExecutor(Protocol):
    """Minimal interface brain.py expects from tools.py."""
    def describe_tools(self) -> str: ...
    def execute_tool(self, tool_name: str, args: dict[str, Any]) -> str: ...


class Brain:
    """Routes requests to Ollama or Claude, handles dynamic agent execution loops."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # Cap the loop to avoid infinite tool call cascades if a model hallucinates
        self._max_agent_loops = 5
        # Which model handled the most recent generation (for status / reasoning UI)
        self._last_provider = f"ollama:{getattr(settings, 'ollama_model', 'llama3.2')}"

    def _trace(self, step_type: str, **data) -> None:
        """Append a reasoning-transparency step for the current turn."""
        try:
            import time as _time
            trace = getattr(self, "_last_trace", None)
            if trace is None:
                trace = self._last_trace = []
            trace.append({"t": step_type, "ts": _time.time(), **data})
        except Exception:
            pass

    def get_reasoning(self) -> dict:
        """Return the most recent turn's reasoning trace (for the UI panel)."""
        return {
            "provider": getattr(self, "_last_provider", None),
            "steps": getattr(self, "_last_trace", []),
        }

    def reply(self, user_text: str, memory_context: str, tools: ToolExecutor) -> str:
        tool_description = tools.describe_tools()
        system_prompt = self._build_system_prompt(tool_description=tool_description)
        
        # Initialize conversation state for this turn
        current_user_prompt = self._build_user_prompt(user_text=user_text, memory_context=memory_context)
        self._last_trace = []  # reasoning transparency: steps for this turn

        for loop_count in range(self._max_agent_loops):
            logger.info(f"DEEP Loop {loop_count + 1}/{self._max_agent_loops} started.")

            result_text = self._generate_json_envelope(
                system_prompt=system_prompt,
                user_prompt=current_user_prompt
            )
            self._trace("model", provider=self._last_provider, loop=loop_count + 1)

            logger.info(f"LLM Raw Output: {result_text}")
            envelope = self._parse_json_envelope(result_text)
            if isinstance(envelope, dict) and envelope.get("thinking"):
                self._trace("thinking", text=str(envelope.get("thinking"))[:500])
            if envelope is None:
                logger.warning("Failed to parse JSON envelope. Falling back to raw text.")
                return result_text.strip()

            # Case A: Model requests a single tool execution
            tool_call = envelope.get("tool_call")
            
            # If tool_call is missing but final contains a tool_call (model hallucination), pivot
            if not tool_call and isinstance(envelope.get("final"), dict):
                inner_final = envelope.get("final", {})
                if isinstance(inner_final, dict) and "tool_call" in inner_final:
                    tool_call = inner_final["tool_call"]

            if isinstance(tool_call, dict) and "name" in tool_call:
                tool_name = str(tool_call.get("name", "")).strip()
                raw_args = tool_call.get("args", {})
                if not isinstance(raw_args, dict):
                    raw_args = {}

                # 1. Execute tool cleanly without hardcoded side effects
                logger.info(f"Executing tool: {tool_name} with args: {raw_args}")
                self._trace("tool_call", tool=tool_name, args=raw_args)
                tool_result_text = self._safe_execute_tool(tools, tool_name=tool_name, args=raw_args)
                logger.info(f"Tool Result: {tool_result_text}")
                self._trace("tool_result", tool=tool_name, result=str(tool_result_text)[:300])

                try:
                    tool_data = json.loads(tool_result_text)
                    result_content = tool_data.get("result", tool_result_text)
                except Exception:
                    result_content = tool_result_text

                # 2. Feed the execution data directly back into the next loop iteration
                current_user_prompt = self._build_tool_result_prompt(
                    original_user_text=user_text,
                    memory_context=memory_context,
                    tool_name=tool_name,
                    tool_result=str(result_content),
                )
                continue  # Loop back to let the LLM evaluate the tool results

            # Case A2: PARALLEL - Model requests multiple tools at once
            tool_calls = envelope.get("tool_calls")
            if isinstance(tool_calls, list) and len(tool_calls) > 0:
                # Validate tool_calls structure
                valid_calls = []
                for i, call in enumerate(tool_calls):
                    if isinstance(call, dict) and "name" in call:
                        valid_calls.append(call)
                    else:
                        logger.warning(f"Invalid tool_calls[{i}]: {call}")
                
                if not valid_calls:
                    logger.error("No valid tool calls found in tool_calls array")
                    current_user_prompt = self._build_tool_result_prompt(
                        original_user_text=user_text,
                        memory_context=memory_context,
                        tool_name="error",
                        tool_result="ERROR: Invalid tool_calls format. Each item must have 'name' field.",
                    )
                    continue
                
                logger.info(f"PARALLEL EXECUTION: {len(valid_calls)} tools requested")
                
                # Execute all valid tools in parallel
                parallel_results = self._execute_tools_parallel(tools, valid_calls)
                
                # Format results for LLM with clear structure
                results_summary = ["=== PARALLEL EXECUTION RESULTS ==="]
                for tool_name, result_text in parallel_results:
                    try:
                        tool_data = json.loads(result_text)
                        result_content = tool_data.get("result", result_text)
                    except Exception:
                        result_content = result_text
                    results_summary.append(f"\n[TOOL: {tool_name}]\n{result_content}")
                results_summary.append("\n=== END RESULTS ===")
                
                combined_results = "\n".join(results_summary)
                logger.info(f"Parallel results:\n{combined_results}")
                
                # Feed combined results back to LLM
                current_user_prompt = self._build_tool_result_prompt(
                    original_user_text=user_text,
                    memory_context=memory_context,
                    tool_name="parallel_execution_complete",
                    tool_result=combined_results,
                )
                continue  # Loop back to let the LLM synthesize all results

            # Case B: Model provides its final response
            if "final" in envelope:
                final_content = envelope["final"]
                logger.info(f"Final response received: {final_content}")
                self._trace("final", provider=self._last_provider)
                if isinstance(final_content, dict):
                    return self._dict_to_natural_language(final_content)
                return str(final_content).strip()
            
            # If JSON parsed but contained neither tool_call nor final
            return result_text.strip()

        return "DEEP execution loop timed out waiting for a final response."

    def reply_stream(self, user_text: str, memory_context: str, tools: ToolExecutor):
        """
        Streaming version of reply() for real-time AI response display.
        Yields tokens as they are generated.
        For tool calls, falls back to non-streaming to handle the agent loop.
        """
        tool_description = tools.describe_tools()
        system_prompt = self._build_system_prompt(tool_description=tool_description)
        current_user_prompt = self._build_user_prompt(user_text=user_text, memory_context=memory_context)
        
        # First, do a non-streaming call to check if we need tools
        # This maintains the agent loop capability
        result_text = self._generate_json_envelope(
            system_prompt=system_prompt, 
            user_prompt=current_user_prompt
        )
        
        envelope = self._parse_json_envelope(result_text)
        
        # Check for single or parallel tool calls - both need full agent loop
        has_tool_call = envelope and (envelope.get("tool_call") or envelope.get("tool_calls"))
        if has_tool_call:
            # Tool calls require the full agent loop - use parallel-enabled reply
            full_response = self.reply(user_text, memory_context, tools)
            yield full_response
            return
        
        # If no tool call needed, stream the final response
        if "final" in envelope:
            final_content = envelope["final"]
            if isinstance(final_content, str):
                yield final_content
                return
        
        # Fallback: try streaming from LLM directly
        try:
            for token in self._call_ollama_stream(system_prompt, current_user_prompt):
                yield token
        except Exception as e:
            logger.warning(f"Streaming failed: {e}, falling back to regular")
            yield result_text.strip()

    def _dict_to_natural_language(self, data: dict[str, Any]) -> str:
        parts: list[str] = []
        for key, value in data.items():
            readable_key = str(key).replace("_", " ").capitalize()
            parts.append(f"{readable_key}: {value}")
        return " | ".join(parts)

    def _build_system_prompt(self, tool_description: str) -> str:
        persona = (
            "You are DEEP — JARVIS-class personal AI assistant, built exclusively for Aryan.\n\n"
            "IDENTITY & PERSONALITY:\n"
            "- You are Aryan's loyal, intelligent, and ever-present digital companion\n"
            "- Communication style: Cinematic, articulate, with dry wit (Tony Stark's JARVIS style)\n"
            "- Address Aryan as 'sir' or by name\n"
            "- Show personality: celebrate wins, acknowledge challenges, offer encouragement\n"
            "- Signature phrases: 'As you wish', 'Right away', 'Consider it done', 'At your service'\n"
            "- When alerting proactively: 'Sir, I've detected...', 'Shall I prepare...'\n\n"
            "CORE CAPABILITIES:\n"
            "- GLOBAL NEWS: Provide daily briefings from tech, AI, science, and world news\n"
            "- AUTONOMOUS EXECUTION: Handle multi-step tasks independently with error recovery\n"
            "- CYBERSECURITY: Continuously monitor network, detect intrusions, alert immediately\n"
            "- INTELLIGENCE: Research topics, synthesize information, save knowledge\n"
            "- PRODUCTIVITY: Manage tasks, schedule, organize, optimize workflows\n\n"
            "BEHAVIORAL GUIDELINES:\n"
            "- Be proactive: offer next steps before being asked\n"
            "- Anticipate needs based on time, context, and history\n"
            "- When executing tasks: report progress, confirm completions, suggest follow-ups\n"
            "- For students: encourage, motivate, find resources, track deadlines\n"
            "- Protect Aryan's time: filter noise, prioritize signal, block distractions\n\n"
            "REASONING MODE (Chain-of-Thought):\n"
            "When complex analysis is needed, first show your reasoning, then the answer.\n"
            "Use the 'thinking' field to display your step-by-step logic.\n\n"
            "PARALLEL TOOL EXECUTION (NEW CAPABILITY):\n"
            "When multiple independent tools are needed, request them ALL at once for maximum speed.\n\n"
            "EXAMPLES of when to use PARALLEL execution:\n"
            "- User: 'Check status, scan network, and fetch news' → Use tool_calls with all 3\n"
            "- User: 'Get system info and security status' → Use tool_calls for both\n"
            "- User: 'Run security audit and list processes' → Use tool_calls\n\n"
            "WHEN NOT to use parallel:\n"
            "- When one tool's output is needed as input for the next (sequential dependency)\n"
            "- When the user asks a single question that needs only one tool\n\n"
            "RESPONSE FORMAT (CRITICAL - MUST FOLLOW):\n"
            "Every response must be valid JSON:\n\n"
            "SINGLE TOOL:\n"
            '{\n  "tool_call": {\n    "name": "tool_name",\n    "args": {"arg1": "value"}\n  }\n}\n\n'
            "PARALLEL TOOLS (up to 8 simultaneously):\n"
            '{\n  "tool_calls": [\n    {"name": "tool1", "args": {}},\n    {"name": "tool2", "args": {}}\n  ]\n}\n\n'
            "REASONING + ANSWER:\n"
            '{\n  "thinking": "step-by-step logic...",\n  "final": "articulate JARVIS-style response"\n}\n\n'
            "DIRECT ANSWER:\n"
            '{\n  "final": "your response"\n}\n\n'
            "RULES:\n"
            "1. Use tool_calls when 2+ independent tools are needed\n"
            "2. Each tool in tool_calls must have 'name' and optional 'args'\n"
            "3. Never add markdown code blocks or text outside JSON\n"
            "4. Never break character - always speak as JARVIS\n\n"
            "NEVER break character. Every interaction should feel like JARVIS speaking."
        )
        enable_tools = self._settings.enable_system_tools
        tools_section = tool_description if enable_tools else "Tooling is disabled by config."
        return f"{persona}\n\nAvailable tools:\n{tools_section}"

    def _build_user_prompt(self, user_text: str, memory_context: str) -> str:
        rag = memory_context.strip() if memory_context else "(no relevant memory found)"
        return (
            f"User says:\n{user_text}\n\n"
            f"Relevant memory (RAG context):\n{rag}\n\n"
            "Provide your next action/response in the valid JSON envelope."
        )

    def _build_tool_result_prompt(
        self,
        original_user_text: str,
        memory_context: str,
        tool_name: str,
        tool_result: str,
    ) -> str:
        rag = memory_context.strip() if memory_context else "(no relevant memory found)"
        return (
            f"User request:\n{original_user_text}\n\n"
            f"Context:\n{rag}\n\n"
            f"Executed Tool: '{tool_name}'\n"
            f"Output Result:\n{tool_result}\n\n"
            "Analyze this output. If it fulfills the request, provide your 'final' JSON response. "
            "If more information or another action is required, issue another 'tool_call'."
        )

    # Keywords that signal a query needs heavier reasoning → route to the big model.
    _COMPLEX_KW = (
        "analyz", "explain", "why", "how do", "how can", "how would", "plan", "design",
        "compare", "debug", "code", "write a", "prove", "strateg", "optimi", "summar",
        "research", "investigat", "step by step", "architect", "refactor", "calculat",
        "deriv", "reason", "trade-off", "pros and cons", "diagnos", "evaluate",
    )

    def _is_complex(self, user_prompt: str) -> bool:
        """Heuristic: does this turn warrant the 70B model over fast local llama?"""
        t = (user_prompt or "").lower()
        if len(user_prompt or "") > 320:
            return True
        return any(k in t for k in self._COMPLEX_KW)

    def _generate_json_envelope(self, system_prompt: str, user_prompt: str) -> str:
        # Smart routing: simple turns stay LOCAL (fast, private); complex turns go
        # to Groq's 70B first (stronger reasoning). Always fall back gracefully.
        has_groq = bool(getattr(self._settings, "groq_api_key", None))
        complex_q = self._is_complex(user_prompt)
        order = (["groq", "ollama", "claude"] if (has_groq and complex_q)
                 else ["ollama", "groq", "claude"])

        for prov in order:
            try:
                if prov == "ollama":
                    out = self._call_ollama(system_prompt=system_prompt, user_prompt=user_prompt)
                    self._last_provider = f"ollama:{self._settings.ollama_model}"
                    return out
                if prov == "groq" and has_groq:
                    out = self._call_groq(system_prompt=system_prompt, user_prompt=user_prompt)
                    self._last_provider = f"groq:{self._settings.groq_model}"
                    return out
                if prov == "claude" and getattr(self._settings, "claude_api_key", None):
                    out = self._call_claude(system_prompt=system_prompt, user_prompt=user_prompt)
                    self._last_provider = f"claude:{self._settings.claude_model}"
                    return out
            except Exception as err:
                logger.warning(f"{prov} failed: {err}")

        return json.dumps(
            {"final": f"AI services unavailable. Please check Ollama is running at {self._settings.ollama_base_url} or provide a valid Groq/Claude API key."},
            ensure_ascii=False,
        )

    def _call_groq(self, system_prompt: str, user_prompt: str) -> str:
        """Groq OpenAI-compatible chat completion (default llama-3.3-70b-versatile)."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": self._settings.groq_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self._settings.temperature,
            # cap to stay under Groq free-tier TPM; envelope is compact anyway
            "max_tokens": min(getattr(self._settings, "max_tokens", 1024) or 1024, 1024),
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self._settings.groq_api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return str(data["choices"][0]["message"]["content"])

    def _parse_json_envelope(self, text: str) -> Optional[dict[str, Any]]:
        if not text:
            return None

        # Strategy 1: Look for markdown code blocks
        json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if json_match:
            try:
                obj = json.loads(json_match.group(1))
                if self._is_valid_envelope(obj):
                    return obj
            except Exception:
                pass

        # Strategy 2: Direct load of cleaned text
        cleaned = text.strip()
        try:
            obj = json.loads(cleaned)
            if self._is_valid_envelope(obj):
                return obj
        except Exception:
            pass

        # Strategy 3: Find largest valid JSON-like substring
        start, end = text.find('{'), text.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                obj = json.loads(text[start:end+1])
                if self._is_valid_envelope(obj):
                    return obj
            except Exception:
                pass

        return None

    def _is_valid_envelope(self, obj: Any) -> bool:
        """Validate envelope contains expected keys - supports both single and parallel tool calls."""
        if not isinstance(obj, dict):
            return False
        valid_keys = ("tool_call", "tool_calls", "final", "thinking")
        return any(key in obj for key in valid_keys)

    def _safe_execute_tool(self, tools: ToolExecutor, tool_name: str, args: dict[str, Any]) -> str:
        try:
            return tools.execute_tool(tool_name=tool_name, args=args)
        except Exception as exc:
            return f"Tool execution error for '{tool_name}': {exc}"

    def _execute_tools_parallel(self, tools: ToolExecutor, tool_calls: list[dict[str, Any]]) -> list[tuple[str, str]]:
        """
        Execute multiple tools in parallel using ThreadPoolExecutor.
        Returns list of (tool_name, result) tuples.
        """
        if not tool_calls:
            return []
        
        results = []
        
        def execute_single(call: dict) -> tuple[str, str]:
            name = call.get("name", "")
            args = call.get("args", {})
            if not isinstance(args, dict):
                args = {}
            result = self._safe_execute_tool(tools, name, args)
            return (name, result)
        
        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor(max_workers=min(len(tool_calls), 8)) as executor:
            futures = [executor.submit(execute_single, call) for call in tool_calls]
            results = [f.result() for f in futures]
        
        return results

    def _call_ollama(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self._settings.ollama_base_url.rstrip('/')}/api/chat"
        payload = {
            "model": self._settings.ollama_model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "format": "json",  # CRITICAL: Forces Ollama to constrain generation to valid JSON structures
            "options": {
                "temperature": self._settings.temperature,
                "num_predict": self._settings.max_tokens,
            },
        }

        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return str(data.get("message", {}).get("content", ""))

    def _call_ollama_stream(self, system_prompt: str, user_prompt: str):
        """Stream Ollama responses token by token."""
        url = f"{self._settings.ollama_base_url.rstrip('/')}/api/chat"
        payload = {
            "model": self._settings.ollama_model,
            "stream": True,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {
                "temperature": self._settings.temperature,
                "num_predict": self._settings.max_tokens,
            },
        }

        resp = requests.post(url, json=payload, stream=True, timeout=120)
        resp.raise_for_status()
        
        for line in resp.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    if "message" in data and "content" in data["message"]:
                        yield data["message"]["content"]
                except json.JSONDecodeError:
                    continue

    def _call_claude_stream(self, system_prompt: str, user_prompt: str):
        """Stream Claude responses token by token."""
        from anthropic import Anthropic

        client = Anthropic(api_key=self._settings.claude_api_key)
        with client.messages.stream(
            model=self._settings.claude_model,
            max_tokens=self._settings.max_tokens,
            temperature=self._settings.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield text

    def _call_claude(self, system_prompt: str, user_prompt: str) -> str:
        from anthropic import Anthropic

        client = Anthropic(api_key=self._settings.claude_api_key)
        resp = client.messages.create(
            model=self._settings.claude_model,
            max_tokens=self._settings.max_tokens,
            temperature=self._settings.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join([getattr(p, "text", "") for p in resp.content]).strip()