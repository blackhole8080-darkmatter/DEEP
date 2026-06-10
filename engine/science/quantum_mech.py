# deep/science/quantum_mech.py — Deep Quantum Mechanics (Bible Section 11)
"""1D/2D Schrödinger, harmonic oscillator, hydrogen atom, tunnelling, spin
dynamics, perturbation theory, WKB, variational method, Bell test, DFT."""
from __future__ import annotations

import math
import re

import numpy as np

try:
    from scipy.linalg import eigh, expm
    from scipy.special import hermite, genlaguerre
    from scipy.optimize import minimize
    from scipy.integrate import quad
    try:                              # scipy >=1.15 renamed sph_harm -> sph_harm_y
        from scipy.special import sph_harm
    except ImportError:
        from scipy.special import sph_harm_y as sph_harm
    SCIPY = True
except Exception:  # pragma: no cover
    SCIPY = False


class QuantumMechanics:
    def __init__(self, config=None):
        self.config = config

    # ── Schrödinger (finite difference) ─────────────────────────────
    def schrodinger_1d(self, V_func, x_range=(-5, 5), n_states=5, N=500, hbar=1.0, m=1.0):
        if not SCIPY:
            return _no_scipy()
        x = np.linspace(x_range[0], x_range[1], N)
        dx = x[1] - x[0]
        if isinstance(V_func, str):
            Vexpr = V_func
            V = np.array([eval(Vexpr, {"x": xi, "np": np, "math": math}) for xi in x])
        else:
            V = np.array([V_func(xi) for xi in x])
        # Hamiltonian: -hbar^2/2m d²/dx² + V
        coeff = hbar**2 / (2 * m * dx**2)
        H = np.diag(2 * coeff + V) + np.diag(-coeff * np.ones(N - 1), 1) + \
            np.diag(-coeff * np.ones(N - 1), -1)
        energies, vecs = eigh(H, subset_by_index=[0, n_states - 1])
        wf = vecs.T / math.sqrt(dx)
        return {"energies": energies.tolist(), "wavefunctions": wf.tolist(),
                "x": x.tolist(), "plot_path": None, "anim_path": None,
                "verbal": f"Lowest {n_states} energies: " +
                          ", ".join(f"{e:.4f}" for e in energies),
                "result": {"energies": energies.tolist()}}

    def harmonic_oscillator_qm(self, n_max=5, omega=1.0, hbar=1.0, m=1.0):
        energies = [(n + 0.5) * hbar * omega for n in range(n_max + 1)]
        x = np.linspace(-6, 6, 400)
        wavefns = []
        if SCIPY:
            alpha = m * omega / hbar
            for n in range(n_max + 1):
                Hn = hermite(n)
                norm = (alpha / math.pi)**0.25 / math.sqrt(2**n * math.factorial(n))
                psi = norm * Hn(np.sqrt(alpha) * x) * np.exp(-alpha * x**2 / 2)
                wavefns.append(psi.tolist())
        return {"energies": energies, "wavefunctions": wavefns, "x": x.tolist(),
                "expectation_x": 0.0, "expectation_p": 0.0, "plot_path": None,
                "verbal": f"Quantum HO: E_n=(n+½)ℏω. Ground state E₀={energies[0]:.4f}, "
                          f"spacing ℏω={hbar*omega:.4f}.",
                "result": {"energies": energies}}

    def hydrogen_atom_wavefunction(self, n=1, l=0, m=0, grid_size=60):
        if not SCIPY:
            return _no_scipy()
        if l >= n or abs(m) > l:
            return {"result": None, "verbal": f"Invalid quantum numbers n={n}, l={l}, m={m}."}
        a0 = 1.0
        r = np.linspace(1e-6, 20 * n, grid_size)
        rho = 2 * r / (n * a0)
        Lag = genlaguerre(n - l - 1, 2 * l + 1)
        norm = math.sqrt((2 / (n * a0))**3 * math.factorial(n - l - 1) /
                         (2 * n * math.factorial(n + l)))
        R = norm * np.exp(-rho / 2) * rho**l * Lag(rho)
        prob_radial = (R**2 * r**2)
        E_n = -13.6 / n**2
        return {"r": r.tolist(), "R_nl": R.tolist(), "prob_density": prob_radial.tolist(),
                "energy_eV": E_n, "radial_plot_path": None, "verbal":
                f"Hydrogen ψ_{n}{l}{m}: binding energy {E_n:.3f} eV; "
                f"most probable radius ≈ {r[int(np.argmax(prob_radial))]:.2f} a₀.",
                "result": {"energy_eV": E_n}}

    def quantum_tunneling(self, E, V0, L, m=1.0):
        """Rectangular barrier transmission (E, V0 in eV; L in nm)."""
        hbar = 1.0545718e-34; me = 9.109e-31; eV = 1.602e-19
        E_j = E * eV; V0_j = V0 * eV; L_m = L * 1e-9; mass = m * me
        if E < V0:
            kappa = math.sqrt(2 * mass * (V0_j - E_j)) / hbar
            arg = kappa * L_m
            T = 1 / (1 + (V0_j**2 * math.sinh(arg)**2) / (4 * E_j * (V0_j - E_j)))
        else:
            k2 = math.sqrt(2 * mass * (E_j - V0_j)) / hbar
            arg = k2 * L_m
            denom = 4 * E_j * (E_j - V0_j)
            T = 1 / (1 + (V0_j**2 * math.sin(arg)**2) / denom) if denom else 1.0
        return {"T_coeff": T, "R_coeff": 1 - T, "plot_T_vs_E_path": None,
                "verbal": f"Tunnelling through {V0} eV barrier ({L} nm) at E={E} eV: "
                          f"transmission {T:.3e}.",
                "result": {"T_coeff": T}}

    def spin_dynamics(self, initial_state=None, B_field=(0, 0, 1), t_max=10.0, gamma=1.0):
        if not SCIPY:
            return _no_scipy()
        sx = np.array([[0, 1], [1, 0]], complex)
        sy = np.array([[0, -1j], [1j, 0]], complex)
        sz = np.array([[1, 0], [0, -1]], complex)
        Bx, By, Bz = B_field
        H = -gamma / 2 * (Bx * sx + By * sy + Bz * sz)
        psi0 = np.array(initial_state, complex) if initial_state else np.array([1, 0], complex)
        psi0 /= np.linalg.norm(psi0)
        ts = np.linspace(0, t_max, 200)
        Sx = []; Sy = []; Sz = []
        for t in ts:
            U = expm(-1j * H * t)
            psi = U @ psi0
            Sx.append(float(np.real(psi.conj() @ sx @ psi) / 2))
            Sy.append(float(np.real(psi.conj() @ sy @ psi) / 2))
            Sz.append(float(np.real(psi.conj() @ sz @ psi) / 2))
        larmor = gamma * math.sqrt(Bx**2 + By**2 + Bz**2)
        return {"Sx": Sx, "Sy": Sy, "Sz": Sz, "t": ts.tolist(), "Bloch_path": None,
                "verbal": f"Spin precesses at Larmor frequency {larmor:.3f} rad/s.",
                "result": {"larmor_freq": larmor}}

    def perturbation_theory(self, H0_energies, H0_states, H_prime, order=2):
        E0 = np.asarray(H0_energies, float)
        Hp = np.asarray(H_prime, float)
        n = len(E0)
        E1 = np.array([Hp[i, i] for i in range(n)])
        E2 = np.zeros(n)
        for i in range(n):
            for k in range(n):
                if k != i and abs(E0[i] - E0[k]) > 1e-12:
                    E2[i] += Hp[i, k] * Hp[k, i] / (E0[i] - E0[k])
        E_corr = E0 + E1 + (E2 if order >= 2 else 0)
        return {"E_corrected": E_corr.tolist(), "E1_corrections": E1.tolist(),
                "E2_corrections": E2.tolist(),
                "verbal": f"First-order corrections: " +
                          ", ".join(f"{e:.4f}" for e in E1) + ".",
                "result": {"E_corrected": E_corr.tolist()}}

    def bell_inequality_test(self, a1=0, a2=math.pi/4, b1=math.pi/8, b2=3*math.pi/8,
                             n_trials=10000):
        def E(a, b):
            return -math.cos(2 * (a - b))
        S = E(a1, b1) - E(a1, b2) + E(a2, b1) + E(a2, b2)
        return {"S_quantum": S, "S_classical": 2.0, "violation": abs(S) > 2,
                "verbal": f"CHSH S = {S:.4f} (classical bound 2). "
                          f"{'Bell inequality violated — quantum!' if abs(S) > 2 else 'No violation.'}",
                "result": {"S": S}}

    def wkb_approximation(self, V_func, E, x_range=(-5, 5), n=400):
        """WKB: turning points + action integral + tunnelling probability."""
        if not SCIPY:
            return _no_scipy()
        x = np.linspace(*x_range, n)
        V = np.array([V_func(xi) for xi in x])
        classically_forbidden = V > E
        # action through the barrier (imaginary momentum)
        kappa = np.sqrt(np.clip(2 * (V - E), 0, None))
        dx = x[1] - x[0]
        action = float(np.sum(kappa[classically_forbidden]) * dx)
        T = math.exp(-2 * action)
        tp = x[np.where(np.diff(classically_forbidden.astype(int)) != 0)[0]]
        return {"turning_points": tp.tolist(), "action": action, "T_WKB": T,
                "result": {"T_WKB": T},
                "verbal": f"WKB approximation: action integral {action:.3f}, "
                          f"tunnelling probability T≈{T:.3e}."}

    def variational_method(self, V_func=None, trial=None, params_init=(1.0,)):
        """Variational ground-state energy for a 1D potential (Gaussian trial)."""
        if not SCIPY:
            return _no_scipy()
        V_func = V_func or (lambda x: 0.5 * x**2)  # harmonic
        x = np.linspace(-8, 8, 600); dx = x[1] - x[0]

        def energy(p):
            a = abs(p[0]) + 1e-3
            psi = (a / math.pi)**0.25 * np.exp(-a * x**2 / 2)
            psi /= np.sqrt(np.sum(psi**2) * dx)
            d2 = np.gradient(np.gradient(psi, dx), dx)
            H = -0.5 * d2 + np.array([V_func(xi) for xi in x]) * psi
            return float(np.sum(psi * H) * dx)
        res = minimize(energy, list(params_init), method="Nelder-Mead")
        return {"E_variational": res.fun, "optimal_params": res.x.tolist(),
                "result": {"E": res.fun},
                "verbal": f"Variational ground-state energy estimate {res.fun:.4f} "
                          f"(exact harmonic = 0.5)."}

    def schrodinger_2d(self, V_func=None, n_states=3, N=40, L=6.0):
        """2D Schrödinger via sparse finite difference (returns lowest energies)."""
        if not SCIPY:
            return _no_scipy()
        from scipy.sparse import diags, kron, identity
        from scipy.sparse.linalg import eigsh
        x = np.linspace(-L/2, L/2, N); dx = x[1] - x[0]
        V_func = V_func or (lambda X, Y: 0.5 * (X**2 + Y**2))
        lap1 = diags([1, -2, 1], [-1, 0, 1], shape=(N, N)) / dx**2
        I = identity(N)
        Lap = kron(lap1, I) + kron(I, lap1)
        X, Y = np.meshgrid(x, x)
        Vdiag = diags(V_func(X, Y).ravel())
        H = -0.5 * Lap + Vdiag
        vals = eigsh(H, k=n_states, which="SM", return_eigenvectors=False)
        vals = np.sort(vals)
        return {"energies": vals.tolist(), "result": {"energies": vals.tolist()},
                "verbal": f"2D Schrödinger lowest {n_states} energies: "
                          f"{', '.join(f'{e:.3f}' for e in vals)} (2D oscillator → 1,2,2,3…)."}

    def dft(self, atom="H 0 0 0; H 0 0 0.74", basis="sto-3g", xc="b3lyp"):
        """DFT energy via PySCF — native if importable, else run it in WSL."""
        try:
            from pyscf import gto, dft as pyscf_dft
        except Exception:
            from .chemistry import _pyscf_via_wsl
            out = _pyscf_via_wsl(atom, basis, method="dft", xc=xc)
            if out.get("result") is not None:
                out["energy_hartree"] = out["result"]
            return out
        mol = gto.M(atom=atom, basis=basis)
        mf = pyscf_dft.RKS(mol); mf.xc = xc
        e = mf.kernel()
        return {"energy_hartree": float(e), "result": float(e),
                "verbal": f"DFT/{xc} ground-state energy: {e:.6f} Hartree."}

    def test(self) -> None:
        ho = self.harmonic_oscillator_qm(3, 1.0)
        assert abs(ho["energies"][0] - 0.5) < 1e-9
        t = self.quantum_tunneling(1.0, 2.0, 1.0)
        assert 0 < t["T_coeff"] < 1
        b = self.bell_inequality_test()
        assert b["violation"]
        assert self.variational_method()["E_variational"] < 0.6   # ~0.5 harmonic
        assert self.wkb_approximation(lambda x: 5 if abs(x) < 1 else 0, 1.0)["T_WKB"] < 1
        if SCIPY:
            e2 = self.schrodinger_2d(n_states=3)["energies"]
            assert abs(e2[0] - 1.0) < 0.3   # 2D SHO ground state ≈ 1
        print("quantum_mech.QuantumMechanics: OK (incl. WKB, variational, 2D Schrödinger)")


def _no_scipy():
    return {"result": None, "verbal": "scipy not available, sir."}


# ── module-level routing functions (INTENT_MAP) ──────────────────────────
_engine = QuantumMechanics()
# Ignore digits glued to a letter label (e.g. the 0 in "V0") so we extract real values.
_NUM = re.compile(r"(?<![A-Za-z0-9.])-?\d+\.?\d*(?:[eE][+-]?\d+)?")


def _nums(text):
    return [float(x) for x in _NUM.findall(text)]


def schrodinger(text: str) -> dict:
    return _engine.schrodinger_1d("0.5*x**2", n_states=5)  # default: SHO potential


def harmonic_oscillator(text: str) -> dict:
    n = _nums(text)
    return _engine.harmonic_oscillator_qm(int(n[0]) if n else 5,
                                          n[1] if len(n) > 1 else 1.0)


def hydrogen(text: str) -> dict:
    n = [int(x) for x in re.findall(r"\d+", text)]
    nn = n[0] if len(n) > 0 else 1
    ll = n[1] if len(n) > 1 else 0
    mm = n[2] if len(n) > 2 else 0
    return _engine.hydrogen_atom_wavefunction(nn, ll, mm)


def tunneling(text: str) -> dict:
    n = _nums(text)
    E = n[0] if len(n) > 0 else 1.0
    V0 = n[1] if len(n) > 1 else 2.0
    L = n[2] if len(n) > 2 else 1.0
    return _engine.quantum_tunneling(E, V0, L)


def spin(text: str) -> dict:
    return _engine.spin_dynamics()


def perturbation(text: str) -> dict:
    return {"result": None,
            "verbal": "Provide H0 energies and H' matrix, sir — "
                      "QuantumMechanics().perturbation_theory(E0, states, Hp)."}


def dft(text: str) -> dict:
    return _engine.dft()


def test() -> None:
    QuantumMechanics().test()


if __name__ == "__main__":
    test()
