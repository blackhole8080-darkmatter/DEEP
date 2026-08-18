"""Human-in-the-loop gate for actions DEEP should not take on its own.

When a tool would do something irreversible or outward-facing — block a
device, drop the VPN, publish a URL to a public scanning service — it parks the
call here instead of executing. The approvals API (``/api/actions/*``) lists
what is waiting; approving re-runs the tool with ``_approved=True``, which the
tool treats as the go-ahead.

The gate is only worth having if a parked action can actually leave the queue,
so three properties matter:

* **Entries expire.** An approval is consent to do a thing *now*. A publish
  request approved an hour after the conversation that produced it has lost the
  context that made it reasonable, so entries carry a TTL and expired ones are
  swept rather than surfaced.
* **The queue is bounded.** A model in a retry loop can enqueue the same action
  repeatedly. Past the cap the oldest entry is dropped, so the queue stays a
  list a human can read rather than a log.
* **Rejection is a first-class outcome.** Without it the only way to clear an
  entry is to approve it, which turns the panel into pressure to say yes.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

#: An approval is consent to act now, not a standing permission.
DEFAULT_TTL_S = 15 * 60

#: Past this, the oldest entry is dropped to make room.
MAX_PENDING = 50

_pending: Dict[str, Dict[str, Any]] = {}

#: Called when the queue changes, as ``notifier(event, payload)``. The HUD
#: needs to hear about a parked action now, not on its next poll — an approval
#: expires in 15 minutes and the user is usually still reading the reply that
#: triggered it. Kept as a hook rather than an event-bus import so this module
#: stays dependency-free and testable on its own; ``interface/server.py`` wires
#: it to the bus, whose wildcard subscriber forwards to the WebSocket.
_notifier: Optional[Callable[[str, Dict[str, Any]], None]] = None


def set_notifier(fn: Optional[Callable[[str, Dict[str, Any]], None]]) -> None:
    """Register the queue-change hook. Pass None to detach."""
    global _notifier
    _notifier = fn


def _notify(event: str, payload: Dict[str, Any]) -> None:
    """Best-effort. A broken notifier must not break the gate it reports on."""
    if _notifier is None:
        return
    try:
        _notifier(event, payload)
    except Exception:  # noqa: BLE001 - the notifier is someone else's code
        logger.warning("[approvals] notifier failed for %s", event, exc_info=True)


def enqueue(
    tool: str,
    args: Dict[str, Any],
    label: str,
    detail: str = "",
    *,
    ttl_s: float = DEFAULT_TTL_S,
) -> str:
    """Park a tool call for confirmation. Returns the id to approve it by."""
    _sweep()
    if len(_pending) >= MAX_PENDING:
        oldest = min(_pending.values(), key=lambda a: a["created"])
        _pending.pop(oldest["id"], None)

    aid = uuid.uuid4().hex[:8]
    now = time.time()
    _pending[aid] = {
        "id": aid,
        "tool": tool,
        # The approved flag is set at approval time, never carried in from the
        # caller — otherwise a tool could enqueue itself pre-approved.
        "args": {k: v for k, v in (args or {}).items() if k != "_approved"},
        "label": label,
        "detail": detail,
        "created": now,
        "expires_at": now + ttl_s,
    }
    _notify("approval_pending", {
        "id": aid, "tool": tool, "label": label, "detail": detail,
        "pending": len(_pending),
    })
    return aid


def list_pending() -> List[Dict[str, Any]]:
    """Everything still awaiting a decision, newest first."""
    _sweep()
    return [
        {
            "id": a["id"],
            "tool": a["tool"],
            "label": a["label"],
            "detail": a["detail"],
            "args": a["args"],
            "created": a["created"],
            "expires_in_s": max(0, int(a["expires_at"] - time.time())),
        }
        for a in sorted(_pending.values(), key=lambda x: -x["created"])
    ]


def get(aid: str) -> Optional[Dict[str, Any]]:
    """Peek at one entry without consuming it. None if unknown or expired."""
    _sweep()
    return _pending.get(aid)


def pop(aid: str) -> Optional[Dict[str, Any]]:
    """Remove and return one entry. None if unknown or already expired."""
    _sweep()
    entry = _pending.pop(aid, None)
    if entry is not None:
        # Fired for approvals and rejections alike: a second browser tab needs
        # to drop the entry from its list either way.
        _notify("approval_resolved", {
            "id": aid, "tool": entry["tool"], "pending": len(_pending),
        })
    return entry


def approved_args(entry: Dict[str, Any]) -> Dict[str, Any]:
    """The stored arguments, marked approved, ready to re-run the tool with."""
    return {**entry["args"], "_approved": True}


def count() -> int:
    _sweep()
    return len(_pending)


def clear() -> None:
    """Drop everything. For tests and for an explicit 'dismiss all'."""
    _pending.clear()


def _sweep() -> None:
    """Drop entries whose consent window has closed."""
    now = time.time()
    for aid in [a for a, entry in _pending.items() if entry["expires_at"] <= now]:
        _pending.pop(aid, None)
