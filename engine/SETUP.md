# DEEP Engineering-Bible — Setup

The `deep/` science/tech engine runs on **system Python 3.11**. Its core depends only on
the scientific stack already present on this machine; heavy domain libraries are optional
and guarded — install only the ones you need.

## Prerequisites

- Python 3.11
- The DEEP server already running (see the project root `start_deep.bat`)
- For animations/plots: **matplotlib** (already installed: 3.10.9). MP4 export additionally
  needs `ffmpeg` on PATH; GIF export uses Pillow (no ffmpeg required).
- Optional for Manim-quality renders: LaTeX (MiKTeX on Windows) + ffmpeg.

## Core install (already satisfied on this box)

```bash
pip install numpy scipy sympy matplotlib scikit-learn networkx
```

These power: maths, physics, quantum mechanics, chemistry (stoichiometry), biology,
astrophysics, nuclear, ML, neural nets (with torch), visualisation, quantum computing
(numpy simulator), robotics, engineering, gaming, cloud, finance.

## Optional domain libraries

| Capability | Install | Falls back to |
|-----------|---------|---------------|
| Deep learning | `pip install torch` (present: 2.11 CPU) | constructors return param counts only |
| Graph NNs | `pip install torch-geometric` | from-scratch numpy GCN |
| Cheminformatics (SMILES, fingerprints) | `pip install rdkit` | formula-based molar mass only |
| Periodic-table data | `pip install mendeleev` | built-in element table |
| Quantum chemistry (HF/DFT) | `pip install pyscf` | explains requirement |
| Quantum computing (hardware/Aer) | `pip install qiskit qiskit-aer` | numpy statevector simulator |
| Computer vision | `pip install opencv-python ultralytics` | numpy Sobel edges |
| NLP transformers | `pip install transformers` (present) | lexicon sentiment, extractive summary |
| Protein LM | `pip install fair-esm` | sequence-property analytics |
| Crypto | `pip install cryptography` (present) | hashing/entropy only |

Full pin list: project-root `requirements.txt` (Bible Section 27).

## First-run checklist

```bash
cd C:\Users\Aryan\Aryan_Private\DEEP

# 1. self-test every module (offline)
python -m pytest engine/tests/ -q          # expect 40 passed

# 2. one-shot command
python -m engine.main "integrate x^2 from 0 to 3"      # -> 9

# 3. interactive
python -m engine.main
```

Outputs (plots, animations) are written to `~/deep_output/` (`plots/`, `animations/`).

## Using it from the live assistant

The bridge tool **`science_compute`** is registered in
`core/application/tool_registry.py`. The LLM calls it automatically for scientific or
technical questions. No extra setup — just ask DEEP in chat or by voice:

> "DEEP, what's the Schwarzschild radius of a 10 solar-mass black hole?"

The first such call lazily imports the science stack (a few seconds), then it's cached.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `scipy not available` in a result | `pip install scipy` |
| `matplotlib unavailable` (no plots) | `pip install matplotlib` |
| `sph_harm` ImportError | handled automatically (SciPy ≥1.15 → `sph_harm_y`) |
| A command routes to the wrong domain | the bible's keywords overlap; phrase with a more specific term, or call the Engine class method directly |
| Quantum/GNN says a library is missing | the numpy fallback still runs; install qiskit / torch-geometric for the full path |
| Unicode crash in a redirected console | run with `PYTHONUTF8=1` (the launcher already sets this) |
