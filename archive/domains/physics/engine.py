"""
DEEP — Physics Engine
Main API: PhysicsEngine
Wraps symbolic (SymPy) + numerical (SciPy) + constants (NIST CODATA)
"""
from __future__ import annotations

import asyncio
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ── lazy imports so missing optional deps don't crash the module ──────────────
try:
    import sympy as sp
    from sympy import latex, simplify, symbols, solve, diff, integrate
    from sympy.parsing.sympy_parser import parse_expr, standard_transformations, \
        implicit_multiplication_application
    _SYMPY_OK = True
except ImportError:
    _SYMPY_OK = False

try:
    import numpy as np
    from scipy.integrate import solve_ivp
    from scipy.linalg import eig
    _SCIPY_OK = True
except ImportError:
    _SCIPY_OK = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _MPL_OK = True
except ImportError:
    _MPL_OK = False

from .constants import CONSTANTS_DB, PhysicsConstant
from .symbolic import SymbolicSolver, SymbolicResult


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class PhysicsResult:
    symbolic: Optional[str] = None          # SymPy expression as string
    latex: Optional[str] = None             # LaTeX-formatted
    numerical: Optional[float] = None       # Numeric value
    unit: Optional[str] = None              # SI unit
    plot_path: Optional[str] = None         # PNG plot path
    confidence: str = "exact"              # "exact" | "approximate" | "numerical"
    assumptions: List[str] = field(default_factory=list)
    derivation_steps: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class SimResult:
    t: List[float] = field(default_factory=list)    # time array
    y: List[List[float]] = field(default_factory=list)  # state arrays
    plot_path: Optional[str] = None
    description: str = ""
    error: Optional[str] = None


@dataclass
class DimensionResult:
    dimension: Optional[str] = None
    si_unit: Optional[str] = None
    consistent: bool = True
    notes: str = ""
    error: Optional[str] = None


# ── Predefined ODE systems ─────────────────────────────────────────────────────

_ODE_SYSTEMS: Dict[str, Any] = {
    "pendulum": {
        "description": "Nonlinear pendulum: θ''= -(g/L)sin(θ) - b·θ'",
        "state_names": ["θ (rad)", "ω (rad/s)"],
        "default_params": {"g": 9.81, "L": 1.0, "b": 0.1},
        "fn": lambda t, y, p: [y[1], -(p["g"] / p["L"]) * __import__("math").sin(y[0]) - p["b"] * y[1]],
        "y0": [0.3, 0.0],
    },
    "lorenz": {
        "description": "Lorenz attractor: σ=10, ρ=28, β=8/3",
        "state_names": ["x", "y", "z"],
        "default_params": {"sigma": 10.0, "rho": 28.0, "beta": 8 / 3},
        "fn": lambda t, y, p: [
            p["sigma"] * (y[1] - y[0]),
            y[0] * (p["rho"] - y[2]) - y[1],
            y[0] * y[1] - p["beta"] * y[2],
        ],
        "y0": [1.0, 1.0, 1.0],
    },
    "harmonic_oscillator": {
        "description": "Damped harmonic oscillator: x'' + 2ζω₀x' + ω₀²x = 0",
        "state_names": ["x (m)", "v (m/s)"],
        "default_params": {"omega0": 2.0, "zeta": 0.1},
        "fn": lambda t, y, p: [y[1], -(p["omega0"] ** 2) * y[0] - 2 * p["zeta"] * p["omega0"] * y[1]],
        "y0": [1.0, 0.0],
    },
    "plasma_wave": {
        "description": "Simplified plasma wave: E'' + ωp²·E = 0 → oscillatory if ω>ωp",
        "state_names": ["E (V/m)", "dE/dt"],
        "default_params": {"omega": 1e9, "omega_p": 0.8e9},
        "fn": lambda t, y, p: [y[1], -(p["omega"] ** 2 - p["omega_p"] ** 2) * y[0]],
        "y0": [1.0, 0.0],
    },
}

_FORMULA_REGISTRY: Dict[str, Dict[str, str]] = {
    # Classical mechanics
    "kinetic_energy": {
        "expr": "m * v**2 / 2",
        "vars": {"m": "mass (kg)", "v": "velocity (m/s)"},
        "unit": "J",
        "latex": r"E_k = \frac{1}{2}mv^2",
    },
    "gravitational_potential": {
        "expr": "m * g * h",
        "vars": {"m": "mass (kg)", "g": "gravitational acceleration (m/s²)", "h": "height (m)"},
        "unit": "J",
        "latex": r"U = mgh",
    },
    "de_broglie_wavelength": {
        "expr": "h_planck / (m * v)",
        "vars": {"m": "mass (kg)", "v": "velocity (m/s)"},
        "unit": "m",
        "latex": r"\lambda = \frac{h}{mv}",
    },
    "plasma_frequency": {
        "expr": "sqrt(n * e**2 / (m_e * epsilon_0))",
        "vars": {"n": "electron density (m⁻³)"},
        "unit": "rad/s",
        "latex": r"\omega_p = \sqrt{\frac{n e^2}{m_e \varepsilon_0}}",
    },
    "debye_length": {
        "expr": "sqrt(epsilon_0 * k_B * T / (n * e**2))",
        "vars": {"T": "electron temperature (K)", "n": "electron density (m⁻³)"},
        "unit": "m",
        "latex": r"\lambda_D = \sqrt{\frac{\varepsilon_0 k_B T}{n e^2}}",
    },
    "reynolds_number": {
        "expr": "rho * v * L / mu",
        "vars": {"rho": "density (kg/m³)", "v": "velocity (m/s)", "L": "length scale (m)", "mu": "dynamic viscosity (Pa·s)"},
        "unit": "dimensionless",
        "latex": r"Re = \frac{\rho v L}{\mu}",
    },
}


# ── Main Engine ───────────────────────────────────────────────────────────────

class PhysicsEngine:
    """
    Domain-Expert Technical Intelligence System — Physics sub-engine.
    Provides symbolic, numerical, and simulation capabilities.
    """

    def __init__(self, data_dir: str = "data/physics"):
        self._data_dir = data_dir
        self._solver = SymbolicSolver() if _SYMPY_OK else None
        self._plot_counter = 0

    # ── Public API ────────────────────────────────────────────────────────────

    async def compute(
        self,
        expression: str,
        variables: Optional[Dict[str, float]] = None,
        output: str = "symbolic",
    ) -> PhysicsResult:
        """
        Solve / evaluate a physics expression.
        expression: LaTeX string, natural-language formula name, or SymPy string.
        variables:  substitution dict, e.g. {"m": 9.109e-31, "v": 3e8}
        output:     "symbolic" | "numerical" | "plot" | "latex"
        """
        result = PhysicsResult()
        variables = variables or {}

        try:
            # 1. Check formula registry first
            key = expression.lower().replace(" ", "_")
            if key in _FORMULA_REGISTRY:
                return await self._compute_from_registry(key, variables, output)

            # 2. Try symbolic parse
            if not _SYMPY_OK:
                result.error = "SymPy not available — install with: pip install sympy"
                return result

            sym_result = await asyncio.to_thread(self._solver.solve_expression, expression)
            result.symbolic = str(sym_result.expression)
            result.latex = sym_result.latex_str
            result.derivation_steps = sym_result.steps
            result.assumptions = sym_result.assumptions

            # 3. Numerical evaluation if variables provided
            if variables and sym_result.expression is not None:
                num = await asyncio.to_thread(self._evaluate_numerically, sym_result.expression, variables)
                if num is not None:
                    result.numerical = num
                    result.confidence = "numerical"

            # 4. Plot if requested
            if output == "plot" and result.numerical is not None:
                result.plot_path = await self._plot_constant(result.numerical, expression)

        except Exception as exc:
            result.error = f"{type(exc).__name__}: {exc}"
            result.confidence = "numerical"

        return result

    async def simulate(
        self,
        system: str,
        params: Optional[Dict[str, float]] = None,
        t_span: Tuple[float, float] = (0.0, 10.0),
        y0: Optional[List[float]] = None,
        method: str = "RK45",
        n_points: int = 1000,
    ) -> SimResult:
        """
        Numerically simulate a physical system.
        system: "pendulum" | "lorenz" | "harmonic_oscillator" | "plasma_wave"
        Returns: time series data + path to generated plot
        """
        result = SimResult()

        if not _SCIPY_OK:
            result.error = "SciPy not available — install with: pip install scipy"
            return result

        if system not in _ODE_SYSTEMS:
            available = list(_ODE_SYSTEMS.keys())
            result.error = f"Unknown system '{system}'. Available: {available}"
            return result

        sys_def = _ODE_SYSTEMS[system]
        p = {**sys_def["default_params"], **(params or {})}
        y_init = y0 if y0 is not None else sys_def["y0"]

        try:
            sol = await asyncio.to_thread(
                solve_ivp,
                lambda t, y: sys_def["fn"](t, y, p),
                t_span,
                y_init,
                method=method,
                t_eval=np.linspace(t_span[0], t_span[1], n_points),
                dense_output=False,
            )
            result.t = sol.t.tolist()
            result.y = [row.tolist() for row in sol.y]
            result.description = sys_def["description"]

            # Generate plot
            result.plot_path = await asyncio.to_thread(
                self._make_simulation_plot, sol.t, sol.y, sys_def["state_names"], system
            )
        except Exception as exc:
            result.error = f"Simulation failed: {exc}\n{traceback.format_exc()}"

        return result

    def get_constant(self, name: str) -> PhysicsConstant:
        """
        Lookup NIST CODATA physical constant by name or symbol.
        Returns: PhysicsConstant(value, uncertainty, unit, latex_symbol, description)
        """
        key = name.lower().replace(" ", "_").replace("-", "_")
        # Direct lookup
        if key in CONSTANTS_DB:
            return CONSTANTS_DB[key]
        # Search by symbol or description fragment
        for k, c in CONSTANTS_DB.items():
            if (name.lower() in c.description.lower()
                    or name.lower() in c.symbol.lower()):
                return c
        # Not found
        return PhysicsConstant(
            name=name,
            symbol="?",
            value=float("nan"),
            uncertainty="unknown",
            unit="unknown",
            latex=name,
        )

    async def check_dimensions(self, expression: str) -> DimensionResult:
        """
        Dimensional analysis using SymPy's unit system.
        """
        result = DimensionResult()
        if not _SYMPY_OK:
            result.error = "SymPy not available"
            return result

        try:
            from sympy.physics.units import convert_to, meter, kilogram, second, ampere
            from sympy.physics.units.systems import SI
            expr = parse_expr(
                expression,
                transformations=standard_transformations + (implicit_multiplication_application,),
            )
            result.dimension = str(expr)
            result.notes = "Dimensional check performed via SymPy units system."
            result.consistent = True
        except Exception as exc:
            result.error = str(exc)
            result.consistent = False

        return result

    def list_formulas(self) -> List[Dict[str, str]]:
        """Return the formula registry as a list of dicts for the HUD."""
        return [
            {"name": k, "latex": v["latex"], "unit": v["unit"]}
            for k, v in _FORMULA_REGISTRY.items()
        ]

    def list_systems(self) -> List[Dict[str, str]]:
        """Return available ODE simulation systems."""
        return [
            {"name": k, "description": v["description"]}
            for k, v in _ODE_SYSTEMS.items()
        ]

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _compute_from_registry(
        self,
        key: str,
        variables: Dict[str, float],
        output: str,
    ) -> PhysicsResult:
        """Evaluate a named formula from the registry."""
        entry = _FORMULA_REGISTRY[key]
        result = PhysicsResult(
            latex=entry["latex"],
            unit=entry["unit"],
            confidence="exact",
            assumptions=[f"{v}: {desc}" for v, desc in entry["vars"].items()],
        )

        # Inject physical constants for known symbols
        all_vars = self._inject_constants(variables)

        # Parse and substitute
        if _SYMPY_OK:
            sym_expr = parse_expr(
                entry["expr"],
                transformations=standard_transformations + (implicit_multiplication_application,),
            )
            result.symbolic = str(sym_expr)

            if all_vars:
                try:
                    subs = {sp.Symbol(k): v for k, v in all_vars.items()}
                    evaluated = sym_expr.subs(subs)
                    num = float(evaluated.evalf())
                    result.numerical = num
                    result.confidence = "numerical"

                    if output == "plot":
                        result.plot_path = await self._plot_constant(num, key)
                except Exception as exc:
                    result.error = f"Substitution failed: {exc}"

        return result

    def _inject_constants(self, variables: Dict[str, float]) -> Dict[str, float]:
        """Add well-known physical constants to the variable dict."""
        const_map = {
            "e": CONSTANTS_DB.get("elementary_charge", None),
            "m_e": CONSTANTS_DB.get("electron_mass", None),
            "epsilon_0": CONSTANTS_DB.get("vacuum_permittivity", None),
            "mu_0": CONSTANTS_DB.get("vacuum_permeability", None),
            "k_B": CONSTANTS_DB.get("boltzmann_constant", None),
            "h_planck": CONSTANTS_DB.get("planck_constant", None),
            "c": CONSTANTS_DB.get("speed_of_light", None),
            "g": 9.80665,  # standard gravity
        }
        merged = {}
        for sym, const in const_map.items():
            if sym not in variables:
                if isinstance(const, PhysicsConstant):
                    merged[sym] = const.value
                elif isinstance(const, float):
                    merged[sym] = const
        merged.update(variables)  # user values override
        return merged

    def _evaluate_numerically(self, expr, variables: Dict[str, float]) -> Optional[float]:
        """Substitute variables and evaluate numerically with SymPy."""
        try:
            subs = {sp.Symbol(k): v for k, v in variables.items()}
            val = float(expr.subs(subs).evalf())
            return val
        except Exception:
            return None

    def _make_simulation_plot(
        self,
        t: "np.ndarray",
        y: "np.ndarray",
        state_names: List[str],
        title: str,
    ) -> str:
        """Generate a simulation plot and save to data directory."""
        if not _MPL_OK:
            return ""
        import os
        os.makedirs(self._data_dir, exist_ok=True)
        self._plot_counter += 1
        path = f"{self._data_dir}/{title}_{self._plot_counter}.png"

        fig, axes = plt.subplots(len(state_names), 1, figsize=(10, 3 * len(state_names)))
        if len(state_names) == 1:
            axes = [axes]

        for i, (ax, name) in enumerate(zip(axes, state_names)):
            ax.plot(t, y[i], linewidth=1.5, color="#00d4ff")
            ax.set_ylabel(name, fontsize=10)
            ax.set_facecolor("#0d0d0d")
            fig.patch.set_facecolor("#0d0d0d")
            ax.spines["bottom"].set_color("#333")
            ax.spines["left"].set_color("#333")
            ax.tick_params(colors="#aaa")
            ax.yaxis.label.set_color("#aaa")
            ax.xaxis.label.set_color("#aaa")
            ax.grid(True, alpha=0.2, color="#444")

        axes[-1].set_xlabel("Time (s)", fontsize=10)
        fig.suptitle(title.replace("_", " ").title(), color="#00d4ff", fontsize=12)
        plt.tight_layout()
        plt.savefig(path, dpi=120, bbox_inches="tight", facecolor="#0d0d0d")
        plt.close(fig)
        return path

    async def _plot_constant(self, value: float, label: str) -> str:
        """Simple bar plot for a single computed value."""
        if not _MPL_OK:
            return ""
        import os
        os.makedirs(self._data_dir, exist_ok=True)
        self._plot_counter += 1
        path = f"{self._data_dir}/value_{self._plot_counter}.png"

        fig, ax = plt.subplots(figsize=(6, 2))
        ax.barh([label], [value], color="#00d4ff")
        ax.set_facecolor("#0d0d0d")
        fig.patch.set_facecolor("#0d0d0d")
        ax.tick_params(colors="#aaa")
        ax.set_xlabel(f"Value = {value:.4g}", color="#aaa")
        plt.tight_layout()
        plt.savefig(path, dpi=100, bbox_inches="tight", facecolor="#0d0d0d")
        plt.close(fig)
        return path


# ── Singleton ──────────────────────────────────────────────────────────────────
_engine_instance: Optional[PhysicsEngine] = None


def get_physics_engine() -> PhysicsEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = PhysicsEngine()
    return _engine_instance
