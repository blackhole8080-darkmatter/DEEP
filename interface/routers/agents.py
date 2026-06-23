"""Agents, Actions, and Interactive Prompts endpoints."""
from fastapi import APIRouter
from datetime import datetime
import uuid
import asyncio
from interface.deps import services

router = APIRouter(tags=["agents"])


@router.get("/api/agents")
async def list_agents():
    """List all active agents."""
    try:
        agents = services.agent_factory.list_agents()
        return {"agents": agents}
    except Exception as e:
        return {"error": str(e)}

@router.post("/api/agents")
async def create_agent_endpoint(data: dict):
    """Create a new agent."""
    name = data.get("name")
    role = data.get("role", "custom")
    if not name:
        return {"error": "Missing name"}
    try:
        agent = services.agent_factory.create_agent(name, role)
        return {"success": True, "agent": agent.to_dict()}
    except ValueError as e:
        return {"error": str(e)}

@router.get("/api/agents/stats")
async def agent_stats():
    """Get agent factory statistics."""
    try:
        return services.agent_factory.stats()
    except Exception as e:
        return {"error": str(e)}

@router.post("/api/agents/task")
async def assign_agent_task(data: dict):
    """Spawn an agent for `role` and run `task` in the background. Returns a task id to poll."""
    import uuid
    task_text = (data.get("task") or "").strip()
    role = (data.get("role") or "researcher").strip()
    if not task_text:
        return {"error": "Missing task"}

    jid = uuid.uuid4().hex[:8]
    name = f"{role}-{jid}"
    try:
        agent = services.agent_factory.create_agent(name, role)
    except Exception:
        agent = services.agent_factory.get_agent(name) or services.agent_factory.create_agent(f"agent-{jid}", "custom")

    job = {
        "id": jid, "agent": agent.name, "role": role, "task": task_text,
        "status": "running", "result": None, "error": None,
        "created": datetime.now().isoformat(), "latency_ms": None,
    }
    services.agent_jobs[jid] = job
    await services.event_bus.publish("agent_task_started", {"id": jid, "agent": agent.name, "role": role, "task": task_text[:120]})

    async def _run():
        try:
            t = await agent.execute(task_text)
            job["status"] = t.status.value if hasattr(t.status, "value") else str(t.status)
            job["result"] = t.result
            job["error"] = t.error
            job["latency_ms"] = round(t.latency_ms) if t.latency_ms else None
        except Exception as e:
            job["status"] = "failed"
            job["error"] = str(e)
        await services.event_bus.publish("agent_task_done", {"id": jid, "agent": agent.name, "status": job["status"]})

    asyncio.create_task(_run())
    return {"success": True, "task_id": jid, "agent": agent.name}

@router.get("/api/agents/tasks")
async def list_agent_tasks():
    """List recent agent task jobs (newest first)."""
    jobs = sorted(services.agent_jobs.values(), key=lambda j: j["created"], reverse=True)[:30]
    return {"tasks": jobs}

@router.get("/api/agents/task/{jid}")
async def get_agent_task(jid: str):
    return services.agent_jobs.get(jid) or {"error": "not found"}

@router.get("/api/security/snapshot")
async def security_snapshot():
    """Full network snapshot with devices and events."""
    try:
        snap = await netmon.get_snapshot()
        return snap.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/actions/pending")
async def actions_pending():
    """Destructive actions DEEP wants to take, awaiting your approval (HITL)."""
    from core.pending_actions import list_pending
    return {"pending": list_pending()}

@router.post("/api/actions/respond")
async def actions_respond(data: dict):
    """Approve or deny a parked action. On approval the tool runs for real."""
    from core.pending_actions import pop
    aid = data.get("id")
    approve = bool(data.get("approve"))
    act = pop(aid) if aid else None
    if not act:
        return {"error": "Action not found (already handled?)"}
    if not approve:
        return {"executed": False, "result": f"Denied: {act.get('label')}"}
    try:
        res = await deep_tools.execute_tool(act["tool"], {**act["args"], "_approved": True})
        return {"executed": True, "result": getattr(res, "content", str(res))}
    except Exception as e:
        return {"executed": False, "result": f"Execution failed: {e}"}

@router.get("/api/interactive/pending")
async def get_pending_interactive():
    """Get all pending interactive responses."""
    from core.interactive_response import interactive_manager
    return {"pending": interactive_manager.list_pending()}

@router.post("/api/interactive/respond")
async def respond_to_interactive(data: dict):
    """Process user response to an interactive prompt."""
    from core.interactive_response import interactive_manager
    response_id = data.get("response_id")
    selection = data.get("selection")
    
    if not response_id or not selection:
        return {"error": "Missing response_id or selection"}
    
    result = interactive_manager.process_selection(response_id, selection)
    return result

