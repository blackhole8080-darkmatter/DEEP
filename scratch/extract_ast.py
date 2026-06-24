import ast

with open(r'c:\Users\Aryan\Aryan_Private\myAi\DEEP\core\application\tool_registry.py', 'r', encoding='utf-8') as f:
    source = f.read()

tree = ast.parse(source)

avail_dict_node = None
science_func_node = None
exec_func_node = None

for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        if isinstance(node.targets[0], ast.Attribute) and node.targets[0].attr == 'available_tools':
            avail_dict_node = node.value
    if isinstance(node, ast.FunctionDef) and node.name == '_science_compute':
        science_func_node = node
    if isinstance(node, ast.AsyncFunctionDef) and node.name == 'execute_tool':
        exec_func_node = node

import re
avail_str = ast.unparse(avail_dict_node)

science_str = ast.unparse(science_func_node)
science_str = science_str.replace("def _science_compute(self, ", "def _science_compute(")
science_str = science_str.replace("DeepToolRegistry._deep_orchestrator", "_deep_orchestrator")
science_str = science_str.replace("from engine.main import DEEP", "global _deep_orchestrator\n        from engine.main import DEEP")

# We want the body of execute_tool
exec_body_nodes = exec_func_node.body
# remove first try/except modern registry check if present
# actually let's just unparse the whole body
exec_body_str = ""
for stmt in exec_body_nodes:
    exec_body_str += ast.unparse(stmt) + "\n"

# replace self with ctx
exec_body_str = exec_body_str.replace("self.", "ctx.")
exec_body_str = exec_body_str.replace("ctx._science_compute", "_science_compute")
exec_body_str = exec_body_str.replace("DeepToolRegistry._deep_orchestrator", "_deep_orchestrator")

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

LEGACY_TOOLS = {avail_str}

_deep_orchestrator = None

{science_str}

async def execute_legacy_tool(ctx, tool_name: str, args: Dict[str, Any]) -> ToolResult:
'''
for line in exec_body_str.split('\n'):
    if line.strip():
        out += "    " + line + "\n"

out += '''

for name, info in LEGACY_TOOLS.items():
    if name in TOOL_SPECS:
        continue # Already ported
    def make_handler(tool_name):
        async def handler(ctx, args):
            return await execute_legacy_tool(ctx, tool_name, args)
        return handler
    # Register it!
    tool(name, info["description"], info.get("args", {}))(make_handler(name))
'''

with open(r'c:\Users\Aryan\Aryan_Private\myAi\DEEP\core\tools\legacy.py', 'w', encoding='utf-8') as f:
    f.write(out)
