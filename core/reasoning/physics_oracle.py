"""
core/reasoning/physics_oracle.py

Physics ground-truth oracle (knowledge-base element: physics).

Two layers:
  1. CONSTANTS  — exact CODATA values via scipy.constants (no hallucination).
  2. FORMULAS   — a curated library of key laws across eras:
                  Ancient.P  (Archimedes, levers, buoyancy)
                  Classical.P (Newton, thermodynamics, EM, waves, fluids)
                  Modern.P   (relativity, quantum, nuclear)
     Each formula is SymPy-parseable, so DEEP can both cite AND compute with it.

Exposed as an LLM oracle (verified facts injected into context) + REST endpoints.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List

try:
    import scipy.constants as _sc
    SCIPY_OK = True
except Exception:  # pragma: no cover
    SCIPY_OK = False


# ── Curated physical constants (friendly name → scipy lookup / literal) ──────
def _const(value, unit, symbol):
    return {"value": value, "unit": unit, "symbol": symbol, "source": "CODATA via scipy.constants"}


CONSTANTS: Dict[str, Dict[str, Any]] = {}
if SCIPY_OK:
    CONSTANTS = {
        "speed of light":        _const(_sc.c, "m/s", "c"),
        "planck constant":       _const(_sc.h, "J·s", "h"),
        "reduced planck constant": _const(_sc.hbar, "J·s", "ħ"),
        "gravitational constant": _const(_sc.G, "m³·kg⁻¹·s⁻²", "G"),
        "elementary charge":     _const(_sc.e, "C", "e"),
        "electron mass":         _const(_sc.m_e, "kg", "mₑ"),
        "proton mass":           _const(_sc.m_p, "kg", "m_p"),
        "neutron mass":          _const(_sc.m_n, "kg", "m_n"),
        "avogadro constant":     _const(_sc.N_A, "mol⁻¹", "N_A"),
        "boltzmann constant":    _const(_sc.k, "J/K", "k_B"),
        "gas constant":          _const(_sc.R, "J·mol⁻¹·K⁻¹", "R"),
        "vacuum permittivity":   _const(_sc.epsilon_0, "F/m", "ε₀"),
        "vacuum permeability":   _const(_sc.mu_0, "N/A²", "μ₀"),
        "fine structure constant": _const(_sc.alpha, "dimensionless", "α"),
        "stefan boltzmann constant": _const(_sc.Stefan_Boltzmann, "W·m⁻²·K⁻⁴", "σ"),
        "rydberg constant":      _const(_sc.Rydberg, "m⁻¹", "R∞"),
        "standard gravity":      _const(_sc.g, "m/s²", "g"),
        "atomic mass unit":      _const(_sc.atomic_mass, "kg", "u"),
        "faraday constant":      _const(_sc.physical_constants["Faraday constant"][0], "C/mol", "F"),
    }


# ── Curated formula library across eras ─────────────────────────────────────
# era ∈ {ancient, classical, modern}
FORMULAS: List[Dict[str, Any]] = [
    # Ancient.P
    {"name": "Archimedes' principle", "era": "ancient", "domain": "fluids",
     "formula": "F_b = rho * g * V", "vars": {"F_b": "buoyant force (N)", "rho": "fluid density (kg/m³)", "g": "gravity (m/s²)", "V": "displaced volume (m³)"},
     "desc": "Upthrust equals the weight of displaced fluid (Archimedes, ~250 BCE)."},
    {"name": "Law of the lever", "era": "ancient", "domain": "mechanics",
     "formula": "F1 * d1 = F2 * d2", "vars": {"F": "force (N)", "d": "distance from fulcrum (m)"},
     "desc": "Mechanical advantage of the lever (Archimedes)."},
    # Classical.P
    {"name": "Newton's second law", "era": "classical", "domain": "mechanics",
     "formula": "F = m * a", "vars": {"F": "force (N)", "m": "mass (kg)", "a": "acceleration (m/s²)"},
     "desc": "Force equals mass times acceleration."},
    {"name": "Newton's law of gravitation", "era": "classical", "domain": "gravity",
     "formula": "F = G * m1 * m2 / r**2", "vars": {"G": "gravitational constant", "m1": "mass 1 (kg)", "m2": "mass 2 (kg)", "r": "separation (m)"},
     "desc": "Universal gravitation between two masses."},
    {"name": "Kinetic energy", "era": "classical", "domain": "energy",
     "formula": "KE = (1/2) * m * v**2", "vars": {"m": "mass (kg)", "v": "speed (m/s)"},
     "desc": "Energy of motion."},
    {"name": "Work-energy", "era": "classical", "domain": "energy",
     "formula": "W = F * d", "vars": {"F": "force (N)", "d": "displacement (m)"}, "desc": "Work done by a constant force."},
    {"name": "Momentum", "era": "classical", "domain": "mechanics",
     "formula": "p = m * v", "vars": {"m": "mass (kg)", "v": "velocity (m/s)"}, "desc": "Linear momentum."},
    {"name": "Ohm's law", "era": "classical", "domain": "electromagnetism",
     "formula": "V = I * R", "vars": {"V": "voltage (V)", "I": "current (A)", "R": "resistance (Ω)"}, "desc": "Voltage across a resistor."},
    {"name": "Coulomb's law", "era": "classical", "domain": "electromagnetism",
     "formula": "F = k * q1 * q2 / r**2", "vars": {"k": "Coulomb constant", "q": "charge (C)", "r": "separation (m)"}, "desc": "Electrostatic force."},
    {"name": "Ideal gas law", "era": "classical", "domain": "thermodynamics",
     "formula": "P * V = n * R * T", "vars": {"P": "pressure (Pa)", "V": "volume (m³)", "n": "moles", "R": "gas constant", "T": "temperature (K)"}, "desc": "Equation of state for an ideal gas."},
    {"name": "Bernoulli's equation", "era": "classical", "domain": "fluids",
     "formula": "P + (1/2)*rho*v**2 + rho*g*h = const", "vars": {"P": "pressure (Pa)", "rho": "density (kg/m³)", "v": "speed (m/s)", "h": "height (m)"}, "desc": "Conservation of energy in fluid flow."},
    {"name": "Wave speed", "era": "classical", "domain": "waves",
     "formula": "v = f * lambda", "vars": {"v": "wave speed (m/s)", "f": "frequency (Hz)", "lambda": "wavelength (m)"}, "desc": "Relation between speed, frequency, wavelength."},
    # Modern.P
    {"name": "Mass-energy equivalence", "era": "modern", "domain": "relativity",
     "formula": "E = m * c**2", "vars": {"E": "energy (J)", "m": "mass (kg)", "c": "speed of light"}, "desc": "Einstein's mass-energy equivalence (1905)."},
    {"name": "Relativistic time dilation", "era": "modern", "domain": "relativity",
     "formula": "t = t0 / sqrt(1 - v**2/c**2)", "vars": {"t": "dilated time", "t0": "proper time", "v": "relative speed", "c": "speed of light"}, "desc": "Moving clocks run slow."},
    {"name": "Photon energy", "era": "modern", "domain": "quantum",
     "formula": "E = h * f", "vars": {"E": "energy (J)", "h": "Planck constant", "f": "frequency (Hz)"}, "desc": "Energy of a photon (Planck/Einstein)."},
    {"name": "de Broglie wavelength", "era": "modern", "domain": "quantum",
     "formula": "lambda = h / p", "vars": {"lambda": "wavelength (m)", "h": "Planck constant", "p": "momentum (kg·m/s)"}, "desc": "Matter waves."},
    {"name": "Heisenberg uncertainty", "era": "modern", "domain": "quantum",
     "formula": "dx * dp >= hbar / 2", "vars": {"dx": "position uncertainty", "dp": "momentum uncertainty", "hbar": "reduced Planck"}, "desc": "Fundamental limit on simultaneous knowledge of position and momentum."},
    {"name": "Mass-energy of a photon (E=pc)", "era": "modern", "domain": "relativity",
     "formula": "E = p * c", "vars": {"E": "energy (J)", "p": "momentum", "c": "speed of light"}, "desc": "Energy-momentum for massless particles."},
]


def lookup_constant(query: str) -> Optional[Dict[str, Any]]:
    if not SCIPY_OK or not query:
        return None
    q = query.lower().strip()
    if q in CONSTANTS:
        return {"name": q, **CONSTANTS[q]}
    for name, data in CONSTANTS.items():
        if name in q or q in name:
            return {"name": name, **data}
    return None


_STOP = {"of", "a", "the", "law", "laws", "formula", "equation", "for", "s",
         "and", "principle", "to", "in", "is", "what", "explain"}

# Direct aliases → formula name (for queries that share no words with the name).
_FORMULA_ALIAS = {
    "e=mc": "Mass-energy equivalence", "e = mc": "Mass-energy equivalence",
    "f=ma": "Newton's second law", "f = ma": "Newton's second law",
    "pv=nrt": "Ideal gas law", "v=ir": "Ohm's law",
    "time dilation": "Relativistic time dilation",
}


def _sig_words(name: str) -> set:
    return {w for w in name.lower().replace("'", "").split() if w not in _STOP and len(w) > 2}


def lookup_formula(query: str) -> Optional[Dict[str, Any]]:
    if not query:
        return None
    q = query.lower()
    # 1) alias shortcut
    for alias, target in _FORMULA_ALIAS.items():
        if alias in q:
            for f in FORMULAS:
                if f["name"] == target:
                    return f
    # 2) full-name substring
    for f in FORMULAS:
        if f["name"].lower() in q:
            return f
    # 3) score by significant-word overlap (ignore stopwords)
    qwords = {w.strip("?.!,") for w in q.split()}
    best, best_score = None, 0
    for f in FORMULAS:
        sig = _sig_words(f["name"])
        if not sig:
            continue
        score = len(sig & qwords)
        # require matching a majority of the name's significant words
        if score >= max(1, len(sig) - 1) and score > best_score:
            best, best_score = f, score
    return best


_PHYS_CUES = ("constant", "speed of light", "planck", "gravitational", "boltzmann",
              "avogadro", "permittivity", "permeability", "newton", "law of",
              "energy", "momentum", "relativity", "quantum", "wavelength",
              "uncertainty", "archimedes", "bernoulli", "ohm", "coulomb",
              "ideal gas", "formula for", "equation for", "e=mc")


def detect(text: str) -> Optional[Dict[str, Any]]:
    """Return a verified constant or formula if the text clearly asks for one."""
    if not text:
        return None
    low = text.lower()
    if not any(c in low for c in _PHYS_CUES):
        return None
    c = lookup_constant(text)
    if c:
        return {"kind": "constant", **c}
    f = lookup_formula(text)
    if f:
        return {"kind": "formula", **f}
    return None


def verified_context(data: Dict[str, Any]) -> str:
    if data.get("kind") == "constant":
        return ("\n=== VERIFIED PHYSICAL CONSTANT (CODATA — state exactly) ===\n"
                f"{data['name']} ({data['symbol']}) = {data['value']} {data['unit']}\n")
    if data.get("kind") == "formula":
        vlines = "; ".join(f"{k} = {v}" for k, v in data.get("vars", {}).items())
        return ("\n=== VERIFIED PHYSICS FORMULA (curated — state exactly) ===\n"
                f"{data['name']} [{data['era']}.P · {data['domain']}]: {data['formula']}\n"
                f"where {vlines}\n{data.get('desc','')}\n")
    return ""
