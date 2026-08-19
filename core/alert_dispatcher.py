"""Delivery for security alerts that matter, off the browser tab.

DEEP already detects well. `alert_correlator` enriches an anomaly with the
MITRE techniques and CVEs that fit it; `global_threat_watch` notices when a
newly-KEV-listed CVE names a tool DEEP knows you actually use. Both publish on
the event bus, both reach the HUD over the WebSocket — and both go nowhere at
all if the HUD isn't open. A console you have to be watching is not an alerting
system; it is a dashboard.

This module is the delivery path. It subscribes to the alert streams, decides
which events are worth interrupting a person for, and hands the survivors to
whichever channels are configured.

The hard part is not sending, it is *not* sending:

* **Severity floor.** Default `high`. An operations console that notifies on
  `info` trains you to ignore it, which is worse than silence.
* **Quiet hours**, borrowed from ``ProactiveCore`` so DEEP has one idea of when
  you're asleep — except that `critical` overrides them. Waking you is the
  entire point of that severity; anything that shouldn't wake you isn't
  critical.
* **Deduplication.** One incident emits the same alert repeatedly. Identical
  alerts inside the cooldown are dropped.
* **Rate limiting** — a minimum gap and a daily cap.
* **Suppression is never silent.** A drop increments a counter that rides along
  on the next delivery ("+4 more suppressed") and shows in ``status()``.
  Alerting you cannot audit is alerting you cannot trust.

**On leaving the device.** DEEP is local-first, and the desktop and log
channels keep it that way. The webhook channel does not: it posts alert
contents — device names, IPs, CVE ids — to a third-party URL. It is therefore
inert unless ``DEEP_ALERT_WEBHOOK`` is set, and nothing enables it implicitly.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SEVERITY_RANK: Dict[str, int] = {
    "info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4,
}


def rank(severity: Any) -> int:
    return SEVERITY_RANK.get(str(severity or "info").strip().lower(), 0)


@dataclass(slots=True)
class Alert:
    """One thing worth telling a person about."""

    id: str
    kind: str
    severity: str
    title: str
    body: str
    source: str
    dedupe_key: str
    url: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    context: Dict[str, Any] = field(default_factory=dict)
    #: How many alerts were dropped by the gates since the last delivery.
    suppressed: int = 0
    #: True when this alert exists because the user just asked for something,
    #: rather than because DEEP noticed something. Quiet hours and rate limits
    #: exist to stop DEEP interrupting a person who did not ask to be
    #: interrupted; applying them to a reply the user is actively waiting for
    #: turns a gate against the person it protects. Solicited alerts therefore
    #: skip those two gates — never the severity floor or deduplication, which
    #: are about the alert's own worth rather than about timing.
    solicited: bool = False
    #: How this alert should be *said*, when a voice channel is delivering it.
    #: Speech is not a shorter title: reading a URL aloud is both unusable and
    #: its own disclosure — a link carrying a session token should not be
    #: announced into a room. Whoever raises the alert supplies this, because
    #: only they know which part is safe and useful to say. Falls back to the
    #: title, which is at least always true.
    speech: str = ""
    #: True when this alert's contents must not leave the machine, whatever
    #: channels are configured. An approval request names the exact thing being
    #: confirmed — for a urlscan submission, a URL that may carry a token or a
    #: session id, which is the very reason it needs confirming. Shipping that
    #: to a third-party webhook before the user has decided (and even if they
    #: then decline) would leak precisely what the gate exists to protect.
    local_only: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "severity": self.severity,
            "title": self.title,
            "body": self.body,
            "source": self.source,
            "url": self.url,
            "timestamp": self.timestamp,
            "context": self.context,
            "suppressed": self.suppressed,
            "speech": self.speech,
            "solicited": self.solicited,
            "local_only": self.local_only,
        }

    def spoken(self) -> str:
        """One sentence a voice channel can read out."""
        return (self.speech or self.title).strip()

    def render(self) -> str:
        """Body as a channel should show it, including any suppression note."""
        text = self.body
        if self.suppressed:
            text += f"\n(+{self.suppressed} more suppressed since the last alert)"
        return text


# ═══════════════════════════════════════════════════════════════════════════
# Channels
# ═══════════════════════════════════════════════════════════════════════════


class Channel:
    """A place an alert can be delivered. Never raises out of ``send``."""

    name = "channel"

    #: True when delivering here sends the alert's contents off this machine.
    #: The dispatcher skips these for ``local_only`` alerts, so a channel must
    #: declare this honestly rather than the dispatcher guessing from its name.
    leaves_device = False

    @property
    def available(self) -> bool:
        return True

    async def send(self, alert: Alert) -> bool:  # pragma: no cover - interface
        raise NotImplementedError

    def status(self) -> Dict[str, Any]:
        return {"name": self.name, "available": self.available}


class LogChannel(Channel):
    """Always on, so an alert is recorded even with nothing else configured."""

    name = "log"

    async def send(self, alert: Alert) -> bool:
        logger.warning(
            "[ALERT %s] %s — %s", alert.severity.upper(), alert.title, alert.render()
        )
        return True


class DesktopChannel(Channel):
    """Native desktop notification via plyer.

    plyer is synchronous and talks to a platform notification daemon, so it
    goes to a worker thread — a blocked D-Bus call must not stall the bus.
    """

    name = "desktop"

    def __init__(self) -> None:
        self._notify = None
        self._reason = ""
        try:
            from plyer import notification

            self._notify = notification
        except Exception as exc:  # noqa: BLE001 - plyer is optional
            self._reason = f"plyer unavailable: {type(exc).__name__}"

    @property
    def available(self) -> bool:
        return self._notify is not None

    #: Notification daemons truncate hard, and an approval's title carries the
    #: decision itself, so the budget is spent on the title rather than on
    #: repeating what the app_name field already says.
    TITLE_BUDGET = 64

    @classmethod
    def headline(cls, alert: Alert) -> str:
        """Notification title: no doubled app name, no cut mid-word."""
        title = alert.title.strip()
        # "DEEP needs your OK: …" under app_name="DEEP" read as "DEEP DEEP".
        prefix = "" if title.upper().startswith("DEEP") else "DEEP "
        text = f"{prefix}[{alert.severity.upper()}] {title}"
        if len(text) <= cls.TITLE_BUDGET:
            return text
        # Back off to the last space so a truncated URL does not end mid-token,
        # which reads as a different address than it is.
        cut = text[: cls.TITLE_BUDGET - 1]
        space = cut.rfind(" ")
        if space > cls.TITLE_BUDGET // 2:
            cut = cut[:space]
        return cut.rstrip(" ,.:;-") + "…"

    async def send(self, alert: Alert) -> bool:
        if self._notify is None:
            return False
        try:
            await asyncio.to_thread(
                self._notify.notify,
                title=self.headline(alert),
                message=alert.render()[:256],
                app_name="DEEP",
                timeout=15,
            )
            return True
        except Exception as exc:  # noqa: BLE001 - headless hosts have no daemon
            self._reason = f"{type(exc).__name__}: {exc}"
            logger.debug("desktop notification failed: %s", self._reason)
            return False

    def status(self) -> Dict[str, Any]:
        return {"name": self.name, "available": self.available, "detail": self._reason}


class WebhookChannel(Channel):
    """POST the alert as JSON to a URL — Slack, Discord, ntfy, anything.

    This is the one channel that sends DEEP's observations off the machine, so
    it exists only when ``DEEP_ALERT_WEBHOOK`` names a destination.
    """

    name = "webhook"
    leaves_device = True

    def __init__(self, url: str, timeout_s: float = 10.0) -> None:
        self._url = url
        self._timeout_s = timeout_s
        self._reason = ""

    @property
    def available(self) -> bool:
        return bool(self._url)

    async def send(self, alert: Alert) -> bool:
        if not self._url:
            return False
        try:
            import aiohttp
        except ImportError:  # pragma: no cover - aiohttp is a hard dependency
            self._reason = "aiohttp not installed"
            return False

        payload = {
            # `text` is what Slack, Discord (via ?wait), and ntfy all read, so
            # one body works everywhere without per-service adapters.
            "text": (
                f"*DEEP [{alert.severity.upper()}]* {alert.title}\n{alert.render()}"
            ),
            "alert": alert.to_dict(),
        }
        try:
            timeout = aiohttp.ClientTimeout(total=self._timeout_s)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self._url, json=payload) as resp:
                    if resp.status >= 400:
                        self._reason = f"HTTP {resp.status}"
                        return False
            self._reason = ""
            return True
        except Exception as exc:  # noqa: BLE001
            self._reason = f"{type(exc).__name__}: {exc}"
            logger.debug("alert webhook failed: %s", self._reason)
            return False

    def status(self) -> Dict[str, Any]:
        # The URL itself is a credential for most services — never echo it.
        return {"name": self.name, "available": self.available,
                "configured": bool(self._url), "detail": self._reason}


class VoiceChannel(Channel):
    """Say the alert out loud, by publishing ``tts_speak`` on the event bus.

    DEEP has no server-side synthesiser — the voice package was removed — so
    this states an intent and the HUD performs it (``interface/web/src/core/
    speech.ts``). That split is deliberate: speech belongs where the speakers
    are, and a headless DEEP on a server should not try to talk.

    It follows that this channel reaches only a machine with the HUD open. It
    is not a replacement for the desktop notification, which survives a closed
    tab; it is for someone sitting at the machine who is not looking at it.

    ``send`` reports success when the intent was published, which is the only
    thing this side can actually observe. Whether a browser was listening, and
    whether the user has muted it, are not knowable from here — so the delivery
    record means "DEEP asked for this to be said", not "the user heard it".
    """

    name = "voice"

    def __init__(self, event_bus: Any = None) -> None:
        self.bus = event_bus

    @property
    def available(self) -> bool:
        return self.bus is not None

    async def send(self, alert: Alert) -> bool:
        if self.bus is None:
            return False
        try:
            await self.bus.publish("tts_speak", {
                "text": alert.spoken(),
                # Critical interrupts whatever is being said; everything else
                # waits its turn rather than talking over it.
                "priority": "urgent" if rank(alert.severity) >= rank("critical") else "normal",
                "source": "alert_dispatcher",
                "alert_id": alert.id,
            })
            return True
        except Exception as exc:  # noqa: BLE001 - a bus failure is not fatal
            logger.debug("voice channel publish failed: %s", exc)
            return False


# ═══════════════════════════════════════════════════════════════════════════
# The dispatcher
# ═══════════════════════════════════════════════════════════════════════════


class AlertDispatcher:
    """Turns alert events into notifications a person actually receives."""

    #: Events carrying something worth delivering, and how to read them.
    SUBSCRIBED = (
        "security_alert_correlated", "world_threat_match", "security_alert",
        # Not a threat — a request. DEEP parked an action it will not take
        # without a yes, and that yes has a 15-minute life. The HUD badge only
        # helps someone looking at the HUD; this is the path for someone who
        # asked DEEP to do something and then switched windows.
        "approval_pending",
    )

    MIN_GAP_SECONDS = 120
    MAX_PER_DAY = 30
    DEDUPE_COOLDOWN_SECONDS = 6 * 3600
    QUIET_START_HOUR = 23
    QUIET_END_HOUR = 7

    def __init__(
        self,
        event_bus: Any = None,
        *,
        channels: Optional[List[Channel]] = None,
        min_severity: Optional[str] = None,
        data_dir: Optional[Path] = None,
    ) -> None:
        self.bus = event_bus
        self.min_severity = (
            min_severity or os.environ.get("DEEP_ALERT_MIN_SEVERITY") or "high"
        ).strip().lower()
        self.channels: List[Channel] = (
            channels if channels is not None else _default_channels(event_bus)
        )

        self.data_dir = Path(data_dir) if data_dir else (
            Path(__file__).parent.parent / "data" / "alerts"
        )
        self._state_file = self.data_dir / "dispatcher_state.json"

        self._seen: Dict[str, float] = {}      # dedupe key -> last delivery epoch
        self._last_delivery: float = 0.0
        self._delivered_today = 0
        self._today: Optional[str] = None
        self._suppressed = 0
        self._counts: Dict[str, int] = {
            "received": 0, "delivered": 0,
            "below_floor": 0, "duplicate": 0, "rate_limited": 0, "quiet_hours": 0,
        }
        self._recent: List[Dict[str, Any]] = []
        self._started = False
        self._load()

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._started or self.bus is None:
            return
        self._started = True
        for event in self.SUBSCRIBED:
            self.bus.subscribe(event, self._on_event)
        logger.info(
            "AlertDispatcher started (floor=%s, channels=%s)",
            self.min_severity,
            ",".join(c.name for c in self.channels if c.available) or "none",
        )

    async def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        for event in self.SUBSCRIBED:
            self.bus.unsubscribe(event, self._on_event)
        self._save()

    # ── ingest ───────────────────────────────────────────────────────────────

    async def _on_event(self, event_name: str, payload: Dict[str, Any]) -> None:
        alert = self.normalise(event_name, payload or {})
        if alert is not None:
            await self.consider(alert)

    @staticmethod
    def normalise(event_name: str, payload: Dict[str, Any]) -> Optional[Alert]:
        """Map one bus event onto an Alert, or None if it carries nothing."""
        if event_name == "approval_pending":
            label = str(payload.get("label") or "").strip()
            action_id = str(payload.get("id") or "").strip()
            if not label or not action_id:
                return None
            tool = str(payload.get("tool") or "an action")
            detail = str(payload.get("detail") or "").strip()
            return Alert(
                id=f"alert_approval_{action_id}",
                kind="approval_request",
                # High rather than critical. It needs an answer inside fifteen
                # minutes, which is what separates it from an FYI — but it is
                # a question, and a question does not get to override the
                # judgement that critical is reserved for.
                severity="high",
                title=f"DEEP needs your OK: {label}"[:96],
                body="\n".join(filter(None, [
                    label,
                    detail,
                    "Approve or reject it in DEEP's Approvals panel. "
                    "It expires in 15 minutes, and nothing runs until you decide.",
                ])),
                source="approvals",
                # Keyed on what is being confirmed, not on the action id, which
                # is fresh every time. A model retrying the same submission
                # produces one notification, not five — while a different URL
                # produces a different label and rightly notifies again.
                dedupe_key=f"approval:{tool}:{label.lower()}",
                # Supplied by whoever parked the action; see
                # pending_actions.enqueue. The fallback is the title, which
                # names the URL — fine on a screen, wrong in a room, which is
                # exactly why the caller is asked to phrase this.
                speech=str(payload.get("speech") or "").strip()
                or f"DEEP needs your approval before it can continue. "
                   f"Check the approvals panel.",
                # The queue only fills when a tool runs, and DEEP's tools run
                # in response to a user turn. Revisit this if an autonomous
                # path ever enqueues an action nobody asked for.
                solicited=True,
                # The label names the exact thing awaiting confirmation — for a
                # urlscan submission, a URL that may carry a token. See
                # Alert.local_only.
                local_only=True,
                context={"action_id": action_id, "tool": tool},
            )

        if event_name == "world_threat_match":
            cve = str(payload.get("cve_id") or "").strip()
            entity = str(payload.get("matched_entity") or "").strip()
            if not cve:
                return None
            return Alert(
                id=f"alert_kev_{cve}",
                kind="stack_exposure",
                # A KEV listing means confirmed in-the-wild exploitation, and
                # this one names something DEEP knows is in your stack. That is
                # high by construction — the feed publishes no severity field.
                severity="high",
                title=f"{cve} affects {entity or 'your stack'}",
                body=(
                    f"{payload.get('source', 'Threat feed')}: "
                    f"{payload.get('title', cve)}"
                    + (f"\nMatched against: {entity}" if entity else "")
                ),
                source=str(payload.get("source") or "global_threat_watch"),
                dedupe_key=f"kev:{cve}:{entity.lower()}",
                url=str(payload.get("url") or ""),
                context={"cve_id": cve, "matched_entity": entity},
            )

        severity = str(payload.get("severity") or "info").lower()
        summary = (
            payload.get("summary")
            or payload.get("title")
            or payload.get("description")
            or ""
        ).strip()
        if not summary:
            return None

        if event_name == "security_alert_correlated":
            techniques = payload.get("techniques") or []
            cves = payload.get("related_cves") or []
            detail = []
            if techniques:
                detail.append("ATT&CK: " + ", ".join(str(t) for t in techniques[:4]))
            if cves:
                detail.append("CVEs: " + ", ".join(str(c) for c in cves[:4]))
            return Alert(
                id=str(payload.get("id") or f"alert_corr_{int(time.time() * 1000)}"),
                kind=str(payload.get("kind") or "threat"),
                severity=severity,
                title=summary[:96],
                body="\n".join([summary] + detail),
                source=str(payload.get("source_event") or "alert_correlator"),
                dedupe_key=f"corr:{payload.get('kind', '')}:{summary.lower()}",
                context={"techniques": techniques, "related_cves": cves},
            )

        # security_alert — raw device-level events from the monitors.
        device = payload.get("device_ip") or payload.get("device_mac") or ""
        return Alert(
            id=str(payload.get("id") or f"alert_raw_{int(time.time() * 1000)}"),
            kind=str(
                payload.get("event_type") or payload.get("type") or "security_event"
            ),
            severity=severity,
            title=summary[:96],
            body=str(payload.get("description") or summary),
            source="network_monitor",
            dedupe_key=(
                f"raw:{payload.get('event_type', '')}:{device}:{summary.lower()}"
            ),
            context={"device": device} if device else {},
        )

    # ── the gates ────────────────────────────────────────────────────────────

    async def consider(self, alert: Alert) -> bool:
        """Run one alert through the gates; deliver it if it survives."""
        self._roll_day()
        self._counts["received"] += 1
        now = time.time()

        reason = self._blocked_because(alert, now)
        if reason:
            self._counts[reason] += 1
            self._suppressed += 1
            logger.debug("alert suppressed (%s): %s", reason, alert.title)
            return False

        alert.suppressed = self._suppressed
        await self._deliver(alert, now)
        return True

    def _blocked_because(self, alert: Alert, now: float) -> str:
        """Name of the gate that stopped this alert, or "" if it passes."""
        if rank(alert.severity) < rank(self.min_severity):
            return "below_floor"

        last = self._seen.get(alert.dedupe_key)
        if last is not None and now - last < self.DEDUPE_COOLDOWN_SECONDS:
            return "duplicate"

        # Critical ignores quiet hours and the daily cap. Anything that should
        # not wake you up does not deserve that label.
        if rank(alert.severity) >= rank("critical"):
            return ""

        # So does a solicited alert, for the opposite reason: the remaining
        # gates all answer "is DEEP interrupting too much?", and an alert the
        # user's own request produced is not an interruption. Holding one back
        # at 23:01 because it is technically quiet hours would strand a request
        # the user is sitting there waiting on.
        if alert.solicited:
            return ""

        if self._in_quiet_hours():
            return "quiet_hours"
        if self._delivered_today >= self.MAX_PER_DAY:
            return "rate_limited"
        if now - self._last_delivery < self.MIN_GAP_SECONDS:
            return "rate_limited"
        return ""

    def _in_quiet_hours(self) -> bool:
        hour = datetime.now().hour
        if self.QUIET_START_HOUR > self.QUIET_END_HOUR:   # window crosses midnight
            return hour >= self.QUIET_START_HOUR or hour < self.QUIET_END_HOUR
        return self.QUIET_START_HOUR <= hour < self.QUIET_END_HOUR

    # ── delivery ─────────────────────────────────────────────────────────────

    async def _deliver(self, alert: Alert, now: float) -> None:
        self._seen[alert.dedupe_key] = now
        self._seen = {
            k: v for k, v in self._seen.items()
            if now - v < self.DEDUPE_COOLDOWN_SECONDS
        }
        self._last_delivery = now
        self._delivered_today += 1
        self._suppressed = 0
        self._counts["delivered"] += 1

        # A local-only alert never reaches a channel that would carry it off
        # the machine, regardless of what is configured.
        targets = [
            c for c in self.channels
            if not (alert.local_only and c.leaves_device)
        ]
        withheld = [c.name for c in self.channels if c not in targets]

        results = await asyncio.gather(
            *(self._send_one(channel, alert) for channel in targets),
            return_exceptions=False,
        )
        delivered_to = [c.name for c, ok in zip(targets, results) if ok]

        record = {**alert.to_dict(), "channels": delivered_to}
        if withheld:
            # Recorded, not silent: a channel the user configured did not fire,
            # and they should be able to see that it was withheld by policy
            # rather than broken.
            record["withheld_from"] = withheld
        self._recent.append(record)
        self._recent = self._recent[-50:]
        self._save()

        if self.bus is not None:
            try:
                await self.bus.publish("alert_delivered", record)
            except Exception as exc:  # noqa: BLE001
                logger.debug("alert_delivered publish failed: %s", exc)

    @staticmethod
    async def _send_one(channel: Channel, alert: Alert) -> bool:
        """One failing channel must not stop the others."""
        try:
            return await channel.send(alert)
        except Exception as exc:  # noqa: BLE001
            logger.warning("alert channel %s failed: %s", channel.name, exc)
            return False

    # ── state ────────────────────────────────────────────────────────────────

    def _roll_day(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        if self._today != today:
            self._today = today
            self._delivered_today = 0

    def _load(self) -> None:
        if not self._state_file.exists():
            return
        try:
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
            self._seen = {k: float(v) for k, v in (data.get("seen") or {}).items()}
            self._recent = (data.get("recent") or [])[-50:]
            self._today = data.get("today")
            self._delivered_today = int(data.get("delivered_today", 0))
            self._suppressed = int(data.get("suppressed", 0))
            self._counts.update(data.get("counts") or {})
        except Exception as exc:  # noqa: BLE001
            logger.warning("alert dispatcher state unreadable: %s", exc)

    def _save(self) -> None:
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(json.dumps({
                "seen": self._seen,
                "recent": self._recent[-50:],
                "today": self._today,
                "delivered_today": self._delivered_today,
                "suppressed": self._suppressed,
                "counts": self._counts,
                "saved_at": datetime.now().isoformat(),
            }, indent=2), encoding="utf-8")
        except Exception:  # noqa: BLE001 - a read-only disk must not break alerting
            pass

    # ── introspection ────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        return {
            "started": self._started,
            "min_severity": self.min_severity,
            "quiet_hours": (
                f"{self.QUIET_START_HOUR:02d}:00-{self.QUIET_END_HOUR:02d}:00"
            ),
            "in_quiet_hours": self._in_quiet_hours(),
            "delivered_today": self._delivered_today,
            "max_per_day": self.MAX_PER_DAY,
            "suppressed_since_last": self._suppressed,
            "counts": dict(self._counts),
            "channels": [c.status() for c in self.channels],
        }

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(reversed(self._recent[-limit:]))


def _default_channels(event_bus: Any = None) -> List[Channel]:
    """Log always; desktop when plyer works; voice with a bus; webhook when set."""
    channels: List[Channel] = [LogChannel()]
    if os.environ.get("DEEP_ALERT_DESKTOP", "1").strip().lower() not in {
        "0", "false", "off", "no",
    }:
        desktop = DesktopChannel()
        if desktop.available:
            channels.append(desktop)
    # On by default: an alert that survived the floor, the dedupe and the rate
    # limit is, by construction, one of the few things a day worth saying out
    # loud. DEEP_ALERT_VOICE=0 turns it off server-side, and the HUD has its own
    # mute — one switch at each end, because whoever is annoyed by it may not be
    # whoever can edit the environment.
    if event_bus is not None and os.environ.get("DEEP_ALERT_VOICE", "1").strip().lower() not in {
        "0", "false", "off", "no",
    }:
        channels.append(VoiceChannel(event_bus))

    webhook_url = (os.environ.get("DEEP_ALERT_WEBHOOK") or "").strip()
    if webhook_url:
        channels.append(WebhookChannel(webhook_url))
    return channels
