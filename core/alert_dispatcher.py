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
        }

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

    async def send(self, alert: Alert) -> bool:
        if self._notify is None:
            return False
        try:
            await asyncio.to_thread(
                self._notify.notify,
                title=f"DEEP [{alert.severity.upper()}] {alert.title}"[:64],
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


# ═══════════════════════════════════════════════════════════════════════════
# The dispatcher
# ═══════════════════════════════════════════════════════════════════════════


class AlertDispatcher:
    """Turns alert events into notifications a person actually receives."""

    #: Events carrying something worth delivering, and how to read them.
    SUBSCRIBED = ("security_alert_correlated", "world_threat_match", "security_alert")

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
            channels if channels is not None else _default_channels()
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

        results = await asyncio.gather(
            *(self._send_one(channel, alert) for channel in self.channels),
            return_exceptions=False,
        )
        delivered_to = [c.name for c, ok in zip(self.channels, results) if ok]

        record = {**alert.to_dict(), "channels": delivered_to}
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


def _default_channels() -> List[Channel]:
    """Log always; desktop when plyer works; webhook only when configured."""
    channels: List[Channel] = [LogChannel()]
    if os.environ.get("DEEP_ALERT_DESKTOP", "1").strip().lower() not in {
        "0", "false", "off", "no",
    }:
        desktop = DesktopChannel()
        if desktop.available:
            channels.append(desktop)
    webhook_url = (os.environ.get("DEEP_ALERT_WEBHOOK") or "").strip()
    if webhook_url:
        channels.append(WebhookChannel(webhook_url))
    return channels
