"""
core/integrations/email.py — Email Intelligence for DEEP

Unified email access: IMAP/SMTP (universal) + Gmail API (optional).
Features:
  - inbox triage (unread count, sender importance, subject clustering)
  - draft composition (via LLM or template)
  - follow-up tracking (flag emails awaiting reply)
  - smart search (sender, subject, date range, body keywords)
  - send email (SMTP)

Graceful degradation: without credentials, returns "Email not configured"
with instructions. All secrets live in .env (GMAIL_API_KEY, SMTP_HOST, etc.)
"""

from __future__ import annotations

import email
import imaplib
import logging
import os
import re
import smtplib
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from email.header import decode_header
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_DB_PATH = _DATA_DIR / "email.db"

# ── helpers ────────────────────────────────────────────────────────────────

def _decode_subject(subject: str) -> str:
    parts = decode_header(subject)
    out = []
    for part, charset in parts:
        if isinstance(part, bytes):
            out.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            out.append(part)
    return "".join(out)


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(key, default)


# ── core engine ─────────────────────────────────────────────────────────────

class EmailIntegration:
    """Email brain for DEEP. IMAP-first; Gmail API optional enhancement."""

    def __init__(self, db_path: Optional[str] = None):
        self.db = db_path or str(_DB_PATH)
        self._init_schema()

    def _init_schema(self) -> None:
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tracked_threads (
                    msg_id TEXT PRIMARY KEY,
                    sender TEXT,
                    subject TEXT,
                    received_at TEXT,
                    needs_reply INTEGER DEFAULT 0,
                    priority INTEGER DEFAULT 0,
                    category TEXT DEFAULT 'general',
                    notes TEXT
                );
                CREATE TABLE IF NOT EXISTS drafts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    to_addr TEXT,
                    subject TEXT,
                    body TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    sent INTEGER DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_tracked_sender ON tracked_threads(sender);
            """)

    # ── IMAP helpers ───────────────────────────────────────────────────────────
    def _imap(self):
        host = _env("IMAP_HOST", "imap.gmail.com")
        port = int(_env("IMAP_PORT", "993"))
        user = _env("EMAIL_USER")
        pwd = _env("EMAIL_PASS")
        if not user or not pwd:
            return None
        try:
            mail = imaplib.IMAP4_SSL(host, port)
            mail.login(user, pwd)
            return mail
        except Exception as e:
            logger.warning(f"[Email] IMAP login failed: {e}")
            return None

    # ── inbox triage ───────────────────────────────────────────────────────────
    def inbox_summary(self, folder: str = "INBOX", limit: int = 20) -> Dict[str, Any]:
        mail = self._imap()
        if not mail:
            return {"ok": False, "verbal": "Email not configured. Set EMAIL_USER and EMAIL_PASS in .env."}

        try:
            mail.select(folder)
            _, data = mail.search(None, "UNSEEN")
            unread_ids = data[0].split() if data and data[0] else []
            unread_count = len(unread_ids)

            # fetch recent N messages
            _, data = mail.search(None, "ALL")
            all_ids = data[0].split() if data and data[0] else []
            recent_ids = all_ids[-limit:] if len(all_ids) > limit else all_ids

            messages = []
            for msg_id in recent_ids:
                _, msg_data = mail.fetch(msg_id, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                subject = _decode_subject(msg.get("Subject", ""))
                sender = msg.get("From", "")
                date = msg.get("Date", "")
                messages.append({
                    "id": msg_id.decode(),
                    "subject": subject,
                    "sender": sender,
                    "date": date,
                    "unread": msg_id in unread_ids,
                })
            mail.close()
            mail.logout()

            return {
                "ok": True,
                "unread_count": unread_count,
                "recent": list(reversed(messages)),
                "verbal": f"{unread_count} unread. {len(messages)} recent messages in {folder}.",
            }
        except Exception as e:
            return {"ok": False, "verbal": f"Inbox error: {e}"}

    # ── smart search ─────────────────────────────────────────────────────────
    def search(self, query: str, folder: str = "INBOX", limit: int = 10) -> Dict[str, Any]:
        mail = self._imap()
        if not mail:
            return {"ok": False, "verbal": "Email not configured. Set EMAIL_USER and EMAIL_PASS."}
        try:
            mail.select(folder)
            # IMAP SEARCH supports OR, FROM, SUBJECT, BODY, SINCE etc.
            # For simplicity: search SUBJECT + FROM + BODY (OR combination not always supported)
            criteria = f'(OR OR FROM "{query}" SUBJECT "{query}" BODY "{query}")'
            _, data = mail.search(None, "UTF-8", criteria.encode("utf-8"))
            ids = data[0].split()[-limit:] if data and data[0] else []
            messages = []
            for msg_id in ids:
                _, msg_data = mail.fetch(msg_id, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                messages.append({
                    "id": msg_id.decode(),
                    "subject": _decode_subject(msg.get("Subject", "")),
                    "sender": msg.get("From", ""),
                    "date": msg.get("Date", ""),
                })
            mail.close(); mail.logout()
            return {"ok": True, "results": list(reversed(messages)), "count": len(messages), "verbal": f"Found {len(messages)} emails matching '{query}'."}
        except Exception as e:
            return {"ok": False, "verbal": f"Search error: {e}"}

    # ── send email ─────────────────────────────────────────────────────────────
    def send(self, to: str, subject: str, body: str, cc: Optional[str] = None) -> Dict[str, Any]:
        smtp_host = _env("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(_env("SMTP_PORT", "587"))
        user = _env("EMAIL_USER")
        pwd = _env("EMAIL_PASS")
        if not user or not pwd:
            return {"ok": False, "verbal": "Email not configured. Set EMAIL_USER and EMAIL_PASS."}

        try:
            msg = EmailMessage()
            msg["From"] = user
            msg["To"] = to
            msg["Subject"] = subject
            if cc:
                msg["Cc"] = cc
            msg.set_content(body)

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(user, pwd)
                server.send_message(msg)
            return {"ok": True, "verbal": f"Email sent to {to}: {subject}."}
        except Exception as e:
            return {"ok": False, "verbal": f"Send failed: {e}"}

    # ── draft / follow-up tracking ───────────────────────────────────────────
    def track_thread(self, msg_id: str, sender: str, subject: str, needs_reply: bool = True, priority: int = 0, notes: str = "") -> Dict[str, Any]:
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute(
                "INSERT OR REPLACE INTO tracked_threads (msg_id, sender, subject, received_at, needs_reply, priority, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (msg_id, sender, subject, datetime.now().isoformat(), int(needs_reply), priority, notes),
            )
        return {"verbal": f"Tracking thread from {sender}: '{subject}' (needs_reply={needs_reply})."}

    def awaiting_reply(self) -> List[Dict[str, Any]]:
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM tracked_threads WHERE needs_reply = 1 ORDER BY received_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_replied(self, msg_id: str) -> Dict[str, Any]:
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("UPDATE tracked_threads SET needs_reply = 0 WHERE msg_id = ?", (msg_id,))
        return {"verbal": f"Marked {msg_id} as replied."}

    # ── high-level verbal ────────────────────────────────────────────────────
    def verbal_status(self) -> str:
        s = self.inbox_summary(limit=5)
        if not s.get("ok"):
            return s["verbal"]
        awaiting = self.awaiting_reply()
        parts = [f"Inbox: {s['unread_count']} unread."]
        if awaiting:
            parts.append(f"{len(awaiting)} threads awaiting your reply.")
        if s.get("recent"):
            latest = s["recent"][0]
            parts.append(f"Latest: '{latest['subject']}' from {latest['sender'][:40]}.")
        return " ".join(parts)


# ── singleton ──────────────────────────────────────────────────────────────
_email = EmailIntegration()


def inbox_summary(**kwargs):
    return _email.inbox_summary(**kwargs)


def search_emails(query: str, **kwargs):
    return _email.search(query, **kwargs)


def send_email(to: str, subject: str, body: str, **kwargs):
    return _email.send(to, subject, body, **kwargs)


def track_thread(**kwargs):
    return _email.track_thread(**kwargs)


def awaiting_reply():
    return _email.awaiting_reply()


def mark_replied(msg_id: str):
    return _email.mark_replied(msg_id)


def verbal_status():
    return _email.verbal_status()


if __name__ == "__main__":
    e = EmailIntegration()
    print(e.verbal_status())
    print(e.track_thread("test-123", "boss@corp.com", "Q3 Report", priority=1, notes="Need figures by Friday"))
    print(e.awaiting_reply())
