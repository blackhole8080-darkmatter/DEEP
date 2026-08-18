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
from core.intel.http import shared_http
from core.intel.live_stats import shared_live_intel
from core.intel.ops_terminal import OpsTerminal, command_catalog
from core.intel.osint_investigator import OSINTInvestigator
from core.intel.refresher import shared_refresher
from core.intel.urlscan import shared_urlscan
from core.playbooks import INSTALL_HINT, normalise_technique, shared_playbooks
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
    target: str = Query(
        ..., min_length=1, max_length=2048,
        description="IP, domain, URL, CVE, ASN, hash, MAC or ecosystem:package",
    ),
):
    """Fan one indicator out across every applicable public source."""
    dossier = await _investigator.investigate(target)
    if dossier.indicator == "unknown":
        raise HTTPException(status_code=422, detail=dossier.summary)
    return dossier.to_dict()


@router.get("/classify")
async def intel_classify(target: str = Query(..., min_length=1, max_length=2048)):
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


# ── response playbooks ───────────────────────────────────────────────────────


@router.get("/playbooks")
async def intel_playbooks(
    technique: Optional[str] = Query(None, description="ATT&CK id, e.g. T1071.001"),
    q: Optional[str] = Query(None, min_length=2, max_length=128,
                             description="free-text topic search"),
    limit: int = Query(10, ge=1, le=50),
):
    """Procedures covering a technique, or matching a topic."""
    library = shared_playbooks()
    if not library.installed:
        raise HTTPException(status_code=503, detail=INSTALL_HINT)
    if technique:
        # A malformed id and a valid id nothing covers are different answers.
        # `for_technique` returns [] for both, so without this check "T1O71"
        # (letter O) reads as "no procedure exists for this" rather than "that
        # is not a technique id".
        if not normalise_technique(technique):
            raise HTTPException(
                status_code=422,
                detail=f"'{technique}' is not an ATT&CK technique id; "
                       "expected TNNNN or TNNNN.NNN, e.g. T1071 or T1071.001",
            )
        found = library.for_technique(technique, limit=limit)
    elif q:
        found = library.search(q, limit=limit)
    else:
        raise HTTPException(status_code=422, detail="pass either technique or q")
    return {"count": len(found), "playbooks": [p.to_dict() for p in found]}


@router.get("/playbooks/status")
async def intel_playbooks_status():
    """Is a corpus installed, how much of it, and mapped to which frameworks."""
    return shared_playbooks().status()


@router.get("/playbooks/{name}")
async def intel_playbook(name: str):
    """One playbook's full procedure."""
    library = shared_playbooks()
    if not library.installed:
        raise HTTPException(status_code=503, detail=INSTALL_HINT)
    playbook = library.get(name)
    if playbook is None:
        raise HTTPException(status_code=404, detail=f"no playbook named '{name}'")
    return playbook.to_dict(include_body=True)


# ── cache & pre-warming ──────────────────────────────────────────────────────


@router.get("/cache")
async def intel_cache():
    """Both cache tiers plus the pre-warm loop — is the console warm or cold?"""
    return {
        "cache": await shared_http().cache_stats(),
        "refresher": shared_refresher().status(),
    }


@router.post("/cache/refresh")
async def intel_cache_refresh():
    """Re-fetch every due hot feed now, bypassing both cache tiers."""
    return await shared_refresher().refresh_once()


@router.delete("/cache")
async def intel_cache_clear():
    """Drop everything cached, in memory and on disk."""
    await shared_http().clear_persistent_cache()
    return {"cleared": True}


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


# ── urlscan.io ───────────────────────────────────────────────────────────────


class ScanRequest(BaseModel):
    url: str = Field(..., min_length=4, max_length=2048)
    visibility: str = Field("public", pattern="^(public|unlisted)$")
    tags: Optional[list[str]] = None


@router.post("/urlscan/submit")
async def urlscan_submit(body: ScanRequest):
    """Submit a URL to urlscan.io for a live scan.

    POST rather than GET because this has a side effect a user would care
    about: a public scan is permanently visible on urlscan.io, and the site
    owner can see it was scanned.
    """
    if not body.url.lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="Expected an http:// or https:// URL.")
    result = await shared_urlscan().submit(
        body.url, visibility=body.visibility, tags=body.tags
    )
    if "error" in result:
        # A missing key is the caller's to fix, not an upstream fault.
        status = 428 if "API key" in result["error"] else 502
        raise HTTPException(status_code=status, detail=result["error"])
    return result


@router.get("/urlscan/result/{uuid}")
async def urlscan_result(uuid: str, full: bool = Query(False)):
    """A finished scan, summarised. ``full=true`` returns the raw document."""
    result = await shared_urlscan().result(uuid, full=full)
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


# ── MCP bridge ───────────────────────────────────────────────────────────────


@router.get("/mcp")
async def intel_mcp_status():
    """External MCP servers DEEP bridges, and the tools they contribute.

    Reports why an unavailable server is unavailable, so a missing tool is
    diagnosable from here rather than by watching the model fail to call it.
    """
    from core.mcp import shared_bridge

    return shared_bridge().status()
