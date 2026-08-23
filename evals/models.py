"""Model adapters for the eval harness.

A `Model` is anything that can turn (system_prompt, user_prompt) into a
completion string. Keeping that surface tiny means the harness can run against
a local Ollama, a cloud model through DEEP's own router, or a scripted stub —
and the scripted one is what lets the harness itself be unit-tested offline,
without which the evals would be a thing nobody can trust either.
"""
from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Dict, List, Optional, Protocol


class Model(Protocol):
    """Anything that completes a prompt."""

    name: str

    async def complete(self, system_prompt: str, user_prompt: str) -> str: ...


class ScriptedModel:
    """Returns canned completions, keyed by a substring of the user prompt.

    For testing the harness, not the assistant. A scripted run must never be
    reported as an eval result — `run_suite` records the model name, and this
    one says so loudly.
    """

    name = "scripted (not a real model)"

    def __init__(self, replies: Dict[str, str], default: str = "I can help with that.") -> None:
        self._replies = replies
        self._default = default
        self.calls: List[tuple[str, str]] = []

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        for fragment, reply in self._replies.items():
            if fragment.lower() in user_prompt.lower():
                return reply
        return self._default


class CallableModel:
    """Wraps a plain function, sync or async."""

    def __init__(self, fn: Callable[[str, str], Any], name: str = "callable") -> None:
        self._fn = fn
        self.name = name

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        out = self._fn(system_prompt, user_prompt)
        if isinstance(out, Awaitable):
            out = await out
        return str(out)


class OllamaModel:
    """A local model over Ollama's HTTP API — DEEP's default brain.

    Deliberately not routed through DEEP's multi-LLM router: an eval wants one
    named model, reproducibly, not whichever provider the router failed over to
    this minute. `temperature=0` for the same reason — tool choice should be
    measured at the model's most decisive, and a run you cannot repeat is not a
    baseline.
    """

    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434",
        timeout_s: float = 120.0,
        temperature: float = 0.0,
    ) -> None:
        self.model = model
        self.name = f"ollama:{model}"
        self._base = base_url.rstrip("/")
        self._timeout = timeout_s
        self._temperature = temperature

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        import aiohttp

        payload = {
            "model": self.model,
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": False,
            "options": {"temperature": self._temperature},
        }
        timeout = aiohttp.ClientTimeout(total=self._timeout)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.post(f"{self._base}/api/generate", json=payload) as resp:
                resp.raise_for_status()
                data = await resp.json()
        return str(data.get("response", ""))

    async def available(self) -> Optional[str]:
        """None when usable, else why not — so `run.py` can say rather than hang."""
        try:
            import aiohttp
        except ImportError:
            return "aiohttp is not installed"
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as s:
                async with s.get(f"{self._base}/api/tags") as r:
                    if r.status != 200:
                        return f"Ollama returned HTTP {r.status}"
                    names = [m.get("name", "") for m in (await r.json()).get("models", [])]
        except asyncio.TimeoutError:
            return f"Ollama did not answer at {self._base} within 5s"
        except Exception as exc:  # noqa: BLE001
            return f"Ollama unreachable at {self._base}: {type(exc).__name__}"
        if names and not any(n.split(":")[0] == self.model.split(":")[0] for n in names):
            return f"model {self.model!r} is not pulled (have: {', '.join(names[:5])})"
        return None


class AnthropicModel:
    """A Claude model through the Anthropic SDK, for a stronger baseline.

    Useful for separating "the tool descriptions are ambiguous" from "the local
    model is too small to follow them" — which look identical in a single-model
    score, and have completely different fixes.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-5",
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> None:
        self.model = model
        self.name = f"anthropic:{model}"
        self._max_tokens = max_tokens
        self._temperature = temperature

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic()
        message = await client.messages.create(
            model=self.model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )

    async def available(self) -> Optional[str]:
        import os

        try:
            import anthropic  # noqa: F401
        except ImportError:
            return "the anthropic package is not installed"
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return "ANTHROPIC_API_KEY is not set"
        return None
