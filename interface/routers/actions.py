"""Approvals: the endpoints that let a parked action actually proceed.

``core/pending_actions.py`` has gated destructive tools for a while, telling
the user their action was "sent to your Approvals panel" — but nothing ever
listed the queue or ran anything out of it. A parked action stayed parked
forever, and the message promising otherwise was wrong. These endpoints make
the gate real.

Approving re-runs the original tool through the same registry the reasoning
brain uses, with ``_approved=True`` added. The arguments come from the stored
entry, never from the approving request: a confirmation must apply to the
action that was actually shown to the user, or it confirms nothing.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from core import pending_actions
from interface.deps import require

router = APIRouter(prefix="/api/actions", tags=["actions"])


@router.get("/pending")
async def actions_pending():
    """Actions awaiting confirmation, newest first."""
    items = pending_actions.list_pending()
    return {"count": len(items), "pending": items}


@router.post("/{action_id}/approve")
async def actions_approve(action_id: str):
    """Confirm a parked action and run it.

    Consumed before execution, so a double-click cannot run it twice — but only
    after the tool registry is known to be reachable. Popping first would burn
    the user's approval on a 503: they said yes, nothing ran, and the entry is
    gone with no sign that their answer was swallowed.
    """
    registry = require("deep_tools")

    entry = pending_actions.pop(action_id)
    if entry is None:
        # Expired and unknown are the same to the caller, and both mean "do not
        # assume this ran". Saying which would leak whether an id ever existed.
        raise HTTPException(
            status_code=404,
            detail="No such pending action. It may have expired — ask DEEP to try again.",
        )

    result = await registry.execute_tool(entry["tool"], pending_actions.approved_args(entry))
    return {
        "id": action_id,
        "tool": entry["tool"],
        "label": entry["label"],
        "ok": bool(getattr(result, "ok", False)),
        "result": getattr(result, "content", ""),
    }


@router.post("/{action_id}/reject")
async def actions_reject(action_id: str):
    """Decline a parked action and drop it."""
    entry = pending_actions.pop(action_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="No such pending action.")
    return {"id": action_id, "tool": entry["tool"], "label": entry["label"], "rejected": True}
