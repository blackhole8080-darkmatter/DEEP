"""Public-API intelligence endpoints: OSINT pivots, live stats, map, terminal.

Unlike the older routers in this package, handlers here return real HTTP status
codes on failure rather than a 200 carrying ``{"error": ...}``. That pattern is
what let three NameError bugs sit undetected in this codebase — the frontend
cannot tell a failure from a result when both are 200.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.intel import public_apis
from core.intel.live_stats import shared_live_intel
from core.intel.osint_investigator import OSINTInvestigator
from core.intel.ops_terminal import OpsTerminal, command_catalog
from interface.deps import services

router = APIRouter(prefix="/api/intel", tags=["intel"])

_investigator = OSINTInvestigator()


def _terminal() -> OpsTerminal:
    # Built per request so it always sees the current service registry.
    return OpsTerminal(investigator=_investigator, live=shared_live_intel(), services=services)


# ── catalog ──────────────────────────────────────────────────────────────────


@router.get("/sources")
async def intel_sources(category: Optional[str] = None):
    """The public-API catalog, with live/keyless status for each source."""
    summary = public_apis.summary()
    if category:
        summary["sources"] = [s for s in summary["sources"] if s["category"] == category.lower()]
    return summary


# ── investigation ────────────────────────────────────────────────────────────


@router.get("/investigate")
async def intel_investigate(
    target: str = Query(..., min_length=1, max_length=253, description="IP, domain, CVE, ASN, hash, MAC or ecosystem:package"),
):
    """Fan one indicator out across every applicable public source."""
    dossier = await _investigator.investigate(target)
    if dossier.indicator == "unknown":
        raise HTTPException(status_code=422, detail=dossier.summary)
    return dossier.to_dict()


@router.get("/classify")
async def intel_classify(target: str = Query(..., min_length=1, max_length=253)):
    """What kind of indicator is this? Used by the UI to preview a pivot."""
    kind = OSINTInvestigator.classify(target)
    if kind is None:
        return {"target": target, "indicator": None, "sources": []}
    return {
        "target": target,
        "indicator": kind.value,
        "sources": [a.to_dict() for a in public_apis.for_indicator(kind)],
    }


# ── live stats & map ─────────────────────────────────────────────────────────


@router.get("/stats")
async def intel_stats():
    """Global cyber statistics for the operations-center tiles."""
    return await shared_live_intel().cyber_stats()


@router.get("/map")
async def intel_map(limit: int = Query(120, ge=1, le=500)):
    """Geolocated attacker and C2 nodes for the intelligence map."""
    return await shared_live_intel().threat_map(limit=limit)


# ── operations terminal ──────────────────────────────────────────────────────


class TerminalCommand(BaseModel):
    line: str = Field(..., min_length=1, max_length=512)


@router.get("/terminal/commands")
async def terminal_commands():
    """Command catalog, for help output and UI autocomplete."""
    return {"commands": command_catalog()}


@router.post("/terminal/exec")
async def terminal_exec(body: TerminalCommand):
    """Execute one read-only operations command."""
    result = await _terminal().execute(body.line)
    return result.to_dict()
