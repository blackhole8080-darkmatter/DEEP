"""Pytest suite for the DEEP Engineering-Bible tech/system package.

Runs each module's built-in ``test()`` plus targeted assertions and end-to-end
routing checks through the orchestrator. All tests run offline (no network, no
API keys); modules whose heavy deps are absent skip gracefully.

The `engine/science/*` package (physics, chemistry, genomics, etc.) was moved
to `archive/engine/science/` — DEEP's focus narrowed to network/cybersecurity
+ memory. Its self-tests moved out of the default suite with it; see
archive/engine/science if that package is ever revived.

Run:  pytest deep/tests/ -v   (from the DEEP folder)
"""
import importlib

import pytest

TECH = ["quantum_computing", "robotics", "computer_vision", "nlp",
        "cybersecurity", "engineering", "gaming", "cloud", "finance", "networking"]
SYSTEM = ["memory", "assistant", "voice", "system_monitor", "files", "apps",
          "security_ops", "research", "home_control", "scheduler"]


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
    ("run a bell state quantum circuit", "tech.quantum_computing"),
    ("stock option price portfolio", "tech.finance"),
])
def test_routing(command, expected_module):
    from engine.main import DEEP
    out = DEEP().process_command(command)
    assert out["module"] == expected_module, f"{command} -> {out['module']}"
