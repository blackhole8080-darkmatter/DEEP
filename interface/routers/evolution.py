"""Self-evaluation / evolution endpoints."""

from fastapi import APIRouter

from interface.deps import services

router = APIRouter(prefix="/api/evolution", tags=["evolution"])


@router.get("/stats")
async def evolution_stats():
    """Get self-evaluation engine statistics."""
    try:
        return services.self_eval.get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.get("/history")
async def evolution_history(limit: int = 20):
    """Get evolution event history."""
    try:
        return {"events": services.self_eval.get_evolution_history(limit)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/lessons")
async def evolution_lessons():
    """Get lessons learned."""
    try:
        return {"lessons": services.self_eval.get_lessons()}
    except Exception as e:
        return {"error": str(e)}


@router.get("/prompts")
async def evolution_prompts():
    """Get all prompt variants."""
    try:
        return {"prompts": services.self_eval.get_prompt_variants()}
    except Exception as e:
        return {"error": str(e)}


@router.get("/current-prompt")
async def current_prompt():
    """Get the current active system prompt."""
    try:
        return {"prompt": services.self_eval.get_current_prompt()}
    except Exception as e:
        return {"error": str(e)}


@router.post("/evaluate")
async def force_evolution():
    """Force an evaluation and potential evolution."""
    try:
        result = services.self_eval.evaluate_and_evolve()
        if result:
            return {"success": True, "result": result}
        return {"success": False, "message": "Not enough data to evaluate"}
    except Exception as e:
        return {"error": str(e)}
