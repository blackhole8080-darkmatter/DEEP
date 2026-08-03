# deep/main.py — DEEP Central Orchestrator (Engineering Bible Section 3)
"""Routes natural-language commands to the 16 science/tech domains.

Self-contained: runnable as `python -m engine.main` from the DEEP folder, and
importable so the live server can call `DEEP().process_command(text)`.
"""
from __future__ import annotations

import argparse
import importlib
import inspect
import os
import re
from typing import Optional


try:
    from loguru import logger
except Exception:  # pragma: no cover
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("deep")


# ── INTENT MAP (Section 3.3) ─────────────────────────────────────────────
INTENT_MAP = {
    ('compute', 'calculate', 'evaluate', 'sympy'):            ('science.compute', 'compute'),
    ('differentiate', 'derivative', 'd/dx'):                  ('science.compute', 'differentiate'),
    ('integrate', 'integral', 'antiderivative'):              ('science.compute', 'integrate'),
    ('solve equation', 'find roots', 'zero of'):              ('science.compute', 'solve'),
    ('laplace', 'z-transform', 'fourier transform'):          ('science.compute', 'transform'),
    ('limit', 'approaches', 'tends to'):                      ('science.compute', 'limit'),
    ('series', 'taylor', 'maclaurin', 'expand'):              ('science.compute', 'series'),
    ('matrix', 'determinant', 'eigenvalue', 'SVD'):           ('science.compute', 'matrix_ops'),
    ('prime', 'factor', 'gcd', 'lcm', 'modular'):             ('science.math_engine', 'number_theory'),
    ('graph theory', 'shortest path', 'spanning tree'):       ('science.math_engine', 'graph_theory'),
    ('combinatorics', 'permutations', 'combinations'):        ('science.math_engine', 'combinatorics'),
    ('geometry', 'polygon', 'convex hull', 'area of'):        ('science.math_engine', 'geometry'),
    ('linear program', 'optimize', 'LP problem'):             ('science.math_engine', 'linear_programming'),
    ('physics', 'projectile', 'trajectory', 'launch'):        ('science.physics', 'projectile'),
    ('pendulum', 'oscillat', 'spring', 'SHM'):                ('science.physics', 'oscillation'),
    ('orbit', 'satellite', 'kepler', 'vis-viva'):             ('science.physics', 'orbital'),
    ('n-body', 'gravitational sim', 'solar'):                 ('science.physics', 'n_body'),
    ('electric field', 'coulomb', 'charge', 'capacitor'):     ('science.physics', 'electrostatics'),
    ('magnetic', 'biot-savart', 'solenoid', 'inductor'):      ('science.physics', 'magnetism'),
    ('circuit', 'kirchhoff', 'resistor', 'voltage', 'current'): ('science.physics', 'circuit'),
    ('maxwell', 'electromagnetic wave', 'FDTD'):              ('science.physics', 'em_wave'),
    ('thermodynamics', 'carnot', 'entropy', 'heat'):          ('science.physics', 'thermodynamics'),
    ('ideal gas', 'PVT', 'maxwell-boltzmann'):                ('science.physics', 'statistical_mech'),
    ('fluid', 'navier-stokes', 'bernoulli', 'flow'):          ('science.physics', 'fluid_dynamics'),
    ('relativity', 'lorentz', 'time dilation', 'spacetime'):  ('science.physics', 'relativity'),
    ('schrodinger', 'wavefunction', 'quantum particle'):      ('science.quantum_mech', 'schrodinger'),
    ('harmonic oscillator', 'quantum HO', 'energy levels'):   ('science.quantum_mech', 'harmonic_oscillator'),
    ('hydrogen atom', 'orbital', 'radial wavefunction'):      ('science.quantum_mech', 'hydrogen'),
    ('tunneling', 'barrier', 'transmission coefficient'):     ('science.quantum_mech', 'tunneling'),
    ('spin', 'pauli', 'bloch sphere', 'magnetic moment'):     ('science.quantum_mech', 'spin'),
    ('perturbation theory', 'energy correction'):             ('science.quantum_mech', 'perturbation'),
    ('DFT', 'density functional', 'PySCF', 'Kohn-Sham'):      ('science.quantum_mech', 'dft'),
    ('molecule', 'SMILES', 'compound', 'molecular weight'):   ('science.chemistry', 'molecule'),
    ('balance equation', 'stoichiometry', 'reaction'):        ('science.chemistry', 'stoichiometry'),
    ('element', 'periodic table', 'atomic number'):           ('science.chemistry', 'periodic_table'),
    ('fingerprint', 'similarity', 'tanimoto'):                ('science.chemistry', 'similarity'),
    ('molecular dynamics', 'force field', 'MD sim'):          ('science.chemistry', 'md_simulation'),
    ('dock', 'binding affinity', 'drug', 'ligand'):           ('science.chemistry', 'drug_discovery'),
    ('star', 'stellar evolution', 'HR diagram', 'main seq'):  ('science.astrophysics', 'stellar_evolution'),
    ('galaxy', 'n-body galaxy', 'dark matter', 'halo'):       ('science.astrophysics', 'galaxy'),
    ('cosmology', 'hubble', 'friedmann', 'expansion'):        ('science.astrophysics', 'cosmology'),
    ('black hole', 'schwarzschild', 'kerr', 'event horizon'): ('science.astrophysics', 'black_hole'),
    ('gravitational wave', 'chirp', 'inspiral', 'LIGO'):      ('science.astrophysics', 'gravitational_waves'),
    ('spectrum', 'redshift', 'spectral line', 'pulsar'):      ('science.astrophysics', 'spectral'),
    ('radioactive', 'decay', 'half-life', 'isotope'):         ('science.nuclear', 'radioactive_decay'),
    ('nuclear reaction', 'fission', 'fusion', 'Q-value'):     ('science.nuclear', 'nuclear_reaction'),
    ('reactor', 'criticality', 'neutron', 'Bateman'):         ('science.nuclear', 'reactor'),
    ('nuclide', 'binding energy', 'shell model', 'magic'):    ('science.nuclear', 'nuclear_structure'),
    ('radiation dose', 'shielding', 'KERMA'):                 ('science.nuclear', 'radiation_safety'),
    ('plot', 'graph', 'chart', 'visualize', 'show function'): ('science.visualizer', 'plot'),
    ('phase portrait', 'vector field', 'nullcline'):          ('science.visualizer', 'phase_portrait'),
    ('heatmap', 'contour', 'surface plot'):                   ('science.visualizer', 'surface_plot'),
    ('animate', 'animation', 'render', 'show me moving'):     ('science.animator', 'animate'),
    ('train model', 'fit', 'regression', 'classify'):         ('science.ml_engine', 'train'),
    ('neural network', 'deep learning', 'backprop'):          ('science.neural_nets', 'build_model'),
    ('GNN', 'graph neural', 'molecular GNN'):                 ('science.gnn', 'build_gnn'),
    ('PINN', 'physics-informed', 'PDE neural'):               ('science.pinn', 'solve_pde'),
    ('neural ODE', 'continuous dynamics'):                    ('science.neural_nets', 'neural_ode'),
    ('quantum circuit', 'qubit', 'gate', 'Grover', 'Shor'):   ('tech.quantum_computing', 'run_circuit'),
    ('VQE', 'variational eigen', 'ground state energy'):      ('tech.quantum_computing', 'vqe'),
    ('QAOA', 'combinatorial quantum', 'quantum optimize'):    ('tech.quantum_computing', 'qaoa'),
    ('robot', 'SLAM', 'navigate', 'arm', 'gripper', 'ROS'):   ('tech.robotics', 'execute'),
    ('detect object', 'classify image', 'YOLO', 'segment'):   ('tech.computer_vision', 'analyze'),
    ('depth estimation', 'point cloud', 'pose estimation'):   ('tech.computer_vision', 'depth'),
    ('summarize text', 'translate', 'sentiment', 'NER', 'NLP'): ('tech.nlp', 'process'),
    ('RAG', 'search documents', 'ask my notes'):             ('tech.nlp', 'rag_query'),
    ('intrusion', 'malware', 'IDS', 'scan threats'):          ('tech.cybersecurity', 'analyze'),
    ('encrypt', 'decrypt', 'hash', 'cipher', 'RSA', 'AES'):   ('tech.cybersecurity', 'crypto'),
    ('FEA', 'stress analysis', 'finite element'):             ('tech.engineering', 'fea'),
    ('filter', 'FFT', 'signal processing', 'spectrum'):       ('tech.engineering', 'signal_processing'),
    ('PID', 'control system', 'bode plot', 'transfer func'):  ('tech.engineering', 'control'),
    ('game', 'NPC', 'level generate', 'procedural', 'PCG'):   ('tech.gaming', 'execute'),
    ('A* game', 'pathfind', 'behavior tree', 'minimax'):      ('tech.gaming', 'pathfind'),
    ('deploy', 'docker', 'kubernetes', 'container', 'API'):   ('tech.cloud', 'execute'),
    ('federated', 'distributed training', 'edge AI'):         ('tech.cloud', 'distributed_ml'),
    ('stock', 'option price', 'portfolio', 'backtest'):       ('tech.finance', 'execute'),
    # ── SYSTEM ───────────────────────────────────────────────────────
    ('system status', 'vitals', 'CPU', 'RAM', 'battery'):     ('system_monitor', 'report'),
    ('search web', 'look up', 'who is', 'Wikipedia'):         ('research', 'search'),
    ('arXiv', 'research paper', 'scientific paper'):          ('research', 'arxiv'),
    ('note', 'remember this', 'write down', 'save that'):     ('files', 'save_note'),
    ('recall', 'what did I say', 'retrieve note'):            ('memory', 'recall'),
    ('open', 'launch app', 'run program', 'start'):           ('apps', 'launch'),
    ('screenshot', 'take a photo of screen'):                 ('apps', 'screenshot'),
    ('remind me', 'set alarm', 'timer'):                      ('apps', 'reminder'),
    ('lights', 'thermostat', 'home automation'):              ('home_control', 'execute'),
    ('port scan', 'ping', 'network check', 'security scan'):  ('security_ops', 'scan'),
}


class DEEP:
    """Central orchestrator."""

    def __init__(self, args: Optional[argparse.Namespace] = None):
        self.args = args
        self._module_cache: dict = {}
        self._sem_router = None  # lazily created semantic fallback

    # ── ROUTING ─────────────────────────────────────────────────────
    def route_intent(self, text: str):
        match = self.keyword_match(text)
        if match:
            return match[0], match[1], {"text": text, "via": "keyword"}
        # Keyword miss: try the optional embedding-based semantic fallback so
        # paraphrases still route. Falls through to None if unavailable.
        sem = self._semantic_match(text)
        if sem:
            return sem[0], sem[1], {"text": text, "via": "semantic"}
        return None, None, {"text": text}

    def _semantic_match(self, text: str):
        """Embedding-based nearest-intent fallback (opt-out via DEEP_SEMANTIC_INTENT=0)."""
        if os.getenv("DEEP_SEMANTIC_INTENT", "true").strip().lower() not in {"1", "true", "yes", "y"}:
            return None
        if self._sem_router is None:
            try:
                from .semantic_router import SemanticIntentRouter
                self._sem_router = SemanticIntentRouter(INTENT_MAP)
            except Exception:
                return None
        try:
            return self._sem_router.match(text)
        except Exception:
            return None

    # Explicit action verbs that should win over a domain noun in the same
    # command (e.g. "animate a projectile" -> animator, not physics).
    PRIORITY = (
        (("animate", "animation", "render", "show me moving"),
         ("science.animator", "animate")),
    )

    def keyword_match(self, text: str):
        """Longest-keyword-wins matching, with explicit action-verb priority.

        The bible checks keywords as substrings of the full command. Many
        keywords overlap (e.g. 'solar' vs 'solar masses', 'reaction' vs
        'nuclear reaction'); picking the *longest* matching keyword resolves
        these specificity collisions in favour of the more specific domain.
        Action verbs in PRIORITY (animate/render) take precedence so an
        explicit "animate ..." request reaches the animator.
        """
        low = text.lower()
        for triggers, target in self.PRIORITY:
            if any(t in low for t in triggers):
                return target
        best = None
        best_len = 0
        for keywords, target in INTENT_MAP.items():
            for kw in keywords:
                if self._kw_matches(kw, low) and len(kw) > best_len:
                    best, best_len = target, len(kw)
        return best

    @staticmethod
    def _kw_matches(kw: str, low: str) -> bool:
        """Substring match, except short/acronym keywords must be whole words.

        Lowercase keywords (e.g. 'oscillat') keep prefix/substring behaviour as
        the bible intends. Short uppercase acronyms (NER, CPU, DFT, VQE, …) match
        only as standalone tokens, so 'NER' no longer fires inside 'generator'.
        """
        kl = kw.lower()
        if kl not in low:
            return False
        if kw.isupper() or (len(kw) <= 3 and kw.isalpha()):
            return re.search(rf"(?<![a-z0-9]){re.escape(kl)}(?![a-z0-9])", low) is not None
        return True

    # ── DISPATCH ────────────────────────────────────────────────────
    def process_command(self, raw_text: str) -> dict:
        text = re.sub(r"\s+", " ", raw_text).strip()
        module_name, function_name, params = self.route_intent(text)
        if module_name is None:
            return {"result": None,
                    "verbal": "I could not match that to a domain, sir.",
                    "module": None, "function": None}
        result = self._dispatch(module_name, function_name, text, params)
        if isinstance(result, dict):
            result.setdefault("module", module_name)
            result.setdefault("function", function_name)
        return result

    def _dispatch(self, module_name, function_name, text, params):
        mod = self._load_module(module_name)
        if mod is None:
            return {"result": None,
                    "verbal": f"The {module_name} module is not available, sir."}
        fn = getattr(mod, function_name, None)
        if fn is None:
            return {"result": None,
                    "verbal": f"No '{function_name}' routine in {module_name} yet, sir."}
        try:
            return self._call(fn, text, params)
        except Exception as e:  # noqa: BLE001
            logger.exception("dispatch error")
            return {"result": None, "verbal": f"That routine failed, sir: {e}"}

    @staticmethod
    def _call(fn, text, params):
        sig = inspect.signature(fn)
        kwargs = {}
        if "text" in sig.parameters:
            kwargs["text"] = text
        if "query" in sig.parameters:
            kwargs["query"] = text
        if "params" in sig.parameters:
            kwargs["params"] = params
        if kwargs:
            return fn(**kwargs)
        req = [p for p in sig.parameters.values()
               if p.default is inspect.Parameter.empty
               and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
        return fn(text) if len(req) == 1 else fn()

    def _load_module(self, module_name):
        if module_name in self._module_cache:
            return self._module_cache[module_name]
        try:
            mod = importlib.import_module(f"engine.{module_name}")
        except Exception as e:  # noqa: BLE001
            logger.debug(f"import engine.{module_name} failed: {e}")
            mod = None
        self._module_cache[module_name] = mod
        return mod


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="DEEP — full-spectrum scientific AI")
    p.add_argument("--test", action="store_true", help="Run module self-tests")
    p.add_argument("command", nargs="*", help="One-shot command to route")
    return p.parse_args(argv)


def run_deep(argv=None):
    args = parse_args(argv)
    m = DEEP(args)
    if args.command:
        out = m.process_command(" ".join(args.command))
        print(out.get("verbal", out))
        return
    print("DEEP science console. Type 'exit' to quit.")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in {"exit", "quit"}:
            break
        if not text:
            continue
        out = m.process_command(text)
        print("deep>", out.get("verbal", out))


if __name__ == "__main__":
    run_deep()
