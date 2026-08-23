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
import math
import os
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.mcp.config import MCPServerConfig

logger = logging.getLogger(__name__)

#: How long to wait for a server to spawn, initialise and list its tools.
#: A warm handshake is ~3s; the headroom is for a cold interpreter importing
#: its dependencies on a machine that is busy doing something else. Override
#: with DEEP_MCP_STARTUP_TIMEOUT when a server is legitimately slower.
def _startup_timeout() -> float:
    raw = os.environ.get("DEEP_MCP_STARTUP_TIMEOUT", "")
    try:
        value = float(raw)
    except ValueError:
        return 60.0
    # float() accepts "inf" and "nan". An infinite budget is not a long budget:
    # it removes the deadline entirely, and a wedged child then hangs the boot
    # it was given a deadline to survive — the exact failure this timeout
    # exists for, reachable by a plausible-looking setting.
    if not math.isfinite(value) or value <= 0:
        return 60.0
    return value


STARTUP_TIMEOUT_S = _startup_timeout()


def describe_exception(exc: BaseException) -> str:
    """A cause a human can act on, even when it arrives wrapped in a group.

    The MCP SDK runs its stdio transport inside an anyio task group, so almost
    every real failure — the interpreter not found, the module refusing to
    import, the child dying mid-handshake — reaches us as an ``ExceptionGroup``
    whose ``str()`` is "unhandled errors in a TaskGroup (1 sub-exception)".
    That sentence names the plumbing and hides the fault, which is how a
    working diagnosis turns into a shrug. Flatten the group and report the
    leaves instead; nesting can be arbitrarily deep, so recurse.
    """
    leaves: List[str] = []

    def walk(err: BaseException) -> None:
        sub = getattr(err, "exceptions", None)
        if sub:
            for item in sub:
                walk(item)
            return
        text = str(err).strip()
        leaves.append(f"{type(err).__name__}: {text}" if text else type(err).__name__)

    walk(exc)
    # Deduplicate while preserving order: a task group that loses five workers
    # to the same broken pipe should say so once.
    seen: set[str] = set()
    unique = [x for x in leaves if not (x in seen or seen.add(x))]
    if not unique:
        return f"{type(exc).__name__}: {exc}"
    return "; ".join(unique)


#: How much of a dying child's stderr to keep. Enough for a traceback's last
#: frames and the exception line; not so much that one bad server floods a log.
STDERR_TAIL_CHARS = 800

#: Ceiling on the captured stderr held in memory. Generous enough that the tail
#: survives a multi-byte encoding and a long traceback; fixed, so a server that
#: chatters for a week costs the same as one that chatters for a minute.
STDERR_TAIL_BYTES = 8192


class _StderrTail:
    """A bounded window onto a child's stderr, kept in memory.

    A temp file was the obvious first choice and it was wrong. This capture
    lives for the whole session rather than just the handshake — ``_serve``
    runs for as long as the server does — and MCP servers log to stderr on
    every request, so the file grew for as long as DEEP ran. Nothing ever
    truncated it, and only the last few hundred characters were ever read.

    The child needs a real file descriptor: the SDK hands ``errlog`` straight
    to ``anyio.open_process(stderr=...)``, so no Python-level buffer can
    receive its writes. Hence a pipe. The pipe must then be drained
    continuously or the child blocks once it has filled it, which would wedge
    the very server we are trying to diagnose — so a daemon thread reads it
    into a fixed-size buffer and throws away everything but the tail. Daemon,
    because a child that never closes its end must not keep DEEP from exiting.
    """

    def __init__(self, limit: int = STDERR_TAIL_BYTES) -> None:
        self._limit = limit
        self._buf = bytearray()
        self._lock = threading.Lock()
        self._read_fd, write_fd = os.pipe()
        #: Handed to the SDK as `errlog`; unbuffered, because the child writes
        #: through the descriptor and anything buffered here would never arrive.
        self.file = os.fdopen(write_fd, "wb", 0)
        self._thread = threading.Thread(
            target=self._drain, name="mcp-stderr", daemon=True
        )
        self._thread.start()

    def _drain(self) -> None:
        try:
            while True:
                chunk = os.read(self._read_fd, 4096)
                if not chunk:  # every writer has closed
                    return
                with self._lock:
                    self._buf.extend(chunk)
                    if len(self._buf) > self._limit:
                        del self._buf[: -self._limit]
        except OSError:
            return
        finally:
            try:
                os.close(self._read_fd)
            except OSError:
                pass

    def text(self) -> str:
        """The tail so far, collapsed to one line."""
        with self._lock:
            raw = bytes(self._buf)
            clipped = len(self._buf) >= self._limit
        text = raw.decode("utf-8", errors="replace").strip()
        if not text:
            return ""
        if len(text) > STDERR_TAIL_CHARS:
            text = text[-STDERR_TAIL_CHARS:]
            clipped = True
        return ("..." if clipped else "") + " ".join(text.split())

    def close(self) -> None:
        """Close our end; the drain thread sees EOF once the child closes too."""
        try:
            self.file.close()
        except OSError:
            pass


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
        # The child's own stderr is the only place that says *why* it died —
        # a bad interpreter, a failed import, a missing key. The SDK sends it
        # to DEEP's stderr by default, where it interleaves with every other
        # subsystem and is lost. Capture it to a private spool instead and
        # attach the tail to the error, so "BrokenResourceError" arrives with
        # the child's explanation next to it.
        spool = _StderrTail()
        try:
            async with stdio_client(params, errlog=spool.file) as (read, write):
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
            self.last_error = describe_exception(exc)
            detail = spool.text()
            if detail:
                self.last_error = f"{self.last_error} — child said: {detail}"
            logger.warning("[MCP] %s session ended: %s", self.config.id, self.last_error)
        finally:
            spool.close()
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
