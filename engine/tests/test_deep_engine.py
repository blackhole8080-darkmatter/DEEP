"""Pytest suite for the DEEP Engineering-Bible science/tech package.

Runs each module's built-in ``test()`` plus targeted assertions and end-to-end
routing checks through the orchestrator. All tests run offline (no network, no
API keys); modules whose heavy deps are absent skip gracefully.

Run:  pytest deep/tests/ -v   (from the DEEP folder)
"""
import importlib

import pytest

SCIENCE = ["compute", "math_engine", "physics", "quantum_mech", "chemistry",
           "genomics", "protein", "biology", "astrophysics", "nuclear",
           "ml_engine", "neural_nets", "gnn", "pinn", "visualizer", "animator",
           "algorithms", "models", "data_engine"]
TECH = ["quantum_computing", "robotics", "computer_vision", "nlp",
        "cybersecurity", "engineering", "gaming", "cloud", "finance", "networking"]
SYSTEM = ["memory", "assistant", "voice", "system_monitor", "files", "apps",
          "security_ops", "research", "home_control", "scheduler"]


@pytest.mark.parametrize("mod", SCIENCE)
def test_science_module_selftest(mod):
    m = importlib.import_module(f"engine.science.{mod}")
    assert hasattr(m, "test")
    m.test()  # raises on failure


@pytest.mark.parametrize("mod", TECH)
def test_tech_module_selftest(mod):
    m = importlib.import_module(f"engine.tech.{mod}")
    assert hasattr(m, "test")
    m.test()


@pytest.mark.parametrize("mod", SYSTEM)
def test_system_module_selftest(mod):
    m = importlib.import_module(f"engine.{mod}")
    assert hasattr(m, "test")
    m.test()


# ── targeted correctness ─────────────────────────────────────────────────
def test_calculus():
    from engine.science.compute import ComputeEngine
    e = ComputeEngine()
    assert e.differentiate("x**3", "x")["symbolic"] == "3*x**2"
    assert e.integrate("x**2", "x", 0, 3)["numeric"] == pytest.approx(9.0)
    assert e.solve("x**2 - 4", "x")["solutions"]


def test_number_theory():
    from engine.science.math_engine import MathEngine
    e = MathEngine()
    assert e.is_prime(97)["is_prime"]
    assert e.factorize(360)["factors"] == {2: 3, 3: 2, 5: 1}
    assert e.fibonacci(10)["value"] == 55


def test_physics_projectile():
    from engine.science.physics import PhysicsEngine
    p = PhysicsEngine().projectile(45, 20)
    assert p["range"] == pytest.approx(40.77, abs=0.5)


def test_quantum_vqe():
    from engine.science.quantum_mech import QuantumMechanics
    t = QuantumMechanics().quantum_tunneling(1.0, 2.0, 1.0)
    assert 0 < t["T_coeff"] < 1


def test_chemistry_balance():
    from engine.science.chemistry import ChemistryEngine
    e = ChemistryEngine()
    assert e.molar_mass("H2O")["molar_mass"] == pytest.approx(18.015, abs=0.01)
    assert e.balance_equation("H2 + O2 -> H2O")["coefficients"]


def test_nuclear_fusion():
    from engine.science.nuclear import NuclearEngine
    q = NuclearEngine().fusion_reaction(("H-2", "H-3"))
    assert q["Q_value"] == pytest.approx(17.6, abs=0.5)


def test_quantum_computing_bell():
    from engine.tech.quantum_computing import QuantumEngine
    counts = QuantumEngine().bell_state("phi+")["counts"]
    assert all(k in ("00", "11") for k in counts)


def test_finance_black_scholes():
    from engine.tech.finance import FinanceEngine
    bs = FinanceEngine().black_scholes(100, 100, 1, 0.05, 0.2, "call")
    assert bs["price"] == pytest.approx(10.45, abs=0.1)


# ── orchestrator routing ─────────────────────────────────────────────────
@pytest.mark.parametrize("command,expected_module", [
    ("integrate x^2 from 0 to 3", "science.compute"),
    ("factor the number 360", "science.math_engine"),
    ("projectile at 45 and 20", "science.physics"),
    ("black hole 10 solar masses", "science.astrophysics"),
    ("nuclear reaction fusion d-t", "science.nuclear"),
    ("run a bell state quantum circuit", "tech.quantum_computing"),
    ("stock option price portfolio", "tech.finance"),
])
def test_routing(command, expected_module):
    from engine.main import DEEP
    out = DEEP().process_command(command)
    assert out["module"] == expected_module, f"{command} -> {out['module']}"
