"""DEEP as an MCP *client* — borrowing other people's hands.

``mcp_server/deep_mcp.py`` points outward: it lets Claude Desktop or Cursor use
DEEP as an intelligence backend. This module is the other direction, and it is
the one that makes DEEP grow without DEEP changing. Any Model Context Protocol
server the operator configures — urlscan, a ticketing system, an internal API,
something written this afternoon — has its tools discovered at startup and
registered into the same ``TOOL_SPECS`` registry the reasoning brain already
reads. No adapter per server, no code change to add one.

Design constraints, all learned from the rest of this codebase:

* **A dead server must not take DEEP down.** Each server is connected
  independently; one that fails to launch is recorded with its reason and the
  rest still load. `status()` reports exactly which are up, so the operator
  never has to discover a gap by asking a question that quietly goes
  unanswered.
* **Names are namespaced.** A server's ``search`` must not silently shadow
  DEEP's own tool of that name — the strangler-pattern hazard that
  `core/tools/__init__.py` documents. Tools register as ``<server>__<tool>``,
  and a collision with an existing name is refused and logged rather than
  overwriting it.
* **Nothing is trusted implicitly.** Tool descriptions from an external server
  are injected into DEEP's system prompt, so they are third-party text reaching
  the model. Descriptions are length-capped, and a server is only ever launched
  from explicit local configuration — never from anything discovered at runtime.
* **It is entirely optional.** No config file, no servers, no cost: the
  registry is unchanged and DEEP behaves exactly as before.

Configuration is the same shape Claude Desktop and Cursor already use, so a
server the operator has running there can be pasted across::

    // data/mcp_servers.json
    {
      "mcpServers": {
        "urlscan": {
          "command": "python",
          "args": ["-m", "urlscan_mcp.server"],
          "env": {"URLSCAN_API_KEY": "..."}
        }
      }
    }
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = "data/mcp_servers.json"

#: External descriptions land in DEEP's system prompt, which is a finite and
#: shared budget. A server advertising an essay gets truncated.
MAX_DESCRIPTION_CHARS = 400

#: How long to wait for a server to start and list its tools.
CONNECT_TIMEOUT_S = 30.0

#: How long a single tool call may take before DEEP gives up on it.
CALL_TIMEOUT_S = 120.0


def client_enabled() -> bool:
    return os.environ.get("DEEP_MCP_CLIENT", "1").strip().lower() not in {
        "0",
        "false",
        "off",
        "no",
    }


@dataclass(slots=True)
class RemoteTool:
    """One tool advertised by an external MCP server."""

    server: str
    name: str  # the tool's name on its own server
    description: str
    schema: Dict[str, Any] = field(default_factory=dict)

    @property
    def qualified_name(self) -> str:
        """Namespaced so an external tool can never shadow one of DEEP's."""
        return f"{self.server}__{self.name}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "server": self.server,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "description": self.description,
        }


@dataclass(slots=True)
class ServerState:
    name: str
    connected: bool = False
    tools: List[RemoteTool] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "connected": self.connected,
            "tools": [t.name for t in self.tools],
            "error": self.error,
        }


class MCPClientHub:
    """Connects to configured MCP servers and exposes their tools to DEEP."""

    def __init__(
        self,
        config_path: Optional[str | Path] = None,
        *,
        connect_timeout: float = CONNECT_TIMEOUT_S,
        call_timeout: float = CALL_TIMEOUT_S,
    ) -> None:
        self._config_path = Path(
            config_path or os.environ.get("DEEP_MCP_CONFIG") or DEFAULT_CONFIG
        )
        self._connect_timeout = connect_timeout
        self._call_timeout = call_timeout
        self._servers: Dict[str, ServerState] = {}
        self._sessions: Dict[str, Any] = {}
        self._stack: Optional[AsyncExitStack] = None
        self._started = False
        self._config_error = ""

    @property
    def config_path(self) -> Path:
        return self._config_path

    # ── configuration ────────────────────────────────────────────────────────

    def load_config(self) -> Dict[str, Dict[str, Any]]:
        """Read the server map. A malformed file is reported, not raised."""
        if not self._config_path.exists():
            return {}
        try:
            raw = json.loads(self._config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self._config_error = f"{self._config_path}: {exc}"
            logger.warning("MCP config unreadable: %s", self._config_error)
            return {}

        servers = raw.get("mcpServers") if isinstance(raw, dict) else None
        if not isinstance(servers, dict):
            self._config_error = (
                f"{self._config_path}: expected an object with an 'mcpServers' key"
            )
            logger.warning("MCP config malformed: %s", self._config_error)
            return {}
        return {k: v for k, v in servers.items() if isinstance(v, dict)}

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> int:
        """Connect every configured server. Returns how many tools registered."""
        if self._started or not client_enabled():
            return 0
        self._started = True

        config = self.load_config()
        if not config:
            return 0

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            self._config_error = (
                "the `mcp` package is not installed — "
                "`pip install 'mcp>=1.2,<2'` to use external MCP servers"
            )
            logger.warning("MCP client disabled: %s", self._config_error)
            return 0

        self._stack = AsyncExitStack()
        registered = 0
        for name, spec in config.items():
            state = ServerState(name=name)
            self._servers[name] = state
            try:
                await asyncio.wait_for(
                    self._connect(
                        name,
                        spec,
                        state,
                        ClientSession,
                        StdioServerParameters,
                        stdio_client,
                    ),
                    timeout=self._connect_timeout,
                )
            except asyncio.TimeoutError:
                state.error = f"did not start within {self._connect_timeout:.0f}s"
                logger.warning("MCP server %s timed out starting", name)
            except Exception as exc:  # noqa: BLE001 - one bad server must not stop the rest
                state.error = f"{type(exc).__name__}: {exc}"
                logger.warning("MCP server %s failed to start: %s", name, state.error)
            else:
                registered += self._register(state)
        return registered

    async def _connect(
        self,
        name,
        spec,
        state,
        ClientSession,
        StdioServerParameters,
        stdio_client,
    ) -> None:
        command = spec.get("command")
        if not command:
            raise ValueError("no 'command' in server config")
        if shutil.which(command) is None and not Path(command).exists():
            raise FileNotFoundError(f"command not found: {command}")

        params = StdioServerParameters(
            command=command,
            args=list(spec.get("args") or []),
            # Inherit DEEP's environment so a server can find its own
            # interpreter and libraries, with the config's env layered on top.
            env={**os.environ, **(spec.get("env") or {})},
        )
        read, write = await self._stack.enter_async_context(stdio_client(params))
        session = await self._stack.enter_async_context(ClientSession(read, write))
        await session.initialize()

        listing = await session.list_tools()
        state.tools = [
            RemoteTool(
                server=name,
                name=tool.name,
                description=(tool.description or "")[:MAX_DESCRIPTION_CHARS],
                schema=getattr(tool, "inputSchema", None) or {},
            )
            for tool in listing.tools
        ]
        state.connected = True
        self._sessions[name] = session
        logger.info("MCP server %s connected with %d tool(s)", name, len(state.tools))

    async def stop(self) -> None:
        if self._stack is not None:
            try:
                await self._stack.aclose()
            except Exception as exc:  # noqa: BLE001
                logger.debug("MCP shutdown: %s", exc)
            self._stack = None
        self._sessions.clear()
        self._started = False

    # ── registration ─────────────────────────────────────────────────────────

    def _register(self, state: ServerState) -> int:
        """Put each remote tool into DEEP's registry under a namespaced name."""
        from core.domain.models import ToolResult
        from core.tools.registry import TOOL_SPECS, ToolSpec

        count = 0
        for remote in state.tools:
            qualified = remote.qualified_name
            if qualified in TOOL_SPECS:
                # Never overwrite. `core/tools/__init__.py` documents what
                # silent shadowing costs; the same rule applies to strangers.
                logger.warning(
                    "MCP tool %s collides with an existing tool — skipped", qualified
                )
                continue

            # `_remote` is bound as a default: a bare closure over the loop
            # variable would leave every handler pointing at the last tool.
            async def handler(ctx, args, _remote=remote):
                result = await self.call(_remote.server, _remote.name, args)
                return ToolResult(
                    result["ok"], result["content"], _remote.qualified_name
                )

            TOOL_SPECS[qualified] = ToolSpec(
                name=qualified,
                description=f"[via MCP server '{state.name}'] {remote.description}",
                args=_schema_to_args(remote.schema),
                handler=handler,
            )
            count += 1
        return count

    # ── invocation ───────────────────────────────────────────────────────────

    async def call(
        self, server: str, tool: str, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Invoke one remote tool. Never raises; returns ok/content."""
        session = self._sessions.get(server)
        if session is None:
            state = self._servers.get(server)
            reason = state.error if state and state.error else "not connected"
            return {
                "ok": False,
                "content": f"MCP server '{server}' is unavailable: {reason}",
            }

        try:
            response = await asyncio.wait_for(
                session.call_tool(tool, args or {}), timeout=self._call_timeout
            )
        except asyncio.TimeoutError:
            return {
                "ok": False,
                "content": f"{server}.{tool} timed out after {self._call_timeout:.0f}s",
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "content": f"{server}.{tool} failed: {type(exc).__name__}: {exc}",
            }

        return {
            "ok": not getattr(response, "isError", False),
            "content": _flatten(response),
        }

    # ── introspection ────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": client_enabled(),
            "config": str(self._config_path),
            "config_present": self._config_path.exists(),
            "config_error": self._config_error,
            "servers": [s.to_dict() for s in self._servers.values()],
            "tools": sum(len(s.tools) for s in self._servers.values() if s.connected),
        }

    def tools(self) -> List[Dict[str, Any]]:
        return [
            t.to_dict() for s in self._servers.values() if s.connected for t in s.tools
        ]


def _schema_to_args(schema: Dict[str, Any]) -> Dict[str, str]:
    """JSON Schema -> the flat {name: description} DEEP's registry expects."""
    properties = (schema or {}).get("properties")
    if not isinstance(properties, dict):
        return {}
    required = set((schema or {}).get("required") or [])
    out: Dict[str, str] = {}
    for name, spec in properties.items():
        if not isinstance(spec, dict):
            continue
        text = str(spec.get("description") or spec.get("type") or "").strip()
        out[name] = f"{text} (required)" if name in required else text
    return out


def _flatten(response: Any) -> str:
    """MCP content blocks -> plain text for the model."""
    parts: List[str] = []
    for block in getattr(response, "content", None) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(str(text))
            continue
        data = getattr(block, "data", None)
        if data is not None:
            parts.append(f"[{getattr(block, 'type', 'binary')} content omitted]")
    return "\n".join(parts) or "(the tool returned no content)"


_shared_hub: Optional[MCPClientHub] = None


def shared_mcp_hub() -> MCPClientHub:
    global _shared_hub
    if _shared_hub is None:
        _shared_hub = MCPClientHub()
    return _shared_hub
