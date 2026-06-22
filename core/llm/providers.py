"""
core/llm/providers.py

Streaming LLM provider clients for DEEP — extracted from the server monolith so
the chat/brain layers depend on a clean, testable provider module instead of
functions buried in server.py.

Each `stream_*_tokens` is an async generator yielding text tokens. Cloud providers
share `_stream_sse` (SSE plumbing); the local vision path uses Ollama directly.
All functions are self-contained: pass the model/key/prompt explicitly, no globals.
"""

from __future__ import annotations

import json


async def _stream_sse(provider: str, url: str, headers: dict, payload: dict, extract, timeout):
    """Shared SSE streaming loop for cloud LLM providers.

    `extract(parsed_json) -> Iterable[str]` pulls the text token(s) out of one
    decoded SSE data frame. The HTTP call, status check, `data:`/`[DONE]`
    handling, and JSON-decode guarding are identical across providers.
    """
    import aiohttp
    async with aiohttp.ClientSession() as sess:
        async with sess.post(url, headers=headers or None, json=payload, timeout=timeout) as resp:
            if resp.status != 200:
                raise Exception(f"{provider} {resp.status}: {(await resp.text())[:200]}")
            async for raw in resp.content:
                line = raw.decode("utf-8").strip()
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    for tok in extract(json.loads(data_str)):
                        if tok:
                            yield tok
                except (json.JSONDecodeError, KeyError, IndexError):
                    pass


def _claude_extract(d: dict):
    if d.get("type") == "content_block_delta" and d.get("delta", {}).get("type") == "text_delta":
        return (d["delta"].get("text", ""),)
    return ()


def _groq_extract(d: dict):
    return (d["choices"][0]["delta"].get("content"),)


def _gemini_extract(d: dict):
    return tuple(p["text"] for p in d["candidates"][0]["content"]["parts"] if "text" in p)


def _parse_data_url(data_url: str):
    """Split a 'data:image/png;base64,XXXX' URL into (media_type, base64_data).

    Accepts a bare base64 string too (defaults to image/png).
    """
    import re as _re
    m = _re.match(r"data:(?P<mt>[\w/+.-]+);base64,(?P<data>.+)$", data_url or "", _re.S)
    if m:
        mt = m.group("mt")
        # Anthropic accepts jpeg/png/gif/webp only.
        if mt not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
            mt = "image/png"
        return mt, m.group("data")
    return "image/png", (data_url or "")


async def stream_ollama_vision_tokens(system_prompt: str, prompt: str, image_b64: str,
                                      model: str, base_url: str, max_tokens: int = 1024):
    """Stream a vision response from a LOCAL Ollama model (e.g. llava) — fully
    offline, no API keys. Ollama's /api/generate accepts an `images` array of
    bare base64 strings (no data-URL prefix)."""
    import aiohttp
    url = f"{base_url.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "system": system_prompt,
        "prompt": prompt or "Describe this image for Aryan.",
        "images": [image_b64],
        "stream": True,
        "options": {"num_predict": max_tokens},
    }
    timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_read=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.content:
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("response"):
                    yield d["response"]
                if d.get("done"):
                    break


def stream_claude_tokens(system_prompt: str, messages: list, model: str, api_key: str, max_tokens: int = 1024):
    """Stream tokens directly from Claude's SSE API."""
    import aiohttp
    return _stream_sse(
        "Claude",
        "https://api.anthropic.com/v1/messages",
        {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        {"model": model, "max_tokens": max_tokens, "system": system_prompt,
         "messages": messages, "stream": True},
        _claude_extract,
        aiohttp.ClientTimeout(total=120, connect=10),
    )


def stream_groq_tokens(system_prompt: str, messages: list, model: str, api_key: str, max_tokens: int = 1024):
    """Stream tokens from Groq (OpenAI-compatible SSE). Very fast, free tier."""
    import aiohttp
    return _stream_sse(
        "Groq",
        "https://api.groq.com/openai/v1/chat/completions",
        {"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
        {"model": model, "max_tokens": max_tokens, "stream": True,
         "messages": [{"role": "system", "content": system_prompt}] + messages},
        _groq_extract,
        aiohttp.ClientTimeout(total=None, connect=10, sock_read=60),
    )


def stream_gemini_tokens(system_prompt: str, messages: list, model: str, api_key: str, max_tokens: int = 1024):
    """Stream tokens from Google Gemini (SSE). Free tier."""
    import aiohttp
    # Map OpenAI-style roles → Gemini roles (assistant → model)
    contents = [
        {"role": ("model" if m["role"] == "assistant" else "user"),
         "parts": [{"text": m["content"]}]}
        for m in messages
    ]
    return _stream_sse(
        "Gemini",
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        f":streamGenerateContent?alt=sse&key={api_key}",
        {},
        {"system_instruction": {"parts": [{"text": system_prompt}]},
         "contents": contents,
         "generationConfig": {"maxOutputTokens": max_tokens}},
        _gemini_extract,
        aiohttp.ClientTimeout(total=None, connect=10, sock_read=60),
    )
