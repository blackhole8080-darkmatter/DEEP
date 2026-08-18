"""MCP client support — DEEP as an MCP *host*, not just an MCP server.

``mcp_server/deep_mcp.py`` exposes DEEP to Claude Desktop and Cursor. This
package points the other way: it lets DEEP's own reasoning brain drive tools
that live in external MCP servers, so a capability someone already built and
tested does not have to be reimplemented inside DEEP to be usable by it.

- :mod:`core.mcp.config` — which servers to run, and whether each is available
- :mod:`core.mcp.client` — one stdio server connection, with lifecycle
- :mod:`core.mcp.bridge` — adapts discovered MCP tools into DEEP's tool registry
"""

from core.mcp.bridge import MCPBridge, shared_bridge
from core.mcp.client import MCPServerConnection
from core.mcp.config import MCPServerConfig, configured_servers

__all__ = [
    "MCPBridge",
    "MCPServerConfig",
    "MCPServerConnection",
    "configured_servers",
    "shared_bridge",
]
