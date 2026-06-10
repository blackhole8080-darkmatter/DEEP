"""
core/pending_actions.py — human-in-the-loop gate for destructive actions.

When DEEP wants to take a protective/irreversible action (block a device, drop
the VPN), the action is parked here instead of executing. The Approvals UI lists
it; on approval the server re-runs the tool with _approved=True.
"""
from __future__ import annotations

import time
import uuid

_pending: dict[str, dict] = {}


def enqueue(tool: str, args: dict, label: str, detail: str = "") -> str:
    aid = uuid.uuid4().hex[:8]
    _pending[aid] = {
        "id": aid, "tool": tool, "args": dict(args or {}),
        "label": label, "detail": detail, "created": time.time(),
    }
    return aid


def list_pending() -> list[dict]:
    # newest first; hide the internal _approved flag
    out = []
    for a in sorted(_pending.values(), key=lambda x: -x["created"]):
        out.append({"id": a["id"], "tool": a["tool"], "label": a["label"], "detail": a["detail"]})
    return out


def pop(aid: str) -> dict | None:
    return _pending.pop(aid, None)


def count() -> int:
    return len(_pending)
