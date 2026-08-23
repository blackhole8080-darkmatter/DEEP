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
import json
import sys

import pytest

from core.mcp import bridge as bridge_mod
from core.mcp.bridge import MCPBridge, render_result
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


def test_binary_content_is_described_not_inlined():
    out = render_result(_Result([_Block(kind="image", mime="image/png")]))
    assert "image content omitted" in out
    assert "image/png" in out


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
