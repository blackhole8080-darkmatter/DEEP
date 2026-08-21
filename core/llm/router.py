"""
core/llm/router.py

LLM routing clients for DEEP, extracted from the server monolith.

- RoutingLLM   : tool-capable client for AsyncBrain — ordered cloud fallback
                 chain (per chat_provider_order) → local Ollama, with retry/backoff.
- GroqAgentLLM : fast Groq adapter for sub-agents (token-capped per step).

Both depend only on the streaming provider functions, not on server globals.
"""

from __future__ import annotations

import asyncio

from .providers import stream_groq_tokens, stream_gemini_tokens, stream_claude_tokens


class RoutingLLM:
    """Tool-capable routing client for AsyncBrain.

    AsyncBrain's [TOOL:] parsing is model-agnostic, so any provider that streams
    text can drive tools. This client builds an ordered cloud fallback chain
    (Groq → Gemini → Claude, per `chat_provider_order`) and finally local Ollama,
    so tool-calling works across every configured cloud provider — not just Groq.
    Exposes last_provider for the reasoning panel.
    """
    #: Providers whose streamer accepts multimodal content in the messages list.
    #: Each wants a different shape — see _shape_for — and a provider only
    #: belongs here once its streamer actually understands that shape. Gemini
    #: was absent until stream_gemini_tokens learned to forward a parts list;
    #: before that a content list would have been stringified into the prompt,
    #: showing the model the characters "[{'inline_data'..." instead of an
    #: image, which is worse than refusing it because it looks like it worked.
    _IMAGE_CAPABLE_PROVIDERS = frozenset({"claude", "groq", "gemini"})

    def __init__(self, local_client, app_settings):
        self._local = local_client
        self._settings = app_settings
        self.last_provider = f"ollama:{app_settings.ollama_model}"
        self.config = type("Cfg", (), {"model": app_settings.groq_model})()

    @property
    def supports_images(self) -> bool:
        """True when *some* reachable provider could actually look at a picture.

        The brain asks this before deciding whether to send an image or to tell
        the user it cannot see one, so a wrong answer here is the difference
        between an honest "I can't view that" and a confident description of a
        page nobody looked at.
        """
        if getattr(self._local, "supports_images", False):
            return True
        return any(
            provider in self._IMAGE_CAPABLE_PROVIDERS
            for provider, _model, _key, _streamer in self._cloud_chain()
        )

    @staticmethod
    def _shape_for(provider: str, user_prompt: str, images) -> object:
        """Per-provider message content. Images lead; the question follows.

        A picture that arrives after the question is one the reasoning was
        already written without.
        """
        if not images:
            return user_prompt
        if provider == "gemini":
            # Gemini takes native `parts`, not typed blocks: inline_data with a
            # bare base64 payload, no data-URI prefix. Returned in Gemini's own
            # shape so stream_gemini_tokens can forward it untouched.
            parts = [
                {"inline_data": {"mime_type": img.mime_type, "data": img.data}}
                for img in images
            ]
            parts.append({"text": user_prompt})
            return parts
        if provider == "claude":
            blocks = [
                {"type": "image",
                 "source": {"type": "base64", "media_type": img.mime_type, "data": img.data}}
                for img in images
            ]
        else:  # groq and any other OpenAI-compatible chat completions endpoint
            blocks = [
                {"type": "image_url",
                 "image_url": {"url": f"data:{img.mime_type};base64,{img.data}"}}
                for img in images
            ]
        blocks.append({"type": "text", "text": user_prompt})
        return blocks

    def _cloud_chain(self):
        """Ordered (provider, model, key, streamer) tuples for configured clouds."""
        s = self._settings
        avail = {
            "groq": (s.groq_model, s.groq_api_key, stream_groq_tokens,
                     bool(s.groq_api_key and len(s.groq_api_key) > 10)),
            "gemini": (s.gemini_model, s.gemini_api_key, stream_gemini_tokens,
                       bool(s.gemini_api_key and len(s.gemini_api_key) > 10)),
            # Respect the same opt-in gate the fast chat path uses for Claude.
            "claude": (s.claude_model, s.claude_api_key, stream_claude_tokens,
                       bool(s.prefer_claude_when_available and s.claude_api_key and len(s.claude_api_key) > 20)),
        }
        order = [p.strip().lower() for p in s.chat_provider_order.split(",") if p.strip()]
        chain = []
        for p in order:
            entry = avail.get(p)
            if entry and entry[3]:
                model, key, streamer, _ = entry
                chain.append((p, model, key, streamer))
        return chain

    async def generate_stream(self, system_prompt: str, user_prompt: str,
                              temperature: float = 0.7, max_tokens: int = 1024, **kw):
        images = list(kw.pop("images", None) or [])
        # Honour the caller's budget up to a configurable ceiling (was a flat
        # 1024 that truncated the 70B model on hard queries). Groq 429s are now
        # handled by retry/backoff + provider fallthrough rather than a tiny cap.
        ceiling = int(getattr(self._settings, "chat_max_tokens_complex", 4096))
        cap = min(max_tokens, ceiling)
        attempts = max(1, int(getattr(self._settings, "llm_retry_attempts", 1)) + 1)
        backoff = float(getattr(self._settings, "llm_retry_backoff_s", 0.8))
        try:
            from core import telemetry as _tel
        except Exception:
            _tel = None
        _start = asyncio.get_event_loop().time()
        _fallthroughs = 0
        _tokens_in = _tel.estimate_tokens(system_prompt + user_prompt) if _tel else 0
        for provider, model, key, streamer in self._cloud_chain():
            # A provider that cannot read the image would be shown the question
            # with the evidence missing and answer anyway, which is worse than
            # falling through to one that can.
            if images and provider not in self._IMAGE_CAPABLE_PROVIDERS:
                continue
            msgs = [{"role": "user", "content": self._shape_for(provider, user_prompt, images)}]
            emitted = False
            _ttft = None
            _completion_chars = 0
            for attempt in range(attempts):
                try:
                    async for tok in streamer(system_prompt, msgs, model, key, cap):
                        if not emitted:
                            _ttft = (asyncio.get_event_loop().time() - _start) * 1000
                        emitted = True
                        _completion_chars += len(tok or "")
                        self.last_provider = f"{provider}:{model}"
                        yield tok
                    if emitted:
                        if _tel:  # record once the successful stream completes
                            _tel.record_llm(provider, model, latency_ms=_ttft, ok=True,
                                            fallthroughs=_fallthroughs, tokens_in=_tokens_in,
                                            tokens_out=_completion_chars // 4)
                        return
                    break  # provider returned nothing — try next provider
                except Exception as e:
                    # Once tokens have been emitted we can't safely retry/resend.
                    if emitted:
                        return
                    transient = any(s in str(e).lower() for s in ("429", "timeout", "timed out", "rate", "503", "502", "500"))
                    if transient and attempt < attempts - 1:
                        print(f"[DEEP] {provider} transient error ({type(e).__name__}); "
                              f"retry {attempt + 1}/{attempts - 1} after {backoff}s")
                        await asyncio.sleep(backoff * (attempt + 1))
                        continue
                    print(f"[DEEP] {provider} brain stream failed, trying next provider: "
                          f"{type(e).__name__}: {str(e)[:160]}")
                    if _tel:
                        _tel.record_llm(provider, model, ok=False, fallthroughs=_fallthroughs,
                                        note=f"{type(e).__name__}: {str(e)[:120]}")
                    break  # move to next provider
            _fallthroughs += 1
        # Final fallback: local Ollama (always available, also tool-capable).
        self.last_provider = f"ollama:{self._settings.ollama_model}"
        if _tel:
            _tel.record_llm("ollama", self._settings.ollama_model, ok=True,
                            fallthroughs=_fallthroughs, note="final-fallback",
                            tokens_in=_tokens_in)
        async for tok in self._local.generate_stream(
            system_prompt=system_prompt, user_prompt=user_prompt,
            temperature=temperature, max_tokens=max_tokens, images=images, **kw
        ):
            yield tok

    async def generate(self, *a, **k):
        return await self._local.generate(*a, **k)

    async def health_check(self):
        # The brain is healthy if ANY provider can serve a request. Previously
        # this only probed local Ollama, so a working cloud chain (Groq/Gemini/
        # Claude) was reported "unreachable" whenever Ollama wasn't running.
        # A configured cloud key counts as available (same convention as the
        # per-provider clients) without spending a live call on every poll.
        if self._cloud_chain():
            return True
        try:
            return await self._local.health_check()
        except Exception:
            return False

    @property
    def model_name(self) -> str:
        """Report the provider actually at the head of the chain, so health and
        the reasoning panel don't mislabel (e.g. show a Groq model when only
        Ollama is live)."""
        chain = self._cloud_chain()
        if chain:
            p, model, _, _ = chain[0]
            return f"{p}:{model}"
        return f"ollama:{self._settings.ollama_model}"

    async def close(self):
        try:
            await self._local.close()
        except Exception:
            pass


class GroqAgentLLM:
    """Adapter so sub-agents run on fast Groq (same interface the factory expects)."""
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.model_name = model
        self.config = type("Cfg", (), {"model": model})()

    async def generate_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 1024, **_):
        # Cap per-step tokens to stay under Groq's free-tier per-minute limit (agents loop several times).
        capped = min(max_tokens, 700)
        async for tok in stream_groq_tokens(system_prompt, [{"role": "user", "content": user_prompt}], self.model, self.api_key, capped):
            yield tok

    async def generate(self, system_prompt: str, user_prompt: str, **kw):
        out = ""
        async for t in self.generate_stream(system_prompt, user_prompt, **kw):
            out += t
        return out

    async def health_check(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 10)
