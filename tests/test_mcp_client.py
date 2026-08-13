"""DEEP as an MCP client — borrowing tools from external servers.

`mcp_server/deep_mcp.py` points outward. This is the other direction: any MCP
server the operator configures has its tools registered into the same
TOOL_SPECS the reasoning brain reads, so DEEP gains capability without DEEP
changing.

Everything here runs offline. Spawning a real subprocess would make the suite
depend on a third-party server being installed, which is exactly the coupling
the hub is designed to survive.
"""

from __future__ import annotations

import json

import pytest

from core.mcp_client import (
    MCPClientHub,
    RemoteTool,
    ServerState,
    _flatten,
    _schema_to_args,
    client_enabled,
)


def _write_config(tmp_path, servers):
    path = tmp_path / "mcp_servers.json"
    path.write_text(json.dumps({"mcpServers": servers}), encoding="utf-8")
    return path


# ═══════════════════════════════════════════════════════════════════════════
# Configuration — absent, malformed, or fine
# ═══════════════════════════════════════════════════════════════════════════


def test_no_config_file_means_no_servers_and_no_complaint(tmp_path):
    """The overwhelmingly common case: DEEP must behave exactly as before."""
    hub = MCPClientHub(tmp_path / "nothing.json")
    assert hub.load_config() == {}
    status = hub.status()
    assert status["config_present"] is False
    assert status["servers"] == []
    assert status["config_error"] == ""


def test_malformed_json_is_reported_not_raised(tmp_path):
    path = tmp_path / "mcp_servers.json"
    path.write_text("{ this is not json", encoding="utf-8")
    hub = MCPClientHub(path)

    assert hub.load_config() == {}
    assert "mcp_servers.json" in hub.status()["config_error"]


def test_a_config_without_mcpservers_is_reported(tmp_path):
    path = tmp_path / "mcp_servers.json"
    path.write_text(json.dumps({"servers": {}}), encoding="utf-8")
    hub = MCPClientHub(path)

    assert hub.load_config() == {}
    assert "mcpServers" in hub.status()["config_error"]


def test_the_claude_desktop_shape_is_accepted(tmp_path):
    """A server the operator already runs in Claude Desktop should paste across."""
    path = _write_config(
        tmp_path,
        {
            "urlscan": {
                "command": "python",
                "args": ["-m", "urlscan_mcp.server"],
                "env": {"URLSCAN_API_KEY": "x"},
            }
        },
    )
    config = MCPClientHub(path).load_config()
    assert config["urlscan"]["args"] == ["-m", "urlscan_mcp.server"]


def test_the_shipped_example_is_valid_and_matches_the_expected_shape():
    from pathlib import Path

    example = json.loads(
        Path("examples/mcp_servers.example.json").read_text(encoding="utf-8")
    )
    assert "urlscan" in example["mcpServers"]
    assert example["mcpServers"]["urlscan"]["command"]


def test_the_client_is_opt_out(monkeypatch):
    monkeypatch.setenv("DEEP_MCP_CLIENT", "0")
    assert client_enabled() is False
    monkeypatch.setenv("DEEP_MCP_CLIENT", "1")
    assert client_enabled() is True


@pytest.mark.asyncio
async def test_a_disabled_client_registers_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEP_MCP_CLIENT", "0")
    path = _write_config(tmp_path, {"x": {"command": "python", "args": ["-c", "pass"]}})
    assert await MCPClientHub(path).start() == 0


# ═══════════════════════════════════════════════════════════════════════════
# One bad server must not take the others down
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_a_missing_command_is_recorded_with_its_reason(tmp_path):
    path = _write_config(
        tmp_path,
        {
            "ghost": {"command": "a-binary-that-does-not-exist", "args": []},
        },
    )
    hub = MCPClientHub(path, connect_timeout=5)
    assert await hub.start() == 0

    server = hub.status()["servers"][0]
    assert server["name"] == "ghost"
    assert server["connected"] is False
    assert "not found" in server["error"], "the operator must learn why, not just that"


@pytest.mark.asyncio
async def test_a_config_entry_with_no_command_is_rejected(tmp_path):
    path = _write_config(tmp_path, {"broken": {"args": ["x"]}})
    hub = MCPClientHub(path, connect_timeout=5)
    await hub.start()
    assert "command" in hub.status()["servers"][0]["error"]


@pytest.mark.asyncio
async def test_calling_a_server_that_never_connected_fails_cleanly():
    hub = MCPClientHub()
    hub._servers["down"] = ServerState(name="down", error="command not found")

    result = await hub.call("down", "anything", {})
    assert result["ok"] is False
    assert "command not found" in result["content"], "the reason must reach the model"


@pytest.mark.asyncio
async def test_calling_an_unknown_server_does_not_raise():
    result = await MCPClientHub().call("never-configured", "tool", {})
    assert result["ok"] is False
    assert "unavailable" in result["content"]


# ═══════════════════════════════════════════════════════════════════════════
# Registration — namespacing and collisions
# ═══════════════════════════════════════════════════════════════════════════


def test_tools_are_namespaced_by_their_server():
    """A stranger's `search` must not shadow one of DEEP's own tools."""
    assert (
        RemoteTool("urlscan", "search_scans", "").qualified_name
        == "urlscan__search_scans"
    )


def test_registration_namespaces_and_is_reversible():
    from core.tools.registry import TOOL_SPECS

    hub = MCPClientHub()
    state = ServerState(
        name="probe",
        connected=True,
        tools=[
            RemoteTool(
                "probe",
                "lookup",
                "Look something up.",
                {
                    "properties": {"q": {"type": "string", "description": "the query"}},
                    "required": ["q"],
                },
            ),
        ],
    )
    try:
        assert hub._register(state) == 1
        spec = TOOL_SPECS["probe__lookup"]
        assert "via MCP server 'probe'" in spec.description
        assert "Look something up." in spec.description
        assert spec.args["q"] == "the query (required)"
    finally:
        TOOL_SPECS.pop("probe__lookup", None)


def test_a_collision_with_an_existing_tool_is_refused_not_overwritten():
    """core/tools/__init__.py documents what silent shadowing costs. The same
    rule has to apply to tools arriving from outside."""
    from core.tools.registry import TOOL_SPECS

    hub = MCPClientHub()
    existing = TOOL_SPECS["threat_lookup"]
    state = ServerState(
        name="x", connected=True, tools=[RemoteTool("x", "y", "impostor")]
    )
    # Force the qualified name to collide with a real tool.
    state.tools[0] = RemoteTool("threat", "lookup", "impostor")
    try:
        TOOL_SPECS["threat__lookup"] = existing
        assert hub._register(state) == 0
        assert TOOL_SPECS["threat__lookup"] is existing
    finally:
        TOOL_SPECS.pop("threat__lookup", None)
    assert TOOL_SPECS["threat_lookup"] is existing


def test_each_handler_targets_its_own_tool():
    """A bare closure over the loop variable would leave every handler
    pointing at the last tool registered."""
    import inspect

    from core.tools.registry import TOOL_SPECS

    hub = MCPClientHub()
    state = ServerState(
        name="multi",
        connected=True,
        tools=[
            RemoteTool("multi", "first", "a"),
            RemoteTool("multi", "second", "b"),
        ],
    )
    try:
        assert hub._register(state) == 2
        for name in ("first", "second"):
            handler = TOOL_SPECS[f"multi__{name}"].handler
            bound = inspect.signature(handler).parameters["_remote"].default
            assert bound.name == name
    finally:
        for name in ("first", "second"):
            TOOL_SPECS.pop(f"multi__{name}", None)


# ═══════════════════════════════════════════════════════════════════════════
# Translation between MCP and DEEP's registry
# ═══════════════════════════════════════════════════════════════════════════


def test_json_schema_becomes_deeps_flat_arg_map():
    args = _schema_to_args(
        {
            "properties": {
                "indicator": {"type": "string", "description": "domain, IP or hash"},
                "days": {"type": "integer"},
            },
            "required": ["indicator"],
        }
    )
    assert args["indicator"] == "domain, IP or hash (required)"
    assert args["days"] == "integer", "a param with no description still needs a type"


def test_a_toolless_or_malformed_schema_is_survivable():
    assert _schema_to_args({}) == {}
    assert _schema_to_args({"properties": "not-a-dict"}) == {}
    assert _schema_to_args({"properties": {"x": "not-a-dict"}}) == {}


def test_content_blocks_flatten_to_text():
    class _Block:
        def __init__(self, text=None, data=None, type="text"):
            self.text, self.data, self.type = text, data, type

    class _Response:
        def __init__(self, content):
            self.content = content

    assert _flatten(_Response([_Block("one"), _Block("two")])) == "one\ntwo"
    assert "omitted" in _flatten(_Response([_Block(data=b"\x00", type="image")]))
    assert _flatten(_Response([])) == "(the tool returned no content)"


def test_an_overlong_description_is_capped():
    """These land in DEEP's system prompt, which is a shared finite budget."""
    from core.mcp_client import MAX_DESCRIPTION_CHARS

    assert MAX_DESCRIPTION_CHARS <= 500


# ═══════════════════════════════════════════════════════════════════════════
# API surface and the packaging bug this uncovered
# ═══════════════════════════════════════════════════════════════════════════


def test_status_endpoint_reports_the_config_location(client):
    response = client.get("/api/mcp/status")
    assert response.status_code == 200
    body = response.json()
    assert "config" in body and "servers" in body


def test_tools_endpoint_returns_a_list(client):
    response = client.get("/api/mcp/tools")
    assert response.status_code == 200
    assert isinstance(response.json()["tools"], list)


def test_the_mcp_dependency_is_declared():
    """mcp_server/deep_mcp.py has imported `mcp` since it was written, with
    nothing declaring it — the same class of bug as the undeclared pyyaml."""
    from pathlib import Path

    requirements = Path("requirements.txt").read_text(encoding="utf-8")
    assert "mcp>=" in requirements
    # The upper bound is load-bearing: mcp 2.0 removed `mcp.server.fastmcp`,
    # which is what deep_mcp.py imports.
    assert "<2" in requirements.split("mcp>=")[1].splitlines()[0]


def test_the_mcp_server_and_deep_cannot_drift_apart_on_the_port():
    """deep_mcp.py defaulted to 7768 while DEEP has always listened on 5174, so
    every tool call from Claude Desktop failed to connect.

    Pinning the literal would only have caught it once. Both files read the
    same DEEP_PORT variable now, which is what actually stops it recurring.
    """
    import re
    from pathlib import Path

    # Read the value out of the call rather than grepping for a number: both
    # files legitimately mention 7768 in a comment explaining the old bug, and
    # a text scan matches that history as readily as a regression.
    pattern = re.compile(r'os\.environ\.get\(\s*"DEEP_PORT"\s*,\s*"(\d+)"')
    defaults = {}
    for path in ("mcp_server/deep_mcp.py", "interface/server.py"):
        found = pattern.findall(Path(path).read_text(encoding="utf-8"))
        assert found, f"{path} does not read DEEP_PORT"
        defaults[path] = set(found)

    assert defaults["mcp_server/deep_mcp.py"] == defaults["interface/server.py"], \
        f"the MCP server and DEEP disagree on the default port: {defaults}"
