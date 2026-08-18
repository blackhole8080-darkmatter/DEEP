"""One connection to one MCP server, over stdio.

The MCP Python SDK exposes a session as nested async context managers, and the
anyio task groups underneath them may only be entered and exited from the same
task. Holding those context managers open on an object whose methods are called
from arbitrary request handlers — which is exactly what DEEP does — produces
"cancel scope in a different task" errors that surface as unrelated tool
failures much later.

So the session is not held on the object at all. Each server gets one worker
task that opens the session, keeps it open, and services calls arriving on a
queue. Everything crossing a task boundary is a plain message and a future.
That buys three things beyond correctness:

* **A hung server cannot hang the assistant.** Calls carry a timeout; on expiry
  the caller gets an error and the worker is torn down rather than left
  half-consumed.
* **A crashed server is restarted, once, on next use.** Subprocesses die — an
  upstream SDK bug, an OOM kill. The retry is single and reported, not a loop
  that hides a server which never comes back.
* **Startup is lazy.** Nothing is spawned until a tool from that server is
  actually called, so an unused server costs DEEP nothing.

Nothing here raises on connection failure. A dead server yields an error string
the model can read and work around, in the same spirit as the intel layer's
``Fetch``: the whole system degrades, it does not fail.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.mcp.config import MCPServerConfig

logger = logging.getLogger(__name__)

#: How long to wait for a server to spawn, initialise and list its tools.
STARTUP_TIMEOUT_S = 30.0


@dataclass(slots=True)
class MCPTool:
    """A tool discovered on a server."""

    server_id: str
    name: str
    description: str
    schema: Dict[str, Any]

    @property
    def arg_hints(self) -> Dict[str, str]:
        """The JSON schema flattened into DEEP's ``{name: description}`` form."""
        properties = (self.schema or {}).get("properties") or {}
        required = set((self.schema or {}).get("required") or [])
        hints: Dict[str, str] = {}
        for name, spec in properties.items():
            if not isinstance(spec, dict):
                continue
            parts = [str(spec.get("type", "any"))]
            if name in required:
                parts.append("required")
            if spec.get("description"):
                parts.append(str(spec["description"]))
            if spec.get("default") is not None:
                parts.append(f"default {spec['default']!r}")
            hints[name] = " — ".join(parts)
        return hints


@dataclass(slots=True)
class _Call:
    name: str
    args: Dict[str, Any]
    future: "asyncio.Future[Any]"


class MCPServerConnection:
    """A lazily-started MCP server subprocess and the tools it offers."""

    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self.tools: List[MCPTool] = []
        self.last_error: str = ""
        self._queue: "asyncio.Queue[Optional[_Call]]" = asyncio.Queue()
        self._worker: Optional[asyncio.Task] = None
        self._ready = asyncio.Event()
        self._start_lock = asyncio.Lock()

    # ── state ────────────────────────────────────────────────────────────────

    @property
    def running(self) -> bool:
        return self._worker is not None and not self._worker.done() and self._ready.is_set()

    def status(self) -> Dict[str, Any]:
        return {
            "id": self.config.id,
            "running": self.running,
            "available": self.config.available,
            "unavailable_reason": self.config.unavailable_reason,
            "tools": [t.name for t in self.tools],
            "last_error": self.last_error,
        }

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> bool:
        """Spawn the server and discover its tools. False (never raises) on failure."""
        if self.running:
            return True
        reason = self.config.unavailable_reason
        if reason:
            self.last_error = reason
            return False

        async with self._start_lock:
            if self.running:
                return True
            await self._teardown()
            self._ready = asyncio.Event()
            self._queue = asyncio.Queue()
            self.last_error = ""
            self._worker = asyncio.create_task(
                self._run(), name=f"mcp-{self.config.id}"
            )
            # Wait for whichever comes first: the server reporting ready, or
            # the worker giving up. Racing them means a server that dies on
            # startup is noticed immediately instead of after the timeout.
            waiter = asyncio.create_task(self._ready.wait())
            try:
                await asyncio.wait(
                    {self._worker, waiter},
                    timeout=STARTUP_TIMEOUT_S,
                    return_when=asyncio.FIRST_COMPLETED,
                )
            finally:
                waiter.cancel()

            if self._ready.is_set():
                logger.info(
                    "[MCP] %s ready with %d tool(s)", self.config.id, len(self.tools)
                )
                return True

            # Either the worker exited early or startup timed out. Both mean
            # the server is unusable; say which.
            if self._worker.done():
                self.last_error = self.last_error or "server exited during startup"
            else:
                self.last_error = f"server did not initialise within {STARTUP_TIMEOUT_S:.0f}s"
            await self._teardown()
            logger.warning("[MCP] %s failed to start: %s", self.config.id, self.last_error)
            return False

    async def aclose(self) -> None:
        await self._teardown()

    async def _teardown(self) -> None:
        worker, self._worker = self._worker, None
        if worker is None:
            return
        if not worker.done():
            await self._queue.put(None)  # graceful stop
            try:
                await asyncio.wait_for(asyncio.shield(worker), timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                worker.cancel()
                try:
                    await worker
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass
        self._ready.clear()

    # ── the worker ───────────────────────────────────────────────────────────

    async def _run(self) -> None:
        """Own the session for its whole life. Never called from outside."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(
            command=self.config.command,
            args=list(self.config.args),
            env=self.config.resolved_env(),
        )
        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    listing = await session.list_tools()
                    self.tools = [
                        MCPTool(
                            server_id=self.config.id,
                            name=t.name,
                            description=(t.description or "").strip(),
                            schema=dict(t.inputSchema or {}),
                        )
                        for t in listing.tools
                        if self._exposed(t.name)
                    ]
                    self._ready.set()
                    await self._serve(session)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - a subprocess can fail any way
            self.last_error = f"{type(exc).__name__}: {exc}"
            logger.warning("[MCP] %s session ended: %s", self.config.id, self.last_error)
        finally:
            self._ready.clear()
            self._drain(self.last_error or "server stopped")

    def _exposed(self, name: str) -> bool:
        if self.config.deny_tools and name in self.config.deny_tools:
            return False
        if self.config.allow_tools and name not in self.config.allow_tools:
            return False
        return True

    async def _serve(self, session: Any) -> None:
        while True:
            call = await self._queue.get()
            if call is None:
                return
            if call.future.done():  # caller already timed out
                continue
            try:
                result = await session.call_tool(call.name, call.args)
                if not call.future.done():
                    call.future.set_result(result)
            except asyncio.CancelledError:
                if not call.future.done():
                    call.future.set_exception(
                        RuntimeError(f"{self.config.id} was shut down mid-call")
                    )
                raise
            except Exception as exc:  # noqa: BLE001
                if not call.future.done():
                    call.future.set_exception(exc)

    def _drain(self, reason: str) -> None:
        """Fail everything still queued, so no caller waits on a dead server."""
        while not self._queue.empty():
            pending = self._queue.get_nowait()
            if pending is not None and not pending.future.done():
                pending.future.set_exception(RuntimeError(reason))

    # ── calling ──────────────────────────────────────────────────────────────

    async def call(self, name: str, args: Dict[str, Any]) -> Any:
        """Invoke a tool, starting or restarting the server as needed.

        Raises :class:`RuntimeError` with an explanatory message rather than
        letting a transport error surface as something unreadable.
        """
        if not self.running and not await self.start():
            raise RuntimeError(
                f"MCP server {self.config.id!r} is unavailable: "
                f"{self.last_error or 'unknown reason'}"
            )

        try:
            return await self._dispatch(name, args)
        except RuntimeError:
            # One restart, then give up. A server that dies twice in a row is
            # broken, and retrying forever would hide that behind slow calls.
            if not await self.start():
                raise RuntimeError(
                    f"MCP server {self.config.id!r} died and could not be restarted: "
                    f"{self.last_error or 'unknown reason'}"
                ) from None
            return await self._dispatch(name, args)

    async def _dispatch(self, name: str, args: Dict[str, Any]) -> Any:
        future: "asyncio.Future[Any]" = asyncio.get_running_loop().create_future()
        await self._queue.put(_Call(name=name, args=args, future=future))
        try:
            return await asyncio.wait_for(future, timeout=self.config.call_timeout_s)
        except asyncio.TimeoutError:
            # The worker may still be inside the call; tearing it down is the
            # only way to be sure the next call is not answered by this one.
            await self._teardown()
            raise RuntimeError(
                f"{self.config.id}.{name} did not answer within "
                f"{self.config.call_timeout_s:.0f}s; the server was restarted."
            ) from None
