"""Email integration endpoints."""
from fastapi import APIRouter
from core.integrations.email import EmailIntegration

router = APIRouter(prefix="/api/email", tags=["email"])
_email_api = EmailIntegration()

@router.get("/inbox")
async def email_inbox(limit: int = 20):
    return _email_api.inbox_summary(limit=limit)

@router.get("/search")
async def email_search(q: str, limit: int = 10):
    return _email_api.search(q, limit=limit)

@router.post("/send")
async def email_send(data: dict):
    return _email_api.send(data.get("to", ""), data.get("subject", ""), data.get("body", ""))

@router.post("/track")
async def email_track(data: dict):
    return _email_api.track_thread(
        data.get("msg_id", ""), data.get("sender", ""), data.get("subject", ""),
        notes=data.get("notes", ""),
    )

@router.get("/awaiting")
async def email_awaiting():
    return {"threads": _email_api.awaiting_reply()}

@router.post("/replied")
async def email_replied(data: dict):
    return _email_api.mark_replied(data.get("msg_id", ""))
