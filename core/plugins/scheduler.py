"""
core/plugins/scheduler.py

Deep Personal Assistant Plugin — Calendar, Reminders & Tasks.

This is the "daily life" core that makes Deep a real assistant:
  - Tasks:     a persistent todo list (create / list / complete / delete).
  - Reminders: time-based nudges that fire via the EventBus (and optionally
               Twilio SMS) when they come due.
  - Calendar:  Google Calendar read/create (optional — gracefully degrades
               if google-api-python-client + credentials aren't present).

Everything persists in a local SQLite DB (data/scheduler.db) so nothing is
lost across restarts. External services (Google, Twilio) are optional and the
plugin runs fully without them.

Tools exposed to the brain (callable via [TOOL:...] markers):
  - create_task, list_tasks, complete_task
  - set_reminder, list_reminders
  - calendar_upcoming, calendar_create_event

Endpoints (for the web UI):
  GET  /api/scheduler/tasks
  POST /api/scheduler/task            {title, due?, priority?}
  POST /api/scheduler/task/complete   {id}
  GET  /api/scheduler/reminders
  POST /api/scheduler/reminder        {text, at}   (at = ISO 8601 datetime)
  GET  /api/scheduler/calendar/upcoming
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

from core.plugins.base import DeepPlugin

logger = logging.getLogger(__name__)

# ─── Optional integrations (graceful degradation) ──────────────────────────
_GOOGLE_AVAILABLE = False
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request as GoogleRequest
    from googleapiclient.discovery import build as google_build

    _GOOGLE_AVAILABLE = True
except ImportError:
    logger.info("[Scheduler] Google API libs not installed — calendar disabled.")

_TWILIO_AVAILABLE = False
try:
    from twilio.rest import Client as TwilioClient

    _TWILIO_AVAILABLE = True
except ImportError:
    logger.info("[Scheduler] twilio not installed — SMS reminders disabled.")


GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str) -> Optional[datetime]:
    """Parse an ISO 8601 string into a tz-aware UTC datetime. Returns None on failure."""
    if not value:
        return None
    try:
        # Accept trailing 'Z'
        v = value.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


class SchedulerPlugin(DeepPlugin):
    """Calendar + reminders + tasks — the personal-assistant core of Deep."""

    name = "scheduler"
    version = "1.0.0"
    description = "Calendar, reminders and task management for Deep."
    author = "Deep"

    REMINDER_POLL_SECONDS = 30.0

    def __init__(self, plugin_manager: Any):
        super().__init__(plugin_manager)
        base = Path(__file__).resolve().parents[2]  # DEEP/
        self.db_path = str(base / "data" / "scheduler.db")
        self._google_dir = base / "data" / "google"
        self._creds_path = self._google_dir / "credentials.json"
        self._token_path = self._google_dir / "token.json"
        self._calendar_service = None

        # Twilio (optional) — read from env
        self._twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self._twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        self._twilio_from = os.getenv("TWILIO_FROM")
        self._user_phone = os.getenv("USER_PHONE")

    # ─── Lifecycle ──────────────────────────────────────────────────────────

    async def on_init(self):
        await self._ensure_db()

        # Tools for the brain
        self.register_tool("create_task", self.tool_create_task,
                           "Create a task. Params: title|due(optional ISO)|priority(low/med/high)")
        self.register_tool("list_tasks", self.tool_list_tasks,
                           "List open tasks. No params.")
        self.register_tool("complete_task", self.tool_complete_task,
                           "Mark a task done. Params: task id (int)")
        self.register_tool("set_reminder", self.tool_set_reminder,
                           "Set a reminder. Params: text|at(ISO datetime)")
        self.register_tool("list_reminders", self.tool_list_reminders,
                           "List pending reminders. No params.")
        self.register_tool("calendar_upcoming", self.tool_calendar_upcoming,
                           "List upcoming Google Calendar events. Params: count(optional int)")
        self.register_tool("calendar_create_event", self.tool_calendar_create_event,
                           "Create a calendar event. Params: title|start(ISO)|end(ISO)")

        # HTTP endpoints
        self.register_endpoint("GET", "/api/scheduler/tasks", self.api_list_tasks)
        self.register_endpoint("POST", "/api/scheduler/task", self.api_create_task)
        self.register_endpoint("POST", "/api/scheduler/task/complete", self.api_complete_task)
        self.register_endpoint("GET", "/api/scheduler/reminders", self.api_list_reminders)
        self.register_endpoint("POST", "/api/scheduler/reminder", self.api_create_reminder)
        self.register_endpoint("GET", "/api/scheduler/calendar/upcoming", self.api_calendar_upcoming)

        # UI panel card
        self.register_panel_card("Scheduler", self._panel_html())

    async def on_start(self):
        self.register_background_task("reminder_loop", self._reminder_loop())

    async def on_stop(self):
        pass

    # ─── Database ─────────────────────────────────────────────────────────────

    async def _ensure_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    due TEXT,
                    priority TEXT DEFAULT 'med',
                    done INTEGER DEFAULT 0,
                    created TEXT NOT NULL
                )"""
            )
            await db.execute(
                """CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    fire_at TEXT NOT NULL,
                    fired INTEGER DEFAULT 0,
                    created TEXT NOT NULL
                )"""
            )
            await db.commit()

    # ─── Tasks ──────────────────────────────────────────────────────────────

    async def add_task(self, title: str, due: Optional[str] = None,
                       priority: str = "med") -> Dict[str, Any]:
        title = (title or "").strip()
        if not title:
            return {"error": "title is required"}
        if priority not in ("low", "med", "high"):
            priority = "med"
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "INSERT INTO tasks (title, due, priority, created) VALUES (?,?,?,?)",
                (title, due, priority, _now_utc().isoformat()),
            )
            await db.commit()
            task_id = cur.lastrowid
        self.pm.emit(self.name, "task_created", {"id": task_id, "title": title})
        return {"id": task_id, "title": title, "due": due, "priority": priority, "done": False}

    async def get_open_tasks(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM tasks WHERE done=0 ORDER BY "
                "CASE priority WHEN 'high' THEN 0 WHEN 'med' THEN 1 ELSE 2 END, "
                "COALESCE(due, '9999') ASC"
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def complete_task(self, task_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("UPDATE tasks SET done=1 WHERE id=?", (task_id,))
            await db.commit()
            if cur.rowcount == 0:
                return {"error": f"no task with id {task_id}"}
        self.pm.emit(self.name, "task_completed", {"id": task_id})
        return {"id": task_id, "done": True}

    # ─── Reminders ────────────────────────────────────────────────────────────

    async def add_reminder(self, text: str, at: str) -> Dict[str, Any]:
        text = (text or "").strip()
        fire_at = _parse_dt(at)
        if not text:
            return {"error": "text is required"}
        if fire_at is None:
            return {"error": f"could not parse datetime: {at!r} (use ISO 8601)"}
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "INSERT INTO reminders (text, fire_at, created) VALUES (?,?,?)",
                (text, fire_at.isoformat(), _now_utc().isoformat()),
            )
            await db.commit()
            rid = cur.lastrowid
        return {"id": rid, "text": text, "fire_at": fire_at.isoformat()}

    async def get_pending_reminders(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM reminders WHERE fired=0 ORDER BY fire_at ASC"
            )
            return [dict(r) for r in await cur.fetchall()]

    async def _reminder_loop(self):
        """Background: fire any reminders whose time has arrived."""
        while True:
            try:
                await self._fire_due_reminders()
            except Exception as e:  # never let the loop die
                logger.error(f"[Scheduler] reminder loop error: {e}")
            await asyncio.sleep(self.REMINDER_POLL_SECONDS)

    async def _fire_due_reminders(self):
        now = _now_utc()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM reminders WHERE fired=0")
            due = [
                dict(r) for r in await cur.fetchall()
                if (_parse_dt(r["fire_at"]) or now) <= now
            ]
            for rem in due:
                await db.execute("UPDATE reminders SET fired=1 WHERE id=?", (rem["id"],))
            if due:
                await db.commit()

        for rem in due:
            logger.info(f"[Scheduler] Reminder due: {rem['text']}")
            self.pm.emit(self.name, "reminder_fired",
                         {"id": rem["id"], "text": rem["text"]})
            self._send_sms(f"Deep reminder: {rem['text']}")

    # ─── Twilio SMS (optional) ─────────────────────────────────────────────────

    def _twilio_ready(self) -> bool:
        return bool(_TWILIO_AVAILABLE and self._twilio_sid and self._twilio_token
                    and self._twilio_from and self._user_phone)

    def _send_sms(self, body: str):
        if not self._twilio_ready():
            return
        try:
            client = TwilioClient(self._twilio_sid, self._twilio_token)
            client.messages.create(body=body, from_=self._twilio_from, to=self._user_phone)
            logger.info("[Scheduler] SMS reminder sent.")
        except Exception as e:
            logger.error(f"[Scheduler] Twilio send failed: {e}")

    # ─── Google Calendar (optional) ─────────────────────────────────────────────

    def _calendar_ready(self) -> bool:
        return bool(_GOOGLE_AVAILABLE and self._creds_path.exists())

    def _get_calendar_service(self):
        """Lazily build (and cache) an authorized Calendar service. Returns None if unavailable."""
        if self._calendar_service is not None:
            return self._calendar_service
        if not self._calendar_ready():
            return None
        try:
            creds = None
            if self._token_path.exists():
                creds = Credentials.from_authorized_user_file(str(self._token_path), GOOGLE_SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(GoogleRequest())
                else:
                    # First-run consent flow (opens a browser on the host machine).
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self._creds_path), GOOGLE_SCOPES)
                    creds = flow.run_local_server(port=0)
                self._token_path.write_text(creds.to_json(), encoding="utf-8")
            self._calendar_service = google_build("calendar", "v3", credentials=creds)
            return self._calendar_service
        except Exception as e:
            logger.error(f"[Scheduler] Google Calendar auth failed: {e}")
            return None

    async def calendar_upcoming(self, count: int = 5) -> Dict[str, Any]:
        svc = await asyncio.to_thread(self._get_calendar_service)
        if svc is None:
            return {"available": False,
                    "hint": "Add data/google/credentials.json and install "
                            "google-api-python-client to enable calendar."}

        def _fetch():
            now = _now_utc().isoformat()
            res = svc.events().list(
                calendarId="primary", timeMin=now, maxResults=count,
                singleEvents=True, orderBy="startTime").execute()
            events = []
            for ev in res.get("items", []):
                start = ev.get("start", {})
                events.append({
                    "summary": ev.get("summary", "(no title)"),
                    "start": start.get("dateTime", start.get("date")),
                })
            return events

        try:
            events = await asyncio.to_thread(_fetch)
            return {"available": True, "events": events}
        except Exception as e:
            logger.error(f"[Scheduler] calendar_upcoming failed: {e}")
            return {"available": False, "error": str(e)}

    async def calendar_create_event(self, title: str, start: str,
                                    end: Optional[str] = None) -> Dict[str, Any]:
        svc = await asyncio.to_thread(self._get_calendar_service)
        if svc is None:
            return {"available": False, "hint": "Calendar not configured."}
        start_dt = _parse_dt(start)
        if start_dt is None:
            return {"error": f"bad start datetime: {start!r}"}
        end_dt = _parse_dt(end) if end else None
        if end_dt is None:
            from datetime import timedelta
            end_dt = start_dt + timedelta(hours=1)

        def _create():
            body = {
                "summary": title,
                "start": {"dateTime": start_dt.isoformat()},
                "end": {"dateTime": end_dt.isoformat()},
            }
            return svc.events().insert(calendarId="primary", body=body).execute()

        try:
            ev = await asyncio.to_thread(_create)
            self.pm.emit(self.name, "event_created", {"title": title})
            return {"available": True, "id": ev.get("id"), "link": ev.get("htmlLink")}
        except Exception as e:
            logger.error(f"[Scheduler] calendar_create_event failed: {e}")
            return {"available": False, "error": str(e)}

    # ─── Tool adapters (string params from the brain) ──────────────────────────

    def _split(self, params: str, n: int) -> List[Optional[str]]:
        parts = [p.strip() for p in (params or "").split("|")]
        parts += [None] * (n - len(parts))
        return parts[:n]

    async def tool_create_task(self, params: str = "") -> Dict[str, Any]:
        title, due, priority = self._split(params, 3)
        return await self.add_task(title or "", due, priority or "med")

    async def tool_list_tasks(self, params: str = "") -> Dict[str, Any]:
        return {"tasks": await self.get_open_tasks()}

    async def tool_complete_task(self, params: str = "") -> Dict[str, Any]:
        try:
            tid = int((params or "").strip())
        except ValueError:
            return {"error": "task id must be an integer"}
        return await self.complete_task(tid)

    async def tool_set_reminder(self, params: str = "") -> Dict[str, Any]:
        text, at = self._split(params, 2)
        return await self.add_reminder(text or "", at or "")

    async def tool_list_reminders(self, params: str = "") -> Dict[str, Any]:
        return {"reminders": await self.get_pending_reminders()}

    async def tool_calendar_upcoming(self, params: str = "") -> Dict[str, Any]:
        try:
            count = int((params or "").strip()) if params and params.strip() else 5
        except ValueError:
            count = 5
        return await self.calendar_upcoming(count)

    async def tool_calendar_create_event(self, params: str = "") -> Dict[str, Any]:
        title, start, end = self._split(params, 3)
        return await self.calendar_create_event(title or "", start or "", end)

    # ─── HTTP endpoints ─────────────────────────────────────────────────────────

    async def api_list_tasks(self):
        return {"tasks": await self.get_open_tasks()}

    async def api_create_task(self, request: "Request"):  # type: ignore[name-defined]
        body = await request.json()
        return await self.add_task(
            body.get("title", ""), body.get("due"), body.get("priority", "med"))

    async def api_complete_task(self, request: "Request"):  # type: ignore[name-defined]
        body = await request.json()
        return await self.complete_task(int(body.get("id")))

    async def api_list_reminders(self):
        return {"reminders": await self.get_pending_reminders()}

    async def api_create_reminder(self, request: "Request"):  # type: ignore[name-defined]
        body = await request.json()
        return await self.add_reminder(body.get("text", ""), body.get("at", ""))

    async def api_calendar_upcoming(self):
        return await self.calendar_upcoming()

    # ─── UI ──────────────────────────────────────────────────────────────────────

    def _panel_html(self) -> str:
        return (
            '<div class="scheduler-card">'
            '<h3>Scheduler</h3>'
            '<p>Tasks, reminders &amp; calendar. Ask Deep to "add a task" or '
            '"remind me at 6pm".</p>'
            '<ul id="scheduler-task-list"></ul>'
            '</div>'
        )


# FastAPI's Request is resolved at call time via the route signature; import here
# so type hints in handlers don't break discovery when fastapi is present.
try:
    from fastapi import Request  # noqa: F401
except ImportError:  # pragma: no cover
    Request = Any  # type: ignore
