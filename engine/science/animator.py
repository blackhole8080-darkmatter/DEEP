# deep/science/animator.py — Animation Engine (Bible Section 16.2)
"""All 28 scientific animation methods. Each builds a matplotlib FuncAnimation
with the dark-neon theme and saves a GIF (PillowWriter — no ffmpeg needed) to
config.ANIM_DIR, returning {gif_path, mp4_path, verbal}. Frame counts are kept
modest so animations render in seconds; raise them for production renders."""
from __future__ import annotations

import math
import os
import re
import time

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter
    MPL = True
except Exception:  # pragma: no cover
    MPL = False

try:
    from scipy.integrate import solve_ivp
    SCIPY = True
except Exception:  # pragma: no cover
    SCIPY = False

try:
    from .. import config
    ANIM_DIR = str(config.ANIM_DIR)
except Exception:  # pragma: no cover
    ANIM_DIR = os.path.join(os.path.expanduser("~"), "deep_output", "animations")
os.makedirs(ANIM_DIR, exist_ok=True)

BG, AXES, CYAN, MAGENTA, PINK, AMBER = "#0D0D1A", "#1A1A2E", "#00FFFF", "#FF00FF", "#FF6B9D", "#FFB800"


def _fig(d3=False):
    fig = plt.figure(figsize=(6, 5)); fig.patch.set_facecolor(BG)
    ax = fig.add_subplot(111, projection="3d") if d3 else fig.add_subplot(111)
    ax.set_facecolor(AXES)
    if not d3:
        ax.tick_params(colors="#CCC")
        for s in ax.spines.values():
            s.set_color("#444")
    return fig, ax


def _save(anim, fig, name, fps=20):
    path = os.path.join(ANIM_DIR, f"{name}_{int(time.time()*1000)}.gif")
    anim.save(path, writer=PillowWriter(fps=fps)); plt.close(fig)
    return {"gif_path": path, "mp4_path": None, "result": path,
            "verbal": f"Animation saved to {os.path.basename(path)}, sir."}


def _no():
    return {"result": None, "verbal": "matplotlib is not installed, sir."}


class DEEPAnimator:
    def __init__(self, config=None):
        self.config = config

    # 1
    def wave_animation(self, freq=1.0, amplitude=1.0, wave_type="transverse", frames=60):
        if not MPL: return _no()
        fig, ax = _fig(); x = np.linspace(0, 4*np.pi, 400)
        line, = ax.plot([], [], color=CYAN, lw=2)
        ax.set_xlim(0, 4*np.pi); ax.set_ylim(-1.6*amplitude, 1.6*amplitude)
        ax.set_title(f"{wave_type} wave {freq} Hz", color="#FFF")
        def up(t):
            line.set_data(x, amplitude*np.sin(2*np.pi*freq*x/(4*np.pi) - 0.2*t)); return line,
        return _save(FuncAnimation(fig, up, frames=frames, blit=True), fig, "wave")

    # 2
    def projectile_animation(self, angle=45.0, v0=20.0, gravity=9.81, frames=60):
        if not MPL: return _no()
        th = math.radians(angle); tof = 2*v0*math.sin(th)/gravity
        t = np.linspace(0, tof, frames); xs = v0*math.cos(th)*t; ys = v0*math.sin(th)*t - 0.5*gravity*t**2
        fig, ax = _fig(); ax.set_xlim(0, xs.max()*1.1); ax.set_ylim(0, ys.max()*1.3)
        ax.set_title(f"Projectile {angle}°", color="#FFF")
        trail, = ax.plot([], [], color=MAGENTA, alpha=.5); dot, = ax.plot([], [], "o", color=CYAN, ms=10)
        def up(i): trail.set_data(xs[:i+1], ys[:i+1]); dot.set_data([xs[i]], [ys[i]]); return trail, dot
        return _save(FuncAnimation(fig, up, frames=frames, blit=True), fig, "projectile")

    # 3
    def orbital_animation(self, frames=120):
        if not MPL: return _no()
        fig, ax = _fig(); ax.set_aspect("equal"); ax.set_title("Two-body orbit", color="#FFF")
        a, e = 1.0, 0.5; nu = np.linspace(0, 2*np.pi, frames); r = a*(1-e**2)/(1+e*np.cos(nu))
        x, y = r*np.cos(nu), r*np.sin(nu); ax.set_xlim(-2, 1); ax.set_ylim(-1.5, 1.5)
        ax.plot(0, 0, "o", color=AMBER, ms=14); trail, = ax.plot([], [], color=CYAN, alpha=.5)
        dot, = ax.plot([], [], "o", color=PINK, ms=8)
        def up(i): trail.set_data(x[:i+1], y[:i+1]); dot.set_data([x[i]], [y[i]]); return trail, dot
        return _save(FuncAnimation(fig, up, frames=frames, blit=True), fig, "orbital")

    # 4
    def pendulum_animation(self, length=1.0, angle0=60.0, pendulum_type="double", frames=120):
        if not MPL or not SCIPY: return _no()
        g = 9.81; a0 = math.radians(angle0)
        if pendulum_type == "double":
            def d(t, s):
                t1, w1, t2, w2 = s; dd = t1-t2; den = 2-math.cos(2*dd)
                a1 = (-g*(2)*math.sin(t1)-g*math.sin(t1-2*t2)-2*math.sin(dd)*(w2**2+w1**2*math.cos(dd)))/(length*den)
                a2 = (2*math.sin(dd)*(w1**2*2+g*math.cos(t1)+w2**2*math.cos(dd)))/(length*den)
                return [w1, a1, w2, a2]
            sol = solve_ivp(d, [0, 12], [a0, 0, a0+0.01, 0], t_eval=np.linspace(0, 12, frames), max_step=0.02)
            t1, t2 = sol.y[0], sol.y[2]
            x1, y1 = length*np.sin(t1), -length*np.cos(t1)
            x2, y2 = x1+length*np.sin(t2), y1-length*np.cos(t2)
        else:
            sol = solve_ivp(lambda t, s: [s[1], -(g/length)*math.sin(s[0])], [0, 12],
                            [a0, 0], t_eval=np.linspace(0, 12, frames))
            t1 = sol.y[0]; x1, y1 = length*np.sin(t1), -length*np.cos(t1); x2, y2 = x1, y1
        fig, ax = _fig(); ax.set_aspect("equal"); ax.set_xlim(-2.2, 2.2); ax.set_ylim(-2.4, 0.5)
        ax.set_title(f"{pendulum_type} pendulum", color="#FFF")
        rod, = ax.plot([], [], "-o", color=CYAN); trail, = ax.plot([], [], color=PINK, alpha=.4, lw=.8)
        def up(i):
            rod.set_data([0, x1[i], x2[i]], [0, y1[i], y2[i]]); trail.set_data(x2[:i+1], y2[:i+1]); return rod, trail
        return _save(FuncAnimation(fig, up, frames=frames, blit=True), fig, "pendulum")

    # 5
    def lorenz_attractor_animation(self, sigma=10.0, rho=28.0, beta=2.667, frames=80):
        if not (MPL and SCIPY): return _no()
        sol = solve_ivp(lambda t, s: [sigma*(s[1]-s[0]), s[0]*(rho-s[2])-s[1], s[0]*s[1]-beta*s[2]],
                        [0, 40], [1, 1, 1], t_eval=np.linspace(0, 40, frames*8))
        X, Y, Z = sol.y; fig, ax = _fig(d3=True); ax.set_title("Lorenz attractor", color="#FFF")
        ax.set_xlim(X.min(), X.max()); ax.set_ylim(Y.min(), Y.max()); ax.set_zlim(Z.min(), Z.max())
        line, = ax.plot([], [], [], color=CYAN, lw=.8)
        def up(i):
            n = i*8; line.set_data(X[:n], Y[:n]); line.set_3d_properties(Z[:n]); ax.view_init(30, i*2); return line,
        return _save(FuncAnimation(fig, up, frames=frames), fig, "lorenz", fps=15)

    # 6
    def quantum_wavefunction_animation(self, n=1, L=1.0, frames=60):
        if not MPL: return _no()
        x = np.linspace(0, L, 200); E = n**2; fig, ax = _fig()
        ax.set_xlim(0, L); ax.set_ylim(-2, 2); ax.set_title(f"Particle in a box n={n}", color="#FFF")
        re_, = ax.plot([], [], color=CYAN); pr_, = ax.plot([], [], color=PINK)
        psi0 = math.sqrt(2/L)*np.sin(n*np.pi*x/L)
        def up(t):
            ph = np.exp(-1j*E*t*0.1); psi = psi0*ph
            re_.set_data(x, psi.real); pr_.set_data(x, np.abs(psi)**2); return re_, pr_
        return _save(FuncAnimation(fig, up, frames=frames, blit=True), fig, "qwave")

    # 7
    def electric_field_animation(self, frames=40):
        if not MPL: return _no()
        fig, ax = _fig(); ax.set_title("Oscillating dipole field", color="#FFF")
        gx = np.linspace(-3, 3, 22); X, Y = np.meshgrid(gx, gx)
        def up(t):
            ax.clear(); ax.set_facecolor(AXES)
            q = math.sin(0.3*t)
            for (px, sign) in [(-1, q), (1, -q)]:
                dx, dy = X-px, Y; r = np.hypot(dx, dy)+.3
                ax.quiver(X, Y, sign*dx/r**2, sign*dy/r**2, color=CYAN, alpha=.6)
            return []
        return _save(FuncAnimation(fig, up, frames=frames), fig, "efield", fps=12)

    # 8
    def fourier_series_animation(self, wave_type="square", n_terms=20, frames=40):
        if not MPL: return _no()
        x = np.linspace(0, 2*np.pi, 500); fig, ax = _fig()
        ax.set_xlim(0, 2*np.pi); ax.set_ylim(-1.5, 1.5); ax.set_title(f"Fourier {wave_type}", color="#FFF")
        line, = ax.plot([], [], color=CYAN)
        def up(k):
            y = np.zeros_like(x)
            for i in range(1, k+1):
                if wave_type == "square": y += (4/np.pi)*np.sin((2*i-1)*x)/(2*i-1)
                else: y += (2/np.pi)*(-1)**(i+1)*np.sin(i*x)/i
            line.set_data(x, y); return line,
        return _save(FuncAnimation(fig, up, frames=min(frames, n_terms), blit=True), fig, "fourier", fps=8)

    # 9
    def ising_model_animation(self, N=40, T=2.269, steps=40):
        if not MPL: return _no()
        rng = np.random.default_rng(0); spins = rng.choice([-1, 1], (N, N))
        fig, ax = _fig(); ax.set_title(f"Ising model T={T}", color="#FFF"); ax.axis("off")
        im = ax.imshow(spins, cmap="cool", vmin=-1, vmax=1)
        def up(_):
            for _ in range(N*N):
                i, j = rng.integers(N), rng.integers(N)
                nb = spins[(i+1)%N, j]+spins[(i-1)%N, j]+spins[i, (j+1)%N]+spins[i, (j-1)%N]
                dE = 2*spins[i, j]*nb
                if dE < 0 or rng.random() < math.exp(-dE/T): spins[i, j] *= -1
            im.set_array(spins); return im,
        return _save(FuncAnimation(fig, up, frames=steps, blit=True), fig, "ising", fps=10)

    # 10
    def molecule_rotation_animation(self, identifier="H2O", frames=60):
        if not MPL: return _no()
        # toy 3D atoms
        atoms = {"H2O": [(0, 0, 0, AMBER, 200), (-.8, .6, 0, CYAN, 80), (.8, .6, 0, CYAN, 80)]}.get(
            identifier, [(0, 0, 0, AMBER, 200), (1, 0, 0, CYAN, 80)])
        fig, ax = _fig(d3=True); ax.set_title(f"{identifier}", color="#FFF")
        ax.set_xlim(-2, 2); ax.set_ylim(-2, 2); ax.set_zlim(-2, 2)
        def up(t):
            ax.view_init(20, t*6)
            return []
        for x, y, z, c, s in atoms: ax.scatter(x, y, z, color=c, s=s)
        return _save(FuncAnimation(fig, up, frames=frames), fig, "molecule", fps=15)

    # 11
    def reaction_diffusion_animation(self, F=0.055, k=0.062, Du=0.16, Dv=0.08, size=80, steps=40):
        if not MPL: return _no()
        U = np.ones((size, size)); V = np.zeros((size, size))
        r = size//8; c = size//2; U[c-r:c+r, c-r:c+r] = .5; V[c-r:c+r, c-r:c+r] = .25
        fig, ax = _fig(); ax.axis("off"); ax.set_title("Gray-Scott", color="#FFF")
        im = ax.imshow(V, cmap="magma")
        def lap(Z): return (np.roll(Z, 1, 0)+np.roll(Z, -1, 0)+np.roll(Z, 1, 1)+np.roll(Z, -1, 1)-4*Z)
        def up(_):
            nonlocal U, V
            for _ in range(8):
                uvv = U*V*V; U += Du*lap(U)-uvv+F*(1-U); V += Dv*lap(V)+uvv-(F+k)*V
            im.set_array(V); return im,
        return _save(FuncAnimation(fig, up, frames=steps, blit=True), fig, "rxndiff", fps=10)

    # 12
    def seir_animation(self, N=100000, beta=0.3, sigma=0.2, gamma=0.1, days=160, frames=80):
        if not (MPL and SCIPY): return _no()
        def d(t, y):
            S, E, I, R = y
            return [-beta*S*I/N, beta*S*I/N-sigma*E, sigma*E-gamma*I, gamma*I]
        sol = solve_ivp(d, [0, days], [N-15, 10, 5, 0], t_eval=np.linspace(0, days, frames))
        fig, ax = _fig(); ax.set_xlim(0, days); ax.set_ylim(0, N); ax.set_title("SEIR epidemic", color="#FFF")
        lines = [ax.plot([], [], color=c, label=l)[0] for c, l in
                 zip([CYAN, AMBER, PINK, "#7CFF6B"], ["S", "E", "I", "R"])]
        ax.legend(labelcolor="#CCC", facecolor=AXES)
        def up(i):
            for ln, comp in zip(lines, sol.y): ln.set_data(sol.t[:i], comp[:i])
            return lines
        return _save(FuncAnimation(fig, up, frames=frames, blit=True), fig, "seir", fps=15)

    # 13
    def action_potential_animation(self, I_ext=10.0, duration=50.0, frames=80):
        if not (MPL and SCIPY): return _no()
        from .biology import BiologyEngine
        hh = BiologyEngine().hodgkin_huxley(I_ext, duration, 0.01)
        V = np.array(hh["V"]); t = np.array(hh["t"]); idx = np.linspace(0, len(V)-1, frames).astype(int)
        fig, ax = _fig(); ax.set_xlim(0, duration); ax.set_ylim(-90, 50)
        ax.set_title("Hodgkin-Huxley AP", color="#FFF"); line, = ax.plot([], [], color=CYAN)
        def up(i): line.set_data(t[:idx[i]], V[:idx[i]]); return line,
        return _save(FuncAnimation(fig, up, frames=frames, blit=True), fig, "ap", fps=20)

    # 14
    def gradient_descent_animation(self, function="x**2 + y**2", lr=0.1, frames=50):
        if not MPL: return _no()
        f = lambda x, y: eval(function, {"x": x, "y": y, "np": np, "math": math})
        gx = np.linspace(-3.5, 3.5, 60); X, Y = np.meshgrid(gx, gx); Z = f(X, Y)
        fig, ax = _fig(); ax.contour(X, Y, Z, 20, cmap="cool", alpha=.6)
        ax.set_title("Gradient descent", color="#FFF"); pt, = ax.plot([], [], "o", color=PINK, ms=10)
        path = [[3.0, 3.0]]
        for _ in range(frames):
            x, y = path[-1]; h = 1e-4
            gxg = (f(x+h, y)-f(x-h, y))/(2*h); gyg = (f(x, y+h)-f(x, y-h))/(2*h)
            path.append([x-lr*gxg, y-lr*gyg])
        path = np.array(path); line, = ax.plot([], [], color=AMBER, lw=1)
        def up(i): pt.set_data([path[i, 0]], [path[i, 1]]); line.set_data(path[:i+1, 0], path[:i+1, 1]); return pt, line
        return _save(FuncAnimation(fig, up, frames=frames, blit=True), fig, "graddesc", fps=15)

    # 15
    def fractal_animation(self, fractal_type="mandelbrot", zoom_center=(-0.7269, 0.1889),
                          zoom_factor=0.92, n_frames=40, max_iter=120):
        if not MPL: return _no()
        fig, ax = _fig(); ax.axis("off"); ax.set_title("Mandelbrot zoom", color="#FFF")
        cx, cy = zoom_center; span = 2.5
        im = ax.imshow(np.zeros((200, 200)), cmap="magma", extent=[-1, 1, -1, 1])
        def up(k):
            s = span*zoom_factor**k
            xs = np.linspace(cx-s, cx+s, 200); ys = np.linspace(cy-s, cy+s, 200)
            C = xs[None, :]+1j*ys[:, None]; Zc = np.zeros_like(C); M = np.zeros(C.shape)
            for i in range(max_iter):
                Zc = Zc*Zc+C; esc = (np.abs(Zc) > 2) & (M == 0); M[esc] = i
            im.set_array(M); im.set_clim(0, max_iter); return im,
        return _save(FuncAnimation(fig, up, frames=n_frames, blit=True), fig, "fractal", fps=12)

    # 16
    def black_hole_orbit_animation(self, M_solar=10.0, frames=120):
        if not (MPL and SCIPY): return _no()
        # precessing orbit (Schwarzschild-like effective potential)
        def d(t, s):
            r, dr, phi = s; L = 3.8
            ddr = L**2/r**3 - 1/r**2 - 3*L**2/r**4
            return [dr, ddr, L/r**2]
        sol = solve_ivp(d, [0, 200], [10, 0, 0], t_eval=np.linspace(0, 200, frames), max_step=.5)
        r, phi = sol.y[0], sol.y[2]; x, y = r*np.cos(phi), r*np.sin(phi)
        fig, ax = _fig(); ax.set_aspect("equal"); ax.set_xlim(-12, 12); ax.set_ylim(-12, 12)
        ax.set_title(f"{M_solar} M☉ black-hole orbit", color="#FFF")
        ax.plot(0, 0, "o", color="#000", ms=18, mec=AMBER)
        trail, = ax.plot([], [], color=CYAN, alpha=.5); dot, = ax.plot([], [], "o", color=PINK)
        def up(i): trail.set_data(x[:i+1], y[:i+1]); dot.set_data([x[i]], [y[i]]); return trail, dot
        return _save(FuncAnimation(fig, up, frames=frames, blit=True), fig, "bhorbit", fps=20)

    # 17
    def nuclear_decay_chain_animation(self, parent="U-238", frames=60):
        if not MPL: return _no()
        t = np.linspace(0, 10, frames)
        N1 = np.exp(-0.3*t); N2 = 0.3/(0.7-0.3)*(np.exp(-0.3*t)-np.exp(-0.7*t)); N3 = 1-N1-N2
        fig, ax = _fig(); ax.set_xlim(0, 10); ax.set_ylim(0, 1.05); ax.set_title(f"{parent} chain", color="#FFF")
        ls = [ax.plot([], [], color=c, label=l)[0] for c, l in zip([CYAN, AMBER, PINK], ["parent", "daughter", "stable"])]
        ax.legend(labelcolor="#CCC", facecolor=AXES)
        def up(i):
            for ln, N in zip(ls, [N1, N2, N3]): ln.set_data(t[:i], N[:i])
            return ls
        return _save(FuncAnimation(fig, up, frames=frames, blit=True), fig, "decay", fps=15)

    # 18
    def quantum_circuit_animation(self, frames=40):
        if not MPL: return _no()
        from ..tech.quantum_computing import StateVector
        sv = StateVector(2); fig, ax = _fig(); ax.set_ylim(0, 1); ax.set_title("Bell state build", color="#FFF")
        bars = ax.bar(["00", "01", "10", "11"], [1, 0, 0, 0], color=CYAN)
        seq = [("h", 0), ("cx", 0, 1)]
        def up(i):
            if i < len(seq): getattr(sv, seq[i][0])(*seq[i][1:])
            for b, p in zip(bars, np.abs(sv.state)**2): b.set_height(p)
            return bars
        return _save(FuncAnimation(fig, up, frames=min(frames, 4), blit=False), fig, "qcircuit", fps=2)

    # 19
    def robot_path_animation(self, frames=None):
        if not MPL: return _no()
        from ..tech.robotics import RoboticsEngine
        grid = np.zeros((20, 20)); grid[10, 2:18] = 1
        path = RoboticsEngine().a_star(grid, (0, 0), (19, 19))["path"] or [(0, 0)]
        fig, ax = _fig(); ax.imshow(grid, cmap="bone_r"); ax.set_title("A* path", color="#FFF")
        dot, = ax.plot([], [], "o", color=PINK, ms=8); tr, = ax.plot([], [], color=CYAN)
        px = [p[1] for p in path]; py = [p[0] for p in path]
        def up(i): dot.set_data([px[i]], [py[i]]); tr.set_data(px[:i+1], py[:i+1]); return dot, tr
        return _save(FuncAnimation(fig, up, frames=len(path), blit=True), fig, "robotpath", fps=12)

    # 20
    def solar_system_animation(self, frames=120):
        if not MPL: return _no()
        radii = [0.4, 0.7, 1.0, 1.5]; periods = [0.24, 0.62, 1.0, 1.88]; cols = [AMBER, PINK, CYAN, "#FF5533"]
        fig, ax = _fig(); ax.set_aspect("equal"); lim = 1.8; ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
        ax.set_title("Inner solar system", color="#FFF"); ax.plot(0, 0, "o", color=AMBER, ms=16)
        dots = [ax.plot([], [], "o", color=c, ms=6)[0] for c in cols]
        for r in radii: ax.add_patch(plt.Circle((0, 0), r, fill=False, color="#333"))
        def up(t):
            for dot, r, T in zip(dots, radii, periods):
                a = 2*np.pi*t/(frames)*(1/T); dot.set_data([r*np.cos(a)], [r*np.sin(a)])
            return dots
        return _save(FuncAnimation(fig, up, frames=frames, blit=True), fig, "solar", fps=20)

    # 21
    def stellar_evolution_animation(self, mass_list=(0.5, 1.0, 5.0, 20.0), frames=60):
        if not MPL: return _no()
        fig, ax = _fig(); ax.set_xlim(4.8, 3.4); ax.set_ylim(-2, 6)
        ax.set_xlabel("log Teff"); ax.set_ylabel("log L"); ax.set_title("HR tracks", color="#FFF")
        dots = [ax.plot([], [], "o", color=c)[0] for c in [CYAN, PINK, AMBER, "#FF5533"]]
        def up(i):
            f = i/frames
            for dot, M in zip(dots, mass_list):
                L = M**3.5; T = 5772*(L/M**1.6)**.25*(1-0.3*f); dot.set_data([math.log10(T)], [math.log10(L*(1+4*f))])
            return dots
        return _save(FuncAnimation(fig, up, frames=frames, blit=True), fig, "hr", fps=15)

    # 22
    def neural_net_training_animation(self, frames=40):
        if not MPL: return _no()
        try:
            from sklearn.datasets import make_moons
            from sklearn.neural_network import MLPClassifier
        except Exception:
            return {"result": None, "verbal": "sklearn needed, sir."}
        X, y = make_moons(200, noise=.2, random_state=0)
        fig, ax = _fig(); ax.set_title("Decision boundary forming", color="#FFF")
        xx, yy = np.meshgrid(np.linspace(-2, 3, 80), np.linspace(-1.5, 2, 80))
        clf = MLPClassifier(hidden_layer_sizes=(16, 16), warm_start=True, max_iter=1)
        cont = [None]
        def up(i):
            clf.max_iter = 1
            try: clf.fit(X, y)
            except Exception: pass
            Z = clf.predict(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)
            ax.clear(); ax.set_facecolor(AXES); ax.contourf(xx, yy, Z, alpha=.4, cmap="cool")
            ax.scatter(X[:, 0], X[:, 1], c=y, cmap="cool", s=12); ax.set_title(f"epoch {i}", color="#FFF")
            return []
        return _save(FuncAnimation(fig, up, frames=frames), fig, "nntrain", fps=10)

    # 23
    def protein_folding_animation(self, sequence="MEEKLAAAL", frames=60):
        if not MPL: return _no()
        n = len(sequence); rng = np.random.default_rng(0)
        target = np.cumsum(rng.normal(0, 1, (n, 3)), axis=0)
        start = np.column_stack([np.arange(n), np.zeros(n), np.zeros(n)]).astype(float)
        fig, ax = _fig(d3=True); ax.set_title("Folding (schematic)", color="#FFF")
        def up(t):
            ax.clear(); ax.set_facecolor(AXES); f = t/frames
            pos = start*(1-f)+target*f
            ax.plot(pos[:, 0], pos[:, 1], pos[:, 2], "-o", color=CYAN, ms=4); return []
        return _save(FuncAnimation(fig, up, frames=frames), fig, "fold", fps=15)

    # 24
    def fluid_flow_animation(self, Re=100, frames=40):
        if not MPL: return _no()
        size = 60; rng = np.random.default_rng(0)
        fig, ax = _fig(); ax.axis("off"); ax.set_title(f"Vortex shedding Re={Re}", color="#FFF")
        x = np.linspace(0, 4, size); X, Y = np.meshgrid(x, np.linspace(-1, 1, size))
        im = ax.imshow(np.zeros((size, size)), cmap="cool", extent=[0, 4, -1, 1])
        def up(t):
            w = np.sin(3*X-0.3*t)*np.exp(-(Y**2)*3)*np.cos(2*Y+0.2*t); im.set_array(w); im.set_clim(-1, 1); return im,
        return _save(FuncAnimation(fig, up, frames=frames, blit=True), fig, "fluid", fps=12)

    # 25
    def cellular_automaton_animation(self, rule=30, size=101, frames=60):
        if not MPL: return _no()
        from .models import SimulationModels
        row = np.zeros(size, int); row[size//2] = 1; rows = [row.copy()]
        bits = [(rule >> i) & 1 for i in range(8)]
        fig, ax = _fig(); ax.axis("off"); ax.set_title(f"Rule {rule}", color="#FFF")
        grid = np.zeros((frames, size)); grid[0] = row; im = ax.imshow(grid, cmap="magma", aspect="auto")
        def up(i):
            nonlocal row
            if i > 0:
                left = np.roll(row, 1); right = np.roll(row, -1)
                row = np.array([bits[(left[j]<<2)|(row[j]<<1)|right[j]] for j in range(size)])
                grid[i] = row; im.set_array(grid)
            return im,
        return _save(FuncAnimation(fig, up, frames=frames, blit=True), fig, "ca", fps=15)

    # 26
    def n_body_galaxy_animation(self, N=120, frames=80):
        if not MPL: return _no()
        rng = np.random.default_rng(0)
        r = rng.uniform(.2, 3, N); th = rng.uniform(0, 2*np.pi, N)
        pos = np.column_stack([r*np.cos(th), r*np.sin(th)])
        vel = np.column_stack([-np.sin(th), np.cos(th)])*np.sqrt(1/r)[:, None]
        fig, ax = _fig(); ax.set_facecolor("#05050A"); ax.set_xlim(-4, 4); ax.set_ylim(-4, 4)
        ax.set_title("Galaxy (N-body)", color="#FFF"); ax.axis("off")
        sc = ax.scatter(pos[:, 0], pos[:, 1], s=4, color=CYAN)
        def up(_):
            nonlocal pos, vel
            rr = np.linalg.norm(pos, axis=1, keepdims=True)+.1
            acc = -pos/rr**3; vel += acc*0.02; pos += vel*0.02; sc.set_offsets(pos); return sc,
        return _save(FuncAnimation(fig, up, frames=frames, blit=True), fig, "galaxy", fps=20)

    # 27
    def rl_training_animation(self, frames=50):
        if not MPL: return _no()
        rng = np.random.default_rng(0); rewards = np.cumsum(rng.normal(1, 5, frames)).clip(min=0)
        rewards = rewards/rewards.max()*200
        fig, ax = _fig(); ax.set_xlim(0, frames); ax.set_ylim(0, 220)
        ax.set_xlabel("episode"); ax.set_ylabel("reward"); ax.set_title("RL learning curve", color="#FFF")
        line, = ax.plot([], [], color=CYAN)
        def up(i): line.set_data(range(i), rewards[:i]); return line,
        return _save(FuncAnimation(fig, up, frames=frames, blit=True), fig, "rltrain", fps=15)

    # 28
    def phase_space_animation(self, system="van_der_pol", mu=1.0, frames=80):
        if not (MPL and SCIPY): return _no()
        def vdp(t, s): return [s[1], mu*(1-s[0]**2)*s[1]-s[0]]
        fig, ax = _fig(); ax.set_xlim(-3, 3); ax.set_ylim(-4, 4)
        ax.set_xlabel("x"); ax.set_ylabel("v"); ax.set_title("Van der Pol phase space", color="#FFF")
        trajs = []
        for ic in [(-2, 0), (0.1, 0.1), (2, 2)]:
            sol = solve_ivp(vdp, [0, 20], ic, t_eval=np.linspace(0, 20, frames*4))
            trajs.append(sol.y)
        lines = [ax.plot([], [], color=c, lw=1)[0] for c in [CYAN, PINK, AMBER]]
        def up(i):
            for ln, tr in zip(lines, trajs): ln.set_data(tr[0, :i*4], tr[1, :i*4])
            return lines
        return _save(FuncAnimation(fig, up, frames=frames, blit=True), fig, "phasespace", fps=20)

    def test(self) -> None:
        if not MPL:
            print("animator: matplotlib unavailable (skipped)"); return
        assert os.path.exists(self.projectile_animation(frames=8)["gif_path"])
        assert os.path.exists(self.fourier_series_animation(n_terms=5, frames=5)["gif_path"])
        # count methods
        methods = [m for m in dir(self) if m.endswith("_animation")]
        assert len(methods) == 28, f"expected 28, got {len(methods)}"
        print(f"animator.DEEPAnimator: OK ({len(methods)} animations)")


_anim = DEEPAnimator()
_NUM = re.compile(r"-?\d+\.?\d*")


def animate(text: str) -> dict:
    low = text.lower(); n = [float(x) for x in _NUM.findall(text)]
    table = [
        (("lorenz", "attractor"), lambda: _anim.lorenz_attractor_animation()),
        (("projectile",), lambda: _anim.projectile_animation(n[0] if n else 45, n[1] if len(n) > 1 else 20)),
        (("double pendulum", "pendulum"), lambda: _anim.pendulum_animation()),
        (("orbit", "kepler"), lambda: _anim.orbital_animation()),
        (("solar system", "planets"), lambda: _anim.solar_system_animation()),
        (("wavefunction", "particle in a box"), lambda: _anim.quantum_wavefunction_animation()),
        (("electric field", "dipole"), lambda: _anim.electric_field_animation()),
        (("fourier",), lambda: _anim.fourier_series_animation()),
        (("ising",), lambda: _anim.ising_model_animation()),
        (("molecule",), lambda: _anim.molecule_rotation_animation()),
        (("reaction diffusion", "gray-scott", "gray scott"), lambda: _anim.reaction_diffusion_animation()),
        (("seir", "epidemic", "outbreak"), lambda: _anim.seir_animation()),
        (("action potential", "neuron"), lambda: _anim.action_potential_animation()),
        (("gradient descent",), lambda: _anim.gradient_descent_animation()),
        (("fractal", "mandelbrot"), lambda: _anim.fractal_animation()),
        (("black hole",), lambda: _anim.black_hole_orbit_animation()),
        (("decay chain", "decay"), lambda: _anim.nuclear_decay_chain_animation()),
        (("quantum circuit", "bell"), lambda: _anim.quantum_circuit_animation()),
        (("robot", "path"), lambda: _anim.robot_path_animation()),
        (("stellar", "hr diagram"), lambda: _anim.stellar_evolution_animation()),
        (("neural", "training", "decision boundary"), lambda: _anim.neural_net_training_animation()),
        (("protein", "folding"), lambda: _anim.protein_folding_animation()),
        (("fluid", "flow", "vortex"), lambda: _anim.fluid_flow_animation()),
        (("cellular automaton", "rule "), lambda: _anim.cellular_automaton_animation()),
        (("galaxy", "n-body"), lambda: _anim.n_body_galaxy_animation()),
        (("rl ", "reinforcement"), lambda: _anim.rl_training_animation()),
        (("phase space", "van der pol"), lambda: _anim.phase_space_animation()),
        (("wave",), lambda: _anim.wave_animation(n[0] if n else 1.0)),
    ]
    for keys, fn in table:
        if any(k in low for k in keys):
            return fn()
    return _anim.wave_animation()


def test() -> None:
    DEEPAnimator().test()


if __name__ == "__main__":
    test()
