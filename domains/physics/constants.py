# domains/physics/constants.py
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class PhysicsConstant:
    name: str
    value: float
    uncertainty: str
    unit: str
    symbol: str
    latex: str

    # ── Compatibility aliases ──────────────────────────────────────────────────
    @property
    def description(self) -> str:
        """Alias for name — used by engine.py legacy lookups."""
        return self.name

    @property
    def latex_symbol(self) -> str:
        """Alias for latex — used by engine.py get_constant fallback."""
        return self.latex

CONSTANTS: Dict[str, PhysicsConstant] = {
    "c": PhysicsConstant(
        name="Speed of light in vacuum",
        value=299792458.0,
        uncertainty="exact",
        unit="m s^-1",
        symbol="c",
        latex="c"
    ),
    "h": PhysicsConstant(
        name="Planck constant",
        value=6.62607015e-34,
        uncertainty="exact",
        unit="J s",
        symbol="h",
        latex="h"
    ),
    "hbar": PhysicsConstant(
        name="Reduced Planck constant",
        value=1.054571817e-34,
        uncertainty="exact",
        unit="J s",
        symbol="hbar",
        latex="\\hbar"
    ),
    "e": PhysicsConstant(
        name="Elementary charge",
        value=1.602176634e-19,
        uncertainty="exact",
        unit="C",
        symbol="e",
        latex="e"
    ),
    "m_e": PhysicsConstant(
        name="Electron mass",
        value=9.1093837015e-31,
        uncertainty="0.0000000028e-31",
        unit="kg",
        symbol="m_e",
        latex="m_e"
    ),
    "m_p": PhysicsConstant(
        name="Proton mass",
        value=1.67262192369e-27,
        uncertainty="0.00000000051e-27",
        unit="kg",
        symbol="m_p",
        latex="m_p"
    ),
    "g": PhysicsConstant(
        name="Standard acceleration of gravity",
        value=9.80665,
        uncertainty="exact",
        unit="m s^-2",
        symbol="g",
        latex="g"
    ),
    "G": PhysicsConstant(
        name="Newtonian constant of gravitation",
        value=6.6743e-11,
        uncertainty="0.00015e-11",
        unit="m^3 kg^-1 s^-2",
        symbol="G",
        latex="G"
    ),
    "epsilon_0": PhysicsConstant(
        name="Vacuum electric permittivity",
        value=8.8541878128e-12,
        uncertainty="0.0000000015e-12",
        unit="F m^-1",
        symbol="epsilon_0",
        latex="\\varepsilon_0"
    ),
    "mu_0": PhysicsConstant(
        name="Vacuum magnetic permeability",
        value=1.25663706212e-6,
        uncertainty="0.00000000019e-6",
        unit="N A^-2",
        symbol="mu_0",
        latex="\\mu_0"
    ),
    "k_B": PhysicsConstant(
        name="Boltzmann constant",
        value=1.380649e-23,
        uncertainty="exact",
        unit="J K^-1",
        symbol="k_B",
        latex="k_B"
    ),
    "R": PhysicsConstant(
        name="Molar gas constant",
        value=8.314462618,
        uncertainty="exact",
        unit="J mol^-1 K^-1",
        symbol="R",
        latex="R"
    ),
    "N_A": PhysicsConstant(
        name="Avogadro constant",
        value=6.02214076e23,
        uncertainty="exact",
        unit="mol^-1",
        symbol="N_A",
        latex="N_A"
    )
}

# ── Aliases for backward-compat (engine.py uses CONSTANTS_DB) ─────────────────
CONSTANTS_DB: Dict[str, PhysicsConstant] = CONSTANTS

# Long-name lookup keys used by engine.py _inject_constants
_LONG_KEYS = {
    "elementary_charge": "e",
    "electron_mass": "m_e",
    "vacuum_permittivity": "epsilon_0",
    "vacuum_permeability": "mu_0",
    "boltzmann_constant": "k_B",
    "planck_constant": "h",
    "speed_of_light": "c",
    "proton_mass": "m_p",
    "reduced_planck": "hbar",
}
# Inject long keys into CONSTANTS_DB so engine.py lookups work
for _long, _short in _LONG_KEYS.items():
    if _long not in CONSTANTS_DB and _short in CONSTANTS:
        CONSTANTS_DB[_long] = CONSTANTS[_short]

def get_constant(name: str) -> Optional[PhysicsConstant]:
    """Retrieve physical constant by symbol or common alias."""
    name_clean = name.strip().replace(" ", "_").lower()
    
    # Map common aliases to symbols
    aliases = {
        "speed_of_light": "c",
        "planck": "h",
        "reduced_planck": "hbar",
        "hbar": "hbar",
        "electron_charge": "e",
        "elementary_charge": "e",
        "electron_mass": "m_e",
        "proton_mass": "m_p",
        "gravity": "g",
        "gravitational_constant": "G",
        "permittivity": "epsilon_0",
        "permeability": "mu_0",
        "boltzmann": "k_B",
        "gas_constant": "R",
        "avogadro": "N_A"
    }
    
    symbol = aliases.get(name_clean, name_clean)
    
    # Direct symbol match (case-sensitive for things like G vs g)
    if name in CONSTANTS:
        return CONSTANTS[name]
        
    # Case-insensitive check
    for key, constant in CONSTANTS.items():
        if key.lower() == symbol:
            return constant
            
    return None
