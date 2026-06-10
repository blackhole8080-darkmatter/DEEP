# DEEP — Scientific & Technological Intelligence Engine

> *"What happens when J.A.R.V.I.S. earns a PhD across every discipline of science and technology, and decides to be useful."*

This package (`engine/`) is the **Engineering-Bible build**: a 16-domain scientific and
technical computation engine that plugs into the live DEEP assistant. Ask it to
differentiate, simulate, price an option, run a quantum circuit, balance a reaction,
or solve a PDE — by voice, chat, or code.

## Quick start

```bash
# from the DEEP project folder
python -m engine.main "integrate x^2 from 0 to 3"
python -m engine.main "black hole 10 solar masses"
python -m engine.main                # interactive console
```

In code:
```python
from engine.main import DEEP
m = DEEP()
print(m.process_command("price a call option, stock option price 105 strike 100")["verbal"])
```

In the **live DEEP chat**, the `science_compute` tool exposes the whole engine to the LLM —
just ask naturally ("what's the binding energy of iron-56?") and it routes automatically.

## The 16 domains

| # | Domain | Module | Highlights |
|---|--------|--------|-----------|
| 1 | Mathematics | `science.compute` | calculus, algebra, linear algebra, transforms |
| 2 | Adv. maths | `science.math_engine` | number/graph theory, combinatorics, geometry, LP |
| 3 | Physics | `science.physics` | mechanics, EM, thermo, fluids, relativity |
| 4 | Quantum mechanics | `science.quantum_mech` | Schrödinger FD, hydrogen, tunnelling, Bell |
| 5 | Chemistry | `science.chemistry` | molar mass, equation balancing, periodic table, HF |
| 6 | Genomics | `science.genomics` | alignment, k-mers, translation, assembly |
| 7 | Protein science | `science.protein` | MW, GRAVY, pI, secondary structure |
| 8 | Biology | `science.biology` | SIR/SEIR, Lotka-Volterra, Hodgkin-Huxley |
| 9 | Astrophysics | `science.astrophysics` | stellar, cosmology, Kerr BH, GW chirp |
| 10 | Nuclear | `science.nuclear` | SEMF binding energy, decay, fusion Q, reactor |
| 11 | Machine learning | `science.ml_engine` | sklearn registry + Q-learning |
| 12 | Neural networks | `science.neural_nets` | trainable MLP, CNN, Transformer, VAE, NeuralODE |
| 13 | GNN / PINN | `science.gnn`, `science.pinn` | scratch GCN; PINN that solves the heat equation |
| 14 | Visualisation | `science.visualizer`, `animator` | dark-neon PNGs + GIF animations |
| 15 | Quantum computing | `tech.quantum_computing` | numpy statevector sim: Grover, VQE, QAOA |
| 16 | Robotics / CV / NLP / cyber / eng / gaming / cloud / finance | `tech.*` | FK/IK, A*, Black-Scholes, FedAvg, … |

## Voice / command examples

- "differentiate sin(x)·x²" → `x²·cos(x) + 2x·sin(x)`
- "integrate x² from 0 to 3" → `9`
- "limit of sin(x)/x as x approaches 0" → `1`
- "projectile at 45 degrees, 20 m/s" → range 40.8 m
- "black hole 10 solar masses" → Schwarzschild radius 29.5 km
- "binding energy Z=26 A=56" → 8.85 MeV/nucleon
- "nuclear reaction fusion d-t" → Q = 17.6 MeV
- "run a Grover search for 101" → finds |101⟩ in 962/1024 shots
- "VQE ground state energy" → −1.4142 (exact)
- "balance equation C3H8 + O2 -> CO2 + H2O" → `C3H8 + 5 O2 -> 3 CO2 + 4 H2O`
- "train a random forest classifier" → accuracy ~1.0
- "solve a PDE with a PINN" → heat-equation PINN, RMSE 0.004
- "plot sin(x)·exp(-0.1x)" → saves a dark-neon PNG
- "animate the Lorenz attractor" → saves a GIF
- "stock option price 105 strike 100" → Black-Scholes price + Greeks

## Architecture

```
deep/
├── config.py          all settings (Bible Section 2)
├── main.py            orchestrator: INTENT_MAP (76 intents) + router + dispatch
├── science/           16 science modules (each: Engine class + routing fns + test())
├── tech/              10 tech modules
└── tests/             pytest suite (40 tests, offline)
```

Routing: `DEEP().process_command(text)` → keyword match (longest-keyword-wins, acronym
word-boundary, action-verb priority) → dynamic dispatch → `{result, verbal, module, function}`.
Every routine returns a spoken `verbal` summary.

## Design principles

- **Graceful degradation** — heavy/optional libraries (qiskit, torch_geometric, rdkit,
  pyscf, opencv, transformers) are guarded; if absent, a numpy/pure-python core still runs
  (e.g. a from-scratch quantum statevector simulator, a scratch GCN).
- **Everything returns `verbal`** so the assistant can speak results.
- **Offline-first** — no network or API keys required for the core.

See `SETUP.md` for installation and the full dependency matrix.
