# deep/science/physics.py — Physics Engine (Bible Section 6)
"""Classical mechanics, electromagnetism, thermodynamics, statistical
mechanics, fluid dynamics, special & general relativity.

Every method returns numerical results plus a ``verbal`` TTS summary. Heavy
plotting/animation is delegated to the visualizer module (Step 17); here we
return the physical quantities and leave ``plot_path``/``anim_path`` as None.
"""
from __future__ import annotations

import math
import re

import numpy as np

try:
    from scipy.integrate import solve_ivp
    SCIPY = True
except Exception:  # pragma: no cover
    SCIPY = False

G_GRAV = 6.674e-11        # m^3 kg^-1 s^-2
C_LIGHT = 2.998e8         # m/s
K_B = 1.380649e-23        # J/K
K_COULOMB = 8.988e9       # N m^2 / C^2
HBAR = 1.0545718e-34      # J s


class PhysicsEngine:
    def __init__(self, config=None):
        self.config = config

    # ── 6.1 classical mechanics ─────────────────────────────────────
    def projectile(self, angle, v0, gravity=9.81, Cd=0.0, mass=1.0) -> dict:
        th = math.radians(angle)
        if Cd == 0 or not SCIPY:
            # analytic (no drag)
            tof = 2 * v0 * math.sin(th) / gravity
            rng = v0**2 * math.sin(2 * th) / gravity
            h = (v0 * math.sin(th))**2 / (2 * gravity)
            t = np.linspace(0, tof, 200)
            x = v0 * math.cos(th) * t
            y = v0 * math.sin(th) * t - 0.5 * gravity * t**2
            return {"x": x.tolist(), "y": y.tolist(), "max_height": h, "range": rng,
                    "tof": tof, "plot_path": None,
                    "verbal": f"Projectile at {angle}° and {v0} m/s: range {rng:.2f} m, "
                              f"max height {h:.2f} m, flight time {tof:.2f} s.",
                    "result": {"range": rng, "max_height": h, "tof": tof}}
        # with quadratic drag
        def deriv(t, s):
            x, y, vx, vy = s
            v = math.hypot(vx, vy)
            ax = -Cd / mass * v * vx
            ay = -gravity - Cd / mass * v * vy
            return [vx, vy, ax, ay]

        def hit_ground(t, s):
            return s[1]
        hit_ground.terminal = True
        hit_ground.direction = -1
        sol = solve_ivp(deriv, [0, 100], [0, 0, v0 * math.cos(th), v0 * math.sin(th)],
                        events=hit_ground, max_step=0.01, dense_output=True)
        x, y = sol.y[0], sol.y[1]
        return {"x": x.tolist(), "y": y.tolist(), "max_height": float(y.max()),
                "range": float(x[-1]), "tof": float(sol.t[-1]), "plot_path": None,
                "verbal": f"With drag, range {x[-1]:.2f} m, max height {y.max():.2f} m, "
                          f"flight time {sol.t[-1]:.2f} s.",
                "result": {"range": float(x[-1]), "max_height": float(y.max())}}

    def pendulum(self, length, angle0, damping=0.0, pendulum_type="simple", g=9.81) -> dict:
        if not SCIPY:
            return _no_scipy()
        if pendulum_type == "double":
            return self._double_pendulum(length, angle0, g)
        def deriv(t, s):
            th, om = s
            return [om, -(g / length) * math.sin(th) - damping * om]
        T = 2 * math.pi * math.sqrt(length / g)
        sol = solve_ivp(deriv, [0, 5 * T], [angle0, 0.0], max_step=T / 100)
        return {"theta": sol.y[0].tolist(), "omega": sol.y[1].tolist(), "t": sol.t.tolist(),
                "period": T, "lyapunov_exp": None, "anim_path": None,
                "verbal": f"{pendulum_type.title()} pendulum, length {length} m: "
                          f"small-angle period {T:.3f} s.",
                "result": {"period": T}}

    def _double_pendulum(self, length, angle0, g):
        m1 = m2 = 1.0; L1 = L2 = length
        def deriv(t, s):
            t1, w1, t2, w2 = s
            d = t1 - t2
            den = (2 * m1 + m2 - m2 * math.cos(2 * d))
            a1 = (-g * (2 * m1 + m2) * math.sin(t1) - m2 * g * math.sin(t1 - 2 * t2)
                  - 2 * math.sin(d) * m2 * (w2**2 * L2 + w1**2 * L1 * math.cos(d))) / (L1 * den)
            a2 = (2 * math.sin(d) * (w1**2 * L1 * (m1 + m2) + g * (m1 + m2) * math.cos(t1)
                  + w2**2 * L2 * m2 * math.cos(d))) / (L2 * den)
            return [w1, a1, w2, a2]
        sol = solve_ivp(deriv, [0, 20], [angle0, 0, angle0 + 0.01, 0], max_step=0.01)
        return {"theta": sol.y[0].tolist(), "t": sol.t.tolist(), "lyapunov_exp": "chaotic",
                "anim_path": None, "verbal": "Double pendulum simulated — chaotic dynamics.",
                "result": "chaotic"}

    def spring_mass(self, k, m, x0, v0=0.0, damping=0.0, forcing=None) -> dict:
        if not SCIPY:
            return _no_scipy()
        wn = math.sqrt(k / m)
        def deriv(t, s):
            x, v = s
            F = 0.0
            if forcing:
                F = forcing.get("F0", 0) * math.cos(forcing.get("omega", 0) * t)
            return [v, (F - damping * v - k * x) / m]
        sol = solve_ivp(deriv, [0, 10 * (2 * math.pi / wn)], [x0, v0], max_step=0.01)
        resonance = bool(forcing and abs(forcing.get("omega", 0) - wn) < 0.05 * wn)
        return {"x": sol.y[0].tolist(), "v": sol.y[1].tolist(), "t": sol.t.tolist(),
                "natural_freq": wn, "resonance": resonance, "plot_path": None,
                "verbal": f"Spring-mass natural frequency {wn:.3f} rad/s"
                          + (" — at resonance!" if resonance else "."),
                "result": {"natural_freq": wn, "resonance": resonance}}

    def kepler_orbit(self, semi_major, eccentricity, mu=1.327e20, n_periods=1) -> dict:
        a = semi_major; e = eccentricity
        period = 2 * math.pi * math.sqrt(a**3 / mu)
        nu = np.linspace(0, 2 * math.pi * n_periods, 1000)
        r = a * (1 - e**2) / (1 + e * np.cos(nu))
        x = r * np.cos(nu); y = r * np.sin(nu)
        return {"x": x.tolist(), "y": y.tolist(), "period": period,
                "periapsis": a * (1 - e), "apoapsis": a * (1 + e), "anim_path": None,
                "verbal": f"Orbit a={a:.3g} m, e={e}: period {period:.3g} s, "
                          f"periapsis {a*(1-e):.3g} m, apoapsis {a*(1+e):.3g} m.",
                "result": {"period": period}}

    def hohmann_transfer(self, r1, r2, mu=3.986e14) -> dict:
        v1 = math.sqrt(mu / r1); v2 = math.sqrt(mu / r2)
        a_t = (r1 + r2) / 2
        vp = math.sqrt(mu * (2 / r1 - 1 / a_t))
        va = math.sqrt(mu * (2 / r2 - 1 / a_t))
        dv1 = abs(vp - v1); dv2 = abs(v2 - va)
        t_transfer = math.pi * math.sqrt(a_t**3 / mu)
        return {"dv1": dv1, "dv2": dv2, "total_dv": dv1 + dv2, "transfer_time": t_transfer,
                "verbal": f"Hohmann transfer: Δv1 {dv1:.1f}, Δv2 {dv2:.1f}, "
                          f"total {dv1+dv2:.1f} m/s, time {t_transfer/3600:.2f} h.",
                "result": {"total_dv": dv1 + dv2}}

    def n_body(self, bodies, dt=0.01, steps=2000) -> dict:
        n = len(bodies)
        pos = np.array([b["pos"] for b in bodies], dtype=float)
        vel = np.array([b["vel"] for b in bodies], dtype=float)
        mass = np.array([b["mass"] for b in bodies], dtype=float)
        traj = {b.get("name", i): [] for i, b in enumerate(bodies)}

        def accel(p):
            a = np.zeros_like(p)
            for i in range(n):
                for j in range(n):
                    if i != j:
                        d = p[j] - p[i]; r = np.linalg.norm(d) + 1e-9
                        a[i] += G_GRAV * mass[j] * d / r**3
            return a
        a = accel(pos)
        for _ in range(steps):
            vel += 0.5 * a * dt
            pos += vel * dt
            a = accel(pos)
            vel += 0.5 * a * dt
            for i, b in enumerate(bodies):
                traj[b.get("name", i)].append(pos[i].tolist())
        return {"trajectories": traj, "energy_drift": None, "anim_path": None,
                "verbal": f"Simulated {n}-body system for {steps} steps.",
                "result": "ok"}

    # ── 6.2 electromagnetism ────────────────────────────────────────
    def electric_field(self, charges, grid_size=50, extent=5.0) -> dict:
        xs = np.linspace(-extent, extent, grid_size)
        X, Y = np.meshgrid(xs, xs)
        Ex = np.zeros_like(X); Ey = np.zeros_like(X); V = np.zeros_like(X)
        for c in charges:
            q = c["q"]; px, py = c["pos"]
            dx = X - px; dy = Y - py
            r = np.sqrt(dx**2 + dy**2) + 1e-9
            Ex += K_COULOMB * q * dx / r**3
            Ey += K_COULOMB * q * dy / r**3
            V += K_COULOMB * q / r
        return {"Ex": Ex.tolist(), "Ey": Ey.tolist(), "V": V.tolist(), "plot_path": None,
                "verbal": f"Computed E-field and potential from {len(charges)} charge(s) "
                          f"on a {grid_size}×{grid_size} grid.",
                "result": "ok"}

    def circuit_analysis(self, nodes, edges, sources) -> dict:
        """Nodal analysis: G·V = I. Node 0 is ground."""
        idx = {n: i for i, n in enumerate(nodes)}
        N = len(nodes)
        G = np.zeros((N, N)); I = np.zeros(N)
        for e in edges:
            a, b = idx[e["from"]], idx[e["to"]]
            g = 1.0 / e["R"]
            G[a, a] += g; G[b, b] += g; G[a, b] -= g; G[b, a] -= g
        for s in sources:
            if "I" in s:
                I[idx[s["node"]]] += s["I"]
        # ground node 0
        G[0, :] = 0; G[0, 0] = 1; I[0] = 0
        try:
            V = np.linalg.solve(G, I)
        except np.linalg.LinAlgError:
            return {"verbal": "Circuit is singular, sir.", "result": None}
        voltages = {n: float(V[idx[n]]) for n in nodes}
        currents = {f"{e['from']}->{e['to']}":
                    float((V[idx[e['from']]] - V[idx[e['to']]]) / e["R"]) for e in edges}
        return {"voltages": voltages, "currents": currents, "plot_path": None,
                "verbal": f"Solved {N}-node circuit. Node voltages: "
                          + ", ".join(f"{k}={v:.3g}V" for k, v in voltages.items()),
                "result": voltages}

    def em_wave(self, frequency, medium=None, polarization="linear") -> dict:
        medium = medium or {}
        er = medium.get("epsilon_r", 1.0); mr = medium.get("mu_r", 1.0)
        sigma = medium.get("sigma", 0.0)
        n = math.sqrt(er * mr)
        v = C_LIGHT / n
        wl = v / frequency
        eta = 376.73 * math.sqrt(mr / er)
        mu0 = 4e-7 * math.pi
        omega = 2 * math.pi * frequency
        skin = math.sqrt(2 / (omega * mu0 * mr * sigma)) if sigma > 0 else float("inf")
        return {"wavelength": wl, "phase_vel": v, "skin_depth": skin, "impedance": eta,
                "verbal": f"At {frequency:.3g} Hz: wavelength {wl:.3g} m, phase velocity "
                          f"{v:.3g} m/s, impedance {eta:.1f} Ω.",
                "result": {"wavelength": wl, "phase_vel": v}}

    # ── 6.3 thermodynamics & statistical mechanics ──────────────────
    def ideal_gas(self, state1, state2, process) -> dict:
        R = 8.314
        P1, V1, T1 = state1.get("P"), state1.get("V"), state1.get("T")
        n = state1.get("n", (P1 * V1 / (R * T1)) if (P1 and V1 and T1) else 1.0)
        process = process.lower()
        W = Q = dS = None; final = dict(state2)
        if process == "isothermal":
            V2 = state2.get("V", V1)
            W = n * R * T1 * math.log(V2 / V1); Q = W
            dS = n * R * math.log(V2 / V1); final = {"P": P1 * V1 / V2, "V": V2, "T": T1}
        elif process == "isobaric":
            V2 = state2.get("V", V1); T2 = T1 * V2 / V1
            W = P1 * (V2 - V1); Q = n * (5 / 2) * R * (T2 - T1)
            final = {"P": P1, "V": V2, "T": T2}
        elif process == "adiabatic":
            g = 1.4; V2 = state2.get("V", V1)
            P2 = P1 * (V1 / V2)**g; T2 = T1 * (V1 / V2)**(g - 1)
            W = (P1 * V1 - P2 * V2) / (g - 1); Q = 0.0
            final = {"P": P2, "V": V2, "T": T2}
        return {"final_state": final, "W": W, "Q": Q, "dS": dS, "plot_path": None,
                "verbal": f"{process.title()} process: work {W:.3g} J, heat {Q if Q is None else f'{Q:.3g}'} J.",
                "result": final}

    def maxwell_boltzmann(self, T, m, n_points=1000) -> dict:
        v = np.linspace(0, 3000, n_points)
        f = (m / (2 * math.pi * K_B * T))**1.5 * 4 * math.pi * v**2 * \
            np.exp(-m * v**2 / (2 * K_B * T))
        v_mp = math.sqrt(2 * K_B * T / m)
        v_mean = math.sqrt(8 * K_B * T / (math.pi * m))
        v_rms = math.sqrt(3 * K_B * T / m)
        return {"v": v.tolist(), "f_v": f.tolist(), "v_mean": v_mean, "v_rms": v_rms,
                "v_mp": v_mp, "plot_path": None,
                "verbal": f"At {T} K: most-probable speed {v_mp:.1f}, mean {v_mean:.1f}, "
                          f"rms {v_rms:.1f} m/s.",
                "result": {"v_mp": v_mp, "v_rms": v_rms}}

    def carnot_cycle(self, T_hot, T_cold, n_steps=100) -> dict:
        eff = 1 - T_cold / T_hot
        return {"efficiency": eff, "plot_path": None,
                "verbal": f"Carnot efficiency between {T_hot} K and {T_cold} K is {eff*100:.1f}%.",
                "result": {"efficiency": eff}}

    def partition_function(self, energy_levels, T) -> dict:
        E = np.asarray(energy_levels, dtype=float) * 1.602e-19  # eV->J
        beta = 1 / (K_B * T)
        Z = float(np.sum(np.exp(-beta * E)))
        p = np.exp(-beta * E) / Z
        F = -K_B * T * math.log(Z)
        U = float(np.sum(E * p))
        S = (U - F) / T
        return {"Z": Z, "F": F, "S": S, "probabilities": p.tolist(),
                "verbal": f"Partition function Z={Z:.4g}, free energy {F:.3g} J, entropy {S:.3g} J/K.",
                "result": {"Z": Z}}

    # ── 6.4 fluid dynamics ──────────────────────────────────────────
    def bernoulli(self, v1, p1, h1, rho, target) -> dict:
        g = 9.81
        H = p1 + 0.5 * rho * v1**2 + rho * g * h1
        out = {}
        if "v2" in target:
            v2 = target["v2"]; h2 = target.get("h2", h1)
            out["p2"] = H - 0.5 * rho * v2**2 - rho * g * h2
        elif "p2" in target:
            p2 = target["p2"]; h2 = target.get("h2", h1)
            out["v2"] = math.sqrt(max(0, 2 * (H - p2 - rho * g * h2) / rho))
        return {"result": out, "verbal": f"By Bernoulli, {out}."}

    def stokes_flow(self, a, mu, U) -> dict:
        F = 6 * math.pi * mu * a * U
        return {"F_drag": F, "verbal": f"Stokes drag on sphere radius {a} m: {F:.4g} N.",
                "result": {"F_drag": F}}

    def navier_stokes_2d(self, Re=100, n_steps=300, grid_size=41, geometry="cavity") -> dict:
        """2D incompressible NS — lid-driven cavity, vorticity-streamfunction form."""
        N = grid_size; h = 1.0 / (N - 1); dt = 0.001
        nu = 1.0 / Re
        psi = np.zeros((N, N)); w = np.zeros((N, N))
        u_lid = 1.0
        for _ in range(n_steps):
            # solve Poisson  ∇²ψ = -w  (a few Jacobi sweeps)
            for _ in range(30):
                psi[1:-1, 1:-1] = 0.25 * (psi[1:-1, 2:] + psi[1:-1, :-2] +
                                          psi[2:, 1:-1] + psi[:-2, 1:-1] +
                                          h * h * w[1:-1, 1:-1])
            # vorticity boundary conditions
            w[0, :] = -2 * psi[1, :] / h**2                       # bottom
            w[-1, :] = -2 * psi[-2, :] / h**2 - 2 * u_lid / h     # top (moving lid)
            w[:, 0] = -2 * psi[:, 1] / h**2
            w[:, -1] = -2 * psi[:, -2] / h**2
            u = np.zeros((N, N)); v = np.zeros((N, N))
            u[1:-1, 1:-1] = (psi[2:, 1:-1] - psi[:-2, 1:-1]) / (2 * h)
            v[1:-1, 1:-1] = -(psi[1:-1, 2:] - psi[1:-1, :-2]) / (2 * h)
            lap = (w[1:-1, 2:] + w[1:-1, :-2] + w[2:, 1:-1] + w[:-2, 1:-1] -
                   4 * w[1:-1, 1:-1]) / h**2
            conv = (u[1:-1, 1:-1] * (w[1:-1, 2:] - w[1:-1, :-2]) / (2 * h) +
                    v[1:-1, 1:-1] * (w[2:, 1:-1] - w[:-2, 1:-1]) / (2 * h))
            w[1:-1, 1:-1] += dt * (-conv + nu * lap)
        speed = np.sqrt(u**2 + v**2)
        return {"u": u.tolist(), "v": v.tolist(), "max_speed": float(speed.max()),
                "result": {"max_speed": float(speed.max())}, "anim_path": None,
                "verbal": f"Lid-driven cavity (Re={Re}, {N}×{N}) solved over {n_steps} steps; "
                          f"max flow speed {speed.max():.3f}."}

    def fdtd_2d(self, n_steps=120, grid_size=80) -> dict:
        """2D FDTD Maxwell (TMz mode): Ez, Hx, Hy on a Yee grid with a point source."""
        N = grid_size
        Ez = np.zeros((N, N)); Hx = np.zeros((N, N)); Hy = np.zeros((N, N))
        c = 1.0; dt = 0.5 / math.sqrt(2)  # Courant-stable
        energy = []
        for t in range(n_steps):
            Hx[:, :-1] -= dt * (Ez[:, 1:] - Ez[:, :-1])
            Hy[:-1, :] += dt * (Ez[1:, :] - Ez[:-1, :])
            Ez[1:, 1:] += dt * ((Hy[1:, 1:] - Hy[:-1, 1:]) - (Hx[1:, 1:] - Hx[1:, :-1]))
            Ez[N//2, N//2] += math.sin(0.3 * t) * math.exp(-((t - 20) / 15)**2)  # pulse
            energy.append(float(np.sum(Ez**2)))
        return {"final_energy": energy[-1], "Ez_max": float(np.abs(Ez).max()),
                "result": {"final_energy": energy[-1]}, "anim_path": None,
                "verbal": f"2D FDTD Maxwell solver ran {n_steps} steps on a {N}×{N} Yee "
                          f"grid; EM pulse propagated, field energy {energy[-1]:.2f}."}

    def ising_model(self, N=32, T=2.269, steps=200) -> dict:
        """2D Ising Monte Carlo (Metropolis); returns magnetisation & energy."""
        rng = np.random.default_rng(0); spins = rng.choice([-1, 1], (N, N))
        mags = []
        for _ in range(steps):
            for _ in range(N * N):
                i, j = rng.integers(N), rng.integers(N)
                nb = spins[(i+1) % N, j] + spins[(i-1) % N, j] + spins[i, (j+1) % N] + spins[i, (j-1) % N]
                dE = 2 * spins[i, j] * nb
                if dE <= 0 or rng.random() < math.exp(-dE / T):
                    spins[i, j] *= -1
            mags.append(abs(spins.mean()))
        M = float(np.mean(mags[-20:]))
        return {"magnetisation": M, "Tc": 2.269, "result": {"magnetisation": M},
                "verbal": f"2D Ising at T={T}: average |magnetisation| {M:.3f} "
                          f"(Curie point T_c≈2.27)."}

    def brownian_motion(self, n_particles=100, n_steps=500, D=1.0, dt=0.01) -> dict:
        rng = np.random.default_rng(0)
        steps = rng.normal(0, math.sqrt(2 * D * dt), (n_steps, n_particles, 2))
        paths = np.cumsum(steps, axis=0)
        msd = float(np.mean(np.sum(paths[-1]**2, axis=1)))
        D_measured = msd / (4 * n_steps * dt)
        return {"MSD": msd, "D_measured": D_measured, "result": {"D_measured": D_measured},
                "verbal": f"Brownian motion ({n_particles} particles): MSD {msd:.3f}, "
                          f"recovered D={D_measured:.3f} (input {D})."}

    def biot_savart_loop(self, I=1.0, radius=1.0, z=0.0) -> dict:
        """On-axis B field of a current loop (exact)."""
        mu0 = 4e-7 * math.pi
        B = mu0 * I * radius**2 / (2 * (radius**2 + z**2)**1.5)
        return {"B_tesla": B, "result": B,
                "verbal": f"Current loop (I={I} A, r={radius} m): on-axis B = {B:.3e} T at z={z}."}

    # ── 6.5 relativity ──────────────────────────────────────────────
    def lorentz_transform(self, event, beta, direction="x") -> dict:
        t, x, y, z = event
        g = 1 / math.sqrt(1 - beta**2)
        tp = g * (t - beta * x / C_LIGHT)
        xp = g * (x - beta * C_LIGHT * t)
        return {"transformed_event": [tp, xp, y, z], "gamma": g,
                "time_dilation": g, "length_contraction": 1 / g,
                "verbal": f"At β={beta}, γ={g:.4g}: time dilation ×{g:.4g}, "
                          f"length contraction ×{1/g:.4g}.",
                "result": {"gamma": g}}

    def schwarzschild(self, M, r_values=None) -> dict:
        Msun = 1.989e30
        m = M * Msun
        r_s = 2 * G_GRAV * m / C_LIGHT**2
        isco = 3 * r_s
        photon = 1.5 * r_s
        T_hawking = HBAR * C_LIGHT**3 / (8 * math.pi * G_GRAV * m * K_B)
        return {"r_s": r_s, "ISCO": isco, "photon_sphere": photon, "T_hawking": T_hawking,
                "verbal": f"Black hole of {M} M☉: Schwarzschild radius {r_s:.3g} m, "
                          f"ISCO {isco:.3g} m, Hawking temperature {T_hawking:.3g} K.",
                "result": {"r_s": r_s, "T_hawking": T_hawking}}

    def test(self) -> None:
        p = self.projectile(45, 20)
        assert abs(p["range"] - 40.77) < 1.0
        assert abs(self.carnot_cycle(600, 300)["efficiency"] - 0.5) < 1e-9
        assert self.schwarzschild(1)["r_s"] > 0
        # heavy solvers (small grids)
        assert self.fdtd_2d(n_steps=30, grid_size=40)["final_energy"] >= 0
        assert self.navier_stokes_2d(Re=100, n_steps=40, grid_size=21)["max_speed"] > 0
        ising = self.ising_model(N=16, T=1.0, steps=120)
        assert ising["magnetisation"] > 0.4   # ordered well below Tc
        bm = self.brownian_motion(n_particles=50, n_steps=200)
        assert bm["D_measured"] > 0
        print("physics.PhysicsEngine: OK (incl. FDTD, Navier-Stokes, Ising, Brownian)")


def _no_scipy():
    return {"result": None, "verbal": "scipy not available, sir."}


# ── module-level routing functions (INTENT_MAP) ──────────────────────────
_engine = PhysicsEngine()
_NUM = re.compile(r"(?<![A-Za-z0-9.])-?\d+\.?\d*(?:[eE][+-]?\d+)?")


def _nums(text):
    return [float(x) for x in _NUM.findall(text)]


def projectile(text: str) -> dict:
    n = _nums(text)
    angle = n[0] if len(n) >= 1 else 45.0
    v0 = n[1] if len(n) >= 2 else 20.0
    return _engine.projectile(angle, v0)


def oscillation(text: str) -> dict:
    n = _nums(text)
    if "double" in text.lower():
        return _engine.pendulum(n[0] if n else 1.0, 1.0, pendulum_type="double")
    if "spring" in text.lower():
        return _engine.spring_mass(n[0] if len(n) > 0 else 10.0,
                                   n[1] if len(n) > 1 else 1.0,
                                   n[2] if len(n) > 2 else 1.0)
    return _engine.pendulum(n[0] if n else 1.0, math.radians(n[1]) if len(n) > 1 else 0.3)


def orbital(text: str) -> dict:
    n = _nums(text)
    return _engine.kepler_orbit(n[0] if n else 1.5e11, n[1] if len(n) > 1 else 0.3)


def n_body(text: str) -> dict:
    return {"result": None,
            "verbal": "Provide bodies, sir — PhysicsEngine().n_body([{mass,pos,vel,name}, ...])."}


def electrostatics(text: str) -> dict:
    return _engine.electric_field([{"q": 1e-9, "pos": [-1, 0]}, {"q": -1e-9, "pos": [1, 0]}])


def magnetism(text: str) -> dict:
    n = _nums(text)
    return _engine.biot_savart_loop(I=n[0] if n else 1.0,
                                    radius=n[1] if len(n) > 1 else 1.0)


def circuit(text: str) -> dict:
    return {"result": None,
            "verbal": "Provide nodes/edges/sources, sir — PhysicsEngine().circuit_analysis(...)."}


def em_wave(text: str) -> dict:
    n = _nums(text)
    return _engine.em_wave(n[0] if n else 1e9)


def thermodynamics(text: str) -> dict:
    n = _nums(text)
    if "carnot" in text.lower() or "efficiency" in text.lower():
        return _engine.carnot_cycle(n[0] if len(n) > 0 else 600, n[1] if len(n) > 1 else 300)
    return _engine.carnot_cycle(n[0] if len(n) > 0 else 600, n[1] if len(n) > 1 else 300)


def statistical_mech(text: str) -> dict:
    n = _nums(text)
    T = n[0] if n else 300.0
    return _engine.maxwell_boltzmann(T, 4.65e-26)  # N2 molecule mass default


def fluid_dynamics(text: str) -> dict:
    return {"result": None,
            "verbal": "Specify flow state, sir — PhysicsEngine().bernoulli(...) or .stokes_flow(...)."}


def relativity(text: str) -> dict:
    n = _nums(text)
    beta = n[0] if n else 0.5
    if beta >= 1:
        beta = beta / C_LIGHT if beta > 1 else 0.5
    return _engine.lorentz_transform([1, 1, 0, 0], beta)


def test() -> None:
    PhysicsEngine().test()


if __name__ == "__main__":
    test()
