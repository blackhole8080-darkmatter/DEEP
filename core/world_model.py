"""
core/world_model.py — DEEP's persistent model of *who Aryan is right now*.

This is the "it knows me" layer. It synthesises a compact, structured profile —
active projects, key people, current priorities, interests, focus — plus a rolling
log of episodic summaries ("this week you were debugging the scanner"), and injects
a short version of it into every chat system prompt so responses are personalised.

Signal comes from the (now clean, LLM-extracted) knowledge graph + recent
conversation snippets; an LLM fuses them into the structured model. Decoupled: the
caller injects an async `generate(system, user)` fn and the recent texts. Fail-soft
— a bad refresh leaves the previous model intact.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

GenerateFn = Callable[[str, str], Awaitable[str]]

_SYSTEM = (
    "You maintain a concise model of a user named Aryan for his AI companion DEEP. "
    "Given the knowledge DEEP has and recent conversation, output a STRICT JSON object "
    "capturing the durable, useful facts — no fluff. Shape:\n"
    '{"summary":"one sentence on who Aryan is and what he is focused on",'
    '"projects":["active projects"],"people":["important people"],'
    '"priorities":["current goals/priorities"],"interests":["recurring interests/skills"],'
    '"current_focus":"what he is working on right now",'
    '"episode":"one past-tense sentence summarising the recent activity"}\n'
    "Keep each list <=6 items, short phrases. Merge duplicates. Output JSON only."
)


def _coerce_json(raw: str) -> Dict[str, Any]:
    if not raw:
        return {}
    s = re.sub(r"^```(?:json)?", "", raw.strip()).strip()
    s = re.sub(r"```$", "", s).strip()
    try:
        return json.loads(s)
    except Exception:
        a, b = s.find("{"), s.rfind("}")
        if a != -1 and b > a:
            try:
                return json.loads(s[a:b + 1])
            except Exception:
                return {}
    return {}


class WorldModel:
    MAX_EPISODES = 12
    MAX_WORLD_ALERTS = 8

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir else (Path(__file__).parent.parent / "data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file = self.data_dir / "world_model.json"
        self.state: Dict[str, Any] = {
            "summary": "", "projects": [], "people": [], "priorities": [],
            "interests": [], "current_focus": "", "episodes": [], "updated_at": None,
            "world_alerts": [],
        }
        self._load()
        self.state.setdefault("world_alerts", [])

    # ── persistence ───────────────────────────────────────────────────────────
    def _load(self) -> None:
        try:
            if self.file.exists():
                self.state.update(json.loads(self.file.read_text(encoding="utf-8")))
        except Exception as e:
            logger.warning(f"[world_model] load failed: {e}")

    def _save(self) -> None:
        try:
            self.file.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"[world_model] save failed: {e}")

    # ── signal from the knowledge graph ───────────────────────────────────────
    @staticmethod
    def _kg_signal(kg) -> str:
        try:
            ents = kg.get_all_entities()
        except Exception:
            return ""
        ents = [e for e in ents if e.get("name")]
        ents.sort(key=lambda e: e.get("mention_count", 0), reverse=True)
        lines = []
        for e in ents[:40]:
            d = (e.get("description") or "").strip()
            lines.append(f"- {e.get('name')} ({e.get('type','?')}, {e.get('mention_count',1)}×)"
                         + (f": {d}" if d else ""))
        return "\n".join(lines)

    # ── refresh ───────────────────────────────────────────────────────────────
    async def refresh(self, kg, recent_texts: List[str], generate: GenerateFn) -> Dict[str, Any]:
        kg_block = self._kg_signal(kg)
        convo = "\n".join(f"- {t.strip()[:200]}" for t in (recent_texts or [])[:12] if t and t.strip())
        if not kg_block and not convo:
            return self.state
        user = (f"What DEEP knows (knowledge graph):\n{kg_block or '(empty)'}\n\n"
                f"Recent conversation snippets:\n{convo or '(none)'}\n\nJSON:")
        try:
            raw = await generate(_SYSTEM, user)
            data = _coerce_json(raw)
        except Exception as e:
            logger.warning(f"[world_model] refresh generate failed: {e}")
            return self.state
        if not data:
            return self.state

        def _list(key):
            v = data.get(key, [])
            return [str(x).strip() for x in v if str(x).strip()][:6] if isinstance(v, list) else []

        for k in ("projects", "people", "priorities", "interests"):
            got = _list(k)
            if got:
                self.state[k] = got
        for k in ("summary", "current_focus"):
            v = str(data.get(k, "")).strip()
            if v:
                self.state[k] = v[:240]

        ep = str(data.get("episode", "")).strip()
        if ep:
            eps = self.state.get("episodes", [])
            if not eps or eps[-1].get("text") != ep:
                eps.append({"text": ep[:240], "at": datetime.now().isoformat()})
            self.state["episodes"] = eps[-self.MAX_EPISODES:]

        self.state["updated_at"] = datetime.now().isoformat()
        self._save()
        return self.state

    # ── world signal (global threat intel matched to known entities) ──────────
    def add_world_alert(self, text: str) -> None:
        """Record a world event that's relevant to something DEEP already knows
        about Aryan (e.g. a KEV disclosure for a project/tool he uses). Bounded,
        deduped, newest last — see global_threat_watch.py, the only caller today."""
        text = (text or "").strip()[:280]
        if not text:
            return
        alerts = self.state.setdefault("world_alerts", [])
        if alerts and alerts[-1].get("text") == text:
            return  # skip immediate dupes (e.g. same watch cycle re-firing)
        alerts.append({"text": text, "at": datetime.now().isoformat()})
        self.state["world_alerts"] = alerts[-self.MAX_WORLD_ALERTS:]
        self._save()

    # ── consumption ───────────────────────────────────────────────────────────
    def context_block(self) -> str:
        """Compact block injected into the chat system prompt. Empty until first refresh."""
        s = self.state
        if not (s.get("summary") or s.get("projects") or s.get("priorities") or s.get("world_alerts")):
            return ""
        parts = ["WHAT YOU KNOW ABOUT ARYAN (use naturally, don't recite):"]
        if s.get("summary"):
            parts.append(s["summary"])
        if s.get("current_focus"):
            parts.append(f"Right now: {s['current_focus']}")
        if s.get("projects"):
            parts.append("Projects: " + ", ".join(s["projects"]))
        if s.get("priorities"):
            parts.append("Priorities: " + ", ".join(s["priorities"]))
        if s.get("people"):
            parts.append("People: " + ", ".join(s["people"]))
        if s.get("interests"):
            parts.append("Interests: " + ", ".join(s["interests"]))
        eps = s.get("episodes", [])
        if eps:
            parts.append("Recently: " + " ".join(e["text"] for e in eps[-3:]))
        world_alerts = s.get("world_alerts", [])
        if world_alerts:
            parts.append(
                "World events relevant to Aryan's known projects/tools (mention "
                "proactively if relevant, don't just recite): "
                + " | ".join(a["text"] for a in world_alerts[-3:])
            )
        return "\n".join(parts) + "\n\n"

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.state)
