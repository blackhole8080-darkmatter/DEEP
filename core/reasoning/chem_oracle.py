"""
core/reasoning/chem_oracle.py

Chemistry ground-truth oracle (knowledge-base element #1: periodic table).

Wraps the `mendeleev` dataset so DEEP can LOOK UP exact element metadata instead
of recalling (and hallucinating) it. Every answer is sourced from a curated
scientific dataset — atomic mass, electron configuration, electronegativity,
ionization energies, phase points, discovery, etc.

Used both as an LLM tool (verified facts injected into context) and to power a
visual periodic table in the UI.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List

try:
    from mendeleev import element as _element
    from mendeleev.db import get_session  # noqa: F401  (ensures package importable)
    MENDELEEV_OK = True
except Exception:  # pragma: no cover
    MENDELEEV_OK = False


# Category → colour family for the visual table (token-driven on the frontend).
SERIES_CLASS = {
    "Nonmetals": "nonmetal",
    "Noble gases": "noble",
    "Alkali metals": "alkali",
    "Alkaline earth metals": "alkaline",
    "Metalloids": "metalloid",
    "Halogens": "halogen",
    "Poor metals": "post-transition",
    "Transition metals": "transition",
    "Lanthanides": "lanthanide",
    "Actinides": "actinide",
}


def _get(e, name):
    try:
        v = getattr(e, name)
        return v() if callable(v) else v
    except Exception:
        return None


def lookup(query: str | int) -> Optional[Dict[str, Any]]:
    """Resolve an element by symbol ('Fe'), name ('iron'), or atomic number (26)."""
    if not MENDELEEV_OK or query is None:
        return None
    try:
        q = query
        if isinstance(q, str):
            q = q.strip()
            if q.isdigit():
                q = int(q)
            else:
                q = q.capitalize() if len(q) <= 2 else q.title()
        e = _element(q)
    except Exception:
        return None

    series = _get(e, "series")
    ion = _get(e, "ionenergies") or {}
    first_ion = ion.get(1) if isinstance(ion, dict) else None
    return {
        "atomic_number": _get(e, "atomic_number"),
        "symbol": _get(e, "symbol"),
        "name": _get(e, "name"),
        "atomic_weight": _get(e, "atomic_weight"),
        "electron_configuration": _get(e, "econf"),
        "electronegativity": _get(e, "electronegativity"),
        "first_ionization_eV": round(first_ion, 4) if first_ion else None,
        "oxidation_states": _get(e, "oxidation_states"),
        "melting_point_K": _get(e, "melting_point"),
        "boiling_point_K": _get(e, "boiling_point"),
        "density_g_cm3": _get(e, "density"),
        "group": _get(e, "group_id"),
        "period": _get(e, "period"),
        "block": _get(e, "block"),
        "series": series,
        "category": SERIES_CLASS.get(series, "other"),
        "cas": _get(e, "cas"),
        "discoverers": _get(e, "discoverers"),
        "discovery_year": _get(e, "discovery_year"),
        "source": "mendeleev (curated dataset)",
    }


_TABLE_CACHE: List[Dict[str, Any]] = []


def table() -> List[Dict[str, Any]]:
    """Minimal data for all 118 elements, for the visual periodic table.

    Cached after first build — the 118 synchronous mendeleev/SQLAlchemy lookups
    are expensive and must not run on the event loop more than once.
    """
    global _TABLE_CACHE
    if _TABLE_CACHE:
        return _TABLE_CACHE
    if not MENDELEEV_OK:
        return []
    out = []
    for z in range(1, 119):
        try:
            e = _element(z)
            series = _get(e, "series")
            out.append({
                "atomic_number": z,
                "symbol": _get(e, "symbol"),
                "name": _get(e, "name"),
                "atomic_weight": _get(e, "atomic_weight"),
                "group": _get(e, "group_id"),
                "period": _get(e, "period"),
                "category": SERIES_CLASS.get(series, "other"),
                "series": series,
            })
        except Exception:
            continue
    _TABLE_CACHE = out
    return out


_CHEM_CUES = (
    "atomic", "element", "electron", "electroneg", "oxidation", "periodic",
    "isotope", "melting point", "boiling point", "density of", "atomic mass",
    "atomic number", "atomic weight", "valence", "noble gas", "ionization",
    "configuration", "proton", "neutron",
)

_NAME_CACHE: Dict[str, int] = {}


def _name_index() -> Dict[str, int]:
    """lowercase element name -> atomic number (built once)."""
    global _NAME_CACHE
    if _NAME_CACHE or not MENDELEEV_OK:
        return _NAME_CACHE
    for row in table():
        if row.get("name"):
            _NAME_CACHE[row["name"].lower()] = row["atomic_number"]
    return _NAME_CACHE


def detect(text: str) -> Optional[Dict[str, Any]]:
    """
    If the text is clearly a question about a chemical element, return its
    verified data. Requires a chemistry cue word + an element name to avoid
    firing on ordinary words (e.g. 'I' or 'He' in normal sentences).
    """
    if not MENDELEEV_OK or not text:
        return None
    low = text.lower()
    if not any(c in low for c in _CHEM_CUES):
        return None
    # Normalise: strip punctuation to plain words so trailing "tungsten?" still
    # matches the element name "tungsten".
    import re as _re
    words = set(_re.findall(r"[a-z]+", low))
    for name, z in _name_index().items():
        if name in words:                       # full single-word element names
            return lookup(z)
    return None


def verified_context(data: Dict[str, Any]) -> str:
    """Format an element lookup as a faithful context block for the LLM."""
    lines = [f"{k}: {v}" for k, v in data.items() if v is not None]
    return ("\n=== VERIFIED ELEMENT DATA (from curated periodic-table dataset — "
            "state these facts exactly) ===\n" + "\n".join(lines) + "\n")
