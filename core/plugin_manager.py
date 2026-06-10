"""
core/plugin_manager.py

DEEP Plugin Manager — Auto-discovery, lifecycle, and orchestration.

Usage:
    from DEEP.core.plugin_manager import PluginManager

    pm = PluginManager()
    await pm.discover_plugins()   # Auto-find all plugins
    await pm.init_all()           # Initialize them
    await pm.start_all()          # Start background work
    
    # Get plugin info
    stats = pm.get_stats()
    
    # Shutdown
    await pm.stop_all()
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import logging
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

try:
    from core.event_bus import EventBus
except ImportError:
    from event_bus import EventBus

from core.plugins.base import DeepPlugin, PluginEndpoint

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Discovers, initializes, and orchestrates DEEP plugins.
    """

    def __init__(self, plugins_dir: Optional[Path] = None, event_bus: EventBus = None):
        self.plugins_dir = plugins_dir or Path(__file__).parent / "plugins"
        self.plugins: Dict[str, DeepPlugin] = {}
        self._bg_tasks: List[asyncio.Task] = []
        self.event_bus = event_bus

    async def start(self) -> None:
        """Activate the plugin manager."""
        logger.info("[PluginManager] Started")

    async def stop(self) -> None:
        """Deactivate the plugin manager."""
        await self.stop_all()
        logger.info("[PluginManager] Stopped")

    def status(self) -> Dict[str, Any]:
        """Return operational status."""
        return {
            "plugins": len(self.plugins),
            "endpoints": len(self.get_all_endpoints()),
        }

    # ─── Discovery ─────────────────────────────────────────────────────────

    async def discover_plugins(self) -> List[str]:
        """Auto-discover all plugin classes in core/plugins/."""
        discovered = []
        
        # Walk the plugins package
        import core.plugins as plugins_pkg
        package_path = Path(plugins_pkg.__file__).parent
        
        for _, module_name, is_pkg in pkgutil.iter_modules([str(package_path)]):
            if is_pkg or module_name in ("base",):
                continue
            
            try:
                module = importlib.import_module(f"core.plugins.{module_name}")
                
                # Find classes that inherit from DeepPlugin
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, DeepPlugin) and 
                        obj is not DeepPlugin and
                        not getattr(obj, '__abstractmethods__', None)):
                        
                        plugin = obj(self)
                        self.plugins[plugin.name] = plugin
                        discovered.append(plugin.name)
                        logger.info(f"[PluginManager] Discovered: {plugin.name} v{plugin.version}")
                        
            except Exception as e:
                logger.warning(f"[PluginManager] Failed to load {module_name}: {e}")
        
        return discovered

    # ─── Lifecycle ───────────────────────────────────────────────────────────

    async def init_all(self):
        """Initialize all discovered plugins."""
        for plugin in self.plugins.values():
            await plugin._init()

    async def start_all(self):
        """Start all initialized plugins."""
        for plugin in self.plugins.values():
            await plugin._start()
            
            # Start background tasks
            for bg in plugin._bg_tasks:
                if bg.interval_seconds:
                    task = asyncio.create_task(
                        self._run_periodic(bg.name, bg.coro, bg.interval_seconds)
                    )
                else:
                    # One-shot/long-lived task: accept a function or a coroutine.
                    c = bg.coro() if callable(bg.coro) else bg.coro
                    task = asyncio.create_task(c)
                self._bg_tasks.append(task)

    async def stop_all(self):
        """Stop all plugins and cancel background tasks."""
        for plugin in self.plugins.values():
            await plugin._stop()
        
        for task in self._bg_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._bg_tasks.clear()

    async def _run_periodic(self, name: str, coro, interval: float):
        """Run a coroutine periodically.

        `coro` is normally a coroutine FUNCTION (called fresh each interval). A
        bare coroutine object is tolerated for the first run, but can only be
        awaited once — so callers should pass the function, not coro().
        """
        while True:
            try:
                c = coro() if callable(coro) else coro
                await c
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"[PluginManager] Periodic task {name} error: {e}")
            await asyncio.sleep(interval)

    # ─── Accessors ───────────────────────────────────────────────────────────

    def get_plugin(self, name: str) -> Optional[DeepPlugin]:
        return self.plugins.get(name)

    def get_all_endpoints(self) -> List[PluginEndpoint]:
        """Collect all endpoints from all plugins."""
        endpoints = []
        for plugin in self.plugins.values():
            endpoints.extend(plugin._endpoints)
        return endpoints

    def get_all_tools(self) -> Dict[str, Callable]:
        """Collect all tools from all plugins."""
        tools = {}
        for plugin in self.plugins.values():
            for tool in plugin._tools:
                tools[tool.name] = tool.handler
        return tools

    def get_all_panel_cards(self) -> List[Dict[str, Any]]:
        """Collect all panel cards from all plugins."""
        cards = []
        for plugin in self.plugins.values():
            for card in plugin._panel_cards:
                cards.append({
                    "plugin": plugin.name,
                    "title": card.title,
                    "html": card.html,
                })
        return cards

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_plugins": len(self.plugins),
            "plugins": [p.to_dict() for p in self.plugins.values()],
            "total_endpoints": len(self.get_all_endpoints()),
            "total_tools": len(self.get_all_tools()),
            "total_panel_cards": len(self.get_all_panel_cards()),
        }

    # ─── Event Routing ──────────────────────────────────────────────────────

    def emit(self, plugin_name: str, event_type: str, payload: Any):
        """Emit an event from a plugin onto the central bus."""
        if self.event_bus:
            try:
                asyncio.create_task(self.event_bus.publish("plugin_event", {
                    "plugin": plugin_name,
                    "event_type": event_type,
                    "payload": payload,
                }))
            except RuntimeError:
                pass
