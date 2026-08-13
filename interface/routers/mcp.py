"""External MCP servers: which are connected, and what they gave DEEP.

A tool that silently failed to register is indistinguishable from one that was
never configured, so this surface exists to tell them apart — per server, with
the reason it is down.
"""

from __future__ import annotations

from fastapi import APIRouter

from core.mcp_client import shared_mcp_hub

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


@router.get("/status")
async def mcp_status():
    """Config location, per-server connection state, and any startup errors."""
    return shared_mcp_hub().status()


@router.get("/tools")
async def mcp_tools():
    """Every tool DEEP borrowed from an external server."""
    return {"tools": shared_mcp_hub().tools()}
