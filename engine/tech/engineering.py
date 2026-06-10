# deep/tech/engineering.py — Engineering (Bible Section 22)
"""FEA (Euler-Bernoulli beam), signal processing (FFT/filters/spectrogram),
control systems (transfer functions, state space), vibration analysis.
numpy/scipy core; the `control`/PySpice/pandapower libs are optional."""
from __future__ import annotations

import math
import re

import numpy as np

try:
    from scipy import signal as sig
    from scipy.linalg import eigh
    SCIPY = True
except Exception:  # pragma: no cover
    SCIPY = False


class EngineeringEngine:
    def __init__(self, config=None):
        self.config = config

    # ── 22.1 FEA: cantilever / simply-supported beam ────────────────
    def fea_beam(self, length=2.0, E=200e9, I=8e-6, load=1000.0,
                 support="cantilever") -> dict:
        """Euler-Bernoulli beam under a point load at the free end / centre."""
        L = length
        if support == "cantilever":
            delta_max = load * L**3 / (3 * E * I)
            M_max = load * L
        else:  # simply supported, central load
            delta_max = load * L**3 / (48 * E * I)
            M_max = load * L / 4
        # max bending stress assuming c = sqrt(I) proxy unavailable; report M
        return {"max_deflection_m": delta_max, "max_moment_Nm": M_max,
                "result": {"max_deflection_m": delta_max},
                "verbal": f"{support} beam ({L} m, EI={E*I:.2e}): max deflection "
                          f"{delta_max*1000:.3f} mm, max bending moment {M_max:.1f} N·m."}

    def euler_buckling(self, E=200e9, I=8e-6, L=2.0, K=1.0) -> dict:
        P_cr = math.pi**2 * E * I / (K * L)**2
        return {"critical_load_N": P_cr, "result": P_cr,
                "verbal": f"Euler critical buckling load: {P_cr/1000:.1f} kN."}

    # ── 22.2 signal processing ──────────────────────────────────────
    def fft_analysis(self, signal_array, sample_rate, window="hann") -> dict:
        x = np.asarray(signal_array, float)
        if SCIPY and window:
            w = sig.get_window(window, len(x))
            x = x * w
        spec = np.fft.rfft(x)
        freqs = np.fft.rfftfreq(len(x), 1 / sample_rate)
        mag = np.abs(spec)
        peaks = freqs[np.argsort(mag)[-3:]][::-1]
        return {"freqs": freqs.tolist(), "magnitude": mag.tolist(),
                "dominant_freqs": peaks.tolist(), "result": {"dominant_freqs": peaks.tolist()},
                "verbal": f"FFT dominant frequencies: "
                          f"{', '.join(f'{f:.1f} Hz' for f in peaks)}."}

    def filter_design(self, filter_type="butter", order=4, cutoff=100,
                      sample_rate=1000, btype="low") -> dict:
        if not SCIPY:
            return {"result": None, "verbal": "scipy.signal needed for filter design, sir."}
        wn = np.atleast_1d(cutoff) / (sample_rate / 2)
        if filter_type in ("cheby1", "chebyshev"):
            b, a = sig.cheby1(order, 1, wn, btype=btype)
        elif filter_type == "ellip":
            b, a = sig.ellip(order, 1, 40, wn, btype=btype)
        else:
            b, a = sig.butter(order, wn, btype=btype)
        return {"b": b.tolist(), "a": a.tolist(), "result": {"order": order},
                "verbal": f"Designed an order-{order} {btype}-pass {filter_type} filter "
                          f"at {cutoff} Hz."}

    # ── 22.3 control systems ────────────────────────────────────────
    def transfer_function_analysis(self, num, den) -> dict:
        num = np.atleast_1d(num).astype(float)
        den = np.atleast_1d(den).astype(float)
        poles = np.roots(den)
        zeros = np.roots(num)
        stable = bool(np.all(poles.real < 0))
        return {"poles": [complex(p) for p in poles], "zeros": [complex(z) for z in zeros],
                "stable": stable, "result": {"stable": stable},
                "verbal": f"Transfer function: poles at "
                          f"{[f'{p.real:.2f}{p.imag:+.2f}j' for p in poles]} — "
                          f"{'stable' if stable else 'unstable'}."}

    def step_response(self, num, den, t_end=10, n=200) -> dict:
        if not SCIPY:
            return {"result": None, "verbal": "scipy needed for step response, sir."}
        system = sig.TransferFunction(num, den)
        t, y = sig.step(system, T=np.linspace(0, t_end, n))
        ss = y[-1]
        overshoot = (np.max(y) - ss) / ss * 100 if ss else 0
        return {"t": t.tolist(), "y": y.tolist(), "steady_state": float(ss),
                "result": {"overshoot_pct": float(max(0, overshoot))},
                "verbal": f"Step response: steady-state {ss:.3f}, "
                          f"overshoot {max(0, overshoot):.1f}%."}

    # ── 22.4 vibration ──────────────────────────────────────────────
    def vibration_analysis(self, M, K) -> dict:
        if not SCIPY:
            return {"result": None, "verbal": "scipy needed for the eigenproblem, sir."}
        M = np.asarray(M, float); K = np.asarray(K, float)
        evals, evecs = eigh(K, M)
        omega = np.sqrt(np.abs(evals))
        freqs = omega / (2 * math.pi)
        return {"natural_freqs_hz": freqs.tolist(), "mode_shapes": evecs.tolist(),
                "result": {"natural_freqs_hz": freqs.tolist()},
                "verbal": f"Natural frequencies: "
                          f"{', '.join(f'{f:.2f} Hz' for f in freqs)}."}

    # ── 22.1 2D truss FEA (real stiffness assembly) ─────────────────
    def fea_truss(self, nodes, elements, supports, loads, E=2e11, A=1e-4) -> dict:
        """Planar truss direct-stiffness solver. nodes: [(x,y)], elements:
        [(i,j)], supports: {node: (fix_x, fix_y)}, loads: {node: (Fx, Fy)}."""
        nn = len(nodes); ndof = 2 * nn
        K = np.zeros((ndof, ndof))
        for (i, j) in elements:
            xi, yi = nodes[i]; xj, yj = nodes[j]
            L = math.hypot(xj - xi, yj - yi); c = (xj - xi) / L; s = (yj - yi) / L
            k = (E * A / L) * np.array([[c*c, c*s, -c*c, -c*s],
                                        [c*s, s*s, -c*s, -s*s],
                                        [-c*c, -c*s, c*c, c*s],
                                        [-c*s, -s*s, c*s, s*s]])
            dofs = [2*i, 2*i+1, 2*j, 2*j+1]
            for a in range(4):
                for b in range(4):
                    K[dofs[a], dofs[b]] += k[a, b]
        F = np.zeros(ndof)
        for node, (fx, fy) in loads.items():
            F[2*node] += fx; F[2*node+1] += fy
        fixed = []
        for node, (fxd_x, fxd_y) in supports.items():
            if fxd_x: fixed.append(2*node)
            if fxd_y: fixed.append(2*node+1)
        free = [d for d in range(ndof) if d not in fixed]
        u = np.zeros(ndof)
        u[np.ix_(free)] = np.linalg.solve(K[np.ix_(free, free)], F[free])
        # element axial stresses
        stresses = []
        for (i, j) in elements:
            xi, yi = nodes[i]; xj, yj = nodes[j]
            L = math.hypot(xj - xi, yj - yi); c = (xj - xi)/L; s = (yj - yi)/L
            du = np.array([u[2*j]-u[2*i], u[2*j+1]-u[2*i+1]])
            stresses.append(float(E/L * (c*du[0] + s*du[1])))
        return {"displacements": u.tolist(), "stresses": stresses,
                "max_displacement": float(np.abs(u).max()), "result": {"stresses": stresses},
                "verbal": f"Truss FEA: {nn} nodes, {len(elements)} members; max nodal "
                          f"displacement {np.abs(u).max()*1000:.3f} mm, max axial stress "
                          f"{max(abs(s) for s in stresses)/1e6:.1f} MPa."}

    def spectrogram(self, signal_array, sample_rate, nperseg=128) -> dict:
        if not SCIPY:
            return {"result": None, "verbal": "scipy.signal needed, sir."}
        f, t, Sxx = sig.spectrogram(np.asarray(signal_array, float), sample_rate, nperseg=nperseg)
        peak_f = float(f[np.unravel_index(np.argmax(Sxx), Sxx.shape)[0]])
        return {"f": f.tolist(), "t": t.tolist(), "peak_freq": peak_f,
                "result": {"peak_freq": peak_f},
                "verbal": f"Spectrogram: {len(t)} time bins, peak energy at {peak_f:.1f} Hz."}

    def psd_estimate(self, signal_array, sample_rate, method="welch") -> dict:
        if not SCIPY:
            return {"result": None, "verbal": "scipy.signal needed, sir."}
        f, P = sig.welch(np.asarray(signal_array, float), sample_rate)
        peak = float(f[np.argmax(P)])
        return {"freqs": f.tolist(), "psd": P.tolist(), "peak_freq": peak,
                "result": {"peak_freq": peak},
                "verbal": f"Welch PSD peak at {peak:.1f} Hz."}

    def wavelet_analysis(self, signal_array, wavelet="db4", level=3) -> dict:
        try:
            import pywt
        except Exception:
            return {"result": None, "verbal": "PyWavelets (pywt) not installed, sir."}
        coeffs = pywt.wavedec(np.asarray(signal_array, float), wavelet, level=level)
        energy = [float(np.sum(c**2)) for c in coeffs]
        return {"n_levels": len(coeffs), "energy_by_level": energy, "result": energy,
                "verbal": f"DWT ({wavelet}, {level} levels): energy distribution {[round(e,1) for e in energy]}."}

    def state_space_analysis(self, A, B, C, D=None) -> dict:
        A = np.asarray(A, float); B = np.atleast_2d(np.asarray(B, float))
        if B.shape[0] == 1 and A.shape[0] > 1:
            B = B.T
        C = np.atleast_2d(np.asarray(C, float)); n = A.shape[0]
        ctrb = np.hstack([np.linalg.matrix_power(A, i) @ B for i in range(n)])
        obsv = np.vstack([C @ np.linalg.matrix_power(A, i) for i in range(n)])
        poles = np.linalg.eigvals(A)
        return {"poles": [complex(p) for p in poles],
                "controllable": bool(np.linalg.matrix_rank(ctrb) == n),
                "observable": bool(np.linalg.matrix_rank(obsv) == n),
                "stable": bool(np.all(poles.real < 0)),
                "result": {"controllable": bool(np.linalg.matrix_rank(ctrb) == n)},
                "verbal": f"State-space: poles {[round(float(p.real),2) for p in poles]}; "
                          f"{'controllable' if np.linalg.matrix_rank(ctrb)==n else 'not controllable'}, "
                          f"{'observable' if np.linalg.matrix_rank(obsv)==n else 'not observable'}."}

    def pid_tune(self, K=1.0, tau=1.0, theta=0.2, method="ziegler_nichols") -> dict:
        """Ziegler-Nichols open-loop (reaction-curve) PID tuning."""
        Kp = 1.2 * tau / (K * theta)
        Ti = 2 * theta; Td = 0.5 * theta
        Ki = Kp / Ti; Kd = Kp * Td
        return {"Kp": Kp, "Ki": Ki, "Kd": Kd, "result": {"Kp": Kp, "Ki": Ki, "Kd": Kd},
                "verbal": f"Ziegler-Nichols PID: Kp={Kp:.3f}, Ki={Ki:.3f}, Kd={Kd:.3f}."}

    def power_flow_dc(self, B_matrix, P_injections, slack=0) -> dict:
        """DC power-flow approximation: θ = B⁻¹ P (slack bus removed)."""
        B = np.asarray(B_matrix, float); P = np.asarray(P_injections, float)
        idx = [i for i in range(len(P)) if i != slack]
        theta = np.zeros(len(P))
        theta[np.ix_(idx)] = np.linalg.solve(B[np.ix_(idx, idx)], P[idx])
        return {"bus_angles_rad": theta.tolist(), "result": theta.tolist(),
                "verbal": f"DC power flow: bus angles {[round(math.degrees(t),2) for t in theta]}°."}

    def test(self) -> None:
        b = self.fea_beam()
        assert b["max_deflection_m"] > 0
        # 2-bar truss
        truss = self.fea_truss([(0, 0), (1, 0), (0.5, 0.5)], [(0, 2), (1, 2)],
                               {0: (1, 1), 1: (1, 1)}, {2: (0, -1000)})
        assert truss["stresses"]
        fs = 500; t = np.arange(0, 1, 1/fs); x = np.sin(2*math.pi*40*t)
        assert abs(self.spectrogram(x, fs)["peak_freq"] - 40) < 10
        assert self.state_space_analysis([[0, 1], [-2, -3]], [0, 1], [1, 0])["controllable"]
        assert self.pid_tune()["Kp"] > 0
        # FFT of a 50 Hz sine
        fs = 1000
        t = np.arange(0, 1, 1 / fs)
        x = np.sin(2 * math.pi * 50 * t)
        f = self.fft_analysis(x, fs)
        assert abs(f["dominant_freqs"][0] - 50) < 2
        tf = self.transfer_function_analysis([1], [1, 2, 1])
        assert tf["stable"]
        print("engineering.EngineeringEngine: OK")


_engine = EngineeringEngine()
_NUM = re.compile(r"-?\d+\.?\d*(?:[eE][+-]?\d+)?")


def fea(text: str) -> dict:
    nums = [float(x) for x in _NUM.findall(text)]
    support = "simply" if "simply" in text.lower() or "supported" in text.lower() else "cantilever"
    return _engine.fea_beam(length=nums[0] if nums else 2.0,
                            load=nums[1] if len(nums) > 1 else 1000.0,
                            support=support)


def signal_processing(text: str) -> dict:
    low = text.lower()
    if "filter" in low:
        nums = [float(x) for x in _NUM.findall(text)]
        return _engine.filter_design(cutoff=nums[0] if nums else 100)
    # default: FFT of a synthetic 50+120 Hz signal
    fs = 1000
    t = np.arange(0, 1, 1 / fs)
    x = np.sin(2 * math.pi * 50 * t) + 0.5 * np.sin(2 * math.pi * 120 * t)
    return _engine.fft_analysis(x, fs)


def control(text: str) -> dict:
    low = text.lower()
    if "step" in low:
        return _engine.step_response([1], [1, 2, 1])
    if "vibration" in low or "natural freq" in low or "mode" in low:
        return _engine.vibration_analysis([[2, 0], [0, 1]], [[3, -1], [-1, 1]])
    return _engine.transfer_function_analysis([1], [1, 2, 1])


def test() -> None:
    EngineeringEngine().test()


if __name__ == "__main__":
    test()
