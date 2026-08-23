"""Tests for DEEP's MCP client bridge.

DEEP shipped an MCP *server* — it could be driven by Claude Desktop. This is
the other direction: DEEP driving external MCP servers as tools of its own.
The subprocess and JSON-RPC transport are faked, because what needs defending
is DEEP's behaviour around a server it does not control:

* a server that will not start must cost one log line, not the assistant's boot
* a tool result must never arrive at the model unbounded, and a truncation must
  be visible in the text rather than silent
* a bridged tool must not shadow a native one
* shutdown must remove the tools along with the subprocess
"""
from __future__ import annotations

import asyncio
import base64
import dataclasses
import json
import sys

import pytest

from core.mcp import bridge as bridge_mod
from core.mcp.bridge import MCPBridge, render_full, render_result
from core.mcp.client import (
    MCPServerConnection,
    MCPTool,
    _read_spool,
    _startup_timeout,
    describe_exception,
)
from core.mcp.config import MCPServerConfig, configured_servers
from core.tools.registry import TOOL_SPECS


# ── fakes ────────────────────────────────────────────────────────────────────


class _Block:
    def __init__(self, text=None, kind="text", mime=""):
        if text is not None:
            self.text = text
        self.type = kind
        self.mimeType = mime


class _Result:
    def __init__(self, blocks, structured=None, is_error=False):
        self.content = blocks
        self.structuredContent = structured
        self.isError = is_error


class FakeConnection:
    """Stands in for a live server: fixed tools, scripted call outcomes."""

    def __init__(self, config, tools, outcome=None):
        self.config = config
        self.tools = tools
        self.last_error = ""
        self.calls: list[tuple[str, dict]] = []
        self._outcome = outcome or _Result([_Block("ok")])
        self.closed = False
        self.started = False

    @property
    def running(self):
        return self.started and not self.closed

    async def start(self):
        self.started = True
        return True

    async def call(self, name, args):
        self.calls.append((name, args))
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome

    async def aclose(self):
        self.closed = True


def _tool(name="ping", schema=None):
    return MCPTool(
        server_id="fake",
        name=name,
        description=f"{name} does a thing.",
        schema=schema or {
            "properties": {"url": {"type": "string", "description": "the target"}},
            "required": ["url"],
        },
    )


def _config(**kwargs):
    defaults = dict(id="fake", command=sys.executable, args=("-c", "pass"))
    defaults.update(kwargs)
    return MCPServerConfig(**defaults)


@pytest.fixture
def clean_registry():
    """Bridged tools land in the global registry; put it back afterwards."""
    before = dict(TOOL_SPECS)
    yield
    TOOL_SPECS.clear()
    TOOL_SPECS.update(before)


async def _bridge_with(monkeypatch, config, tools, outcome=None):
    connection = FakeConnection(config, tools, outcome)
    monkeypatch.setattr(bridge_mod, "MCPServerConnection", lambda cfg: connection)
    bridge = MCPBridge([config])
    report = await bridge.start()
    return bridge, connection, report


# ── configuration ────────────────────────────────────────────────────────────


def test_urlscan_ships_as_a_builtin_server():
    ids = [s.id for s in configured_servers()]
    assert "urlscan" in ids


def test_unavailability_is_explained_not_just_flagged():
    config = _config(id="nope", command="definitely-not-a-real-command")
    assert config.available is False
    assert "not on PATH" in config.unavailable_reason


def test_a_missing_env_var_stops_a_server_before_it_spawns(monkeypatch):
    monkeypatch.delenv("SOME_TOKEN", raising=False)
    config = _config(requires_env=("SOME_TOKEN",))
    assert config.unavailable_reason == "needs SOME_TOKEN in the environment"
    monkeypatch.setenv("SOME_TOKEN", "x")
    assert config.available is True


def test_unresolved_env_references_are_dropped_not_passed_through(monkeypatch):
    """A server must never receive the literal string '${URLSCAN_API_KEY}'."""
    monkeypatch.delenv("URLSCAN_API_KEY", raising=False)
    env = _config(env={"URLSCAN_API_KEY": "${URLSCAN_API_KEY}"}).resolved_env()
    assert "URLSCAN_API_KEY" not in env

    monkeypatch.setenv("URLSCAN_API_KEY", "secret")
    env = _config(env={"URLSCAN_API_KEY": "${URLSCAN_API_KEY}"}).resolved_env()
    assert env["URLSCAN_API_KEY"] == "secret"


def test_a_broken_config_file_is_ignored_not_fatal(tmp_path):
    path = tmp_path / "mcp_servers.json"
    path.write_text("{not json at all", encoding="utf-8")
    assert [s.id for s in configured_servers(path)] == [s.id for s in configured_servers("/nonexistent")]


def test_user_config_overrides_a_builtin_by_id(tmp_path):
    path = tmp_path / "mcp_servers.json"
    path.write_text(json.dumps({"servers": [{"id": "urlscan", "enabled": False}]}), encoding="utf-8")
    urlscan = next(s for s in configured_servers(path) if s.id == "urlscan")
    assert urlscan.enabled is False
    assert urlscan.unavailable_reason == "disabled in configuration"


def test_the_urlscan_bridge_does_not_duplicate_the_native_path():
    """Corpus search and assessment are already native; bridging them again
    would give the model two paths to the same evidence."""
    urlscan = next(s for s in configured_servers() if s.id == "urlscan")
    assert "assess_indicator" not in urlscan.allow_tools
    assert "search_by_domain" not in urlscan.allow_tools
    assert "scan_url" in urlscan.allow_tools


# ── registration ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tools_are_registered_under_a_server_prefix(monkeypatch, clean_registry):
    bridge, _, report = await _bridge_with(monkeypatch, _config(), [_tool("scan_url")])

    assert "fake_scan_url" in TOOL_SPECS
    assert report["tools_registered"] == 1
    assert TOOL_SPECS["fake_scan_url"].description.startswith("[fake]")
    await bridge.aclose()


@pytest.mark.asyncio
async def test_a_bridged_tool_never_shadows_a_native_one(monkeypatch, clean_registry):
    from core.tools.registry import ToolSpec

    async def native(ctx, args):
        return "native"

    TOOL_SPECS["fake_threat_lookup"] = ToolSpec("fake_threat_lookup", "native", {}, native)
    bridge, _, report = await _bridge_with(monkeypatch, _config(), [_tool("threat_lookup")])

    assert TOOL_SPECS["fake_threat_lookup"].description == "native"
    assert report["tools_registered"] == 0
    await bridge.aclose()


@pytest.mark.asyncio
async def test_the_json_schema_becomes_readable_argument_hints(monkeypatch, clean_registry):
    bridge, _, _ = await _bridge_with(monkeypatch, _config(), [_tool("scan_url")])

    hints = TOOL_SPECS["fake_scan_url"].args
    assert "required" in hints["url"] and "the target" in hints["url"]
    await bridge.aclose()


@pytest.mark.asyncio
async def test_calling_a_bridged_tool_reaches_the_server(monkeypatch, clean_registry):
    bridge, connection, _ = await _bridge_with(
        monkeypatch, _config(), [_tool("scan_url")], _Result([_Block("scanned")])
    )
    result = await TOOL_SPECS["fake_scan_url"].handler(None, {"url": "https://x.test"})

    assert result.ok and result.content == "scanned"
    assert connection.calls == [("scan_url", {"url": "https://x.test"})]
    await bridge.aclose()


@pytest.mark.asyncio
async def test_a_failing_call_is_an_error_result_not_an_exception(monkeypatch, clean_registry):
    bridge, _, _ = await _bridge_with(
        monkeypatch, _config(), [_tool("scan_url")], RuntimeError("server died")
    )
    result = await TOOL_SPECS["fake_scan_url"].handler(None, {})

    assert result.ok is False
    assert "server died" in result.content
    await bridge.aclose()


@pytest.mark.asyncio
async def test_an_unstartable_server_costs_no_tools_and_no_exception(clean_registry):
    bridge = MCPBridge([_config(id="nope", command="definitely-not-a-real-command")])
    report = await bridge.start()

    assert report["tools_registered"] == 0
    assert report["servers"][0]["skipped"]
    assert bridge.status()["total_bridged"] == 0


@pytest.mark.asyncio
async def test_shutdown_removes_the_tools_with_the_subprocess(monkeypatch, clean_registry):
    bridge, connection, _ = await _bridge_with(monkeypatch, _config(), [_tool("scan_url")])
    assert "fake_scan_url" in TOOL_SPECS

    await bridge.aclose()
    assert "fake_scan_url" not in TOOL_SPECS, "a tool whose server is gone must not stay advertised"
    assert connection.closed is True


@pytest.mark.asyncio
async def test_status_reports_why_a_server_is_not_running(clean_registry):
    bridge = MCPBridge([_config(id="nope", command="definitely-not-a-real-command")])
    await bridge.start()
    status = bridge.status()["servers"][0]

    assert status["running"] is False
    assert "not on PATH" in status["unavailable_reason"]


# ── result rendering ─────────────────────────────────────────────────────────


def test_text_blocks_are_joined():
    assert render_result(_Result([_Block("a"), _Block("b")])) == "a\nb"


def test_structured_content_wins_over_text():
    out = render_result(_Result([_Block("ignored")], structured={"verdict": "malicious"}))
    assert json.loads(out) == {"verdict": "malicious"}


def test_a_non_image_binary_block_still_says_why_it_is_absent():
    out = render_result(_Result([_Block(kind="audio", mime="audio/wav")]))
    assert "could not be included" in out
    assert "says nothing about what it contained" in out


def test_the_screenshot_tool_is_advertised_now_that_images_travel():
    urlscan = next(s for s in configured_servers() if s.id == "urlscan")
    assert "analyze_screenshot" in urlscan.allow_tools
    assert "analyze_screenshot" not in urlscan.cache_tools, "an image would evict the cache"


def test_an_error_result_says_so():
    out = render_result(_Result([_Block("nope")], is_error=True))
    assert out.startswith("Tool reported an error:")


def test_oversized_results_are_truncated_visibly():
    """A silent truncation makes the model treat a partial list as complete."""
    out = render_result(_Result([_Block("x" * (bridge_mod.MAX_RESULT_CHARS + 5000))]))

    assert len(out) < bridge_mod.MAX_RESULT_CHARS + 500
    assert "truncated" in out
    assert "5,000 more characters" in out


def test_empty_content_is_stated():
    assert render_result(_Result([])) == "(no content)"
    assert render_result(None) == "(no content)"


# ── connection plumbing ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_call_to_an_unavailable_server_explains_itself():
    connection = MCPServerConnection(_config(id="nope", command="definitely-not-a-real-command"))
    with pytest.raises(RuntimeError, match="unavailable"):
        await connection.call("anything", {})


@pytest.mark.asyncio
async def test_a_server_that_exits_immediately_fails_startup_quickly():
    """A dead subprocess must be noticed by the race, not the 30s timeout."""
    connection = MCPServerConnection(
        _config(id="dies", command=sys.executable, args=("-c", "raise SystemExit(1)"))
    )
    started = await asyncio.wait_for(connection.start(), timeout=25)

    assert started is False
    assert connection.last_error
    await connection.aclose()


@pytest.mark.asyncio
async def test_deny_and_allow_lists_filter_the_discovered_tools():
    connection = MCPServerConnection(_config(allow_tools=("a", "b"), deny_tools=("b",)))
    assert connection._exposed("a") is True
    assert connection._exposed("b") is False   # deny beats allow
    assert connection._exposed("c") is False   # not on the allow list


# ── end to end, against the real urlscan server ──────────────────────────────


@pytest.mark.asyncio
async def test_the_real_urlscan_server_bridges_end_to_end(clean_registry):
    """Spawns the actual subprocess and calls a tool through it.

    Everything above fakes the transport, which cannot catch a wrong module
    path, an SDK signature change, or the cancel-scope errors this client
    exists to avoid. `server_capabilities` touches no network and needs no key,
    so this stays offline while exercising the whole path.
    """
    pytest.importorskip("urlscan_mcp")
    pytest.importorskip("mcp")

    config = next(s for s in configured_servers() if s.id == "urlscan")
    if not config.available:
        pytest.skip(config.unavailable_reason)

    bridge = MCPBridge([config])
    try:
        report = await asyncio.wait_for(bridge.start(), timeout=60)
        assert report["tools_registered"] > 0, report
        assert "urlscan_scan_url" in TOOL_SPECS

        result = await TOOL_SPECS["urlscan_server_capabilities"].handler(None, {})
        assert result.ok, result.content
        assert "authenticated" in result.content
    finally:
        await bridge.aclose()

    assert "urlscan_scan_url" not in TOOL_SPECS


@pytest.mark.asyncio
async def test_a_real_screenshot_survives_the_subprocess_boundary(clean_registry, tmp_path):
    """The one seam every other test in this file fakes.

    ToolResult.images, the bridge's image extraction, the brain's admission
    budget — all of it is tested against blocks built in-process. None of that
    proves an actual PNG survives base64 encoding, a JSON-RPC frame, a pipe and
    a decode with its bytes intact, which is the only property that matters
    when the model is finally shown the page.

    urlscan.io is unreachable from CI and needs no key for screenshots anyway,
    so a local stand-in serves one and URLSCAN_BASE_URL points the child at it.
    The image is checked byte-for-byte at the far end.
    """
    pytest.importorskip("urlscan_mcp")
    pytest.importorskip("mcp")

    import json as _json
    import struct
    import threading
    import zlib
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    def png(width: int, height: int) -> bytes:
        def chunk(tag: bytes, body: bytes) -> bytes:
            return (struct.pack(">I", len(body)) + tag + body
                    + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))

        raw = b"".join(b"\x00" + bytes([(y * 5) % 256, 90, 210] * width)
                       for y in range(height))
        return (b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 6))
                + chunk(b"IEND", b""))

    # Wider than one screen and taller than the crop threshold, so the child
    # does real work on it rather than passing the bytes through.
    screenshot = png(1280, 4200)
    uuid = "0198fb1a-6f0d-7b2c-9c31-2a4f9d0e1c77"
    result_doc = {
        "task": {"uuid": uuid, "url": "https://example.com/login",
                 "time": "2026-08-20T10:00:00.000Z"},
        "page": {"url": "https://cdn-elsewhere.net/x", "domain": "cdn-elsewhere.net",
                 "country": "US", "title": "Sign in"},
        "verdicts": {"overall": {"score": 0, "malicious": False}},
        "stats": {}, "lists": {"domains": [], "urls": []},
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):  # noqa: N802
            if self.path.startswith("/screenshots/"):
                body, ctype = screenshot, "image/png"
            elif self.path.startswith("/api/v1/result/"):
                body, ctype = _json.dumps(result_doc).encode(), "application/json"
            else:
                body, ctype = b'{"message":"not found"}', "application/json"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"

    config = next(s for s in configured_servers() if s.id == "urlscan")
    if not config.available:
        server.shutdown()
        pytest.skip(config.unavailable_reason)

    # The child inherits this environment; no proxy, or it would be asked to
    # tunnel to loopback.
    env = dict(config.env)
    env.update({"URLSCAN_BASE_URL": base, "NO_PROXY": "127.0.0.1,localhost",
                "no_proxy": "127.0.0.1,localhost", "HTTP_PROXY": "", "HTTPS_PROXY": "",
                "http_proxy": "", "https_proxy": ""})
    config = dataclasses.replace(config, env=env)

    bridge = MCPBridge([config])
    try:
        await asyncio.wait_for(bridge.start(), timeout=60)
        assert "urlscan_analyze_screenshot" in TOOL_SPECS

        result = await asyncio.wait_for(
            TOOL_SPECS["urlscan_analyze_screenshot"].handler(None, {"uuid": uuid}),
            timeout=60,
        )
        # And again with the domain DEEP already holds for the indicator it is
        # investigating: the scan's own domain comes from a result document
        # that needs an API key, so keyless this is the only way the brief has
        # anything to compare the brand against.
        with_domain = await asyncio.wait_for(
            TOOL_SPECS["urlscan_analyze_screenshot"].handler(
                None, {"uuid": uuid, "domain": "login-microsoft.example"}
            ),
            timeout=60,
        )
    finally:
        await bridge.aclose()
        server.shutdown()

    assert result.ok, result.content
    assert result.images, "the image did not survive the boundary"

    # ToolImage carries base64, because that is the shape every provider wants
    # on the wire. Decoding here is the point: it proves what crossed the pipe
    # is still a PNG and not a truncated or re-encoded approximation of one.
    image = result.images[0]
    assert image.mime_type == "image/png"
    decoded = base64.b64decode(image.data)
    assert decoded.startswith(b"\x89PNG"), "arrived corrupt, not merely truncated"
    assert decoded.endswith(b"IEND\xaeB`\x82"), "arrived truncated"
    assert image.approx_bytes > 1000

    # Pillow is optional: with it the child crops and downscales, without it the
    # bytes come through untouched. Both are correct; silently losing them is not.
    try:
        from io import BytesIO

        from PIL import Image

        with Image.open(BytesIO(decoded)) as img:
            assert img.width <= 1280
            assert img.height / img.width <= 3.0, "the crop did not happen"
    except ImportError:
        assert decoded == screenshot

    # And the brief travels with it. No key here, so the scan's result document
    # is unreadable and the brief must decline the brand-versus-domain
    # comparison rather than invite one against "unknown".
    assert "NOT a clean verdict" in result.content
    assert "could not be determined" in result.content
    assert "cannot be made from" in result.content

    # With a domain supplied, the comparison is back on — flagged as the
    # caller's claim, since nothing in the scan record confirms it.
    assert with_domain.images
    assert "login-microsoft.example" in with_domain.content
    assert "NOT confirmed against this scan's record" in with_domain.content


# ── diagnosing a server that will not start ──────────────────────────────────
#
# The bridge already proved it survives a dead server. What it did not prove is
# that it can say *why* one died — and that gap cost a real debugging session.
# The MCP SDK runs its transport in an anyio task group, so a failed spawn
# arrives as an ExceptionGroup whose str() is "unhandled errors in a TaskGroup
# (1 sub-exception)". Reported verbatim, that names the plumbing and hides the
# fault. These pin the diagnosis, not just the survival.


def test_a_task_group_failure_reports_the_cause_not_the_wrapper():
    group = ExceptionGroup(
        "unhandled errors in a TaskGroup",
        [FileNotFoundError(2, "No such file or directory")],
    )
    described = describe_exception(group)
    assert "No such file or directory" in described
    assert "TaskGroup" not in described


def test_nested_groups_are_flattened_to_their_leaves():
    inner = ExceptionGroup("inner", [RuntimeError("child exited"), ValueError("bad arg")])
    described = describe_exception(ExceptionGroup("outer", [inner]))
    assert "RuntimeError: child exited" in described
    assert "ValueError: bad arg" in described


def test_one_fault_repeated_across_tasks_is_reported_once():
    group = ExceptionGroup("g", [BrokenPipeError("pipe"), BrokenPipeError("pipe")])
    assert describe_exception(group).count("BrokenPipeError") == 1


def test_an_ordinary_exception_is_described_unchanged():
    assert describe_exception(ValueError("plain")) == "ValueError: plain"


def test_an_exception_with_no_message_still_names_its_type():
    assert describe_exception(RuntimeError()) == "RuntimeError"


def test_the_childs_own_stderr_is_attached_to_the_failure():
    """A dying subprocess explains itself on stderr; that text must survive.

    Without it the operator gets a transport-level symptom ("BrokenResourceError")
    and no cause, which is indistinguishable from a bug in DEEP.
    """
    import tempfile

    spool = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
    spool.write("Traceback (most recent call last):\nModuleNotFoundError: No module named 'urlscan_mcp'\n")
    assert "No module named 'urlscan_mcp'" in _read_spool(spool)
    spool.close()


def test_a_closed_spool_does_not_raise():
    """Reading the child's stderr must never become a second failure."""
    import tempfile

    spool = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
    spool.close()
    assert _read_spool(spool) == ""


def test_a_flood_of_child_output_is_truncated():
    import tempfile

    spool = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
    spool.write("x" * 50_000 + "the actual error")
    text = _read_spool(spool)
    assert len(text) < 1_200
    assert "the actual error" in text  # the tail is what matters, so keep it
    spool.close()


def test_the_startup_budget_survives_a_nonsense_override(monkeypatch):
    """A typo in the environment must not set the timeout to zero."""
    monkeypatch.setenv("DEEP_MCP_STARTUP_TIMEOUT", "not-a-number")
    assert _startup_timeout() == 60.0
    monkeypatch.setenv("DEEP_MCP_STARTUP_TIMEOUT", "-1")
    assert _startup_timeout() == 60.0
    monkeypatch.setenv("DEEP_MCP_STARTUP_TIMEOUT", "12.5")
    assert _startup_timeout() == 12.5


def test_an_infinite_budget_is_not_a_budget(monkeypatch):
    """float() accepts these, and both remove the deadline entirely.

    "inf" reads like "be patient", but it means a wedged child hangs the boot
    the timeout exists to protect — the failure, reachable through a setting
    that looks reasonable. "nan" fails every comparison, so a deadline built
    from it never trips either.
    """
    for value in ("inf", "-inf", "Infinity", "nan"):
        monkeypatch.setenv("DEEP_MCP_STARTUP_TIMEOUT", value)
        assert _startup_timeout() == 60.0, value


# ── caching ──────────────────────────────────────────────────────────────────
#
# A bridged tool runs in its own subprocess with its own HTTP client, so it
# never touches DEEP's intel cache or per-host throttle. Two identical pivots
# in one investigation hit the upstream twice where the native path would hit
# it once. What must NOT be cached matters more than what is.


async def _cached_bridge(monkeypatch, *, cache_tools=("search_scans",), ttl=900.0, outcome=None):
    config = _config(cache_tools=cache_tools, cache_ttl_s=ttl)
    return await _bridge_with(monkeypatch, config, [_tool("search_scans"), _tool("scan_url")], outcome)


@pytest.mark.asyncio
async def test_a_repeated_read_is_served_from_cache(clean_registry, monkeypatch):
    bridge, conn, _ = await _cached_bridge(monkeypatch, outcome=_Result([_Block("hits")]))
    handler = TOOL_SPECS["fake_search_scans"].handler

    first = await handler(None, {"query": "domain:evil.test"})
    second = await handler(None, {"query": "domain:evil.test"})

    assert first.content == second.content == "hits"
    assert len(conn.calls) == 1, "the second call must not reach the server"
    assert bridge.status()["cache"]["hits"] == 1
    await bridge.aclose()


@pytest.mark.asyncio
async def test_argument_order_does_not_defeat_the_cache(clean_registry, monkeypatch):
    """Models do not emit arguments in a stable order."""
    bridge, conn, _ = await _cached_bridge(monkeypatch, outcome=_Result([_Block("hits")]))
    handler = TOOL_SPECS["fake_search_scans"].handler

    await handler(None, {"a": 1, "b": 2})
    await handler(None, {"b": 2, "a": 1})

    assert len(conn.calls) == 1
    await bridge.aclose()


@pytest.mark.asyncio
async def test_different_arguments_are_different_entries(clean_registry, monkeypatch):
    bridge, conn, _ = await _cached_bridge(monkeypatch, outcome=_Result([_Block("hits")]))
    handler = TOOL_SPECS["fake_search_scans"].handler

    await handler(None, {"query": "one"})
    await handler(None, {"query": "two"})

    assert len(conn.calls) == 2
    await bridge.aclose()


@pytest.mark.asyncio
async def test_a_tool_with_side_effects_is_never_cached(clean_registry, monkeypatch):
    """Caching a submission would hand back a scan id for a scan that never ran."""
    bridge, conn, _ = await _cached_bridge(monkeypatch, outcome=_Result([_Block("submitted")]))
    handler = TOOL_SPECS["fake_scan_url"].handler

    await handler(None, {"url": "https://x.test"})
    await handler(None, {"url": "https://x.test"})

    assert len(conn.calls) == 2, "scan_url is not on the cache list"
    await bridge.aclose()


@pytest.mark.asyncio
async def test_a_failure_is_not_cached(clean_registry, monkeypatch):
    """One bad minute upstream must not become an hour of repeating it."""
    bridge, conn, _ = await _cached_bridge(
        monkeypatch, outcome=_Result([_Block("upstream is down")], is_error=True)
    )
    handler = TOOL_SPECS["fake_search_scans"].handler

    await handler(None, {"query": "x"})
    await handler(None, {"query": "x"})

    assert len(conn.calls) == 2
    await bridge.aclose()


@pytest.mark.asyncio
async def test_an_expired_entry_is_refetched(clean_registry, monkeypatch):
    bridge, conn, _ = await _cached_bridge(
        monkeypatch, ttl=-1, outcome=_Result([_Block("hits")])
    )
    handler = TOOL_SPECS["fake_search_scans"].handler

    await handler(None, {"query": "x"})
    await handler(None, {"query": "x"})

    assert len(conn.calls) == 2
    await bridge.aclose()


@pytest.mark.asyncio
async def test_the_cache_is_bounded(clean_registry, monkeypatch):
    bridge, _, _ = await _cached_bridge(monkeypatch, outcome=_Result([_Block("hits")]))
    handler = TOOL_SPECS["fake_search_scans"].handler

    for i in range(bridge_mod.MAX_CACHE_ENTRIES + 20):
        await handler(None, {"query": f"q{i}"})

    assert bridge.status()["cache"]["entries"] <= bridge_mod.MAX_CACHE_ENTRIES
    await bridge.aclose()


@pytest.mark.asyncio
async def test_caching_is_off_unless_a_server_declares_it(clean_registry, monkeypatch):
    """The bridge cannot tell a read from a write by looking at a name."""
    bridge, conn, _ = await _cached_bridge(
        monkeypatch, cache_tools=(), outcome=_Result([_Block("hits")])
    )
    handler = TOOL_SPECS["fake_search_scans"].handler

    await handler(None, {"query": "x"})
    await handler(None, {"query": "x"})

    assert len(conn.calls) == 2
    await bridge.aclose()


def test_the_urlscan_server_caches_reads_but_not_submissions():
    urlscan = next(s for s in configured_servers() if s.id == "urlscan")

    assert "search_scans" in urlscan.cache_tools
    assert "get_scan_result" in urlscan.cache_tools
    for write_or_volatile in ("scan_url", "scan_and_wait", "get_quotas"):
        assert write_or_volatile not in urlscan.cache_tools, write_or_volatile


# ── images ───────────────────────────────────────────────────────────────────
#
# An image block used to be described and thrown away, which made a tool whose
# whole point is a picture arrive as "[image omitted]" — advertised, and
# silently not happening.


class _ImageBlock:
    def __init__(self, data="aGVsbG8=", mime="image/png"):
        self.type = "image"
        self.data = data
        self.mimeType = mime


def test_an_image_block_reaches_the_caller():
    text, images = render_full(_Result([_Block("look at this"), _ImageBlock()]))

    assert len(images) == 1
    assert images[0].mime_type == "image/png"
    assert images[0].data == "aGVsbG8="
    assert "look at this" in text
    assert "[image/png attached]" in text, "the text should mark where it sits"


def test_an_image_with_no_text_is_not_reported_as_empty():
    text, images = render_full(_Result([_ImageBlock()]))
    assert images
    assert "[image/png attached]" in text
    assert "(no content)" not in text


def test_an_oversized_image_is_dropped_rather_than_blowing_the_context():
    huge = _ImageBlock(data="A" * (bridge_mod.MAX_IMAGE_BYTES * 2))
    _, images = render_full(_Result([huge]))
    assert images == []


def test_an_empty_image_payload_is_skipped():
    _, images = render_full(_Result([_ImageBlock(data="")]))
    assert images == []


def test_an_error_result_carries_no_images():
    """Whatever the server attached, an error is not evidence to look at."""
    _, images = render_full(_Result([_ImageBlock()], is_error=True))
    assert images == []


@pytest.mark.asyncio
async def test_a_tool_returning_an_image_puts_it_on_the_result(clean_registry, monkeypatch):
    bridge, _, _ = await _bridge_with(
        monkeypatch, _config(), [_tool("analyze_screenshot")],
        _Result([_Block("Screenshot of evil.test"), _ImageBlock()]),
    )
    result = await TOOL_SPECS["fake_analyze_screenshot"].handler(None, {"uuid": "u1"})

    assert result.ok
    assert len(result.images) == 1
    assert "evil.test" in result.content
    await bridge.aclose()


@pytest.mark.asyncio
async def test_a_result_with_images_is_never_cached(clean_registry, monkeypatch):
    """One cached screenshot would evict the whole working set."""
    config = _config(cache_tools=("analyze_screenshot",))
    connection = FakeConnection(
        config, [_tool("analyze_screenshot")], _Result([_Block("x"), _ImageBlock()])
    )
    monkeypatch.setattr(bridge_mod, "MCPServerConnection", lambda cfg: connection)
    bridge = MCPBridge([config])
    await bridge.start()

    handler = TOOL_SPECS["fake_analyze_screenshot"].handler
    await handler(None, {"uuid": "u1"})
    await handler(None, {"uuid": "u1"})

    assert len(connection.calls) == 2
    await bridge.aclose()


# ── shutdown while startup is still in flight ────────────────────────────────
#
# Bridge startup was moved off the boot critical path, which means a process
# that dies young can reach shutdown with the handshake still running. Closing
# the bridge underneath its own start() lets that task spawn subprocesses and
# register tools *after* everything has been torn down — a child left running
# past the server that owns it, and tools in the registry pointing at it.


@pytest.mark.asyncio
async def test_shutdown_stops_the_starter_before_closing_the_bridge(
    monkeypatch, clean_registry
):
    started_late = False

    class SlowConnection(FakeConnection):
        async def start(self):
            nonlocal started_late
            await asyncio.sleep(0.2)  # a handshake still in flight at shutdown
            started_late = True
            return await super().start()

    config = _config()
    connection = SlowConnection(config, [_tool("thing")])
    monkeypatch.setattr(bridge_mod, "MCPServerConnection", lambda cfg: connection)

    bridge = MCPBridge([config])
    task = asyncio.create_task(bridge.start())
    await asyncio.sleep(0)  # let start() reach its first await

    # What interface/server.py's shutdown does, in the same order.
    if not task.done():
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
    await bridge.aclose()

    await asyncio.sleep(0.3)  # past when the slow handshake would have landed
    assert not started_late, "the handshake continued after shutdown"
    assert "fake_thing" not in TOOL_SPECS, "a tool was registered after shutdown"


# ── a failure must arrive as a failure ───────────────────────────────────────


@pytest.mark.asyncio
async def test_a_server_side_error_is_not_reported_as_success(monkeypatch, clean_registry):
    """The text said "Tool reported an error" while the data said ok=True.

    ToolResult.ok is what the rest of DEEP branches on — metrics, retries, and
    the brain's own judgement of whether it has an answer. Only the prose
    carried the failure, so everything that reads the flag counted it as a
    success.
    """
    bridge, _, _ = await _bridge_with(
        monkeypatch, _config(), [_tool("thing")],
        _Result([_Block("upstream is down")], is_error=True),
    )
    try:
        result = await TOOL_SPECS["fake_thing"].handler(None, {})
    finally:
        await bridge.aclose()

    assert result.ok is False
    assert "upstream is down" in result.content


@pytest.mark.asyncio
async def test_one_servers_surprise_does_not_unregister_the_others(
    monkeypatch, clean_registry
):
    """A server that fails in an unanticipated way is a missing capability.

    Without return_exceptions, the first surprise aborts the whole gather and
    every healthy server beside it goes unregistered — the bridge reporting
    nothing bridged because one entry out of several was bad.
    """
    good = _config(id="good")
    bad = _config(id="bad")
    healthy = FakeConnection(good, [_tool("works")])

    def build(cfg):
        if cfg.id == "bad":
            raise RuntimeError("config blew up on construction")
        return healthy

    monkeypatch.setattr(bridge_mod, "MCPServerConnection", build)

    bridge = MCPBridge([bad, good])
    try:
        report = await bridge.start()

        assert "good_works" in TOOL_SPECS, "the healthy server was lost with the bad one"
        assert report["tools_registered"] == 1
        failed = next(e for e in report["servers"] if e["id"] == "bad")
        assert "config blew up" in failed["error"]
    finally:
        await bridge.aclose()
