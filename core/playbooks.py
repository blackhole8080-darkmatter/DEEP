"""Response playbooks, keyed by the ATT&CK techniques DEEP already matches.

``alert_correlator`` tells you an anomaly looks like ``T1071.001``. That is a
diagnosis with no next step: knowing the technique's name is not knowing what
to do about it at 03:00. This module closes that gap by indexing a corpus of
procedural security playbooks and answering the question the console could not
answer before — *given this technique, what do I actually do?*

The corpus format is Anthropic's Skills layout — ``<root>/skills/<slug>/SKILL.md``,
YAML frontmatter over a Markdown body — which
`mukul975/Anthropic-Cybersecurity-Skills <https://github.com/mukul975/Anthropic-Cybersecurity-Skills>`_
publishes under Apache-2.0 with ~800 skills already mapped to MITRE ATT&CK,
NIST CSF, ATLAS, D3FEND, AI RMF and F3. DEEP reads that layout rather than
vendoring anyone's corpus: ``make playbooks`` fetches it into ``data/``, and any
directory following the same convention works just as well.

Two details carry most of the value:

* **Sub-technique matching runs both ways.** A playbook tagged ``T1071`` is the
  right answer for an alert on ``T1071.001``, and a playbook tagged
  ``T1071.004`` is worth showing for a bare ``T1071``. Exact matches rank first.
* **Absent is not broken.** With no corpus installed every call returns an empty
  result and ``status()`` explains how to install one. A fresh clone must not
  see a stack trace where a playbook would be.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_ROOT = "data/playbooks"
INSTALL_HINT = (
    "no playbooks installed — run `make playbooks` (clones "
    "github.com/mukul975/Anthropic-Cybersecurity-Skills into data/playbooks), "
    "or point DEEP_PLAYBOOKS_DIR at any Anthropic-Skills-format corpus"
)

#: Frontmatter keys that carry framework references, normalised to a short name.
_FRAMEWORK_KEYS = {
    "mitre_attack": "attack",
    "atlas_techniques": "atlas",
    "d3fend_techniques": "d3fend",
    "mitre_f3": "f3",
    "nist_csf": "nist_csf",
    "nist_ai_rmf": "nist_ai_rmf",
}

_TECHNIQUE_RE = re.compile(r"^T\d{4}(\.\d{3})?$", re.IGNORECASE)


def normalise_technique(value: Any) -> str:
    """`t1071.001` -> `T1071.001`. Returns "" for anything that isn't an id."""
    text = str(value or "").strip().upper()
    return text if _TECHNIQUE_RE.match(text) else ""


def technique_base(technique: str) -> str:
    """`T1071.001` -> `T1071`. A sub-technique's parent covers it."""
    return technique.split(".", 1)[0]


@dataclass(slots=True)
class Playbook:
    """One procedure, indexed by what it covers."""

    name: str
    description: str
    path: Path
    domain: str = ""
    subdomain: str = ""
    tags: List[str] = field(default_factory=list)
    frameworks: Dict[str, List[str]] = field(default_factory=dict)
    version: str = ""
    license: str = ""

    @property
    def techniques(self) -> List[str]:
        return self.frameworks.get("attack", [])

    def body(self) -> str:
        """The Markdown procedure itself, read on demand.

        Bodies are several KB each and a corpus runs to hundreds of files, so
        the index holds metadata only — nobody wants 800 procedures resident to
        answer "which ones mention T1071".
        """
        try:
            text = self.path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.debug("playbook %s unreadable: %s", self.name, exc)
            return ""
        return _strip_frontmatter(text).strip()

    def sections(self) -> Dict[str, str]:
        """Body split on its H2 headings — 'Workflow', 'Prerequisites', …"""
        out: Dict[str, str] = {}
        current = ""
        buffer: List[str] = []
        for line in self.body().splitlines():
            if line.startswith("## "):
                if current:
                    out[current] = "\n".join(buffer).strip()
                current = line[3:].strip()
                buffer = []
            elif current:
                buffer.append(line)
        if current:
            out[current] = "\n".join(buffer).strip()
        return out

    def to_dict(self, *, include_body: bool = False) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "subdomain": self.subdomain,
            "tags": self.tags,
            "frameworks": self.frameworks,
            "techniques": self.techniques,
            "version": self.version,
            "license": self.license,
        }
        if include_body:
            data["sections"] = self.sections()
        return data


class PlaybookLibrary:
    """Indexes a playbook corpus and answers lookups against it."""

    def __init__(self, root: Optional[str | Path] = None) -> None:
        self._root = Path(root or os.environ.get("DEEP_PLAYBOOKS_DIR") or DEFAULT_ROOT)
        self._by_name: Dict[str, Playbook] = {}
        self._by_technique: Dict[str, List[str]] = {}   # exact id -> playbook names
        self._loaded = False
        self._errors: List[str] = []

    @property
    def root(self) -> Path:
        return self._root

    @property
    def installed(self) -> bool:
        return self._skills_dir() is not None

    def _skills_dir(self) -> Optional[Path]:
        """Accept either the repo root or the skills directory itself."""
        for candidate in (self._root / "skills", self._root):
            if candidate.is_dir() and any(candidate.glob("*/SKILL.md")):
                return candidate
        return None

    # ── indexing ─────────────────────────────────────────────────────────────

    def load(self, *, force: bool = False) -> int:
        """Index the corpus. Returns the number of playbooks found."""
        if self._loaded and not force:
            return len(self._by_name)
        self._by_name.clear()
        self._by_technique.clear()
        self._errors.clear()
        self._loaded = True

        skills = self._skills_dir()
        if skills is None:
            return 0

        for skill_file in sorted(skills.glob("*/SKILL.md")):
            playbook = self._parse(skill_file)
            if playbook is None:
                continue
            self._by_name[playbook.name] = playbook
            for technique in playbook.techniques:
                self._by_technique.setdefault(technique, []).append(playbook.name)

        logger.info("indexed %d playbooks from %s", len(self._by_name), skills)
        return len(self._by_name)

    def _parse(self, path: Path) -> Optional[Playbook]:
        try:
            head = _read_frontmatter(path)
        except OSError as exc:
            self._errors.append(f"{path.name}: {exc}")
            return None
        if not head:
            self._errors.append(f"{path.parent.name}: no frontmatter")
            return None

        name = str(head.get("name") or path.parent.name).strip()
        if not name:
            return None

        frameworks: Dict[str, List[str]] = {}
        borrowed_attack: List[str] = []
        for key, short in _FRAMEWORK_KEYS.items():
            values = head.get(key)
            if not values:
                continue
            ids, attack_ids = _flatten_framework(values)
            if short == "attack":
                ids = [t for t in (normalise_technique(i) for i in ids) if t]
            if ids:
                frameworks.setdefault(short, []).extend(ids)
            borrowed_attack.extend(attack_ids)

        # F3's technique table cites ATT&CK ids alongside its own (each entry
        # names its `source`), so folding those into the ATT&CK index is
        # coverage the corpus already paid for and we would otherwise drop.
        if borrowed_attack:
            bucket = frameworks.setdefault("attack", [])
            for candidate in borrowed_attack:
                technique = normalise_technique(candidate)
                if technique and technique not in bucket:
                    bucket.append(technique)

        tags = head.get("tags") or []
        return Playbook(
            name=name,
            description=str(head.get("description") or "").strip(),
            path=path,
            domain=str(head.get("domain") or "").strip(),
            subdomain=str(head.get("subdomain") or "").strip(),
            tags=[str(t).strip() for t in tags if str(t).strip()],
            frameworks=frameworks,
            version=str(head.get("version") or "").strip(),
            license=str(head.get("license") or "").strip(),
        )

    # ── lookups ──────────────────────────────────────────────────────────────

    def for_technique(self, technique: str, limit: int = 5) -> List[Playbook]:
        """Playbooks covering an ATT&CK technique, exact matches first.

        Matching runs in both directions across the sub-technique boundary: the
        correlator emits whatever the enrichment produced, and refusing to show
        the ``T1071`` procedure for a ``T1071.001`` alert would be pedantry at
        the exact moment someone needs an answer.
        """
        self.load()
        wanted = normalise_technique(technique)
        if not wanted:
            return []
        base = technique_base(wanted)

        exact = self._rank(self._by_technique.get(wanted, []), wanted)
        related_names: List[str] = []
        for indexed, names in self._by_technique.items():
            if indexed == wanted:
                continue
            if indexed == base or technique_base(indexed) == base:
                related_names.extend(names)
        related = self._rank(related_names, base)

        ordered: List[str] = []
        for name in exact + related:
            if name not in ordered:
                ordered.append(name)
        return [self._by_name[n] for n in ordered[:limit] if n in self._by_name]

    def _rank(self, names: List[str], technique: str) -> List[str]:
        """Order candidates so the most on-topic procedure comes first.

        Insertion order is alphabetical by filename, which put broad survey
        playbooks ahead of the one that is actually about the technique. Two
        signals fix that, both read straight off the corpus: a technique listed
        *first* in a playbook's mapping is that playbook's subject rather than
        an aside, and a playbook covering fewer techniques is more targeted.
        """
        def key(name: str):
            playbook = self._by_name.get(name)
            if playbook is None:
                return (99, 99, name)
            techniques = playbook.techniques
            try:
                position = techniques.index(technique)
            except ValueError:
                position = next(
                    (i for i, t in enumerate(techniques)
                     if technique_base(t) == technique_base(technique)),
                    99,
                )
            return (position, len(techniques), playbook.name)

        return sorted(dict.fromkeys(names), key=key)

    def for_techniques(self, techniques: List[str], limit: int = 5) -> List[Playbook]:
        """Union across several techniques — one alert usually matches a few."""
        self.load()
        seen: Dict[str, Playbook] = {}
        for technique in techniques:
            for playbook in self.for_technique(technique, limit=limit):
                seen.setdefault(playbook.name, playbook)
        return list(seen.values())[:limit]

    def get(self, name: str) -> Optional[Playbook]:
        self.load()
        key = str(name or "").strip()
        if key in self._by_name:
            return self._by_name[key]
        # Tolerate a near-miss slug rather than making the operator retype it.
        lowered = key.lower().replace(" ", "-")
        for candidate, playbook in self._by_name.items():
            if candidate.lower() == lowered:
                return playbook
        return None

    def search(self, query: str, limit: int = 10) -> List[Playbook]:
        """Substring match over name, description and tags, best match first."""
        self.load()
        needle = str(query or "").strip().lower()
        if not needle:
            return []
        scored: List[tuple[int, Playbook]] = []
        for playbook in self._by_name.values():
            score = 0
            if needle in playbook.name.lower():
                score += 3
            if needle in " ".join(playbook.tags).lower():
                score += 2
            if needle in playbook.description.lower():
                score += 1
            if score:
                scored.append((score, playbook))
        scored.sort(key=lambda pair: (-pair[0], pair[1].name))
        return [playbook for _, playbook in scored[:limit]]

    # ── introspection ────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        self.load()
        by_framework = {
            short: sum(1 for p in self._by_name.values() if p.frameworks.get(short))
            for short in sorted(set(_FRAMEWORK_KEYS.values()))
        }
        out: Dict[str, Any] = {
            "installed": self.installed,
            "root": str(self._root),
            "playbooks": len(self._by_name),
            "techniques_covered": len(self._by_technique),
            "by_framework": by_framework,
            "parse_errors": self._errors[:10],
        }
        if not self.installed:
            out["hint"] = INSTALL_HINT
        return out


# ── frontmatter ──────────────────────────────────────────────────────────────


def _flatten_framework(value: Any) -> tuple[List[str], List[str]]:
    """Framework ids from one frontmatter value, as ``(own_ids, attack_ids)``.

    Most keys are a plain list of ids. F3 is a nested table — version, tactics,
    and a ``techniques`` list whose entries each declare their ``source`` — and
    stringifying that whole dict, as a naive reader does, dumps several hundred
    characters of YAML into the model's context in place of an id.
    """
    if isinstance(value, dict):
        own: List[str] = []
        attack: List[str] = []
        for entry in value.get("techniques") or []:
            if not isinstance(entry, dict):
                continue
            ident = str(entry.get("id") or "").strip()
            if not ident:
                continue
            if str(entry.get("source") or "").strip().lower() == "attack":
                attack.append(ident)
            else:
                own.append(ident)
        return own, attack

    items = value if isinstance(value, list) else [value]
    return [str(v).strip() for v in items if str(v).strip()], []


def _read_frontmatter(path: Path) -> Dict[str, Any]:
    """Parse the leading `---` YAML block. Never raises on bad YAML."""
    text = path.read_text(encoding="utf-8", errors="replace")
    block = _frontmatter_block(text)
    if not block:
        return {}
    try:
        import yaml

        data = yaml.safe_load(block)
    except Exception as exc:  # noqa: BLE001 - one malformed skill must not stop the index
        logger.debug("frontmatter unparseable in %s: %s", path, exc)
        return {}
    return data if isinstance(data, dict) else {}


def _frontmatter_block(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[1:i])
    return ""


def _strip_frontmatter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[i + 1:])
    return text


_shared_library: Optional[PlaybookLibrary] = None


def shared_playbooks() -> PlaybookLibrary:
    global _shared_library
    if _shared_library is None:
        _shared_library = PlaybookLibrary()
    return _shared_library
