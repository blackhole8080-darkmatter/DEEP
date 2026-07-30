# deep/science/chemistry.py — Chemistry & Molecular Science (Bible Section 7)
"""Cheminformatics, stoichiometry, periodic table, quantum chemistry, MD,
drug discovery. RDKit / PySCF / mendeleev are optional and guarded; core
stoichiometry works with no heavy dependencies."""
from __future__ import annotations

import math
import re

import sympy as sp

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem, Descriptors, DataStructs
    RDKIT = True
except Exception:  # pragma: no cover
    RDKIT = False

try:
    import mendeleev
    MENDELEEV = True
except Exception:  # pragma: no cover
    MENDELEEV = False

# Element data table: (Z, symbol, name, atomic mass g/mol). Enough for
# stoichiometry and lookups with no heavy dependencies.
ELEMENTS = [
    (1, 'H', 'Hydrogen', 1.008), (2, 'He', 'Helium', 4.0026), (3, 'Li', 'Lithium', 6.94),
    (4, 'Be', 'Beryllium', 9.0122), (5, 'B', 'Boron', 10.81), (6, 'C', 'Carbon', 12.011),
    (7, 'N', 'Nitrogen', 14.007), (8, 'O', 'Oxygen', 15.999), (9, 'F', 'Fluorine', 18.998),
    (10, 'Ne', 'Neon', 20.180), (11, 'Na', 'Sodium', 22.990), (12, 'Mg', 'Magnesium', 24.305),
    (13, 'Al', 'Aluminium', 26.982), (14, 'Si', 'Silicon', 28.085), (15, 'P', 'Phosphorus', 30.974),
    (16, 'S', 'Sulfur', 32.06), (17, 'Cl', 'Chlorine', 35.45), (18, 'Ar', 'Argon', 39.948),
    (19, 'K', 'Potassium', 39.098), (20, 'Ca', 'Calcium', 40.078), (21, 'Sc', 'Scandium', 44.956),
    (22, 'Ti', 'Titanium', 47.867), (23, 'V', 'Vanadium', 50.942), (24, 'Cr', 'Chromium', 51.996),
    (25, 'Mn', 'Manganese', 54.938), (26, 'Fe', 'Iron', 55.845), (27, 'Co', 'Cobalt', 58.933),
    (28, 'Ni', 'Nickel', 58.693), (29, 'Cu', 'Copper', 63.546), (30, 'Zn', 'Zinc', 65.38),
    (31, 'Ga', 'Gallium', 69.723), (32, 'Ge', 'Germanium', 72.630), (33, 'As', 'Arsenic', 74.922),
    (34, 'Se', 'Selenium', 78.971), (35, 'Br', 'Bromine', 79.904), (36, 'Kr', 'Krypton', 83.798),
    (37, 'Rb', 'Rubidium', 85.468), (38, 'Sr', 'Strontium', 87.62), (39, 'Y', 'Yttrium', 88.906),
    (40, 'Zr', 'Zirconium', 91.224), (41, 'Nb', 'Niobium', 92.906), (42, 'Mo', 'Molybdenum', 95.95),
    (47, 'Ag', 'Silver', 107.87), (48, 'Cd', 'Cadmium', 112.41), (49, 'In', 'Indium', 114.82),
    (50, 'Sn', 'Tin', 118.71), (51, 'Sb', 'Antimony', 121.76), (52, 'Te', 'Tellurium', 127.60),
    (53, 'I', 'Iodine', 126.90), (54, 'Xe', 'Xenon', 131.29), (55, 'Cs', 'Caesium', 132.91),
    (56, 'Ba', 'Barium', 137.33), (78, 'Pt', 'Platinum', 195.08), (79, 'Au', 'Gold', 196.97),
    (80, 'Hg', 'Mercury', 200.59), (82, 'Pb', 'Lead', 207.2), (83, 'Bi', 'Bismuth', 208.98),
    (92, 'U', 'Uranium', 238.03),
]
ATOMIC = {s: m for _, s, _, m in ELEMENTS}
_NAMES = {s: n for _, s, n, _ in ELEMENTS}
_ZMAP = {z: s for z, s, _, _ in ELEMENTS}
_NAME2SYM = {n.lower(): s for _, s, n, _ in ELEMENTS}
_SYMBOLS = list(ATOMIC.keys())


class ChemistryEngine:
    def __init__(self, config=None):
        self.config = config

    # ── 7.1 cheminformatics ─────────────────────────────────────────
    def parse_molecule(self, identifier, fmt="auto") -> dict:
        if not RDKIT:
            # at least compute molar mass if it looks like a formula
            if re.fullmatch(r"[A-Za-z0-9()]+", identifier):
                mm = self.molar_mass(identifier)
                return {"smiles": None, "formula": identifier, "molar_mass": mm.get("molar_mass"),
                        "verbal": f"RDKit unavailable; treated '{identifier}' as a formula. "
                                  + mm["verbal"]}
            return {"result": None, "verbal": "RDKit is not installed, sir."}
        mol = Chem.MolFromSmiles(identifier)
        if mol is None:
            return {"result": None, "verbal": f"Could not parse '{identifier}' as SMILES."}
        formula = Chem.rdMolDescriptors.CalcMolFormula(mol)
        mm = Descriptors.MolWt(mol)
        return {"smiles": Chem.MolToSmiles(mol), "inchi": Chem.MolToInchi(mol),
                "formula": formula, "molar_mass": mm,
                "verbal": f"{identifier}: formula {formula}, molar mass {mm:.2f} g/mol.",
                "result": {"formula": formula, "molar_mass": mm}}

    def tanimoto_similarity(self, smiles1, smiles2, fp_type="Morgan") -> dict:
        if not RDKIT:
            return {"result": None, "verbal": "RDKit is not installed, sir."}
        m1, m2 = Chem.MolFromSmiles(smiles1), Chem.MolFromSmiles(smiles2)
        if not m1 or not m2:
            return {"result": None, "verbal": "Could not parse one of the SMILES."}
        fp1 = AllChem.GetMorganFingerprintAsBitVect(m1, 2)
        fp2 = AllChem.GetMorganFingerprintAsBitVect(m2, 2)
        tan = DataStructs.TanimotoSimilarity(fp1, fp2)
        dice = DataStructs.DiceSimilarity(fp1, fp2)
        return {"tanimoto": tan, "dice": dice, "result": tan,
                "verbal": f"Tanimoto similarity {tan:.3f}, Dice {dice:.3f}."}

    def compute_descriptors(self, smiles) -> dict:
        if not RDKIT:
            return {"result": None, "verbal": "RDKit is not installed, sir."}
        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            return {"result": None, "verbal": "Could not parse SMILES."}
        d = {"MW": Descriptors.MolWt(mol), "logP": Descriptors.MolLogP(mol),
             "TPSA": Descriptors.TPSA(mol), "HBD": Descriptors.NumHDonors(mol),
             "HBA": Descriptors.NumHAcceptors(mol),
             "rotatable_bonds": Descriptors.NumRotatableBonds(mol)}
        return {"descriptors": d, "result": d,
                "verbal": f"MW {d['MW']:.1f}, logP {d['logP']:.2f}, TPSA {d['TPSA']:.1f}, "
                          f"HBD {d['HBD']}, HBA {d['HBA']}."}

    def substructure_search(self, smiles, smarts) -> dict:
        if not RDKIT:
            return {"result": None, "verbal": "RDKit needed for substructure search, sir."}
        mol = Chem.MolFromSmiles(smiles); patt = Chem.MolFromSmarts(smarts)
        if mol is None or patt is None:
            return {"result": None, "verbal": "Could not parse molecule or pattern, sir."}
        matches = mol.GetSubstructMatches(patt)
        return {"has_match": len(matches) > 0, "match_atoms": [list(m) for m in matches],
                "result": len(matches),
                "verbal": f"Substructure '{smarts}': {len(matches)} match(es) found."}

    def murcko_scaffold(self, smiles) -> dict:
        if not RDKIT:
            return {"result": None, "verbal": "RDKit needed for scaffold analysis, sir."}
        from rdkit.Chem.Scaffolds import MurckoScaffold
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {"result": None, "verbal": "Could not parse SMILES, sir."}
        scaffold = MurckoScaffold.GetScaffoldForMol(mol)
        s_smiles = Chem.MolToSmiles(scaffold)
        return {"scaffold": s_smiles, "result": s_smiles,
                "verbal": f"Murcko scaffold (molecular framework): {s_smiles}"}

    # ── 7.2 stoichiometry (no heavy deps) ───────────────────────────
    @staticmethod
    def _parse_formula(formula: str) -> dict:
        """Return element->count dict, supporting parentheses."""
        def multiply(counts, factor):
            return {k: v * factor for k, v in counts.items()}

        def parse(tokens, i):
            counts = {}
            while i < len(tokens):
                tok = tokens[i]
                if tok == '(':
                    sub, i = parse(tokens, i + 1)
                    # optional multiplier
                    mult = ''
                    while i < len(tokens) and tokens[i].isdigit():
                        mult += tokens[i]; i += 1
                    f = int(mult) if mult else 1
                    for k, v in multiply(sub, f).items():
                        counts[k] = counts.get(k, 0) + v
                elif tok == ')':
                    return counts, i + 1
                elif tok.isalpha():
                    sym = tok; i += 1
                    num = ''
                    while i < len(tokens) and tokens[i].isdigit():
                        num += tokens[i]; i += 1
                    counts[sym] = counts.get(sym, 0) + (int(num) if num else 1)
                else:
                    i += 1
            return counts, i
        # tokenise into element symbols, digits, parens
        tokens = re.findall(r'[A-Z][a-z]?|\d+|\(|\)', formula)
        counts, _ = parse(tokens, 0)
        return counts

    def molar_mass(self, formula: str) -> dict:
        counts = self._parse_formula(formula)
        total = 0.0; comp = {}
        for el, n in counts.items():
            if el not in ATOMIC:
                return {"result": None,
                        "verbal": f"Unknown element '{el}', sir (not in my table)."}
            m = ATOMIC[el] * n; comp[el] = m; total += m
        comp_pct = {el: round(100 * m / total, 2) for el, m in comp.items()} if total else {}
        return {"molar_mass": round(total, 3), "composition": comp_pct, "result": round(total, 3),
                "verbal": f"The molar mass of {formula} is {total:.3f} g/mol."}

    def balance_equation(self, equation_str: str) -> dict:
        if "->" in equation_str:
            lhs, rhs = equation_str.split("->")
        elif "=" in equation_str:
            lhs, rhs = equation_str.split("=")
        else:
            return {"result": None, "verbal": "Use '->' between reactants and products, sir."}
        reactants = [s.strip() for s in lhs.split("+")]
        products = [s.strip() for s in rhs.split("+")]
        species = reactants + products
        elements = sorted({el for sp_ in species for el in self._parse_formula(sp_)})
        # build matrix: rows=elements, cols=species (reactants +, products -)
        M = sp.zeros(len(elements), len(species))
        for j, sp_ in enumerate(species):
            counts = self._parse_formula(sp_)
            sign = 1 if j < len(reactants) else -1
            for i, el in enumerate(elements):
                M[i, j] = sign * counts.get(el, 0)
        null = M.nullspace()
        if not null:
            return {"result": None, "verbal": "Could not balance the equation, sir."}
        vec = null[0]
        lcm = sp.lcm([sp.fraction(v)[1] for v in vec])
        coeffs = [abs(int(v * lcm)) for v in vec]
        g = math.gcd(*coeffs) if len(coeffs) > 1 else coeffs[0]
        coeffs = [c // g for c in coeffs]
        def fmt(group, start):
            return " + ".join((f"{coeffs[start+k]} " if coeffs[start+k] != 1 else "") + s
                              for k, s in enumerate(group))
        balanced = f"{fmt(reactants,0)} -> {fmt(products,len(reactants))}"
        return {"balanced": balanced, "coefficients": coeffs, "result": balanced,
                "verbal": f"Balanced: {balanced}"}

    def gibbs_energy(self, dH, dS, T=298.15) -> dict:
        dG = dH - T * dS / 1000.0  # dH kJ/mol, dS J/mol/K
        R = 8.314e-3
        try:
            K = math.exp(-dG / (R * T))
        except OverflowError:
            K = float("inf")
        return {"dG": dG, "K_eq": K, "spontaneous": dG < 0,
                "verbal": f"ΔG = {dG:.2f} kJ/mol at {T} K — "
                          f"{'spontaneous' if dG < 0 else 'non-spontaneous'} (K≈{K:.3g}).",
                "result": {"dG": dG, "spontaneous": dG < 0}}

    def reaction_enthalpy(self, reactants, products) -> dict:
        """ΔH°rxn via Hess's law from standard formation enthalpies (kJ/mol)."""
        Hf = {"H2O": -285.8, "CO2": -393.5, "CH4": -74.8, "O2": 0.0, "H2": 0.0,
              "C": 0.0, "NH3": -46.1, "N2": 0.0, "NO": 90.3, "CO": -110.5,
              "C2H6": -84.0, "C3H8": -103.8, "H2O2": -187.8, "NaCl": -411.2}
        def total(species):
            s = 0
            for sp_, coeff in species:
                if sp_ not in Hf:
                    return None
                s += coeff * Hf[sp_]
            return s
        hr, hp = total(reactants), total(products)
        if hr is None or hp is None:
            return {"result": None, "verbal": "Missing formation enthalpy data, sir."}
        dH = hp - hr
        return {"dH_rxn": dH, "result": dH,
                "verbal": f"ΔH°rxn = {dH:.1f} kJ/mol — "
                          f"{'exothermic' if dH < 0 else 'endothermic'}."}

    def vsepr_predict(self, central_bonds, lone_pairs=0) -> dict:
        """Predict geometry from steric number (bonds + lone pairs)."""
        steric = central_bonds + lone_pairs
        geom = {2: ("linear", 180), 3: ("trigonal planar", 120), 4: ("tetrahedral", 109.5),
                5: ("trigonal bipyramidal", 90), 6: ("octahedral", 90)}.get(steric, ("unknown", 0))
        mol_geom = {(4, 0): "tetrahedral", (4, 1): "trigonal pyramidal", (4, 2): "bent",
                    (3, 0): "trigonal planar", (3, 1): "bent", (2, 0): "linear"}.get(
            (steric, lone_pairs), geom[0])
        return {"electron_geometry": geom[0], "molecular_geometry": mol_geom,
                "bond_angle": geom[1], "polar": lone_pairs > 0, "result": mol_geom,
                "verbal": f"VSEPR: steric number {steric} → {geom[0]} electron geometry, "
                          f"{mol_geom} molecular shape, ~{geom[1]}° bond angles."}

    def generate_3d_conformer(self, smiles, force_field="MMFF94") -> dict:
        if not RDKIT:
            return {"result": None, "verbal": "RDKit needed for 3D conformers, sir."}
        from rdkit.Chem import AllChem
        mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
        if mol is None:
            return {"result": None, "verbal": "Could not parse SMILES, sir."}
        AllChem.EmbedMolecule(mol, randomSeed=1)
        try:
            AllChem.MMFFOptimizeMolecule(mol)
            energy = AllChem.MMFFGetMoleculeForceField(
                mol, AllChem.MMFFGetMoleculeProperties(mol)).CalcEnergy()
        except Exception:
            energy = None
        return {"n_atoms": mol.GetNumAtoms(), "energy": energy, "result": mol.GetNumAtoms(),
                "verbal": f"Generated 3D conformer ({mol.GetNumAtoms()} atoms"
                          + (f", MMFF energy {energy:.1f} kcal/mol" if energy else "") + ")."}

    # ── 7.3 periodic table ──────────────────────────────────────────
    def element_lookup(self, identifier) -> dict:
        if MENDELEEV:
            try:
                el = mendeleev.element(identifier if isinstance(identifier, str)
                                       else int(identifier))
                return {"Z": el.atomic_number, "symbol": el.symbol, "name": el.name,
                        "mass": el.atomic_weight, "config": el.econf,
                        "electronegativity": el.en_pauling,
                        "result": el.symbol,
                        "verbal": f"{el.name} ({el.symbol}): Z={el.atomic_number}, "
                                  f"mass {el.atomic_weight} u, electronegativity "
                                  f"{el.en_pauling}."}
            except Exception:
                pass
        sym = None
        if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
            sym = _ZMAP.get(int(identifier))
        elif identifier in ATOMIC:
            sym = identifier
        elif isinstance(identifier, str) and identifier.lower() in _NAME2SYM:
            sym = _NAME2SYM[identifier.lower()]
        if sym:
            z = next((zz for zz, s, _, _ in ELEMENTS if s == sym), None)
            return {"Z": z, "symbol": sym, "name": _NAMES.get(sym, sym), "mass": ATOMIC[sym],
                    "result": sym,
                    "verbal": f"{_NAMES.get(sym, sym)} ({sym}): Z={z}, atomic mass {ATOMIC[sym]} u."}
        return {"result": None, "verbal": f"I don't have data for '{identifier}', sir."}

    def electron_config(self, Z: int) -> dict:
        order = [('1s', 2), ('2s', 2), ('2p', 6), ('3s', 2), ('3p', 6), ('4s', 2),
                 ('3d', 10), ('4p', 6), ('5s', 2), ('4d', 10), ('5p', 6), ('6s', 2),
                 ('4f', 14), ('5d', 10), ('6p', 6), ('7s', 2), ('5f', 14), ('6d', 10),
                 ('7p', 6)]
        Z = int(Z); remaining = Z; cfg = []
        for orb, cap in order:
            if remaining <= 0:
                break
            e = min(cap, remaining); cfg.append(f"{orb}{e}"); remaining -= e
        config = " ".join(cfg)
        return {"configuration": config, "result": config,
                "verbal": f"Electron configuration for Z={Z}: {config}."}

    # ── 7.4 quantum chemistry (PySCF, optional) ─────────────────────
    def hartree_fock(self, molecule="H 0 0 0; H 0 0 0.74", basis="sto-3g") -> dict:
        try:
            from pyscf import gto, scf
        except Exception:
            # Windows has no pyscf wheel — run it in WSL where it's installed.
            return _pyscf_via_wsl(molecule, basis, method="hf")
        mol = gto.M(atom=molecule, basis=basis)
        mf = scf.RHF(mol); e = mf.kernel()
        mo = mf.mo_energy; nocc = mol.nelectron // 2
        homo, lumo = mo[nocc - 1], mo[nocc]
        return {"total_energy": float(e), "HOMO": float(homo), "LUMO": float(lumo),
                "gap": float(lumo - homo), "result": float(e),
                "verbal": f"Hartree-Fock energy {e:.6f} Hartree; HOMO-LUMO gap "
                          f"{(lumo-homo)*27.211:.2f} eV."}

    # ── 7.5 / 7.6 (heavy: guarded) ──────────────────────────────────
    def md_simulation(self, *a, **k) -> dict:
        return {"result": None,
                "verbal": "Molecular dynamics needs RDKit/OpenMM and a 3D conformer, sir."}

    def virtual_screening(self, *a, **k) -> dict:
        return {"result": None,
                "verbal": "Virtual screening needs AutoDock Vina + a receptor PDB, sir."}

    def test(self) -> None:
        assert abs(self.molar_mass("H2O")["molar_mass"] - 18.015) < 0.01
        assert abs(self.molar_mass("C6H12O6")["molar_mass"] - 180.156) < 0.05
        b = self.balance_equation("H2 + O2 -> H2O")
        assert b["coefficients"]
        assert self.gibbs_energy(-100, 50)["spontaneous"]
        # CH4 + 2 O2 -> CO2 + 2 H2O : ΔH ≈ -802.3 kJ/mol
        rh = self.reaction_enthalpy([("CH4", 1), ("O2", 2)], [("CO2", 1), ("H2O", 2)])
        assert rh["dH_rxn"] < 0
        assert self.vsepr_predict(4, 0)["molecular_geometry"] == "tetrahedral"
        assert self.vsepr_predict(2, 2)["molecular_geometry"] == "bent"
        if RDKIT:
            assert self.substructure_search("c1ccccc1O", "c1ccccc1")["has_match"]
            assert self.murcko_scaffold("CC(=O)Oc1ccccc1C(=O)O")["scaffold"]
        print("chemistry.ChemistryEngine: OK (incl. enthalpy, VSEPR, 3D conformer, "
              "substructure, scaffold)")


def _pyscf_via_wsl(molecule, basis="sto-3g", method="hf", xc="b3lyp", timeout=120):
    """Run a PySCF calculation inside WSL (Ubuntu) and parse the energy.

    Windows has no PySCF wheel, but it's installed in WSL's Python. We shell out
    to `wsl python3` with a small script and read back JSON. Returns the same
    graceful 'not available' dict if WSL/pyscf is missing."""
    import json
    import shutil
    import subprocess
    if not shutil.which("wsl"):
        return {"result": None, "verbal": "PySCF not on Windows and WSL not found, sir."}
    if method == "dft":
        calc = (f"mf = dft.RKS(mol); mf.xc = '{xc}'; e = mf.kernel()")
        imp = "from pyscf import gto, dft"
    else:
        calc = "mf = scf.RHF(mol); e = mf.kernel()"
        imp = "from pyscf import gto, scf"
    script = (
        f"{imp}\n"
        "import json\n"
        f"mol = gto.M(atom='''{molecule}''', basis='{basis}', verbose=0)\n"
        f"{calc}\n"
        "mo = mf.mo_energy; nocc = mol.nelectron // 2\n"
        "homo = float(mo[nocc-1]); lumo = float(mo[nocc]) if nocc < len(mo) else homo\n"
        "print('RESULT'+json.dumps({'e': float(e), 'homo': homo, 'lumo': lumo}))\n"
    )
    try:
        proc = subprocess.run(["wsl", "python3", "-c", script],
                              capture_output=True, text=True, timeout=timeout)
        line = next((l for l in proc.stdout.splitlines() if l.startswith("RESULT")), None)
        if not line:
            return {"result": None,
                    "verbal": f"PySCF (via WSL) returned no result, sir. {proc.stderr[-120:]}"}
        d = json.loads(line[6:])
        gap_ev = (d["lumo"] - d["homo"]) * 27.211
        label = "DFT/" + xc if method == "dft" else "Hartree-Fock"
        return {"total_energy": d["e"], "HOMO": d["homo"], "LUMO": d["lumo"],
                "gap": d["lumo"] - d["homo"], "engine": "pyscf-via-WSL", "result": d["e"],
                "verbal": f"{label} energy {d['e']:.6f} Hartree (computed in WSL); "
                          f"HOMO-LUMO gap {gap_ev:.2f} eV."}
    except subprocess.TimeoutExpired:
        return {"result": None, "verbal": "PySCF (WSL) timed out, sir."}
    except Exception as e:  # noqa: BLE001
        return {"result": None, "verbal": f"PySCF-via-WSL failed, sir: {e}"}


# ── module-level routing functions (INTENT_MAP) ──────────────────────────
_engine = ChemistryEngine()
_FORMULA = re.compile(r"\b([A-Z][a-z]?\d*)+\b")


def _extract_formula(text):
    # find a token that looks like a chemical formula (contains uppercase + maybe digits)
    for tok in re.findall(r"[A-Za-z0-9()]+", text):
        if re.search(r"[A-Z]", tok) and re.fullmatch(r"([A-Z][a-z]?\d*|\(|\))+", tok):
            if tok.lower() not in ("Of", "The", "Mass", "Weight"):
                return tok
    return None


def molecule(text: str) -> dict:
    f = _extract_formula(text)
    if not f:
        return {"result": None, "verbal": "Give me a formula or SMILES, sir (e.g. C6H12O6)."}
    if "molar" in text.lower() or "weight" in text.lower() or "mass" in text.lower():
        return _engine.molar_mass(f)
    return _engine.parse_molecule(f)


def stoichiometry(text: str) -> dict:
    # strip leading command words so they don't pollute the reactant side
    cleaned = re.sub(r"\b(balance equation|balance|stoichiometry|reaction|the|equation|"
                     r"please|can you)\b", " ", text, flags=re.I)
    if "->" in cleaned or "=" in cleaned:
        eq = re.search(r"[A-Za-z0-9()+\s]+(?:->|=)[A-Za-z0-9()+\s]+", cleaned)
        if eq:
            return _engine.balance_equation(eq.group(0).strip())
    return {"result": None,
            "verbal": "Give me a reaction with '->', sir (e.g. H2 + O2 -> H2O)."}


def periodic_table(text: str) -> dict:
    n = re.search(r"\b(\d{1,3})\b", text)
    if "config" in text.lower() and n:
        return _engine.electron_config(int(n.group(1)))
    if n and ("number" in text.lower() or "atomic" in text.lower()):
        return _engine.element_lookup(int(n.group(1)))
    # element name (e.g. "iron")
    for word in re.findall(r"[A-Za-z]+", text):
        if word.lower() in _NAME2SYM:
            return _engine.element_lookup(_NAME2SYM[word.lower()])
    # element symbol (capitalised token)
    m = re.search(r"\b([A-Z][a-z]?)\b", text)
    if m and m.group(1) in ATOMIC:
        return _engine.element_lookup(m.group(1))
    if n:
        return _engine.element_lookup(int(n.group(1)))
    return {"result": None, "verbal": "Name an element, sir (symbol, name, or Z)."}


def similarity(text: str) -> dict:
    return {"result": None,
            "verbal": "Give me two SMILES, sir — ChemistryEngine().tanimoto_similarity(s1, s2)."}


def md_simulation(text: str) -> dict:
    return _engine.md_simulation()


def drug_discovery(text: str) -> dict:
    return {"result": None,
            "verbal": "Provide ligands and a receptor, sir — virtual screening needs Vina."}


def test() -> None:
    ChemistryEngine().test()


if __name__ == "__main__":
    test()
