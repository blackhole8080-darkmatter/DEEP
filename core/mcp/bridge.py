"""Adapts tools discovered on MCP servers into DEEP's own tool registry.

Once bridged, an MCP tool is indistinguishable from a native one to the
reasoning brain: same `[TOOL:{...}]` call format, same `ToolResult`, same
telemetry. The model does not need to know that `urlscan_scan_url` runs in a
subprocess speaking JSON-RPC over a pipe.

Three decisions shape this:

* **Names are prefixed by server.** `urlscan_scan_url`, not `scan_url`. Two
  servers offering `search` would otherwise collide in a flat registry, and the
  first one registered would silently win. The prefix also tells the model —
  and anyone reading a transcript — where a capability came from.
* **Results are compacted before they reach the prompt.** A tool result is fed
  straight back into the model's context, so an unbounded one costs the
  conversation its window. Text is capped and the truncation is stated, never
  silent: a model that cannot see that output was cut will reason about a
  truncated list as though it were complete.
* **Registration never fails DEEP.** A server that will not start contributes
  no tools and one line in the log. The assistant comes up either way; the
  bridge's status is readable through `/api/intel/mcp` rather than discovered
  through an exception at startup.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from core.domain.models import ToolResult
from core.mcp.client import MCPServerConnection, MCPTool
from core.mcp.config import MCPServerConfig, configured_servers
from core.tools.registry import TOOL_SPECS, ToolSpec

logger = logging.getLogger(__name__)

#: Largest tool result we will put in front of the model. Roughly 6k tokens —
#: enough for a shaped urlscan summary or a truncated DOM, small enough that
#: three of them do not evict the conversation.
MAX_RESULT_CHARS = 24_000


class MCPBridge:
    """Owns every MCP server connection and their registered tool specs."""

    def __init__(self, servers: Optional[List[MCPServerConfig]] = None) -> None:
        self._configs = servers if servers is not None else configured_servers()
        self._connections: Dict[str, MCPServerConnection] = {}
        self._registered: List[str] = []

    # ── startup ──────────────────────────────────────────────────────────────

    async def start(self) -> Dict[str, Any]:
        """Start every available server and register the tools it offers.

        Returns a report rather than raising: a server DEEP could not start is
        a missing capability, not a failed boot.
        """
        report: Dict[str, Any] = {"servers": [], "tools_registered": 0}
        for config in self._configs:
            entry: Dict[str, Any] = {"id": config.id, "tools": []}
            if not config.available:
                entry["skipped"] = config.unavailable_reason
                report["servers"].append(entry)
                logger.info("[MCP] skipping %s: %s", config.id, config.unavailable_reason)
                continue

            connection = MCPServerConnection(config)
            self._connections[config.id] = connection
            if not await connection.start():
                entry["error"] = connection.last_error
                report["servers"].append(entry)
                continue

            for tool in connection.tools:
                name = self._register(connection, tool)
                if name:
                    entry["tools"].append(name)
            report["tools_registered"] += len(entry["tools"])
            report["servers"].append(entry)
        return report

    async def aclose(self) -> None:
        """Shut every server down. Registered specs are removed with them.

        Leaving the specs behind would advertise tools whose subprocess is
        gone — the model would call them and get a restart attempt during
        shutdown.
        """
        for name in self._registered:
            TOOL_SPECS.pop(name, None)
        self._registered.clear()
        for connection in self._connections.values():
            await connection.aclose()
        self._connections.clear()

    # ── registration ─────────────────────────────────────────────────────────

    def _register(self, connection: MCPServerConnection, tool: MCPTool) -> Optional[str]:
        name = f"{connection.config.prefix}_{tool.name}"
        if name in TOOL_SPECS:
            # A native tool of the same name wins: it is on DEEP's own HTTP
            # stack, with DEEP's caching and attribution.
            logger.warning("[MCP] %s already registered; not bridging %s", name, tool.name)
            return None

        description = tool.description or f"{tool.name} on the {connection.config.id} MCP server."
        description = f"[{connection.config.id}] {description}"

        async def handler(ctx: Any, args: Dict[str, Any], _tool=tool, _conn=connection) -> ToolResult:
            try:
                raw = await _conn.call(_tool.name, args or {})
            except Exception as exc:  # noqa: BLE001 - subprocess, any failure mode
                logger.warning("[MCP] %s.%s failed: %s", _conn.config.id, _tool.name, exc)
                return ToolResult(False, f"{name} failed: {exc}", name)
            return ToolResult(True, render_result(raw), name)

        TOOL_SPECS[name] = ToolSpec(name, description, tool.arg_hints, handler)
        self._registered.append(name)
        return name

    # ── introspection ────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """What is configured, what is running, and why anything is not."""
        running = {c.config.id: c for c in self._connections.values()}
        servers = []
        for config in self._configs:
            entry = config.to_dict()
            connection = running.get(config.id)
            entry["running"] = bool(connection and connection.running)
            entry["last_error"] = connection.last_error if connection else ""
            entry["tools"] = [t.name for t in connection.tools] if connection else []
            servers.append(entry)
        return {
            "servers": servers,
            "bridged_tools": list(self._registered),
            "total_bridged": len(self._registered),
        }


def render_result(raw: Any) -> str:
    """Turn an MCP CallToolResult into bounded text for the model's context.

    An MCP result is a list of content blocks that may carry text, structured
    JSON, or binary. Anything non-textual is described rather than inlined —
    a base64 image in a prompt is thousands of wasted tokens and no
    information.
    """
    if raw is None:
        return "(no content)"

    if getattr(raw, "isError", False):
        return _truncate(f"Tool reported an error: {_blocks_to_text(raw)}")

    structured = getattr(raw, "structuredContent", None)
    if structured:
        return _truncate(_dumps(structured))

    text = _blocks_to_text(raw)
    return _truncate(text or "(no content)")


def _blocks_to_text(raw: Any) -> str:
    blocks = getattr(raw, "content", None)
    if blocks is None:
        return _dumps(raw)

    parts: List[str] = []
    for block in blocks:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(str(text))
            continue
        kind = getattr(block, "type", type(block).__name__)
        mime = getattr(block, "mimeType", "") or ""
        parts.append(f"[{kind} content omitted{f' ({mime})' if mime else ''}]")
    return "\n".join(parts)


def _dumps(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(value)


def _truncate(text: str) -> str:
    if len(text) <= MAX_RESULT_CHARS:
        return text
    omitted = len(text) - MAX_RESULT_CHARS
    # Stated, not silent: a model that cannot see the cut will treat a
    # truncated list as a complete one.
    return (
        f"{text[:MAX_RESULT_CHARS]}\n\n"
        f"[truncated — {omitted:,} more characters. Narrow the request "
        "(fewer results, a specific field) rather than assuming this is all of it.]"
    )


_shared: Optional[MCPBridge] = None


def shared_bridge() -> MCPBridge:
    """Process-wide bridge, so tools are registered exactly once."""
    global _shared
    if _shared is None:
        _shared = MCPBridge()
    return _shared
