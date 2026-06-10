# deep/science/nuclear.py — Nuclear Physics & Energy (Bible Section 10)
"""Binding energy (Bethe-Weizsäcker), radioactive decay, fusion/fission
Q-values, reactor point kinetics, Lawson criterion, radiation dosimetry."""
from __future__ import annotations

import math
import re

import numpy as np

try:
    from scipy.integrate import solve_ivp
    SCIPY = True
except Exception:  # pragma: no cover
    SCIPY = False

MAGIC = [2, 8, 20, 28, 50, 82, 126]
# Half-lives (seconds) for common isotopes
HALF_LIFE = {
    'U-235': 2.221e16, 'U-238': 1.41e17, 'C-14': 1.81e11, 'Co-60': 1.663e8,
    'I-131': 6.93e5, 'Cs-137': 9.49e8, 'Ra-226': 5.05e10, 'Pu-239': 7.6e11,
    'H-3': 3.89e8, 'Sr-90': 9.08e8, 'Tc-99m': 2.16e4, 'Rn-222': 3.30e5,
}
# Mass excess (MeV) for light nuclei (for fusion Q-values)
MASS_EXCESS = {'n': 8.071, 'H-1': 7.289, 'H-2': 13.136, 'H-3': 14.950,
               'He-3': 14.931, 'He-4': 2.425, 'Li-6': 14.087, 'Li-7': 14.907}


class NuclearEngine:
    def __init__(self, config=None):
        self.config = config

    # ── binding energy (SEMF) ───────────────────────────────────────
    def binding_energy(self, Z, A) -> dict:
        Z, A = int(Z), int(A)
        N = A - Z
        aV, aS, aC, aA, aP = 15.75, 17.8, 0.711, 23.7, 11.18
        vol = aV * A
        surf = -aS * A**(2/3)
        coul = -aC * Z * (Z - 1) / A**(1/3)
        asym = -aA * (A - 2 * Z)**2 / A
        if A % 2 == 1:
            pair = 0.0
        elif Z % 2 == 0 and N % 2 == 0:
            pair = aP / A**0.5
        else:
            pair = -aP / A**0.5
        BE = vol + surf + coul + asym + pair
        return {"BE_total": BE, "BE_per_nucleon": BE / A,
                "terms": {"volume": vol, "surface": surf, "coulomb": coul,
                          "asymmetry": asym, "pairing": pair},
                "result": {"BE_total": BE, "BE_per_nucleon": BE / A},
                "verbal": f"Z={Z}, A={A}: total binding energy {BE:.2f} MeV, "
                          f"{BE/A:.3f} MeV per nucleon."}

    def nuclear_shell_model(self, Z, N) -> dict:
        Z, N = int(Z), int(N)
        near_Z = [m for m in MAGIC if abs(m - Z) <= 2]
        near_N = [m for m in MAGIC if abs(m - N) <= 2]
        doubly = Z in MAGIC and N in MAGIC
        return {"magic_Z_nearby": near_Z, "magic_N_nearby": near_N,
                "doubly_magic": doubly, "result": {"doubly_magic": doubly},
                "verbal": f"Z={Z}, N={N}: "
                          + ("doubly magic — exceptionally stable." if doubly else
                             f"{'Z is magic. ' if Z in MAGIC else ''}"
                             f"{'N is magic.' if N in MAGIC else 'no closed shells nearby.'}")}

    # ── decay ───────────────────────────────────────────────────────
    def radioactive_decay(self, isotope, t_max=None, activity0=1.0) -> dict:
        thalf = HALF_LIFE.get(isotope)
        if thalf is None:
            return {"result": None,
                    "verbal": f"I don't have a half-life for {isotope}, sir."}
        lam = math.log(2) / thalf
        t_max = t_max or 5 * thalf
        t = np.linspace(0, t_max, 200)
        A = activity0 * np.exp(-lam * t)
        mean_life = 1 / lam
        return {"t": t.tolist(), "A": A.tolist(), "half_life_s": thalf,
                "mean_lifetime_s": mean_life, "decay_const": lam,
                "result": {"half_life_s": thalf},
                "verbal": f"{isotope}: half-life {thalf:.3e} s ({thalf/3.156e7:.3g} yr), "
                          f"mean lifetime {mean_life:.3e} s."}

    def decay_chain(self, lambdas=(0.05, 0.2, 0.0), t_max=60, n0=(1.0, 0.0, 0.0)) -> dict:
        """Solve the Bateman equations for a multi-step decay chain numerically."""
        if not SCIPY:
            return {"result": None, "verbal": "scipy needed for Bateman solver, sir."}
        lam = np.asarray(lambdas, float)

        def chain(t, N):
            dN = np.zeros_like(N)
            dN[0] = -lam[0] * N[0]
            for i in range(1, len(N)):
                dN[i] = lam[i-1] * N[i-1] - lam[i] * N[i]
            return dN
        sol = solve_ivp(chain, [0, t_max], list(n0), t_eval=np.linspace(0, t_max, 200))
        finals = sol.y[:, -1]
        return {"t": sol.t.tolist(), "activities": sol.y.tolist(),
                "result": finals.tolist(),
                "verbal": f"Bateman chain solved: final populations "
                          f"{[round(float(v), 3) for v in finals]}."}

    def neutron_diffusion_1d(self, width=100.0, D=1.0, Sigma_a=0.02, nuSigma_f=0.025,
                             n_mesh=100) -> dict:
        """1-group 1D neutron diffusion eigenvalue problem -> k_eff and flux."""
        dx = width / n_mesh
        # build -D φ'' + Σa φ = (1/k) νΣf φ  with zero-flux boundaries
        main = (2 * D / dx**2 + Sigma_a) * np.ones(n_mesh)
        off = (-D / dx**2) * np.ones(n_mesh - 1)
        A = np.diag(main) + np.diag(off, 1) + np.diag(off, -1)
        F = nuSigma_f * np.eye(n_mesh)
        # generalised eigenproblem A φ = (1/k) F φ  ->  largest k
        evals = np.linalg.eigvals(np.linalg.solve(A, F))
        k_eff = float(np.max(evals.real))
        return {"k_eff": k_eff, "critical": abs(k_eff - 1) < 0.05,
                "result": {"k_eff": k_eff},
                "verbal": f"1D neutron diffusion: k_eff = {k_eff:.4f} — reactor is "
                          f"{'critical' if abs(k_eff-1)<0.02 else ('supercritical' if k_eff>1 else 'subcritical')}."}

    def monte_carlo_neutron(self, n_neutrons=5000, slab_width=10.0, Sigma_t=0.5,
                            Sigma_s=0.4, Sigma_f=0.05) -> dict:
        """Simple Monte Carlo neutron transport in a slab; estimates leakage & k."""
        rng = np.random.default_rng(0)
        absorbed = scattered = leaked = fissioned = 0
        for _ in range(n_neutrons):
            x = slab_width / 2; mu = rng.uniform(-1, 1); alive = True
            while alive:
                d = -math.log(rng.random()) / Sigma_t
                x += mu * d
                if x < 0 or x > slab_width:
                    leaked += 1; break
                r = rng.random() * Sigma_t
                if r < Sigma_s:
                    mu = rng.uniform(-1, 1); scattered += 1
                elif r < Sigma_s + Sigma_f:
                    fissioned += 1; alive = False
                else:
                    absorbed += 1; alive = False
        k_mc = fissioned * 2.4 / n_neutrons  # ν≈2.4 neutrons per fission
        return {"leaked": leaked, "absorbed": absorbed, "fissioned": fissioned,
                "leakage_fraction": leaked / n_neutrons, "k_mc": k_mc,
                "result": {"k_mc": k_mc, "leakage": leaked / n_neutrons},
                "verbal": f"MC neutron transport ({n_neutrons} histories): "
                          f"{100*leaked/n_neutrons:.1f}% leaked, k≈{k_mc:.3f}."}

    # ── reactions ───────────────────────────────────────────────────
    def fusion_reaction(self, reactants=("H-2", "H-3"), T_keV=10) -> dict:
        # D + T -> He-4 + n   (Q from mass excess)
        if set(reactants) == {"H-2", "H-3"}:
            products = ["He-4", "n"]
        elif set(reactants) == {"H-2"}:
            products = ["He-3", "n"]
        else:
            products = []
        if not products:
            return {"result": None, "verbal": "I can do D-T or D-D fusion, sir."}
        Q = sum(MASS_EXCESS[r] for r in reactants) - sum(MASS_EXCESS[p] for p in products)
        return {"Q_value": Q, "products": products, "result": {"Q_value": Q},
                "verbal": f"Fusion {'+'.join(reactants)} → {'+'.join(products)}: "
                          f"Q = {Q:.2f} MeV released."}

    def lawson_criterion(self, T_keV=15, n=1e20, tau_E=3) -> dict:
        n_tau = n * tau_E
        triple = n * tau_E * T_keV
        required = 1.5e20  # s/m^3 for D-T ignition
        triple_req = 3e21  # keV s / m^3
        return {"n_tau": n_tau, "triple_product": triple,
                "ignition": triple >= triple_req,
                "result": {"triple_product": triple, "ignition": triple >= triple_req},
                "verbal": f"Triple product nTτ = {triple:.2e} keV·s/m³ "
                          f"(ignition needs ≳ {triple_req:.0e}) — "
                          f"{'ignition achievable' if triple >= triple_req else 'below ignition'}."}

    # ── reactor ─────────────────────────────────────────────────────
    def point_kinetics(self, rho=200, Lambda=2e-5, t_max=10) -> dict:
        """6-group reactor point kinetics. rho in pcm."""
        if not SCIPY:
            return {"result": None, "verbal": "scipy not available, sir."}
        beta_i = np.array([0.00021, 0.00141, 0.00127, 0.00255, 0.00074, 0.00027])
        lam_i = np.array([0.0124, 0.0305, 0.111, 0.301, 1.14, 3.01])
        beta = beta_i.sum()
        rho_frac = rho / 1e5  # pcm -> fraction

        def kin(t, y):
            n = y[0]; C = y[1:]
            dn = (rho_frac - beta) / Lambda * n + np.sum(lam_i * C)
            dC = beta_i / Lambda * n - lam_i * C
            return [dn, *dC]
        C0 = beta_i / (Lambda * lam_i)
        sol = solve_ivp(kin, [0, t_max], [1.0, *C0], max_step=t_max/2000)
        n_final = sol.y[0][-1]
        period = t_max / math.log(n_final) if n_final > 1 else float("inf")
        return {"t": sol.t.tolist(), "n": sol.y[0].tolist(), "reactor_period_s": period,
                "result": {"n_final": n_final},
                "verbal": f"Reactor with {rho} pcm reactivity: neutron population "
                          f"×{n_final:.2f} over {t_max}s (β={beta*1e5:.0f} pcm)."}

    # ── radiation safety ────────────────────────────────────────────
    def radiation_dose(self, source_activity, material="lead", thickness=1.0,
                       distance=1.0, energy_MeV=1.0) -> dict:
        # linear attenuation coeff (1/cm) approximate at ~1 MeV
        mu = {"lead": 0.77, "concrete": 0.15, "water": 0.07, "iron": 0.42,
              "air": 1e-4}.get(material, 0.2)
        transmission = math.exp(-mu * thickness)
        hvl = math.log(2) / mu
        # crude dose rate ~ A/(distance^2) scaled, mSv/hr
        dose_unshielded = source_activity * energy_MeV * 1.6e-13 / (4 * math.pi * distance**2)
        dose = dose_unshielded * transmission * 3.6e6  # to mSv/hr-ish scale
        return {"transmission": transmission, "HVL_cm": hvl, "dose_rate": dose,
                "result": {"transmission": transmission, "HVL_cm": hvl},
                "verbal": f"{thickness} cm of {material}: transmission {transmission*100:.1f}%, "
                          f"half-value layer {hvl:.2f} cm."}

    def test(self) -> None:
        be = self.binding_energy(26, 56)  # Fe-56
        assert abs(be["BE_per_nucleon"] - 8.79) < 0.3
        f = self.fusion_reaction(("H-2", "H-3"))
        assert abs(f["Q_value"] - 17.6) < 0.5
        assert self.nuclear_shell_model(82, 126)["doubly_magic"]
        # heavy solvers
        assert self.decay_chain()["result"]
        assert self.neutron_diffusion_1d()["k_eff"] > 0
        mc = self.monte_carlo_neutron(n_neutrons=1500)
        assert 0 <= mc["leakage_fraction"] <= 1
        print("nuclear.NuclearEngine: OK (incl. Bateman, diffusion k_eff, MC transport)")


_engine = NuclearEngine()
_NUM = re.compile(r"(?<![A-Za-z0-9.-])-?\d+\.?\d*(?:[eE][+-]?\d+)?")


def _nums(text):
    return [float(x) for x in _NUM.findall(text)]


def _isotope(text):
    m = re.search(r"\b([A-Z][a-z]?-\d{1,3})\b", text)
    return m.group(1) if m else None


def radioactive_decay(text: str) -> dict:
    iso = _isotope(text)
    if iso:
        return _engine.radioactive_decay(iso)
    return {"result": None, "verbal": "Name an isotope, sir (e.g. Co-60, U-235)."}


def nuclear_reaction(text: str) -> dict:
    low = text.lower()
    if "fusion" in low or "d-t" in low or "deuterium" in low:
        return _engine.fusion_reaction()
    if "lawson" in low or "ignition" in low:
        return _engine.lawson_criterion()
    return _engine.fusion_reaction()


def reactor(text: str) -> dict:
    n = _nums(text)
    return _engine.point_kinetics(rho=n[0] if n else 200)


def nuclear_structure(text: str) -> dict:
    n = [int(x) for x in re.findall(r"\d+", text)]
    if len(n) >= 2:
        Z, A = n[0], n[1]
        if A < Z:
            Z, A = A, Z
        return _engine.binding_energy(Z, A)
    return {"result": None, "verbal": "Give me Z and A, sir (e.g. binding energy Z=26 A=56)."}


def radiation_safety(text: str) -> dict:
    n = _nums(text)
    mat = next((m for m in ("lead", "concrete", "water", "iron", "air")
                if m in text.lower()), "lead")
    return _engine.radiation_dose(n[0] if n else 1e9, mat,
                                  n[1] if len(n) > 1 else 1.0)


def test() -> None:
    NuclearEngine().test()


if __name__ == "__main__":
    test()
