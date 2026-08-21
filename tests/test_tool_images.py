"""Images travelling from a tool to a model that can look at them.

DEEP's tool channel was text, so a tool whose whole point is a picture —
urlscan's analyze_screenshot — arrived as "[image omitted]": advertised, and
silently not happening. These cover the path that fixed it, and the two ways it
could go wrong in a manner nobody notices.

The one that matters most is the text-only case. DEEP's default model
(llama3.2) cannot see. A model handed a screenshot it cannot read, with no
mention that a screenshot exists, answers from the surrounding text as though
it had looked at the page — which for a phishing capture is precisely the
confident wrong answer this whole feature exists to produce evidence against.
"""
from __future__ import annotations

import pytest

from core.domain.models import ToolImage, ToolResult
from core.infrastructure.async_brain import AsyncBrain
from core.infrastructure.llm_clients import ClaudeClient, OllamaClient, _ollama_model_sees


class RecordingLLM:
    """Captures what the brain sends, including whether images came along."""

    model_name = "recording"
    is_available = True
    _settings = None

    def __init__(self, replies, supports_images: bool):
        self._replies = list(replies)
        self.supports_images = supports_images
        self.calls: list[dict] = []

    async def generate_stream(self, system_prompt, user_prompt, **kwargs):
        self.calls.append({"user_prompt": user_prompt, "images": kwargs.get("images") or []})
        yield self._replies.pop(0) if self._replies else "Done."

    async def generate(self, *a, **k):
        return ""

    def health_check(self):
        return True


class ImageTool:
    """A minimal executor whose tool returns a picture."""

    def __init__(self, images):
        self._images = images

    def describe_tools(self):
        return "AVAILABLE TOOLS:\n- look: look at a page | Args: {}"

    def list_tools(self):
        return ["look"]

    @property
    def available_tools(self):
        return {"look": {"description": "look at a page", "args": {}}}

    async def execute_tool(self, name, args):
        return ToolResult(True, "Screenshot of evil.test, served from evil.test",
                          name, images=list(self._images))


def _brain(llm, **kw):
    brain = AsyncBrain(llm, enable_tools=True, **kw)
    brain.persona = None
    return brain


def _png(kb: int = 1) -> ToolImage:
    return ToolImage(data="A" * (kb * 1024), mime_type="image/png", label="a screenshot")


async def _run(brain, tools):
    return "".join([t async for t in brain.process_stream("is it phishing?", "", tools)])


# ── the happy path ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_an_image_reaches_a_model_that_can_see():
    llm = RecordingLLM(['[TOOL:{"name": "look", "args": {}}]', "It is a fake login."],
                       supports_images=True)
    await _run(_brain(llm, max_loops=2), ImageTool([_png()]))

    assert len(llm.calls) == 2
    assert llm.calls[0]["images"] == [], "nothing to send before the tool ran"
    assert len(llm.calls[1]["images"]) == 1, "the picture must ride with the next request"


@pytest.mark.asyncio
async def test_an_image_is_sent_once_not_every_loop():
    """Re-sending would re-bill the same picture and crowd out the text."""
    llm = RecordingLLM(
        ['[TOOL:{"name": "look", "args": {}}]', '[TOOL:{"name": "look", "args": {"a": 1}}]', "Done."],
        supports_images=True,
    )
    await _run(_brain(llm, max_loops=3), ImageTool([_png()]))

    sent = [len(c["images"]) for c in llm.calls]
    assert sent[1] == 1
    assert sent[2] == 1, "the second call's own image, not the first one again"


# ── the honesty path ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_text_only_model_is_told_the_image_exists():
    llm = RecordingLLM(['[TOOL:{"name": "look", "args": {}}]', "I cannot see it."],
                       supports_images=False)
    await _run(_brain(llm, max_loops=2), ImageTool([_png()]))

    follow_up = llm.calls[1]["user_prompt"]
    assert llm.calls[1]["images"] == [], "never send a picture to a model that cannot read it"
    assert "cannot view images" in follow_up
    assert "Do not describe or judge the image contents" in follow_up
    assert "a screenshot" in follow_up, "say what was withheld"


@pytest.mark.asyncio
async def test_the_note_is_not_added_when_there_is_no_image():
    llm = RecordingLLM(['[TOOL:{"name": "look", "args": {}}]', "Done."], supports_images=False)
    await _run(_brain(llm, max_loops=2), ImageTool([]))

    assert "cannot view images" not in llm.calls[1]["user_prompt"]


# ── budget ───────────────────────────────────────────────────────────────────


def test_an_oversized_image_is_refused_by_the_turn_budget():
    brain = AsyncBrain.__new__(AsyncBrain)
    huge = ToolImage(data="A" * (AsyncBrain.MAX_IMAGE_BYTES_PER_TURN * 2), label="huge")

    assert brain._admit_images("look", [huge]) == []


def test_the_number_of_images_per_turn_is_capped():
    brain = AsyncBrain.__new__(AsyncBrain)
    many = [_png() for _ in range(AsyncBrain.MAX_IMAGES_PER_TURN + 5)]

    assert len(brain._admit_images("look", many)) == AsyncBrain.MAX_IMAGES_PER_TURN


def test_images_within_budget_all_pass():
    brain = AsyncBrain.__new__(AsyncBrain)
    assert len(brain._admit_images("look", [_png(), _png()])) == 2


# ── provider capability ──────────────────────────────────────────────────────


def test_deeps_default_local_model_reports_that_it_cannot_see():
    """llama3.2 is text-only. Claiming otherwise is how the wrong answer starts."""
    assert OllamaClient(model="llama3.2").supports_images is False
    assert _ollama_model_sees("llava:13b") is True
    assert _ollama_model_sees("llama3.2-vision") is True


def test_the_vision_override_exists_for_a_model_we_do_not_know(monkeypatch):
    monkeypatch.setenv("DEEP_OLLAMA_VISION", "1")
    assert _ollama_model_sees("some-new-vlm") is True


def test_ollama_attaches_images_only_when_the_model_can_use_them():
    image = _png()
    seeing = OllamaClient(model="llava")._payload("s", "u", stream=True, images=[image])
    blind = OllamaClient(model="llama3.2")._payload("s", "u", stream=True, images=[image])

    assert seeing["images"] == [image.data]
    assert "images" not in blind


def test_claude_puts_the_image_before_the_question():
    """A picture arriving after the question is one the reasoning skipped."""
    blocks = ClaudeClient._content_blocks("what is this?", [_png()])

    assert [b["type"] for b in blocks] == ["image", "text"]
    assert blocks[0]["source"]["media_type"] == "image/png"


def test_claude_sends_a_plain_string_when_there_are_no_images():
    assert ClaudeClient._content_blocks("hello", []) == "hello"
    assert ClaudeClient._content_blocks("hello", None) == "hello"


# ── the runtime client: RoutingLLM ───────────────────────────────────────────
#
# The brain is handed a RoutingLLM at runtime, not a bare client, so the
# capability answer and the per-provider shaping have to be right *here* or the
# whole path works only in tests.


def _routing(**settings):
    from core.llm.router import RoutingLLM

    base = {
        "ollama_model": "llama3.2", "groq_model": "llama-3.3-70b", "groq_api_key": "",
        "gemini_model": "gemini-2.0-flash", "gemini_api_key": "",
        "claude_model": "claude-sonnet-4-5", "claude_api_key": "",
        "prefer_claude_when_available": False,
        "chat_provider_order": "groq,gemini,claude",
        "chat_max_tokens_complex": 4096, "llm_retry_attempts": 1, "llm_retry_backoff_s": 0.1,
    }
    base.update(settings)
    cfg = type("S", (), base)()
    return RoutingLLM(OllamaClient(model=base["ollama_model"]), cfg)


def test_routing_says_it_cannot_see_when_nothing_reachable_can():
    """Local llama3.2, no cloud keys — an honest no."""
    assert _routing().supports_images is False


def test_routing_says_it_can_see_when_a_cloud_provider_can():
    assert _routing(groq_api_key="k" * 20).supports_images is True


def test_routing_says_it_can_see_when_the_local_model_can():
    assert _routing(ollama_model="llava").supports_images is True


def test_a_gemini_only_setup_reports_vision():
    assert _routing(gemini_api_key="k" * 20, chat_provider_order="gemini").supports_images is True


def test_claude_content_leads_with_the_image():
    from core.llm.router import RoutingLLM

    blocks = RoutingLLM._shape_for("claude", "what is this?", [_png()])
    assert [b["type"] for b in blocks] == ["image", "text"]
    assert blocks[0]["source"]["type"] == "base64"


def test_groq_content_uses_the_openai_data_uri_shape():
    from core.llm.router import RoutingLLM

    blocks = RoutingLLM._shape_for("groq", "what is this?", [_png()])
    assert [b["type"] for b in blocks] == ["image_url", "text"]
    assert blocks[0]["image_url"]["url"].startswith("data:image/png;base64,")


def test_no_images_means_a_plain_string_for_every_provider():
    from core.llm.router import RoutingLLM

    for provider in ("claude", "groq", "gemini"):
        assert RoutingLLM._shape_for(provider, "hello", []) == "hello"


# ── Gemini ───────────────────────────────────────────────────────────────────
#
# Gemini does not take typed blocks like the others. It takes native `parts`
# with inline_data and a bare base64 payload, and its streamer used to flatten
# every message to {"text": content} — so a block list would have been
# stringified into the prompt and the model shown the characters
# "[{'inline_data'...". That is worse than refusing the image, because it looks
# like it worked.


def test_gemini_content_is_native_parts_not_typed_blocks():
    from core.llm.router import RoutingLLM

    parts = RoutingLLM._shape_for("gemini", "what is this?", [_png()])

    assert list(parts[0]) == ["inline_data"]
    assert parts[0]["inline_data"]["mime_type"] == "image/png"
    assert parts[-1] == {"text": "what is this?"}
    assert "type" not in parts[0], "typed blocks are Claude/OpenAI, not Gemini"


def test_gemini_gets_a_bare_base64_payload_not_a_data_uri():
    from core.llm.router import RoutingLLM

    parts = RoutingLLM._shape_for("gemini", "q", [_png()])
    assert not parts[0]["inline_data"]["data"].startswith("data:")


def test_the_gemini_streamer_forwards_a_parts_list_untouched():
    from core.llm.providers import _gemini_parts

    parts = [{"inline_data": {"mime_type": "image/png", "data": "QUJD"}}, {"text": "q"}]
    assert _gemini_parts(parts) is parts


def test_the_gemini_streamer_still_wraps_plain_text():
    from core.llm.providers import _gemini_parts

    assert _gemini_parts("hello") == [{"text": "hello"}]


def test_the_gemini_request_body_carries_the_image():
    """End to end through the real streamer, with the network faked at the SSE call."""
    from unittest.mock import patch

    from core.llm import providers
    from core.llm.router import RoutingLLM

    captured = {}

    def fake_sse(name, url, headers, body, extract, timeout):
        captured["body"] = body

        async def gen():
            if False:
                yield ""

        return gen()

    msgs = [{"role": "user", "content": RoutingLLM._shape_for("gemini", "is this phishing?", [_png()])}]
    with patch.object(providers, "_stream_sse", fake_sse):
        providers.stream_gemini_tokens("You are DEEP.", msgs, "gemini-2.0-flash", "KEY")

    parts = captured["body"]["contents"][0]["parts"]
    assert "inline_data" in parts[0], "the image must survive into the request"
    assert parts[1]["text"] == "is this phishing?"
    assert captured["body"]["system_instruction"]["parts"] == [{"text": "You are DEEP."}]


def test_a_text_only_gemini_request_is_unchanged():
    """The common path must not regress for the sake of the rare one."""
    from unittest.mock import patch

    from core.llm import providers

    captured = {}

    def fake_sse(name, url, headers, body, extract, timeout):
        captured["body"] = body

        async def gen():
            if False:
                yield ""

        return gen()

    with patch.object(providers, "_stream_sse", fake_sse):
        providers.stream_gemini_tokens("sys", [{"role": "user", "content": "hi"}], "m", "k")

    assert captured["body"]["contents"][0]["parts"] == [{"text": "hi"}]


def test_gemini_is_no_longer_skipped_when_an_image_is_present():
    """It used to be filtered out of the chain; now it is a valid destination."""
    from core.llm.router import RoutingLLM

    assert "gemini" in RoutingLLM._IMAGE_CAPABLE_PROVIDERS
