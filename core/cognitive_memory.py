"""
core/cognitive_memory.py

DEEP Layer 3 — Cognitive Memory.

The existing LongTermMemory is one undifferentiated vector store. Real cognition
separates *kinds* of memory, because they answer different questions and decay
differently:

    episodic   — what happened and WHEN        ("Aryan asked about Tailscale at 2pm Friday")
    semantic   — durable facts / knowledge      ("Aryan's main project is DEEP")
    procedural — HOW to do things (step lists)   ("To restart DEEP: kill :7768, run start_deep.bat")
    user_model — a rolling profile of Aryan      (goals, prefs, working hours, tone)

This module is a thin cognitive facade *over* LongTermMemory — it does not
replace it. Each layer is just a `memory_type` partition in the same Chroma
collection, plus a small JSON-backed user_model that's cheap to read every turn.

Design choices:
- Zero new heavy deps — reuses the LTM embedding/vector stack already loaded.
- Every public method is defensive: a failure in one layer never breaks chat.
- `recall_layered()` returns ONE formatted block ready to drop into a prompt.
- `consolidate()` promotes facts that recur across episodic memories into
  semantic memory (the "it happened enough times that it's now just true" move).

Usage:
    from core.cognitive_memory import CognitiveMemory
    mem = CognitiveMemory(ltm)                      # wrap existing LongTermMemory

    mem.record_episode("user", "How do I restart DEEP?")
    mem.learn_fact("Aryan's project is DEEP", importance=1.6)
    mem.learn_procedure("restart DEEP", ["kill python on :7768", "run start_deep.bat"])
    mem.update_user_model(goals=["ship proactive layer"], tone="concise")

    block = mem.recall_layered("how do I restart the server")  # -> prompt-ready text
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Memory-type partition names (stored in the LTM `memory_type` field).
EPISODIC = "episodic"
SEMANTIC = "semantic"
PROCEDURAL = "procedural"

# Tokens we ignore when mining recurring facts for consolidation.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "for", "is",
    "are", "was", "were", "be", "do", "does", "did", "how", "what", "why",
    "when", "i", "you", "it", "this", "that", "my", "me", "we", "with", "can",
    "please", "deep", "aryan",
}


class CognitiveMemory:
    """Typed memory facade over LongTermMemory + a JSON user model."""

    def __init__(self, ltm, data_dir: Optional[Path] = None) -> None:
        self._ltm = ltm
        self.data_dir = Path(data_dir) if data_dir else (
            Path(__file__).parent.parent / "data" / "cognitive"
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._user_model_file = self.data_dir / "user_model.json"
        self._user_model: Dict[str, Any] = self._load_user_model()

    # ─── User model (cheap, read every turn) ──────────────────────────────────

    def _default_user_model(self) -> Dict[str, Any]:
        return {
            "name": "Aryan",
            "goals": [],            # active goals, most-recent-first
            "preferences": [],      # durable prefs ("concise", "no 'sir'")
            "tone": "warm, concise, candid",
            "working_hours": {},    # hour_bucket -> count, learned over time
            "facts": [],            # short profile facts surfaced every turn
            "updated_at": None,
        }

    def _load_user_model(self) -> Dict[str, Any]:
        if self._user_model_file.exists():
            try:
                data = json.loads(self._user_model_file.read_text(encoding="utf-8"))
                base = self._default_user_model()
                base.update(data)
                return base
            except Exception:
                pass
        return self._default_user_model()

    def _save_user_model(self) -> None:
        try:
            self._user_model["updated_at"] = datetime.now().isoformat()
            self._user_model_file.write_text(
                json.dumps(self._user_model, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def update_user_model(self, *, goals: Optional[List[str]] = None,
                          preferences: Optional[List[str]] = None,
                          tone: Optional[str] = None,
                          facts: Optional[List[str]] = None,
                          active_hour: Optional[int] = None) -> None:
        """Merge new signal into the rolling user model (dedup, bounded)."""
        m = self._user_model
        if goals:
            for g in goals:
                g = g.strip()
                if g and g not in m["goals"]:
                    m["goals"].insert(0, g)
            m["goals"] = m["goals"][:8]
        if preferences:
            for p in preferences:
                p = p.strip()
                if p and p not in m["preferences"]:
                    m["preferences"].insert(0, p)
            m["preferences"] = m["preferences"][:12]
        if facts:
            for f in facts:
                f = f.strip()
                if f and f not in m["facts"]:
                    m["facts"].insert(0, f)
            m["facts"] = m["facts"][:12]
        if tone:
            m["tone"] = tone.strip()
        if active_hour is not None:
            wh = m["working_hours"]
            wh[str(active_hour)] = wh.get(str(active_hour), 0) + 1
        self._save_user_model()

    def get_user_model(self) -> Dict[str, Any]:
        return dict(self._user_model)

    def complete_goal(self, fragment: str) -> bool:
        """Remove a goal that matches `fragment` (case-insensitive substring)."""
        frag = fragment.lower().strip()
        before = len(self._user_model["goals"])
        self._user_model["goals"] = [
            g for g in self._user_model["goals"] if frag not in g.lower()
        ]
        if len(self._user_model["goals"]) != before:
            self._save_user_model()
            return True
        return False

    # ─── Episodic ─────────────────────────────────────────────────────────────

    def record_episode(self, role: str, text: str,
                       importance: float = 1.0,
                       tags: Optional[List[str]] = None) -> Optional[str]:
        """Store a timestamped event. Episodic = the diary of what happened."""
        text = (text or "").strip()
        if not text:
            return None
        speaker = "Aryan" if role == "user" else "Deep"
        now = datetime.now()
        # Track when Aryan tends to be active (feeds proactive timing).
        if role == "user":
            self.update_user_model(active_hour=now.hour)
        meta = {
            "role": role,
            "speaker": speaker,
            "layer": EPISODIC,
            "when_human": now.strftime("%A %Y-%m-%d %H:%M"),
        }
        if tags:
            meta["tags"] = ",".join(tags)
        return self._safe_store(EPISODIC, text, meta, importance)

    # ─── Semantic ─────────────────────────────────────────────────────────────

    def learn_fact(self, fact: str, importance: float = 1.5,
                   source: str = "conversation") -> Optional[str]:
        """Store a durable fact. Semantic = timeless knowledge, no 'when'."""
        fact = (fact or "").strip()
        if not fact:
            return None
        return self._safe_store(
            SEMANTIC, fact, {"layer": SEMANTIC, "source": source}, importance
        )

    # ─── Procedural ───────────────────────────────────────────────────────────

    def learn_procedure(self, name: str, steps: List[str],
                        importance: float = 1.6) -> Optional[str]:
        """Store a how-to as an ordered step list. Procedural = skills."""
        name = (name or "").strip()
        steps = [s.strip() for s in (steps or []) if s.strip()]
        if not name or not steps:
            return None
        body = f"How to {name}:\n" + "\n".join(
            f"  {i}. {s}" for i, s in enumerate(steps, 1)
        )
        return self._safe_store(
            PROCEDURAL, body,
            {"layer": PROCEDURAL, "name": name, "step_count": len(steps)},
            importance,
        )

    # ─── Layered recall ───────────────────────────────────────────────────────

    def recall_layered(self, query: str, *, k_each: int = 3) -> str:
        """Retrieve from every layer and format ONE prompt-ready context block.

        The layers are labelled so the model knows *what kind* of memory each
        line is — a fact it can rely on vs. a thing that merely happened once.
        """
        query = (query or "").strip()
        sections: List[str] = []

        # User model first — it's the cheapest, highest-signal context.
        um = self._user_model
        um_lines = []
        if um.get("goals"):
            um_lines.append("Active goals: " + "; ".join(um["goals"][:4]))
        if um.get("preferences"):
            um_lines.append("Preferences: " + "; ".join(um["preferences"][:5]))
        if um.get("facts"):
            um_lines.append("Profile: " + "; ".join(um["facts"][:5]))
        if um.get("tone"):
            um_lines.append(f"Preferred tone: {um['tone']}")
        if um_lines:
            sections.append("=== USER MODEL (Aryan) ===\n" + "\n".join(um_lines))

        if query:
            sem = self._recall_layer(SEMANTIC, query, k_each)
            if sem:
                sections.append(
                    "=== SEMANTIC MEMORY (facts you can rely on) ===\n"
                    + "\n".join(f"- {c}" for c in sem)
                )
            proc = self._recall_layer(PROCEDURAL, query, k_each)
            if proc:
                sections.append(
                    "=== PROCEDURAL MEMORY (how-to) ===\n" + "\n\n".join(proc)
                )
            epi = self._recall_layer(EPISODIC, query, k_each)
            if epi:
                sections.append(
                    "=== EPISODIC MEMORY (things that happened) ===\n"
                    + "\n".join(f"- {c}" for c in epi)
                )

        return "\n\n".join(sections)

    def _recall_layer(self, layer: str, query: str, k: int) -> List[str]:
        """Pull top-k contents from a single layer via LTM's typed recall."""
        try:
            results = self._ltm.recall(query, k=k, memory_type=layer)
            out = []
            for r in results:
                content = getattr(r, "content", None) or (
                    r.get("content") if isinstance(r, dict) else None
                )
                if content:
                    out.append(content.strip())
            return out
        except Exception:
            return []

    # ─── Consolidation (episodic -> semantic) ─────────────────────────────────

    def consolidate(self, min_occurrences: int = 3) -> List[str]:
        """Promote recurring episodic content into semantic memory.

        If the same salient phrase shows up across enough episodes, it has
        earned the status of a fact. Returns the list of promoted facts.
        This is the "sleep / memory replay" step — call it periodically.
        """
        promoted: List[str] = []
        try:
            episodes = self._ltm.recall("Aryan", k=80, memory_type=EPISODIC)
        except Exception:
            return promoted

        phrase_counts: Counter = Counter()
        phrase_example: Dict[str, str] = {}
        for ep in episodes:
            content = getattr(ep, "content", "") or ""
            for phrase in self._salient_phrases(content):
                phrase_counts[phrase] += 1
                phrase_example.setdefault(phrase, content.strip())

        for phrase, count in phrase_counts.items():
            if count >= min_occurrences:
                fact = phrase_example[phrase]
                # Only promote if not already known semantically.
                existing = self._recall_layer(SEMANTIC, fact, 1)
                if existing and self._similar(existing[0], fact):
                    continue
                if self.learn_fact(fact, importance=1.4, source="consolidation"):
                    promoted.append(fact)
        return promoted

    @staticmethod
    def _salient_phrases(text: str) -> List[str]:
        """Crude key-phrase extraction: content bigrams minus stopwords."""
        words = [w for w in re.findall(r"[a-zA-Z']+", text.lower())
                 if w not in _STOPWORDS and len(w) > 2]
        return [f"{a} {b}" for a, b in zip(words, words[1:])]

    @staticmethod
    def _similar(a: str, b: str) -> bool:
        sa, sb = set(a.lower().split()), set(b.lower().split())
        if not sa or not sb:
            return False
        return len(sa & sb) / len(sa | sb) > 0.6

    # ─── internals ────────────────────────────────────────────────────────────

    def _safe_store(self, layer: str, content: str, meta: Dict[str, Any],
                    importance: float) -> Optional[str]:
        try:
            return self._ltm.store(
                memory_type=layer,
                content=content,
                metadata=meta,
                importance=importance,
            )
        except Exception:
            return None

    def stats(self) -> Dict[str, Any]:
        out = {"user_model": {
            "goals": len(self._user_model.get("goals", [])),
            "preferences": len(self._user_model.get("preferences", [])),
            "facts": len(self._user_model.get("facts", [])),
        }}
        for layer in (EPISODIC, SEMANTIC, PROCEDURAL):
            try:
                out[layer] = len(self._ltm.recall(" ", k=200, memory_type=layer))
            except Exception:
                out[layer] = 0
        return out


# ─── standalone smoke test ────────────────────────────────────────────────────
if __name__ == "__main__":
    import tempfile
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.ltm_memory import LongTermMemory

    tmp = tempfile.mkdtemp()
    ltm = LongTermMemory(data_dir=str(Path(tmp) / "ltm"))
    mem = CognitiveMemory(ltm, data_dir=Path(tmp) / "cog")

    print("storing across layers...")
    mem.learn_fact("Aryan's main project is DEEP, a JARVIS-tier assistant.", 1.7)
    mem.learn_procedure("restart DEEP",
                        ["kill the python process on port 7768",
                         "run start_deep.bat from the DEEP folder"])
    for _ in range(4):
        mem.record_episode("user", "How do I restart the DEEP server on port 7768?")
    mem.update_user_model(goals=["ship the proactive layer"],
                          preferences=["concise replies", "call me Aryan not sir"])

    print("\n--- recall_layered('restart the server') ---")
    print(mem.recall_layered("restart the server"))

    print("\n--- consolidate() ---")
    print("promoted:", mem.consolidate(min_occurrences=3))

    print("\n--- stats ---")
    print(json.dumps(mem.stats(), indent=2))
    print("\nOK")
