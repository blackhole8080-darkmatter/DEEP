"""Tests for the LLM tool registry.

The registry populates `TOOL_SPECS` as a side effect of `@tool` decorators
running at import time. Nothing imported the modules that carry those
decorators, so the live server advertised zero tools to the model while its
system prompt promised them. These tests pin the wiring so that can't silently
recur, and cover the intel tools that put the public-API layer in front of the
reasoning brain.
"""
from __future__ import annotations

import pytest

import core.tools  # noqa: F401  — importing the package is what registers tools
from core.tools.registry import TOOL_SPECS


# ═══════════════════════════════════════════════════════════════════════════
# Registration wiring
# ═══════════════════════════════════════════════════════════════════════════


def test_importing_the_package_registers_tools():
    """Regression: TOOL_SPECS was empty in the running server."""
    assert len(TOOL_SPECS) > 50, f"only {len(TOOL_SPECS)} tools registered"


def test_the_server_advertises_tools_to_the_model():
    """describe_tools() used to emit a header and nothing else."""
    from core.tools.deep_registry import DeepToolRegistry

    described = DeepToolRegistry().describe_tools()
    for name in ("threat_lookup", "cve_intel", "investigate", "network_scan"):
        assert name in described, f"{name} missing from the tool description"
    assert described.count("\n- ") > 50


def test_every_spec_is_well_formed():
    for name, spec in TOOL_SPECS.items():
        assert spec.name == name
        assert spec.description.strip(), f"{name} has no description"
        assert callable(spec.handler), f"{name} has no handler"
        assert isinstance(spec.args, dict)


def test_migrated_tools_win_over_legacy_shims():
    """`legacy` must import last, or its generic shims shadow real handlers.

    legacy.py registers with `if name in TOOL_SPECS: continue`, so import
    order is what decides which implementation a name resolves to.
    """
    import core.tools.builtin as builtin_mod

    assert TOOL_SPECS["get_time"].handler.__module__ == builtin_mod.__name__


def test_archived_science_tools_are_not_advertised():
    """Their engine lives in archive/; offering them would guarantee failures."""
    for dead in ("science_compute", "solve_math", "run_simulation", "quant_finance"):
        assert dead not in TOOL_SPECS


# ═══════════════════════════════════════════════════════════════════════════
# Intel tools
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def registry():
    from core.tools.deep_registry import DeepToolRegistry

    return DeepToolRegistry()


@pytest.mark.parametrize(
    "name",
    ["threat_lookup", "cve_intel", "dependency_audit", "threat_landscape", "intel_sources"],
)
def test_intel_tools_are_registered(name):
    assert name in TOOL_SPECS


@pytest.mark.asyncio
async def test_intel_sources_lists_the_catalog(registry):
    result = await registry.execute_tool("intel_sources", {})
    assert result.ok
    assert "sources usable right now" in result.content
    assert "CISA Known Exploited Vulnerabilities" in result.content


@pytest.mark.asyncio
async def test_intel_sources_filters_by_category(registry):
    result = await registry.execute_tool("intel_sources", {"category": "certificate"})
    assert result.ok
    assert "crt.sh" in result.content
    assert "CISA Known Exploited Vulnerabilities" not in result.content


@pytest.mark.asyncio
async def test_intel_sources_rejects_a_bad_category_with_the_valid_set(registry):
    result = await registry.execute_tool("intel_sources", {"category": "bogus"})
    assert not result.ok
    assert "vulnerability" in result.content  # tells the model what it may use


@pytest.mark.asyncio
async def test_threat_lookup_short_circuits_private_addresses(registry):
    """No outbound call, and the model is told why there's nothing to report."""
    result = await registry.execute_tool("threat_lookup", {"target": "192.168.1.10"})
    assert result.ok
    assert "private or reserved" in result.content


@pytest.mark.asyncio
async def test_threat_lookup_rejects_unrecognised_indicators(registry):
    result = await registry.execute_tool("threat_lookup", {"target": "???"})
    assert not result.ok
    assert "Unrecognised indicator" in result.content


@pytest.mark.asyncio
async def test_tools_require_their_arguments(registry):
    for name, key in [
        ("threat_lookup", "target"),
        ("cve_intel", "cve_id"),
        ("dependency_audit", "package"),
    ]:
        result = await registry.execute_tool(name, {})
        assert not result.ok, name
        assert key in result.content.lower(), name


@pytest.mark.asyncio
async def test_cve_intel_rejects_non_cve_input(registry):
    result = await registry.execute_tool("cve_intel", {"cve_id": "not-a-cve"})
    assert not result.ok
    assert "CVE-YYYY-NNNNN" in result.content


@pytest.mark.asyncio
async def test_dependency_audit_rejects_a_bare_package_name(registry):
    result = await registry.execute_tool("dependency_audit", {"package": "requests"})
    assert not result.ok
    assert "ecosystem:name" in result.content


@pytest.mark.asyncio
async def test_findings_are_rendered_with_their_source():
    """The model must be able to attribute every claim it repeats."""
    from core.intel.osint_investigator import Dossier, Finding
    from core.tools.intel import _render

    dossier = Dossier(
        target="45.33.32.156",
        indicator="ip",
        risk="critical",
        summary="45.33.32.156 (ip) — CRITICAL",
        findings=[
            Finding("shodan_internetdb", "open_ports", [22, 443], "medium"),
            Finding("feodo", "botnet_c2", "Emotet", "critical"),
        ],
        degraded={"sans_isc": "timeout"},
    )
    text = _render(dossier)

    assert "[source: shodan_internetdb]" in text
    assert "[source: feodo]" in text
    assert "unreachable this run: sans_isc" in text
    # Highest-priority finding is surfaced before the lower one.
    assert text.index("botnet_c2") < text.index("open_ports")


@pytest.mark.asyncio
async def test_unknown_tool_is_reported_not_raised(registry):
    result = await registry.execute_tool("no_such_tool", {})
    assert not result.ok
    assert "Unknown tool" in result.content


# ═══════════════════════════════════════════════════════════════════════════
# Tool surface: nothing advertised that cannot run
# ═══════════════════════════════════════════════════════════════════════════


def test_no_tool_references_a_registry_attribute_that_does_not_exist():
    """Every ctx.<attr> a handler reaches for must be constructed.

    Regression: handlers used ctx.email / ctx.finance / ctx.rag /
    ctx.local_system, none of which DeepToolRegistry built — so 22 registered
    tools could only ever raise AttributeError at call time.
    """
    import re

    from core.tools import legacy as legacy_mod
    from core.tools import files as files_mod
    from core.tools.deep_registry import DeepToolRegistry

    registry = DeepToolRegistry()
    referenced = set()
    for module in (legacy_mod, files_mod):
        with open(module.__file__, encoding="utf-8") as fh:
            referenced |= set(re.findall(r"\bctx\.([a-z_][a-z0-9_]*)", fh.read()))

    # Attributes set per-call by the server, not in __init__.
    runtime_supplied = {"world_model", "plugin_manager"}
    missing = {
        a for a in referenced
        if a not in runtime_supplied and not hasattr(registry, a) and not a.startswith("_")
    }
    assert not missing, f"handlers reference attributes the registry never builds: {missing}"


def test_every_legacy_tool_has_a_dispatch_branch():
    """Regression: the five agent_* tools were advertised with no branch at all,
    so the model could call them and only ever get "Unknown tool"."""
    import re

    from core.tools.legacy import LEGACY_TOOLS, execute_legacy_tool
    import inspect

    source = inspect.getsource(execute_legacy_tool)
    dispatched = set(re.findall(r"tool_name (?:==|in) \(?'([a-z_]+)'", source))
    dispatched |= set(re.findall(r"'([a-z_]+)'", source))

    undispatched = {n for n in LEGACY_TOOLS if n not in dispatched}
    assert not undispatched, f"advertised with no implementation: {undispatched}"


def test_legacy_dispatch_does_not_delegate_to_itself():
    """Regression: execute_legacy_tool looked up TOOL_SPECS[tool_name] and
    awaited its handler — but that handler *is* this function's only caller,
    so every legacy tool recursed until the stack blew."""
    import inspect

    from core.tools.legacy import execute_legacy_tool

    source = inspect.getsource(execute_legacy_tool)
    assert "TOOL_SPECS.get(tool_name)" not in source
    assert "spec.handler" not in source


def test_shell_execution_is_opt_in():
    """run_command is arbitrary shell — LocalSystem sandboxes cwd, not the
    command — so it must not be handed to the model by default."""
    import os

    assert not os.environ.get("DEEP_ENABLE_SHELL_TOOL")
    assert "run_command" not in TOOL_SPECS


def test_file_tools_are_registered_and_backed():
    from core.tools.deep_registry import DeepToolRegistry

    for name in ("read_file", "list_directory", "glob_files", "search_code"):
        assert name in TOOL_SPECS
    assert hasattr(DeepToolRegistry(), "local_system")


@pytest.mark.asyncio
async def test_file_tools_refuse_to_escape_the_workspace(registry):
    result = await registry.execute_tool("read_file", {"filepath": "/etc/passwd"})
    assert not result.ok
    assert "escapes the workspace sandbox" in result.content


def test_off_mission_tools_are_no_longer_advertised():
    """A cybersecurity console shouldn't spend prompt budget on phone control,
    personal finance, email or XR."""
    for name in ("phone_tap", "send_email", "set_budget", "xr_send_command",
                 "home_automation", "agent_swarm", "research_query"):
        assert name not in TOOL_SPECS, f"{name} still advertised"


def test_tool_description_payload_stays_bounded():
    """This text is injected into every prompt; it was 17KB of mostly-dead
    tools. Guard against silent regrowth."""
    from core.tools.deep_registry import DeepToolRegistry

    described = DeepToolRegistry().describe_tools()
    assert len(described) < 13_000, f"tool description grew to {len(described)} chars"
