"""
core/tools/deep_registry.py

Tool Registry Bridge - Links Integrations to the modern @tool registry.
Replaces the old monolithic core/application/tool_registry.py
"""
import json
import logging
from typing import Dict, Any

from core.domain.interfaces import ToolExecutor
from core.domain.models import ToolResult
from core.integrations import integration_manager

# Import modern tool decorators to register them
from core.tools.registry import TOOL_SPECS
import core.tools.builtin
import core.tools.ml
import core.tools.files
import core.tools.etis
import core.tools.legacy # Auto-registers remaining tools from the old monolith

logger = logging.getLogger(__name__)

class DeepToolRegistry(ToolExecutor):
    """
    Exposes available integrations as tools to the LLM.
    """
    
    def __init__(self):
        from core.integrations.cyber_sec import CyberSecurityIntegration
        from core.integrations.vision import VisionIntegration
        from core.integrations.xr_bridge import XRBridgeIntegration
        from core.interactive_response import interactive_manager
        
        self.cyber = CyberSecurityIntegration()
        self.vision = VisionIntegration()
        self.xr = XRBridgeIntegration()
        self.interactive = interactive_manager
        
        from core.integrations.phone_control import PhoneControl

        self.phone = PhoneControl()  # ADB (Android) + Shortcuts (iPhone) bridge
        self.phone = PhoneControl()  # ADB (Android) + Shortcuts (iPhone) bridge
        self.world_model = None
        self.plugin_manager = None  # set by server after plugins start; bridges plugin tools

    def describe_tools(self) -> str:
        desc = "AVAILABLE TOOLS:\n"
        for name, spec in TOOL_SPECS.items():
            desc += f"- {name}: {spec.description} | Args: {json.dumps(spec.args)}\n"
        desc += "\\nTo use a tool, YOU MUST output ONLY this exact format: [TOOL:{\"name\": \"tool_name\", \"args\": {\"arg\": \"value\"}}]"
        return desc

    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
        logger.info(f"[TOOL] Executing {tool_name} with {args}")
        import time as _time
        try:
            from core import telemetry as _tel
        except Exception:
            _tel = None
        _t0 = _time.time()

        def _record(ok: bool, error: str = "") -> None:
            if _tel:
                _tel.record_tool(tool_name, (_time.time() - _t0) * 1000, ok=ok, error=error)

        spec = TOOL_SPECS.get(tool_name)
        if spec is None:
            _record(False, "unknown tool")
            return ToolResult(False, f"Unknown tool: {tool_name}", tool_name)
        try:
            result = await spec.handler(self, args)
            _record(bool(getattr(result, "ok", True)),
                    "" if getattr(result, "ok", True) else getattr(result, "content", "")[:200])
            return result
        except Exception as e:
            logger.error(f"[TOOL ERROR] {tool_name}: {e}")
            _record(False, f"{type(e).__name__}: {e}")
            return ToolResult(False, f"Exception executing {tool_name}: {e}", tool_name)
