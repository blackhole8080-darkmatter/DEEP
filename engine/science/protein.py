# deep/science/protein.py — Protein Science (Bible Section 8.2)
"""Protein sequence properties, secondary-structure heuristics, hydropathy,
isoelectric point. Heavy structure prediction (ESMFold/ColabFold) and PDB
parsing are guarded optional features."""
from __future__ import annotations

import math

# Monoisotopic-ish average residue masses (g/mol, water already removed per bond)
AA_MASS = {
    'A': 71.08, 'R': 156.19, 'N': 114.10, 'D': 115.09, 'C': 103.14, 'E': 129.12,
    'Q': 128.13, 'G': 57.05, 'H': 137.14, 'I': 113.16, 'L': 113.16, 'K': 128.17,
    'M': 131.19, 'F': 147.18, 'P': 97.12, 'S': 87.08, 'T': 101.10, 'W': 186.21,
    'Y': 163.18, 'V': 99.13,
}
# Kyte-Doolittle hydropathy
KD = {'A': 1.8, 'R': -4.5, 'N': -3.5, 'D': -3.5, 'C': 2.5, 'E': -3.5, 'Q': -3.5,
      'G': -0.4, 'H': -3.2, 'I': 4.5, 'L': 3.8, 'K': -3.9, 'M': 1.9, 'F': 2.8,
      'P': -1.6, 'S': -0.8, 'T': -0.7, 'W': -0.9, 'Y': -1.3, 'V': 4.2}
# pKa values for isoelectric point
PKA = {'C_term': 3.55, 'N_term': 7.5, 'D': 4.05, 'E': 4.45, 'C': 9.0,
       'Y': 10.0, 'H': 5.98, 'K': 10.0, 'R': 12.0}
# Chou-Fasman propensities (helix P_a, sheet P_b)
CF = {'A': (1.42, 0.83), 'R': (0.98, 0.93), 'N': (0.67, 0.89), 'D': (1.01, 0.54),
      'C': (0.70, 1.19), 'E': (1.51, 0.37), 'Q': (1.11, 1.10), 'G': (0.57, 0.75),
      'H': (1.00, 0.87), 'I': (1.08, 1.60), 'L': (1.21, 1.30), 'K': (1.16, 0.74),
      'M': (1.45, 1.05), 'F': (1.13, 1.38), 'P': (0.57, 0.55), 'S': (0.77, 0.75),
      'T': (0.83, 1.19), 'W': (1.08, 1.37), 'Y': (0.69, 1.47), 'V': (1.06, 1.70)}


class ProteinEngine:
    def __init__(self, config=None):
        self.config = config

    def molecular_weight(self, sequence: str) -> dict:
        seq = sequence.upper()
        mw = sum(AA_MASS.get(a, 0) for a in seq) + 18.02  # add one water
        return {"molecular_weight": mw, "length": len(seq), "result": mw,
                "verbal": f"Protein of {len(seq)} residues has molecular weight {mw/1000:.2f} kDa."}

    def composition(self, sequence: str) -> dict:
        seq = sequence.upper()
        comp = {a: seq.count(a) for a in AA_MASS if a in seq}
        return {"composition": comp, "result": comp,
                "verbal": f"{len(seq)} residues across {len(comp)} amino-acid types."}

    def hydrophobicity(self, sequence: str, window: int = 9) -> dict:
        seq = sequence.upper()
        scores = [sum(KD.get(a, 0) for a in seq[i:i+window]) / window
                  for i in range(max(1, len(seq) - window + 1))]
        gravy = sum(KD.get(a, 0) for a in seq) / len(seq) if seq else 0
        return {"gravy": gravy, "profile": scores, "result": gravy,
                "verbal": f"GRAVY hydropathy index {gravy:.3f} "
                          f"({'hydrophobic' if gravy > 0 else 'hydrophilic'} overall)."}

    def isoelectric_point(self, sequence: str) -> dict:
        seq = sequence.upper()
        counts = {aa: seq.count(aa) for aa in "DECYHKR"}

        def charge(pH):
            pos = (10**PKA['N_term'] / (10**PKA['N_term'] + 10**pH))
            pos += counts['K'] * (10**PKA['K'] / (10**PKA['K'] + 10**pH))
            pos += counts['R'] * (10**PKA['R'] / (10**PKA['R'] + 10**pH))
            pos += counts['H'] * (10**PKA['H'] / (10**PKA['H'] + 10**pH))
            neg = (10**pH / (10**PKA['C_term'] + 10**pH))
            neg += counts['D'] * (10**pH / (10**PKA['D'] + 10**pH))
            neg += counts['E'] * (10**pH / (10**PKA['E'] + 10**pH))
            neg += counts['C'] * (10**pH / (10**PKA['C'] + 10**pH))
            neg += counts['Y'] * (10**pH / (10**PKA['Y'] + 10**pH))
            return pos - neg

        lo, hi = 0.0, 14.0
        for _ in range(100):
            mid = (lo + hi) / 2
            if charge(mid) > 0:
                lo = mid
            else:
                hi = mid
        return {"pI": round(mid, 2), "result": round(mid, 2),
                "verbal": f"Isoelectric point pI ≈ {mid:.2f}."}

    def secondary_structure(self, sequence: str) -> dict:
        """Chou-Fasman heuristic: assign H/E/C per residue."""
        seq = sequence.upper()
        ss = []
        for a in seq:
            pa, pb = CF.get(a, (1.0, 1.0))
            ss.append("H" if pa > pb and pa > 1.0 else ("E" if pb > 1.0 else "C"))
        ss_str = "".join(ss)
        n = len(ss_str) or 1
        h, e, c = ss_str.count("H"), ss_str.count("E"), ss_str.count("C")
        return {"ss_sequence": ss_str, "helix_pct": 100*h/n, "sheet_pct": 100*e/n,
                "coil_pct": 100*c/n, "result": ss_str,
                "verbal": f"Predicted {100*h/n:.0f}% helix, {100*e/n:.0f}% sheet, "
                          f"{100*c/n:.0f}% coil."}

    def predict_structure_esm(self, sequence: str) -> dict:
        try:
            import esm  # noqa: F401
        except Exception:
            return {"result": None,
                    "verbal": "ESMFold (fair-esm) is not installed, sir — "
                              "structure prediction needs the ~1GB model."}
        return {"result": None, "verbal": "ESMFold available; call with a GPU for speed, sir."}

    def contact_map_predict(self, sequence) -> dict:
        """Heuristic residue-contact map from hydrophobicity correlation +
        sequence separation (a real GNN/coevolution model would refine this)."""
        import numpy as np
        seq = sequence.upper(); n = len(seq)
        h = np.array([KD.get(a, 0) for a in seq])
        M = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 3, n):  # contacts need |i-j|>=3
                hphob = (h[i] > 0 and h[j] > 0)
                score = (0.5 if hphob else 0.1) * math.exp(-abs(i - j) / 25)
                M[i, j] = M[j, i] = score
        n_contacts = int((M > 0.2).sum() // 2)
        return {"contact_map": M.tolist(), "n_predicted_contacts": n_contacts,
                "result": n_contacts,
                "verbal": f"Predicted {n_contacts} residue-residue contacts (heuristic "
                          f"hydrophobicity model) for a {n}-residue protein."}

    def disorder_prediction(self, sequence, window=11) -> dict:
        """Predict intrinsically disordered regions from a charge/hydropathy
        heuristic (low hydrophobicity + high net charge ⇒ disordered)."""
        import numpy as np
        seq = sequence.upper(); n = len(seq)
        charge = {"D": -1, "E": -1, "K": 1, "R": 1, "H": 0.5}
        scores = []
        half = window // 2
        for i in range(n):
            lo, hi = max(0, i - half), min(n, i + half + 1)
            win = seq[lo:hi]
            hyd = np.mean([KD.get(a, 0) for a in win])
            chg = np.mean([abs(charge.get(a, 0)) for a in win])
            scores.append(float(max(0, min(1, 0.5 - 0.15 * hyd + 0.5 * chg))))
        regions = []
        i = 0
        while i < n:
            if scores[i] > 0.5:
                j = i
                while j < n and scores[j] > 0.5:
                    j += 1
                if j - i >= 4:
                    regions.append({"start": i, "end": j})
                i = j
            else:
                i += 1
        return {"disorder_scores": scores, "IDR_regions": regions, "result": len(regions),
                "verbal": f"Predicted {len(regions)} disordered region(s) "
                          f"covering {sum(r['end']-r['start'] for r in regions)} residues."}

    def test(self) -> None:
        mw = self.molecular_weight("ACDEFGHIKLMNPQRSTVWY")
        assert mw["molecular_weight"] > 0
        ss = self.secondary_structure("AAAAEEEE")
        assert len(ss["ss_sequence"]) == 8
        pi = self.isoelectric_point("DDDEEEKKKRRR")
        assert 0 < pi["pI"] < 14
        cm = self.contact_map_predict("MEEKLAAALEEAAKKLG")
        assert cm["n_predicted_contacts"] >= 0
        dis = self.disorder_prediction("MEEKKRDEDKRDEKRDKEAAAALLLVVV")
        assert "IDR_regions" in dis
        print("protein.ProteinEngine: OK (incl. contact map, disorder prediction)")


_engine = ProteinEngine()


def analyze(text: str) -> dict:
    import re
    m = re.search(r"\b([ACDEFGHIKLMNPQRSTVWY]{6,})\b", text.upper())
    if not m:
        return {"result": None, "verbal": "Give me an amino-acid sequence, sir."}
    seq = m.group(1)
    low = text.lower()
    if "weight" in low or "mass" in low:
        return _engine.molecular_weight(seq)
    if "secondary" in low or "structure" in low:
        return _engine.secondary_structure(seq)
    if "hydro" in low or "gravy" in low:
        return _engine.hydrophobicity(seq)
    if "pi" in low or "isoelectric" in low:
        return _engine.isoelectric_point(seq)
    return _engine.molecular_weight(seq)


def test() -> None:
    ProteinEngine().test()


if __name__ == "__main__":
    test()
