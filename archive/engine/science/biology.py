# deep/science/biology.py — Systems & Computational Biology (Bible Section 8.3)
"""Epidemiology (SIR/SEIR), ecology (Lotka-Volterra), neuroscience
(Hodgkin-Huxley), stochastic chemistry (Gillespie). scipy-backed."""
from __future__ import annotations

import math
import re

import numpy as np

try:
    from scipy.integrate import solve_ivp
    SCIPY = True
except Exception:  # pragma: no cover
    SCIPY = False


class BiologyEngine:
    def __init__(self, config=None):
        self.config = config

    # ── 8.3 epidemiology ────────────────────────────────────────────
    def sir_model(self, S0, I0, R0, beta, gamma, days, variant="SIR") -> dict:
        if not SCIPY:
            return _no_scipy()
        N = S0 + I0 + R0

        def sir(t, y):
            S, I, R = y
            return [-beta * S * I / N, beta * S * I / N - gamma * I, gamma * I]
        sol = solve_ivp(sir, [0, days], [S0, I0, R0], t_eval=np.linspace(0, days, days + 1))
        R_0 = beta / gamma
        I_arr = sol.y[1]
        peak_day = int(np.argmax(I_arr))
        herd = 1 - 1 / R_0 if R_0 > 0 else 0
        return {"S": sol.y[0].tolist(), "I": I_arr.tolist(), "R": sol.y[2].tolist(),
                "t": sol.t.tolist(), "R0": R_0, "peak_day": peak_day,
                "herd_threshold": herd, "anim_path": None, "result": {"R0": R_0},
                "verbal": f"R₀ = {R_0:.2f}; infection peaks on day {peak_day} at "
                          f"{I_arr.max():.0f} cases; herd-immunity threshold {herd*100:.0f}%."}

    def lotka_volterra(self, x0, y0, alpha, beta, delta, gamma, days) -> dict:
        if not SCIPY:
            return _no_scipy()

        def lv(t, z):
            x, y = z
            return [alpha * x - beta * x * y, delta * x * y - gamma * y]
        sol = solve_ivp(lv, [0, days], [x0, y0], t_eval=np.linspace(0, days, days * 5),
                        max_step=0.1)
        eq = (gamma / delta, alpha / beta)
        return {"prey": sol.y[0].tolist(), "predator": sol.y[1].tolist(),
                "t": sol.t.tolist(), "equilibrium": eq, "anim_path": None,
                "result": {"equilibrium": eq},
                "verbal": f"Predator-prey equilibrium at prey={eq[0]:.1f}, "
                          f"predator={eq[1]:.1f}."}

    # ── 8.3 neuroscience ────────────────────────────────────────────
    def hodgkin_huxley(self, I_ext=10.0, duration=50.0, dt=0.01) -> dict:
        if not SCIPY:
            return _no_scipy()
        Cm = 1.0; gNa, gK, gL = 120.0, 36.0, 0.3
        ENa, EK, EL = 50.0, -77.0, -54.387

        def alpha_n(V): return 0.01 * (V + 55) / (1 - math.exp(-(V + 55) / 10))
        def beta_n(V): return 0.125 * math.exp(-(V + 65) / 80)
        def alpha_m(V): return 0.1 * (V + 40) / (1 - math.exp(-(V + 40) / 10))
        def beta_m(V): return 4.0 * math.exp(-(V + 65) / 18)
        def alpha_h(V): return 0.07 * math.exp(-(V + 65) / 20)
        def beta_h(V): return 1.0 / (1 + math.exp(-(V + 35) / 10))

        def hh(t, y):
            V, m, h, n = y
            INa = gNa * m**3 * h * (V - ENa)
            IK = gK * n**4 * (V - EK)
            IL = gL * (V - EL)
            dV = (I_ext - INa - IK - IL) / Cm
            return [dV, alpha_m(V)*(1-m)-beta_m(V)*m, alpha_h(V)*(1-h)-beta_h(V)*h,
                    alpha_n(V)*(1-n)-beta_n(V)*n]
        sol = solve_ivp(hh, [0, duration], [-65, 0.05, 0.6, 0.32],
                        t_eval=np.arange(0, duration, dt), max_step=dt)
        V = sol.y[0]
        spikes = int(np.sum((V[1:-1] > 0) & (V[1:-1] > V[:-2]) & (V[1:-1] > V[2:])))
        return {"V": V.tolist(), "t": sol.t.tolist(), "spike_count": spikes,
                "anim_path": None, "result": {"spikes": spikes},
                "verbal": f"Hodgkin-Huxley neuron fired {spikes} action potential(s) "
                          f"under {I_ext} µA/cm² over {duration} ms."}

    # ── 8.3 stochastic chemistry ────────────────────────────────────
    def gillespie_algorithm(self, reactions, species, T_max) -> dict:
        """reactions: list of {reactants:{sp:coeff}, products:{sp:coeff}, rate}."""
        state = dict(species)
        t = 0.0
        times = [0.0]; hist = {s: [v] for s, v in state.items()}
        rng = np.random.default_rng()
        while t < T_max:
            rates = []
            for r in reactions:
                a = r["rate"]
                for sp_, c in r["reactants"].items():
                    for k in range(c):
                        a *= max(0, state.get(sp_, 0) - k)
                rates.append(a)
            total = sum(rates)
            if total <= 0:
                break
            t += rng.exponential(1 / total)
            idx = rng.choice(len(reactions), p=np.array(rates) / total)
            for sp_, c in reactions[idx]["reactants"].items():
                state[sp_] = state.get(sp_, 0) - c
            for sp_, c in reactions[idx]["products"].items():
                state[sp_] = state.get(sp_, 0) + c
            times.append(t)
            for s in hist:
                hist[s].append(state.get(s, 0))
        return {"times": times, "populations": hist, "result": state,
                "verbal": f"Gillespie SSA ran {len(times)} reaction events to t={t:.2f}."}

    def logistic_growth(self, N0, r, K, days) -> dict:
        t = np.linspace(0, days, days + 1)
        N = K / (1 + (K - N0) / N0 * np.exp(-r * t))
        return {"t": t.tolist(), "N": N.tolist(), "carrying_capacity": K,
                "result": N.tolist(),
                "verbal": f"Logistic growth approaches carrying capacity {K} "
                          f"(reaches {N[-1]:.0f} by day {days})."}

    def test(self) -> None:
        s = self.sir_model(990, 10, 0, 0.3, 0.1, 100)
        assert abs(s["R0"] - 3.0) < 1e-9
        lg = self.logistic_growth(10, 0.5, 1000, 30)
        assert lg["N"][-1] <= 1000
        print("biology.BiologyEngine: OK")


def _no_scipy():
    return {"result": None, "verbal": "scipy not available, sir."}


_engine = BiologyEngine()


def analyze(text: str) -> dict:
    low = text.lower()
    nums = [float(x) for x in re.findall(r"-?\d+\.?\d*", text)]
    if "sir" in low or "epidemic" in low or "outbreak" in low:
        return _engine.sir_model(nums[0] if nums else 990, nums[1] if len(nums) > 1 else 10,
                                 0, nums[2] if len(nums) > 2 else 0.3,
                                 nums[3] if len(nums) > 3 else 0.1,
                                 int(nums[4]) if len(nums) > 4 else 100)
    if "predator" in low or "lotka" in low:
        return _engine.lotka_volterra(10, 5, 1.1, 0.4, 0.1, 0.4, 100)
    if "neuron" in low or "hodgkin" in low or "action potential" in low:
        return _engine.hodgkin_huxley()
    return {"result": None, "verbal": "Specify a model, sir (SIR, Lotka-Volterra, HH neuron)."}


def test() -> None:
    BiologyEngine().test()


if __name__ == "__main__":
    test()
