import re

with open(r'c:\Users\Aryan\Aryan_Private\myAi\DEEP\core\application\tool_registry.py', 'r', encoding='utf-8') as f:
    source = f.read()

# Extract available_tools
avail_match = re.search(r'self\.available_tools = (\{.*?\n        \})', source, re.DOTALL)

# Extract science_compute
science_match = re.search(r'def _science_compute\(self, query: str\).*?return \{\}\n', source, re.DOTALL)

# Extract execute_tool body
exec_match = re.search(r'    async def execute_tool\(self, tool_name: str, args: Dict\[str, Any\]\) -> ToolResult:\n(.*?)    # ----------\n    # OLD REFLECTION', source, re.DOTALL)

science_func = science_match.group(0)
science_func = science_func.replace("def _science_compute(self, ", "def _science_compute(")
science_func = science_func.replace("DeepToolRegistry._deep_orchestrator", "global _deep_orchestrator\n        if _deep_orchestrator is None:\n            from engine.main import DEEP\n            _deep_orchestrator = DEEP()\n        return _deep_orchestrator")

exec_body = exec_match.group(1)
# remove the first few lines that do modern registry check
exec_body = re.sub(r'        try:\n            # Modern registry first.*?\n            if spec is not None:\n                return await spec\.handler\(self, args\)', '        try:', exec_body, flags=re.DOTALL)

out = f'''"""
core/tools/legacy.py

This module encapsulates the legacy tool registry.
It dynamically wraps all unmigrated tools into the modern @tool decorator registry.
"""
import asyncio
import json
import logging
from typing import Dict, Any

from core.domain.models import ToolResult
from core.tools.registry import tool, TOOL_SPECS
from core.integrations import integration_manager

logger = logging.getLogger(__name__)

LEGACY_TOOLS = {avail_match.group(1)}

_deep_orchestrator = None

{science_func}

async def execute_legacy_tool(ctx, tool_name: str, args: Dict[str, Any]) -> ToolResult:
{exec_body}

for name, info in LEGACY_TOOLS.items():
    if name in TOOL_SPECS:
        continue # Already ported
    def make_handler(tool_name):
        async def handler(ctx, args):
            return await execute_legacy_tool(ctx, tool_name, args)
        return handler
    # Register it!
    tool(name, info["description"], info.get("args", {{}}))(make_handler(name))
'''

out = out.replace('self._science_compute', '_science_compute')
out = out.replace('self.', 'ctx.')
out = out.replace('DeepToolRegistry._deep_orchestrator', '_deep_orchestrator')

with open(r'c:\Users\Aryan\Aryan_Private\myAi\DEEP\core\tools\legacy.py', 'w', encoding='utf-8') as f:
    f.write(out)
