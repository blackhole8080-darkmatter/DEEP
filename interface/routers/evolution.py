"""Self-evaluation / evolution endpoints."""

from fastapi import APIRouter, HTTPException, Query

from interface.deps import require

router = APIRouter(prefix="/api/evolution", tags=["evolution"])


@router.get("/stats")
async def evolution_stats():
    """Get self-evaluation engine statistics."""
    return require("self_eval").get_stats()


@router.get("/history")
async def evolution_history(limit: int = Query(20, ge=1, le=200)):
    """Get evolution event history."""
    return {"events": require("self_eval").get_evolution_history(limit)}


@router.get("/lessons")
async def evolution_lessons():
    """Get lessons learned."""
    return {"lessons": require("self_eval").get_lessons()}


@router.get("/prompts")
async def evolution_prompts():
    """Get all prompt variants."""
    return {"prompts": require("self_eval").get_prompt_variants()}


@router.get("/current-prompt")
async def current_prompt():
    """Get the current active system prompt."""
    return {"prompt": require("self_eval").get_current_prompt()}


@router.post("/evaluate")
async def force_evolution():
    """Force an evaluation and potential evolution."""
    result = require("self_eval").evaluate_and_evolve()
    if not result:
        # Too little history to evaluate is a fact about the request, not a
        # server fault — and not a success either, which is how the old
        # {"success": false} at 200 read to anything checking the status.
        raise HTTPException(
            status_code=409,
            detail="not enough interaction history to evaluate yet",
        )
    return {"success": True, "result": result}
