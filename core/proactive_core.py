"""
core/proactive_core.py

DEEP Proactive Core — the layer that makes DEEP *act before being asked*.

This replaces the dead `autonomous.ProactiveEngine` (that import never
resolved, so the old proactive loop returned immediately and DEEP only ever
spoke when spoken to). This one is real and wired to things that actually
exist in the codebase:

    - PredictiveEngine  -> time/sequence "you usually do X now" suggestions
    - MetaCognition     -> surfaces stale active goals ("still want to ship X?")
    - CognitiveMemory   -> idle nudges from episodic threads / user model
    - reminders         -> simple time-due reminders stored locally

A single async loop (`run()`) ticks on an interval, asks each source for
candidate nudges, fuses + dedups + rate-limits them, and emits the survivors on
the EventBus as `proactive_suggestion` events. The server's WebSocket layer is
already subscribed to the bus, so suggestions reach the UI with no extra wiring.

Guardrails (so DEEP is helpful, not a nag):
    - hard daily cap
    - min gap between nudges
    - quiet hours
    - never repeat the same suggestion text within a cooldown window
    - confidence floor

Usage (server):
    proactive = ProactiveCore(event_bus=bus, predictive=predictive_engine,
                              meta=meta, memory=cog_memory)
    asyncio.create_task(proactive.run())
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Reminder:
    id: str
    text: str
    due_iso: str
    fired: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "text": self.text, "due_iso": self.due_iso,
                "fired": self.fired}


@dataclass
class Nudge:
    id: str
    kind: str          # prediction | goal | reminder | idle
    title: str
    body: str
    confidence: float
    payload: Dict[str, Any] = field(default_factory=dict)
    created_iso: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "title": self.title,
                "body": self.body, "confidence": round(self.confidence, 3),
                "payload": self.payload,
                "created": self.created_iso}


class ProactiveCore:
    """Background engine that surfaces relevant suggestions unprompted."""

    TICK_SECONDS = 60          # how often the loop wakes
    MIN_GAP_SECONDS = 600      # >=10 min between emitted nudges
    MAX_PER_DAY = 8
    QUIET_START_HOUR = 23      # 23:00..07:00 = no nudges
    QUIET_END_HOUR = 7
    CONFIDENCE_FLOOR = 0.45
    REPEAT_COOLDOWN_SECONDS = 6 * 3600

    def __init__(self, event_bus=None, predictive=None, meta=None, memory=None,
                 kg=None, data_dir: Optional[Path] = None) -> None:
        self.bus = event_bus
        self.predictive = predictive
        self.meta = meta
        self.memory = memory
        self.kg = kg   # KnowledgeGraph → graph-derived inferences (habits/stale facts)

        self.data_dir = Path(data_dir) if data_dir else (
            Path(__file__).parent.parent / "data" / "proactive"
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = self.data_dir / "proactive_state.json"

        self.reminders: List[Reminder] = []
        self.history: List[Dict[str, Any]] = []     # emitted nudges (for UI/API)
        self._recent_texts: Dict[str, float] = {}    # text -> last emit epoch
        self._last_emit_epoch: float = 0.0
        self._emitted_today: int = 0
        self._today: Optional[str] = None
        self._running = False
        self._last_user_activity: float = time.time()

        self._load()

    # ─── lifecycle ────────────────────────────────────────────────────────────

    async def run(self) -> None:
        """Main loop — schedule with asyncio.create_task(core.run())."""
        self._running = True
        logger.info("[ProactiveCore] started")
        # Small initial delay so startup noise settles.
        await asyncio.sleep(8)
        while self._running:
            try:
                await self.tick()
            except Exception as e:
                logger.warning(f"[ProactiveCore] tick error: {e}")
            await asyncio.sleep(self.TICK_SECONDS)

    def stop(self) -> None:
        self._running = False

    def note_user_activity(self) -> None:
        """Call on each user message so idle-nudges only fire when truly idle."""
        self._last_user_activity = time.time()

    # ─── one tick ─────────────────────────────────────────────────────────────

    async def tick(self) -> Optional[Nudge]:
        """Gather candidates, pick the best admissible one, emit it."""
        self._roll_day()
        if not self._within_budget():
            return None

        candidates: List[Nudge] = []
        candidates.extend(self._from_reminders())     # highest priority
        candidates.extend(self._from_predictions())
        candidates.extend(self._from_graph_inference())
        candidates.extend(self._from_goals())
        candidates.extend(self._from_idle())
        candidates.extend(await self._from_system())
        candidates.extend(self._from_geo_anomalies())

        # Admissibility filter: confidence floor + not a recent repeat.
        now = time.time()
        admissible = [
            c for c in candidates
            if c.confidence >= self.CONFIDENCE_FLOOR and not self._is_repeat(c, now)
        ]
        if not admissible:
            return None

        # Reminders always win; otherwise highest confidence.
        admissible.sort(key=lambda c: (c.kind != "reminder", -c.confidence))
        chosen = admissible[0]
        await self._emit(chosen)
        return chosen

    def _within_budget(self) -> bool:
        now = datetime.now()
        if not (self.QUIET_END_HOUR <= now.hour < self.QUIET_START_HOUR):
            return False
        if self._emitted_today >= self.MAX_PER_DAY:
            return False
        if time.time() - self._last_emit_epoch < self.MIN_GAP_SECONDS:
            return False
        return True

    # ─── candidate sources ────────────────────────────────────────────────────

    def _from_reminders(self) -> List[Nudge]:
        out = []
        now = datetime.now()
        for r in self.reminders:
            if r.fired:
                continue
            try:
                due = datetime.fromisoformat(r.due_iso)
            except Exception:
                continue
            if due <= now:
                out.append(Nudge(
                    id=f"nudge_rem_{r.id}",
                    kind="reminder",
                    title="Reminder",
                    body=r.text,
                    confidence=1.0,
                ))
                r.fired = True
        if out:
            self._save()
        return out

    def _from_predictions(self) -> List[Nudge]:
        if not self.predictive:
            return []
        try:
            preds = self.predictive.get_predictions(max_results=2)
        except Exception:
            return []
        out = []
        for p in preds:
            out.append(Nudge(
                id=f"nudge_pred_{int(time.time()*1000)}_{len(out)}",
                kind="prediction",
                title="Anticipating your next move",
                body=f"{p.get('suggestion', '')} ({p.get('reason', '')})".strip(),
                confidence=float(p.get("confidence", 0.5)),
            ))
        return out

    def _from_graph_inference(self) -> List[Nudge]:
        """Surface actionable inferences from the knowledge graph — the JARVIS
        'I noticed…' layer. Uses graph_inference (cheap; no GNN here). We only
        promote *actionable* inference types to nudges (stale facts worth
        revisiting, predicted connections), not bare habit statements."""
        if not self.kg:
            return []
        try:
            from core.graph_inference import infer
            items = infer(self.kg, max_items=6)
        except Exception:
            return []
        out: List[Nudge] = []
        for it in items:
            ty = it.get("type")
            if ty not in ("stale", "connection"):
                continue
            # The inference 'score' measures the fact's strength, not how worth
            # surfacing it is. A stale fact is low-strength *by design* — that's
            # the point — so map to a worth-surfacing confidence that clears the
            # ProactiveCore floor; a connection rides its prediction score.
            conf = 0.55 if ty == "stale" else max(0.5, float(it.get("score", 0.5)))
            out.append(Nudge(
                id=f"nudge_kg_{int(time.time()*1000)}_{len(out)}",
                kind="insight",
                title="From what I've learned",
                body=it.get("text", ""),
                confidence=conf,
            ))
            if len(out) >= 2:
                break
        return out

    def _from_goals(self) -> List[Nudge]:
        """Surface a stale-but-active goal so it doesn't quietly die."""
        if not self.meta:
            return []
        try:
            goal = self.meta.active_goal()
        except Exception:
            return []
        if not goal:
            return []
        # Only nudge if the goal hasn't been reinforced in a while.
        try:
            last = datetime.fromisoformat(goal.last_seen)
        except Exception:
            return []
        idle_hours = (datetime.now() - last).total_seconds() / 3600
        if idle_hours < 6:
            return []
        # Confidence scales with how reinforced the goal was, decays as it ages.
        conf = min(0.85, 0.45 + 0.1 * goal.hits) * max(0.4, 1.0 - idle_hours / 72)
        return [Nudge(
            id=f"nudge_goal_{int(time.time()*1000)}",
            kind="goal",
            title="Picking up where we left off",
            body=f"Earlier you wanted to {goal.text}. Want to continue on that?",
            confidence=conf,
        )]

    def _from_idle(self) -> List[Nudge]:
        """When Aryan's been quiet a long time, offer a relevant re-entry point."""
        idle = time.time() - self._last_user_activity
        if idle < 3 * 3600:   # only after 3h of silence
            return []
        if not self.memory:
            return []
        try:
            um = self.memory.get_user_model()
        except Exception:
            return []
        goals = um.get("goals", [])
        if not goals:
            return []
        return [Nudge(
            id=f"nudge_idle_{int(time.time()*1000)}",
            kind="idle",
            title="Whenever you're ready",
            body=f"I'm here when you want to get back to: {goals[0]}.",
            confidence=0.5,
        )]

    async def _from_system(self) -> List[Nudge]:
        """Deterministic 3 AM Network Scan."""
        now = datetime.now()
        if now.hour != 3:
            return []
        
        # Only run once per day
        scan_key = f"scan_{now.strftime('%Y-%m-%d')}"
        if self._recent_texts.get(scan_key):
            return []
            
        self._recent_texts[scan_key] = time.time()
        
        try:
            from core.tools.registry import TOOL_SPECS
            import core.tools.deep_registry
            from core.integrations.cyber_sec import CyberSecurityIntegration
            
            # Temporary instantiation of cyber to run the scan
            cyber = CyberSecurityIntegration()
            res = await cyber.scan_network_arp()
            
            nudges = []
            nudges.append(Nudge(
                id=f"nudge_scan_{int(time.time()*1000)}",
                kind="security",
                title="3 AM Security Scan Complete",
                body=f"Network scan finished automatically: {res[:200]}...",
                confidence=1.0,
                payload={"type": "network_scan", "results": res}
            ))
            
            # Local Vuln Matcher
            vulns = await cyber.scan_local_vulns()
            if vulns:
                for v in vulns:
                    nudges.append(Nudge(
                        id=f"nudge_vuln_{v['cve_id']}_{int(time.time()*100)}",
                        kind="security",
                        title=f"⚠ Possibly Affected: {v['software']}",
                        body=f"Local software '{v['software']}' (v{v['version']}) fuzzy-matched a recent KEV: {v['cve_id']}. Please verify your version against the CVE.",
                        confidence=0.5,  # Low confidence due to loose string matching
                        payload={"type": "local_vuln", "data": v}
                    ))
            
            return nudges
        except Exception as e:
            return []

    def _from_geo_anomalies(self) -> List[Nudge]:
        """Check for WAN connection anomalies (10-minute throttle)."""
        now = time.time()
        geo_key = "geo_anomaly_check"
        last_check = self._recent_texts.get(geo_key, 0)
        
        # 10 minute throttle
        if now - last_check < 600:
            return []
            
        self._recent_texts[geo_key] = now
        
        try:
            from network.connection_geo import check_geo_anomalies
            anomalies = check_geo_anomalies()
            nudges = []
            for a in anomalies:
                # Deduplicate exact anomalies using title
                if self._recent_texts.get(f"geo_anom_{a['title']}"):
                    continue
                self._recent_texts[f"geo_anom_{a['title']}"] = now
                
                nudges.append(Nudge(
                    id=f"nudge_geo_{int(time.time()*1000)}",
                    kind="security",
                    title=f"Anomaly: {a['title']}",
                    body=a['description'],
                    confidence=0.85 if a['severity'] == "medium" else 0.7,
                    payload={"type": "geo_anomaly", "data": a}
                ))
            return nudges
        except Exception as e:
            return []

    # ─── emission + dedup ─────────────────────────────────────────────────────

    def _is_repeat(self, nudge: Nudge, now: float) -> bool:
        key = nudge.body.strip().lower()
        last = self._recent_texts.get(key)
        return last is not None and (now - last) < self.REPEAT_COOLDOWN_SECONDS

    async def _emit(self, nudge: Nudge) -> None:
        now = time.time()
        self._recent_texts[nudge.body.strip().lower()] = now
        # prune cooldown table
        self._recent_texts = {
            k: v for k, v in self._recent_texts.items()
            if now - v < self.REPEAT_COOLDOWN_SECONDS
        }
        self._last_emit_epoch = now
        self._emitted_today += 1
        self.history.append(nudge.to_dict())
        self.history = self.history[-50:]
        self._save()

        logger.info(f"[ProactiveCore] emit {nudge.kind}: {nudge.body[:60]}")
        if self.bus:
            try:
                await self.bus.publish("proactive_suggestion", nudge.to_dict())
            except Exception as e:
                logger.warning(f"[ProactiveCore] publish failed: {e}")

    # ─── reminders API ────────────────────────────────────────────────────────

    def add_reminder(self, text: str, due: datetime) -> Reminder:
        r = Reminder(id=f"rem_{int(time.time()*1000)}", text=text.strip(),
                     due_iso=due.isoformat())
        self.reminders.append(r)
        self.reminders = self.reminders[-100:]
        self._save()
        return r

    def list_reminders(self, include_fired: bool = False) -> List[Dict[str, Any]]:
        rs = self.reminders if include_fired else [r for r in self.reminders if not r.fired]
        return [r.to_dict() for r in rs]

    # ─── persistence + housekeeping ───────────────────────────────────────────

    def _roll_day(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        if self._today != today:
            self._today = today
            self._emitted_today = 0

    def _load(self) -> None:
        if not self._state_file.exists():
            return
        try:
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
            self.reminders = [Reminder(**r) for r in data.get("reminders", [])]
            self.history = data.get("history", [])[-50:]
            self._recent_texts = data.get("recent_texts", {})
            self._today = data.get("today")
            self._emitted_today = data.get("emitted_today", 0)
        except Exception as e:
            logger.warning(f"[ProactiveCore] load failed: {e}")

    def _save(self) -> None:
        try:
            self._state_file.write_text(json.dumps({
                "reminders": [r.to_dict() for r in self.reminders],
                "history": self.history[-50:],
                "recent_texts": self._recent_texts,
                "today": self._today,
                "emitted_today": self._emitted_today,
                "saved_at": datetime.now().isoformat(),
            }, indent=2), encoding="utf-8")
        except Exception:
            pass

    def stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "emitted_today": self._emitted_today,
            "max_per_day": self.MAX_PER_DAY,
            "pending_reminders": sum(1 for r in self.reminders if not r.fired),
            "history_count": len(self.history),
        }

    def recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        return list(reversed(self.history[-limit:]))


# ─── standalone smoke test ────────────────────────────────────────────────────
if __name__ == "__main__":
    import tempfile

    logging.basicConfig(level=logging.INFO)

    class _FakeBus:
        def __init__(self): self.events = []
        async def publish(self, name, payload): self.events.append((name, payload))

    class _FakePredictive:
        def get_predictions(self, max_results=2):
            return [{"suggestion": "Would you like to continue coding?",
                     "reason": "you often code around now", "confidence": 0.7}]

    class _FakeGoal:
        text = "ship the proactive layer"
        last_seen = (datetime.now() - timedelta(hours=10)).isoformat()
        hits = 3

    class _FakeMeta:
        def active_goal(self): return _FakeGoal()

    bus = _FakeBus()
    core = ProactiveCore(event_bus=bus, predictive=_FakePredictive(),
                         meta=_FakeMeta(), data_dir=Path(tempfile.mkdtemp()))
    # Force budget open regardless of wall-clock hour for the test.
    core._within_budget = lambda: True

    async def _demo():
        core.add_reminder("call the bank", datetime.now() - timedelta(minutes=1))
        n1 = await core.tick()
        print("tick1:", n1.kind, "|", n1.body if n1 else None)
        # reminder fired; next tick should pick a non-reminder candidate
        core._last_emit_epoch = 0
        n2 = await core.tick()
        print("tick2:", n2.kind if n2 else None, "|", n2.body if n2 else None)
        print("\nemitted events on bus:", len(bus.events))
        print("stats:", json.dumps(core.stats(), indent=2))

    asyncio.run(_demo())
    print("\nOK")
