"""Which MCP servers DEEP runs, and whether each can actually start.

Servers are declared here as data. A server is *declared* unconditionally and
*available* only when its command can be found and its requirements are met —
the same distinction the public-API catalog draws between a source that exists
and a source that is configured, and for the same reason: a capability listed
as present but broken is worse than one honestly reported as absent, because
the model discovers the limitation by hitting it mid-answer.

Users can add their own servers without touching this file by writing
``data/mcp_servers.json``:

```json
{
  "servers": [
    {"id": "github", "command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"],
     "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"}, "tool_prefix": "gh"}
  ]
}
```

Entries there are merged over the built-ins by ``id``, so a built-in can be
disabled (``"enabled": false``) or repointed without editing code.
"""
from __future__ import annotations

import importlib.util
import json
import logging
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CONFIG_PATH = Path("data/mcp_servers.json")

#: A tool call is a synchronous step in the reasoning loop — the user is
#: waiting. Long enough for a urlscan submission round-trip, short enough that
#: a wedged server does not hang the conversation.
DEFAULT_CALL_TIMEOUT_S = 45.0


@dataclass(frozen=True, slots=True)
class MCPServerConfig:
    """One MCP server DEEP can run as a subprocess."""

    id: str
    command: str
    args: tuple[str, ...] = ()
    #: Environment for the child. ``${VAR}`` values are resolved from DEEP's
    #: own environment at launch, so keys stay in one place and are never
    #: written into this file.
    env: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    #: Prefix for the tools this server contributes, keeping names unique and
    #: telling the model where a tool came from. "" means the server id.
    tool_prefix: str = ""
    #: Only expose these tools. Empty means all of them.
    allow_tools: tuple[str, ...] = ()
    #: Never expose these, even if the server offers them.
    deny_tools: tuple[str, ...] = ()
    #: An importable module the server needs. Checked before spawning, because
    #: a subprocess that exits on an ImportError is a confusing failure.
    requires_package: Optional[str] = None
    #: Env vars without which the server is not worth starting.
    requires_env: tuple[str, ...] = ()
    enabled: bool = True
    call_timeout_s: float = DEFAULT_CALL_TIMEOUT_S
    #: Tools whose results may be reused from cache. Empty means none — the
    #: safe default, because the bridge cannot tell a read from a write by
    #: looking at a name, and caching a submission would return a stale scan id
    #: for a scan that never ran. Whoever declares the server knows which of its
    #: tools are pure; nobody else does.
    cache_tools: tuple[str, ...] = ()
    #: How long a cached result stays usable.
    cache_ttl_s: float = 900.0

    @property
    def prefix(self) -> str:
        return self.tool_prefix or self.id

    def resolved_env(self) -> Dict[str, str]:
        """Child environment, with ``${VAR}`` references filled in.

        The child inherits DEEP's environment; unresolved references are
        dropped rather than passed through literally, so a server never
        receives the string "${URLSCAN_API_KEY}" as a credential and reports a
        confusing auth failure instead of a missing key.
        """
        out = dict(os.environ)
        for key, value in self.env.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                resolved = os.environ.get(value[2:-1])
                if resolved:
                    out[key] = resolved
                else:
                    out.pop(key, None)
            else:
                out[key] = value
        return out

    @property
    def unavailable_reason(self) -> Optional[str]:
        """Why this server cannot start, in words a user can act on."""
        if not self.enabled:
            return "disabled in configuration"
        if importlib.util.find_spec("mcp") is None:
            return "the mcp package is not installed (pip install -r requirements.txt)"
        if self.requires_package and importlib.util.find_spec(self.requires_package) is None:
            return f"needs the {self.requires_package} package (pip install {self.requires_package})"
        # sys.executable is always present; anything else must be on PATH.
        if self.command != sys.executable and shutil.which(self.command) is None:
            return f"command {self.command!r} is not on PATH"
        missing = [v for v in self.requires_env if not os.environ.get(v)]
        if missing:
            return f"needs {', '.join(missing)} in the environment"
        return None

    @property
    def available(self) -> bool:
        return self.unavailable_reason is None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "command": self.command,
            "args": list(self.args),
            "description": self.description,
            "tool_prefix": self.prefix,
            "enabled": self.enabled,
            "available": self.available,
            "unavailable_reason": self.unavailable_reason,
            "requires_package": self.requires_package,
            "requires_env": list(self.requires_env),
        }


#: Servers DEEP ships with. urlscan is the first: DEEP already reads urlscan
#: natively through core/intel/urlscan.py for the dossier fan-out, and the
#: server adds the operations a fan-out has no business performing on its own
#: — submitting a live scan, pulling a DOM, running an arbitrary corpus query.
BUILTIN_SERVERS: tuple[MCPServerConfig, ...] = (
    MCPServerConfig(
        id="urlscan",
        command=sys.executable,
        args=("-m", "urlscan_mcp.server"),
        env={"URLSCAN_API_KEY": "${URLSCAN_API_KEY}"},
        description=(
            "urlscan.io: submit live scans, read captured DOMs, and query the "
            "historical scan corpus."
        ),
        requires_package="urlscan_mcp",
        # Corpus search and assessment are already available through
        # threat_lookup on DEEP's own HTTP stack — cached, throttled and
        # attributed. Bridging them again would give the model two paths to the
        # same evidence with different failure modes, so the bridge exposes
        # only what the native path cannot do.
        allow_tools=(
            "scan_url", "scan_and_wait", "get_scan_result", "get_page_dom",
            "get_screenshot_url", "search_scans", "get_quotas",
            "list_available_countries", "server_capabilities",
        ),
        call_timeout_s=120.0,  # scan_and_wait polls for up to 90s by design
        # A bridged tool runs in a subprocess with its own HTTP client, so it
        # never sees core/intel/http.py's cache or its per-host throttle. Two
        # identical pivots during one investigation therefore hit urlscan.io
        # twice, where the native path would have hit it once — the bridge was
        # quietly the impolite half of the same integration.
        #
        # Only immutable or cheap reads are listed. A finished scan never
        # changes, and the country list changes yearly. Submissions are absent
        # on purpose: caching one would hand back a scan id for a scan that
        # never ran. get_quotas is absent because a stale quota is worse than
        # no quota, and get_page_dom because a cached megabyte per uuid is a
        # memory leak wearing a hat.
        cache_tools=(
            "search_scans", "get_scan_result", "get_screenshot_url",
            "list_available_countries", "server_capabilities",
        ),
        cache_ttl_s=3600.0,
    ),
)


def _coerce(entry: Dict[str, Any]) -> Optional[MCPServerConfig]:
    try:
        return MCPServerConfig(
            id=str(entry["id"]),
            command=str(entry.get("command") or sys.executable),
            args=tuple(str(a) for a in entry.get("args", ())),
            env={str(k): str(v) for k, v in (entry.get("env") or {}).items()},
            description=str(entry.get("description", "")),
            tool_prefix=str(entry.get("tool_prefix", "")),
            allow_tools=tuple(str(t) for t in entry.get("allow_tools", ())),
            deny_tools=tuple(str(t) for t in entry.get("deny_tools", ())),
            requires_package=entry.get("requires_package") or None,
            requires_env=tuple(str(v) for v in entry.get("requires_env", ())),
            enabled=bool(entry.get("enabled", True)),
            call_timeout_s=float(entry.get("call_timeout_s", DEFAULT_CALL_TIMEOUT_S)),
            cache_tools=tuple(str(t) for t in entry.get("cache_tools", ())),
            cache_ttl_s=float(entry.get("cache_ttl_s", 900.0)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("[MCP] ignoring malformed server entry %r: %s", entry, exc)
        return None


def _user_servers(path: Path) -> List[MCPServerConfig]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        # A broken config file must not take the assistant down with it.
        logger.warning("[MCP] could not read %s: %s", path, exc)
        return []
    entries = raw.get("servers") if isinstance(raw, dict) else raw
    if not isinstance(entries, list):
        logger.warning("[MCP] %s has no 'servers' list; ignoring", path)
        return []
    return [c for c in (_coerce(e) for e in entries if isinstance(e, dict)) if c]


def configured_servers(path: Path | str | None = None) -> List[MCPServerConfig]:
    """Built-in servers, overridden by ``data/mcp_servers.json`` where ids match."""
    merged: Dict[str, MCPServerConfig] = {s.id: s for s in BUILTIN_SERVERS}
    for server in _user_servers(Path(path) if path else CONFIG_PATH):
        merged[server.id] = server
    return list(merged.values())


def available_servers(path: Path | str | None = None) -> List[MCPServerConfig]:
    return [s for s in configured_servers(path) if s.available]
