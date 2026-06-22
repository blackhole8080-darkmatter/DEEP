"""
core/tools/builtin.py

Built-in DEEP tools defined with the modern @tool registry. Tools migrate here
from the legacy if/elif in core/application/tool_registry.py one at a time; each
becomes a small, self-contained handler instead of a switch branch.

Handlers receive `ctx` (the DeepToolRegistry instance — use it to reach
integrations like ctx.rag / ctx.finance / ctx.local_system) and `args` (dict).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from core.tools.registry import tool
from core.domain.models import ToolResult


@tool("get_time", "Get current exact date and time.", {})
async def get_time(ctx: Any, args: Dict[str, Any]) -> ToolResult:
    return ToolResult(True, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "get_time")
