"""
core/tools/registry.py

Modern, decorator-driven tool registry for DEEP — the replacement for the
1,100-line if/elif dispatch in core/application/tool_registry.py.

A tool is registered with one decorator:

    @tool("get_time", "Get the current date and time.", {})
    async def get_time(ctx, args):
        return ToolResult(True, ..., "get_time")

`ctx` is the DeepToolRegistry instance (so handlers reach its integrations:
ctx.rag, ctx.finance, ctx.local_system, ...). Dispatch is an O(1) dict lookup.
DeepToolRegistry consults this registry FIRST and falls back to its legacy switch,
so tools migrate over incrementally with zero behaviour change (strangler pattern).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict

Handler = Callable[[Any, Dict[str, Any]], Awaitable[Any]]


@dataclass
class ToolSpec:
    name: str
    description: str
    args: Dict[str, str]
    handler: Handler


# Global registry. Populated by @tool decorators at import time.
TOOL_SPECS: Dict[str, ToolSpec] = {}


def tool(name: str, description: str, args: Dict[str, str] | None = None):
    """Register an async tool handler. Handler signature: (ctx, args) -> ToolResult."""
    def deco(fn: Handler) -> Handler:
        if name in TOOL_SPECS:
            raise ValueError(f"duplicate tool registration: {name!r}")
        TOOL_SPECS[name] = ToolSpec(name, description, args or {}, fn)
        return fn
    return deco
