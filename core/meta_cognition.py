"""
core/meta_cognition.py

DEEP Layer 5 — Meta-Intelligence (the "wisdom" layer).

Raw intelligence answers the question. Meta-intelligence asks:
  - How sure am I about that answer?
  - Is this beyond what I can actually know?
  - Did I just drift away from what Aryan was actually trying to do?
  - Should I flag a caveat instead of stating it flat?

This module is pure local analysis — no API keys, no extra model calls. It runs
*after* a reply is generated and produces a `SelfAudit`:

    confidence      0..1  — calibrated from hedging, retrieval support, claim type
    boundaries      list  — knowledge-limit flags ("past training cutoff", "no memory backs this")
    drift           0..1  — how far the reply wandered from the user's goal/intent
    rider           str   — an optional honesty rider to append ("I'm not certain about X")
    notes           list  — internal critique (shown in a meta panel, not necessarily to user)

Goal tracking lives here too: DEEP keeps a small set of *active goals* inferred
from what Aryan says, and drift detection compares each reply against the live
goal + the user's last message.

Usage:
    meta = MetaCognition()
    meta.observe_user("help me ship the proactive layer for DEEP today")
    audit = meta.self_audit(
        user_text="will this approach scale?",
        reply_text="It should scale fine, though I'm not 100% sure about ...",
        retrieved_context="=== SEMANTIC MEMORY ===\n- DEEP runs on one machine",
    )
    print(audit.confidence, audit.rider)
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Knowledge cutoff DEEP should be honest about when asked about "now".
_KNOWLEDGE_CUTOFF = "January 2026"

# Language that signals the model is hedging / uncertain.
_HEDGES = [
    "i think", "i believe", "probably", "might", "may ", "maybe", "perhaps",
    "i'm not sure", "im not sure", "not certain", "possibly", "i guess",
    "as far as i know", "afaik", "could be", "should be", "i assume",
    "likely", "seems", "appears", "roughly", "approximately", "i'd guess",
]

# Language that signals overconfident absolutes (risky when unsupported).
_ABSOLUTES = [
    "definitely", "certainly", "guaranteed", "always", "never", "100%",
    "without a doubt", "absolutely", "for sure", "undoubtedly", "no question",
]

# Topics that are inherently time-sensitive / beyond a static model.
_REALTIME_MARKERS = [
    "today", "right now", "currently", "latest", "current price", "this week",
    "as of now", "live", "breaking", "just released", "this morning",
    "stock price", "weather", "score", "who won", "trending",
]

# Phrasing that asks for a fact/claim (vs. opinion/creative), where calibration matters more.
_FACTUAL_MARKERS = [
    "what is", "what are", "how many", "when did", "when was", "who is",
    "where is", "is it true", "fact", "exactly", "define", "how much",
]


@dataclass
class Goal:
    text: str
    created_at: str
    last_seen: str
    hits: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "created_at": self.created_at,
                "last_seen": self.last_seen, "hits": self.hits}


@dataclass
class SelfAudit:
    confidence: float
    boundaries: List[str] = field(default_factory=list)
    drift: float = 0.0
    rider: str = ""
    notes: List[str] = field(default_factory=list)
    goal: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence": round(self.confidence, 3),
            "boundaries": self.boundaries,
            "drift": round(self.drift, 3),
            "rider": self.rider,
            "notes": self.notes,
            "goal": self.goal,
        }


_GOAL_TRIGGERS = [
    "i want to", "i need to", "help me", "let's", "lets ", "i'm trying to",
    "im trying to", "my goal", "i'd like to", "id like to", "can you help",
    "i'm building", "im building", "i'm working on", "im working on",
    "we should", "i plan to", "the plan is",
]


class MetaCognition:
    """Self-audit, confidence calibration, knowledge boundaries, goal/drift."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else (
            Path(__file__).parent.parent / "data" / "meta"
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = self.data_dir / "meta_state.json"
        self.goals: List[Goal] = []
        self.audit_log: List[Dict[str, Any]] = []
        self._load()

    # ─── persistence ──────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not self._state_file.exists():
            return
        try:
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
            for g in data.get("goals", []):
                self.goals.append(Goal(**g))
            self.audit_log = data.get("audit_log", [])[-50:]
        except Exception:
            pass

    def _save(self) -> None:
        try:
            self._state_file.write_text(json.dumps({
                "goals": [g.to_dict() for g in self.goals],
                "audit_log": self.audit_log[-50:],
                "saved_at": datetime.now().isoformat(),
            }, indent=2), encoding="utf-8")
        except Exception:
            pass

    # ─── goal tracking ────────────────────────────────────────────────────────

    def observe_user(self, user_text: str) -> Optional[Goal]:
        """Update the active-goal set from a user message. Returns new/updated goal."""
        text = (user_text or "").strip()
        low = text.lower()
        if not text:
            return None

        # Does this message express a goal/intent?
        trigger = next((t for t in _GOAL_TRIGGERS if t in low), None)
        if not trigger:
            return None

        # Extract the goal clause after the trigger.
        idx = low.find(trigger) + len(trigger)
        clause = text[idx:].strip(" ,.?!").strip()
        clause = re.split(r"[.?!]", clause)[0].strip()
        if len(clause) < 4:
            return None
        clause = clause[:140]

        now = datetime.now().isoformat()
        # Merge with an existing similar goal.
        for g in self.goals:
            if self._overlap(g.text, clause) > 0.5:
                g.hits += 1
                g.last_seen = now
                self._reorder_save()
                return g
        goal = Goal(text=clause, created_at=now, last_seen=now)
        self.goals.insert(0, goal)
        self.goals = self.goals[:8]
        self._save()
        return goal

    def active_goal(self) -> Optional[Goal]:
        """The freshest goal (most recently reinforced)."""
        if not self.goals:
            return None
        return sorted(self.goals, key=lambda g: g.last_seen, reverse=True)[0]

    def resolve_goal(self, fragment: str) -> bool:
        frag = fragment.lower().strip()
        before = len(self.goals)
        self.goals = [g for g in self.goals if frag not in g.text.lower()]
        if len(self.goals) != before:
            self._save()
            return True
        return False

    # ─── the core: self-audit ─────────────────────────────────────────────────

    def self_audit(self, user_text: str, reply_text: str,
                   retrieved_context: str = "") -> SelfAudit:
        """Audit a freshly generated reply. Cheap, deterministic, local."""
        reply = (reply_text or "").strip()
        user = (user_text or "").strip()
        rlow, ulow = reply.lower(), user.lower()
        notes: List[str] = []
        boundaries: List[str] = []

        # ── confidence calibration ──
        confidence = 0.7  # neutral prior

        hedge_count = sum(1 for h in _HEDGES if h in rlow)
        abs_count = sum(1 for a in _ABSOLUTES if a in rlow)
        is_factual = any(m in ulow for m in _FACTUAL_MARKERS)
        has_support = bool(retrieved_context.strip())

        # Hedging lowers stated confidence — but that's *appropriate* calibration,
        # so we treat a couple of hedges as healthy, many as genuine uncertainty.
        if hedge_count >= 1:
            confidence -= min(hedge_count, 4) * 0.06
            if hedge_count >= 3:
                notes.append(f"{hedge_count} hedge markers — reply is genuinely uncertain")
        # Absolutes raise confidence only if backed; otherwise they're a risk.
        if abs_count:
            if has_support:
                confidence += 0.05
            else:
                confidence -= 0.08
                notes.append("absolute claims without retrieval support — possible overconfidence")
        # Factual question answered with retrieval support => more trustworthy.
        if is_factual and has_support:
            confidence += 0.1
        if is_factual and not has_support:
            confidence -= 0.1
            notes.append("factual question answered from parametric memory only (no retrieval)")

        # Very short answer to a substantive question is suspicious.
        if len(reply) < 40 and len(user) > 40:
            confidence -= 0.1
            notes.append("answer is short relative to the question")

        confidence = max(0.05, min(0.98, confidence))

        # ── knowledge boundaries ──
        if any(m in ulow for m in _REALTIME_MARKERS):
            boundaries.append(
                f"time-sensitive query; static knowledge ends ~{_KNOWLEDGE_CUTOFF}"
            )
        # Reply asserts a recent-sounding fact with no support.
        if any(m in rlow for m in _REALTIME_MARKERS) and not has_support:
            boundaries.append("reply makes a 'current'-sounding claim with no live source")
        # Reply itself admits ignorance — good, surface it as a boundary, not low conf.
        if any(p in rlow for p in ("i don't know", "i dont know", "not sure i can",
                                   "i can't verify", "i cannot verify", "no information")):
            boundaries.append("DEEP explicitly flagged missing knowledge")

        # ── drift detection ──
        # Real drift = the reply doesn't serve what Aryan JUST asked (a tangent
        # DEEP went off on). We measure against the current user turn, not a
        # stale goal — if Aryan changes topic, that's him steering, not DEEP
        # drifting. Containment (how much of the question the reply addresses)
        # is more forgiving than Jaccard for long replies.
        goal = self.active_goal()
        drift = 0.0
        if len(user) > 12:
            cover = self._containment(user, reply)
            drift = round(max(0.0, 1.0 - cover * 2.0), 3)  # cover>=0.5 => no drift
            # Off-goal note only when the reply ALSO ignores the active goal —
            # i.e. it serves neither the question nor the goal.
            if drift > 0.7 and goal and self._containment(goal.text, reply) < 0.2:
                notes.append(f"reply addresses neither the question nor goal: '{goal.text}'")
            elif drift > 0.7:
                notes.append("reply may not directly address the question asked")

        # ── honesty rider (optional, user-facing) ──
        rider = ""
        if boundaries and confidence < 0.6:
            rider = self._build_rider(boundaries, user)

        audit = SelfAudit(
            confidence=confidence,
            boundaries=boundaries,
            drift=drift,
            rider=rider,
            notes=notes,
            goal=goal.text if goal else None,
        )

        self.audit_log.append({
            "ts": datetime.now().isoformat(),
            "user": user[:160],
            **audit.to_dict(),
        })
        if len(self.audit_log) > 60:
            self.audit_log = self.audit_log[-50:]
        self._save()
        return audit

    @staticmethod
    def _build_rider(boundaries: List[str], user_text: str) -> str:
        if any("time-sensitive" in b or "current" in b for b in boundaries):
            return ("Heads up — this touches live/current info that may be past "
                    "what I can verify, so double-check anything time-sensitive.")
        return ("I'm flagging some uncertainty here — I don't have solid memory "
                "or a live source backing this, so treat it as my best estimate.")

    # ─── prompt augmentation ──────────────────────────────────────────────────

    def goal_directive(self) -> str:
        """A one-line directive to inject into the system prompt so DEEP stays on-goal."""
        goal = self.active_goal()
        if not goal:
            return ""
        return (f"Aryan's current active goal: \"{goal.text}\". "
                f"Keep your answer in service of it; if you must digress, say so.")

    # ─── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _overlap(a: str, b: str) -> float:
        """Jaccard overlap of content words — cheap semantic-ish proximity."""
        wa = {w for w in re.findall(r"[a-zA-Z']+", a.lower()) if len(w) > 3}
        wb = {w for w in re.findall(r"[a-zA-Z']+", b.lower()) if len(w) > 3}
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / len(wa | wb)

    @staticmethod
    def _containment(needle: str, haystack: str) -> float:
        """Fraction of `needle`'s content words present in `haystack` (stem-tolerant)."""
        def toks(s: str) -> set:
            out = set()
            for w in re.findall(r"[a-zA-Z']+", s.lower()):
                if len(w) > 3:
                    out.add(w[:-1] if w.endswith("s") else w)  # crude singularize
            return out
        wn, wh = toks(needle), toks(haystack)
        if not wn:
            return 1.0
        return len(wn & wh) / len(wn)

    def _reorder_save(self) -> None:
        self.goals.sort(key=lambda g: g.last_seen, reverse=True)
        self._save()

    def stats(self) -> Dict[str, Any]:
        recent = self.audit_log[-20:]
        avg_conf = (sum(a["confidence"] for a in recent) / len(recent)) if recent else 0.0
        avg_drift = (sum(a["drift"] for a in recent) / len(recent)) if recent else 0.0
        return {
            "active_goals": len(self.goals),
            "top_goal": self.active_goal().text if self.active_goal() else None,
            "audits_logged": len(self.audit_log),
            "avg_confidence_recent": round(avg_conf, 3),
            "avg_drift_recent": round(avg_drift, 3),
        }

    def recent_audits(self, limit: int = 10) -> List[Dict[str, Any]]:
        return list(reversed(self.audit_log[-limit:]))

    def list_goals(self) -> List[Dict[str, Any]]:
        return [g.to_dict() for g in self.goals]


# ─── standalone smoke test ────────────────────────────────────────────────────
if __name__ == "__main__":
    import tempfile
    meta = MetaCognition(data_dir=Path(tempfile.mkdtemp()))

    g = meta.observe_user("help me ship the proactive layer for DEEP today")
    print("goal captured:", g.text if g else None)

    print("\n--- audit 1: confident, supported, on-goal ---")
    a1 = meta.self_audit(
        user_text="how should the proactive loop be structured?",
        reply_text="Use a background asyncio loop that polls the predictive engine "
                    "and emits suggestions through the event bus, rate-limited per day.",
        retrieved_context="=== SEMANTIC ===\n- DEEP uses an async EventBus",
    )
    print(json.dumps(a1.to_dict(), indent=2))

    print("\n--- audit 2: hedgy, time-sensitive, no support ---")
    a2 = meta.self_audit(
        user_text="what's the latest price of the stock right now?",
        reply_text="I think it's probably around there, but I'm not sure, maybe check.",
        retrieved_context="",
    )
    print(json.dumps(a2.to_dict(), indent=2))

    print("\n--- audit 3: off-goal drift ---")
    a3 = meta.self_audit(
        user_text="anyway, tell me a story about dragons",
        reply_text="Once upon a time a dragon named Ember soared over crimson mountains...",
        retrieved_context="",
    )
    print("drift:", a3.drift, "| notes:", a3.notes)

    print("\n--- goal directive ---")
    print(meta.goal_directive())
    print("\n--- stats ---")
    print(json.dumps(meta.stats(), indent=2))
    print("\nOK")
