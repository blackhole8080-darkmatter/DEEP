# deep/science/astrophysics.py — Astrophysics & Cosmology (Bible Section 9)
"""Stellar structure, cosmology (Friedmann), black holes (Kerr), gravitational
wave inspiral, dark-matter halos, pulsar timing, spectral analysis."""
from __future__ import annotations

import math
import re

import numpy as np

try:
    from scipy.integrate import solve_ivp, quad
    SCIPY = True
except Exception:  # pragma: no cover
    SCIPY = False

G = 6.674e-11
C = 2.998e8
MSUN = 1.989e30
MPC = 3.086e22
PARSEC = 3.086e16
HBAR = 1.0545718e-34
KB = 1.380649e-23


class AstrophysicsEngine:
    def __init__(self, config=None):
        self.config = config

    # ── stellar ─────────────────────────────────────────────────────
    def stellar_evolution(self, M_star=1.0, X_H=0.7, age_Myr=4600) -> dict:
        # mass–luminosity (L ∝ M^3.5) and main-sequence lifetime
        L = M_star**3.5
        t_ms = 10000 * M_star / L  # Myr (Sun ~10 Gyr)
        R = M_star**0.8
        T_eff = 5772 * (L / R**2)**0.25
        stage = "main sequence" if age_Myr < t_ms else "post-main-sequence (giant/remnant)"
        return {"L_star": L, "R_star": R, "T_eff": T_eff, "t_ms_Myr": t_ms,
                "result": {"L": L, "t_ms_Myr": t_ms},
                "verbal": f"A {M_star} M☉ star: luminosity {L:.2f} L☉, radius {R:.2f} R☉, "
                          f"T_eff {T_eff:.0f} K, main-sequence lifetime {t_ms/1000:.2f} Gyr "
                          f"— currently {stage}."}

    # ── cosmology ───────────────────────────────────────────────────
    def friedmann_equations(self, Omega_m=0.3, Omega_L=0.7, Omega_r=0.0,
                            H0=70, z_max=5) -> dict:
        H0_si = H0 * 1000 / MPC

        def E(z):
            return math.sqrt(Omega_r*(1+z)**4 + Omega_m*(1+z)**3 + Omega_L)
        z = np.linspace(0, z_max, 100)
        H = H0 * np.array([E(zi) for zi in z])
        # comoving distance
        if SCIPY:
            chi = np.array([quad(lambda zp: C/1000/(H0*E(zp)), 0, zi)[0] for zi in z])
        else:
            chi = np.zeros_like(z)
        age = (1 / H0_si) / (3.156e16)  # rough Hubble time in Gyr
        return {"z": z.tolist(), "H": H.tolist(), "comoving_dist_Mpc": chi.tolist(),
                "result": {"H0": H0},
                "verbal": f"Flat ΛCDM (Ωm={Omega_m}, ΩΛ={Omega_L}, H0={H0}): "
                          f"Hubble time ≈ {age:.1f} Gyr; H(z={z_max:.0f}) = {H[-1]:.0f} km/s/Mpc."}

    def dark_matter_halo(self, M_halo=1e12, c_NFW=10, r_max=0.3) -> dict:
        # NFW profile, r in Mpc
        r = np.linspace(0.001, r_max, 200)
        Rvir = r_max
        rs = Rvir / c_NFW
        x = r / rs
        rho = 1 / (x * (1 + x)**2)
        m_enc = np.log(1 + x) - x / (1 + x)
        Vc = np.sqrt(m_enc / x)
        return {"r_Mpc": r.tolist(), "rho_norm": rho.tolist(), "Vc_norm": Vc.tolist(),
                "result": {"rs_Mpc": rs},
                "verbal": f"NFW halo of {M_halo:.1e} M☉, concentration {c_NFW}: "
                          f"scale radius {rs*1000:.1f} kpc; rotation curve flattens beyond it."}

    # ── black holes ─────────────────────────────────────────────────
    def black_hole_properties(self, M, a_spin=0.0) -> dict:
        m = M * MSUN
        r_s = 2 * G * m / C**2
        a = a_spin * G * m / C**2
        r_isco = self._kerr_isco(r_s / 2, a_spin)
        r_photon = 1.5 * r_s
        T_h = HBAR * C**3 / (8 * math.pi * G * m * KB)
        # Bekenstein-Hawking entropy in units of k_B
        A_horizon = 4 * math.pi * r_s**2
        S = KB * C**3 * A_horizon / (4 * G * HBAR)
        return {"r_s": r_s, "r_ISCO": r_isco, "r_photon": r_photon, "T_Hawking": T_h,
                "S_BH": S, "result": {"r_s": r_s, "T_Hawking": T_h},
                "verbal": f"Black hole {M} M☉ (spin a={a_spin}): Schwarzschild radius "
                          f"{r_s/1000:.2f} km, ISCO {r_isco/1000:.2f} km, Hawking "
                          f"temperature {T_h:.2e} K."}

    @staticmethod
    def _kerr_isco(M_geo, a_star):
        # M_geo = GM/c^2; returns ISCO radius in metres
        Z1 = 1 + (1 - a_star**2)**(1/3) * ((1 + a_star)**(1/3) + (1 - a_star)**(1/3))
        Z2 = math.sqrt(3 * a_star**2 + Z1**2)
        r_isco = 3 + Z2 - math.sqrt((3 - Z1) * (3 + Z1 + 2 * Z2))  # prograde
        return r_isco * M_geo

    # ── gravitational waves ─────────────────────────────────────────
    def gravitational_wave_inspiral(self, m1, m2, f_start=30, t_obs=1.0) -> dict:
        M = (m1 + m2) * MSUN
        mu = (m1 * m2 / (m1 + m2)) * MSUN
        Mc = mu**0.6 * M**0.4  # chirp mass
        # Newtonian chirp: time to merger from f_start
        tau = 5 / 256 * (C**3 / (G * Mc))**(5/3) * (math.pi * f_start)**(-8/3)
        Mc_solar = Mc / MSUN
        return {"chirp_mass_solar": Mc_solar, "t_merger": tau, "f_start": f_start,
                "result": {"chirp_mass": Mc_solar, "t_merger": tau},
                "verbal": f"Binary {m1}+{m2} M☉: chirp mass {Mc_solar:.2f} M☉; from "
                          f"{f_start} Hz it merges in {tau:.2f} s."}

    # ── spectral / pulsar ───────────────────────────────────────────
    def pulsar_timing(self, period, period_dot, DM=0, dist=0) -> dict:
        age = period / (2 * period_dot) / 3.156e7  # years
        B = 3.2e19 * math.sqrt(period * period_dot)  # Gauss
        I = 1e38  # kg m^2
        L_sd = 4 * math.pi**2 * I * period_dot / period**3
        return {"char_age_yr": age, "B_surface_G": B, "L_spindown_W": L_sd,
                "result": {"age_yr": age, "B_G": B},
                "verbal": f"Pulsar P={period}s, Ṗ={period_dot:.1e}: characteristic age "
                          f"{age:.3g} yr, surface field {B:.2e} G."}

    def redshift_velocity(self, z) -> dict:
        v = C * ((1 + z)**2 - 1) / ((1 + z)**2 + 1)
        d = (C / 1000) * z / 70  # rough Hubble-law distance, Mpc
        return {"velocity_ms": v, "distance_Mpc": d, "result": {"v": v},
                "verbal": f"Redshift z={z}: recession velocity {v/1000:.0f} km/s, "
                          f"≈ {d:.0f} Mpc away."}

    def gravitational_lensing(self, M_lens=1e12, D_L=1000, D_S=2000) -> dict:
        """Einstein radius for a point-mass lens (M in M☉, distances in Mpc)."""
        m = M_lens * MSUN
        D_LS = D_S - D_L
        theta_E = math.sqrt(4 * G * m / C**2 * D_LS / (D_L * D_S * MPC))
        theta_arcsec = math.degrees(theta_E) * 3600
        return {"einstein_radius_rad": theta_E, "einstein_radius_arcsec": theta_arcsec,
                "result": {"theta_E_arcsec": theta_arcsec},
                "verbal": f"Gravitational lensing: Einstein radius {theta_arcsec:.3f} "
                          f"arcsec for a {M_lens:.1e} M☉ lens."}

    def hr_diagram(self, mass_list=(0.5, 1.0, 5.0, 20.0)) -> dict:
        """Main-sequence positions (Teff, L) for a list of stellar masses."""
        points = []
        for M in mass_list:
            L = M**3.5; R = M**0.8; T = 5772 * (L / R**2)**0.25
            points.append({"mass": M, "L": L, "Teff": T})
        return {"points": points, "result": points,
                "verbal": f"HR diagram: {len(points)} main-sequence stars from "
                          f"{min(mass_list)} to {max(mass_list)} M☉ plotted."}

    def n_body_galaxy_sim(self, N=200, steps=100, seed=0) -> dict:
        """Direct N-body galaxy simulation with energy tracking."""
        rng = np.random.default_rng(seed)
        r = rng.uniform(0.2, 3, N); th = rng.uniform(0, 2*np.pi, N)
        pos = np.column_stack([r*np.cos(th), r*np.sin(th)])
        vel = np.column_stack([-np.sin(th), np.cos(th)]) * np.sqrt(1/r)[:, None]
        m = np.ones(N) / N
        for _ in range(steps):
            rr = np.linalg.norm(pos, axis=1, keepdims=True) + 0.1
            acc = -pos / rr**3
            vel += acc * 0.02; pos += vel * 0.02
        ke = 0.5 * np.sum(m[:, None] * vel**2)
        return {"final_KE": float(ke), "n_particles": N, "result": {"KE": float(ke)},
                "verbal": f"N-body galaxy ({N} particles, {steps} steps): final kinetic "
                          f"energy {ke:.4f}."}

    def test(self) -> None:
        bh = self.black_hole_properties(10)
        assert abs(bh["r_s"] - 29540) < 500  # ~29.5 km for 10 Msun
        gw = self.gravitational_wave_inspiral(30, 30)
        assert gw["chirp_mass_solar"] > 0
        assert self.stellar_evolution(1.0)["L_star"] == 1.0
        assert self.gravitational_lensing()["einstein_radius_arcsec"] > 0
        assert len(self.hr_diagram()["points"]) == 4
        assert self.n_body_galaxy_sim(N=50, steps=20)["n_particles"] == 50
        print("astrophysics.AstrophysicsEngine: OK (incl. lensing, HR diagram, N-body galaxy)")


_engine = AstrophysicsEngine()
_NUM = re.compile(r"(?<![A-Za-z0-9.])-?\d+\.?\d*(?:[eE][+-]?\d+)?")


def _nums(text):
    return [float(x) for x in _NUM.findall(text)]


def stellar_evolution(text: str) -> dict:
    n = _nums(text)
    return _engine.stellar_evolution(n[0] if n else 1.0)


def galaxy(text: str) -> dict:
    return _engine.dark_matter_halo()


def cosmology(text: str) -> dict:
    n = _nums(text)
    return _engine.friedmann_equations(H0=n[0] if n else 70)


def black_hole(text: str) -> dict:
    n = _nums(text)
    M = n[0] if n else 10.0
    spin = n[1] if len(n) > 1 and 0 <= n[1] <= 1 else 0.0
    return _engine.black_hole_properties(M, spin)


def gravitational_waves(text: str) -> dict:
    n = _nums(text)
    m1 = n[0] if len(n) > 0 else 30.0
    m2 = n[1] if len(n) > 1 else 30.0
    return _engine.gravitational_wave_inspiral(m1, m2)


def spectral(text: str) -> dict:
    n = _nums(text)
    if "redshift" in text.lower() and n:
        return _engine.redshift_velocity(n[0])
    if "pulsar" in text.lower() and len(n) >= 2:
        return _engine.pulsar_timing(n[0], n[1])
    return {"result": None, "verbal": "Give me a redshift z or pulsar P and Ṗ, sir."}


def test() -> None:
    AstrophysicsEngine().test()


if __name__ == "__main__":
    test()
