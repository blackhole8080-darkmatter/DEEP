"""
core/plugins/base.py

Base class for all DEEP plugins.

Every plugin must inherit from DeepPlugin and implement its hooks.
The PluginManager auto-discovers and orchestrates them.

Example:
    class MyPlugin(DeepPlugin):
        name = "my_plugin"
        version = "1.0"

        async def on_init(self):
            self.register_tool("my_tool", self.my_tool_func)
            self.register_endpoint("GET", "/api/my/status", self.get_status)
            self.register_panel_card("My Module", "<div>stats</div>")

        async def on_start(self):
            self.start_background_task(self.poll_loop())

        async def on_stop(self):
            pass
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional, Awaitable

logger = logging.getLogger(__name__)


@dataclass
class PluginEndpoint:
    """An endpoint registered by a plugin."""
    method: str
    path: str
    handler: Callable


@dataclass
class PluginTool:
    """A tool registered by a plugin."""
    name: str
    handler: Callable
    description: str = ""


@dataclass
class PluginPanelCard:
    """A UI panel card registered by a plugin."""
    title: str
    html: str
    js_init: Optional[str] = None


@dataclass
class PluginBackgroundTask:
    """A background task registered by a plugin."""
    name: str
    coro: Awaitable
    interval_seconds: Optional[float] = None


class DeepPlugin(ABC):
    """
    Base class for all DEEP plugins.
    """

    # Override these in your plugin subclass
    name: str = "unnamed"
    version: str = "0.0.1"
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)

    def __init__(self, plugin_manager: Any):
        self.pm = plugin_manager
        self._endpoints: List[PluginEndpoint] = []
        self._tools: List[PluginTool] = []
        self._panel_cards: List[PluginPanelCard] = []
        self._bg_tasks: List[PluginBackgroundTask] = []
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._is_initialized = False
        self._is_running = False
        logger.info(f"[Plugin] Created {self.name} v{self.version}")

    # ─── Registration API (call these in on_init) ───────────────────────────

    def register_endpoint(self, method: str, path: str, handler: Callable):
        """Register a FastAPI endpoint."""
        self._endpoints.append(PluginEndpoint(method, path, handler))

    def register_tool(self, name: str, handler: Callable, description: str = ""):
        """Register a tool callable by the AI brain."""
        self._tools.append(PluginTool(name, handler, description))

    def register_panel_card(self, title: str, html: str, js_init: Optional[str] = None):
        """Register a UI panel card."""
        self._panel_cards.append(PluginPanelCard(title, html, js_init))

    def register_background_task(self, name: str, coro: Awaitable, interval: Optional[float] = None):
        """Register a background coroutine to run."""
        self._bg_tasks.append(PluginBackgroundTask(name, coro, interval))

    def register_event_handler(self, event_type: str, handler: Callable):
        """Register a handler for WebSocket events."""
        self._event_handlers.setdefault(event_type, []).append(handler)

    # ─── Lifecycle Hooks (override these) ──────────────────────────────────

    @abstractmethod
    async def on_init(self):
        """Called once during plugin initialization. Register your stuff here."""
        pass

    @abstractmethod
    async def on_start(self):
        """Called when the plugin should begin active work."""
        pass

    @abstractmethod
    async def on_stop(self):
        """Called during shutdown. Clean up resources."""
        pass

    # ─── Internal Lifecycle ──────────────────────────────────────────────────

    async def _init(self):
        if self._is_initialized:
            return
        try:
            await self.on_init()
            self._is_initialized = True
            logger.info(f"[Plugin] Initialized {self.name}")
        except Exception as e:
            logger.error(f"[Plugin] {self.name} init failed: {e}")

    async def _start(self):
        if not self._is_initialized:
            await self._init()
        if self._is_running:
            return
        try:
            await self.on_start()
            self._is_running = True
            logger.info(f"[Plugin] Started {self.name}")
        except Exception as e:
            logger.error(f"[Plugin] {self.name} start failed: {e}")

    async def _stop(self):
        if not self._is_running:
            return
        try:
            await self.on_stop()
            self._is_running = False
            logger.info(f"[Plugin] Stopped {self.name}")
        except Exception as e:
            logger.error(f"[Plugin] {self.name} stop failed: {e}")

    # ─── Introspection ──────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "initialized": self._is_initialized,
            "running": self._is_running,
            "endpoints": len(self._endpoints),
            "tools": [t.name for t in self._tools],
            "panel_cards": [c.title for c in self._panel_cards],
            "bg_tasks": [t.name for t in self._bg_tasks],
        }
