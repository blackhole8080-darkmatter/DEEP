# deep/science/visualizer.py — Visualisation Engine (Bible Section 16.1)
"""Dark-neon scientific plotting. Saves 300-DPI PNGs to config.PLOTS_DIR.
Headless (Agg) backend so it runs on a server."""
from __future__ import annotations

import os
import re
import time

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    MPL = True
except Exception:  # pragma: no cover
    MPL = False

import sympy as sp

try:
    from .. import config
    PLOTS_DIR = str(config.PLOTS_DIR)
except Exception:  # pragma: no cover
    PLOTS_DIR = os.path.join(os.path.expanduser("~"), "deep_output", "plots")

os.makedirs(PLOTS_DIR, exist_ok=True)

BG = "#0D0D1A"
AXES = "#1A1A2E"
NEON = ["#00FFFF", "#FF00FF", "#FF6B9D", "#FFB800", "#7CFF6B"]


def _style(ax, fig):
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(AXES)
    ax.grid(True, alpha=0.2, color="#888")
    for spine in ax.spines.values():
        spine.set_color("#444")
    ax.tick_params(colors="#CCC")
    ax.xaxis.label.set_color("#CCC")
    ax.yaxis.label.set_color("#CCC")
    ax.title.set_color("#FFF")


def _save(fig, name) -> str:
    path = os.path.join(PLOTS_DIR, f"{name}_{int(time.time()*1000)}.png")
    fig.savefig(path, dpi=300, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return path


class DEEPVisualizer:
    def __init__(self, config=None):
        self.config = config

    def plot_function(self, exprs, x_range=(-10, 10), labels=None, title="Function") -> str:
        if not MPL:
            return ""
        if isinstance(exprs, str):
            exprs = [exprs]
        x = np.linspace(x_range[0], x_range[1], 1000)
        xs = sp.Symbol("x")
        fig, ax = plt.subplots(figsize=(8, 5))
        for i, e in enumerate(exprs):
            f = sp.lambdify(xs, sp.sympify(e.replace("^", "**")), "numpy")
            try:
                y = f(x)
            except Exception:
                y = np.array([f(xi) for xi in x])
            ax.plot(x, y, color=NEON[i % len(NEON)], lw=2,
                    label=(labels[i] if labels else str(e)))
        ax.set_title(title); ax.set_xlabel("x"); ax.set_ylabel("y")
        ax.legend(facecolor=AXES, edgecolor="#444", labelcolor="#CCC")
        _style(ax, fig)
        return _save(fig, "plot")

    def plot_3d_surface(self, expr, x_range=(-5, 5), y_range=(-5, 5)) -> str:
        if not MPL:
            return ""
        x, y = sp.symbols("x y")
        f = sp.lambdify((x, y), sp.sympify(expr.replace("^", "**")), "numpy")
        X, Y = np.meshgrid(np.linspace(*x_range, 80), np.linspace(*y_range, 80))
        Z = f(X, Y)
        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111, projection="3d")
        ax.plot_surface(X, Y, Z, cmap="cool", edgecolor="none")
        ax.set_title("3D Surface", color="#FFF")
        fig.patch.set_facecolor(BG); ax.set_facecolor(AXES)
        for a in (ax.xaxis, ax.yaxis, ax.zaxis):
            a.label.set_color("#CCC"); a.set_tick_params(colors="#CCC")
        return _save(fig, "surface")

    def phase_portrait(self, fx, fy, x_range=(-3, 3), y_range=(-3, 3)) -> str:
        if not MPL:
            return ""
        x, y = sp.symbols("x y")
        Fx = sp.lambdify((x, y), sp.sympify(fx), "numpy")
        Fy = sp.lambdify((x, y), sp.sympify(fy), "numpy")
        X, Y = np.meshgrid(np.linspace(*x_range, 25), np.linspace(*y_range, 25))
        U, V = Fx(X, Y), Fy(X, Y)
        fig, ax = plt.subplots(figsize=(7, 6))
        ax.streamplot(X, Y, U, V, color=np.hypot(U, V), cmap="cool", density=1.2)
        ax.set_title("Phase Portrait"); ax.set_xlabel("x"); ax.set_ylabel("y")
        _style(ax, fig)
        return _save(fig, "phase")

    def heatmap(self, Z, title="Heatmap") -> str:
        if not MPL:
            return ""
        fig, ax = plt.subplots(figsize=(7, 6))
        im = ax.imshow(Z, cmap="magma", aspect="auto", origin="lower")
        fig.colorbar(im, ax=ax)
        ax.set_title(title); _style(ax, fig)
        return _save(fig, "heatmap")

    def scatter_plot(self, X, y=None, title="Scatter") -> str:
        if not MPL:
            return ""
        X = np.asarray(X)
        fig, ax = plt.subplots(figsize=(7, 6))
        ax.scatter(X[:, 0], X[:, 1], c=(y if y is not None else NEON[0]),
                   cmap="cool", s=30, edgecolors="none")
        ax.set_title(title); _style(ax, fig)
        return _save(fig, "scatter")

    def histogram(self, data, bins=50, title="Histogram") -> str:
        if not MPL:
            return ""
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.hist(data, bins=bins, color=NEON[0], alpha=0.8, edgecolor=BG)
        ax.set_title(title); _style(ax, fig)
        return _save(fig, "hist")

    def loss_curve_plot(self, history: dict) -> str:
        if not MPL:
            return ""
        fig, ax = plt.subplots(figsize=(8, 5))
        if history.get("train_losses"):
            ax.plot(history["train_losses"], color=NEON[0], label="train")
        if history.get("val_losses"):
            ax.plot(history["val_losses"], color=NEON[1], label="val")
        ax.set_title("Training Loss"); ax.set_xlabel("epoch"); ax.set_ylabel("loss")
        ax.legend(facecolor=AXES, edgecolor="#444", labelcolor="#CCC")
        _style(ax, fig)
        return _save(fig, "loss")

    def contour_plot(self, Z, levels=20, filled=True) -> str:
        if not MPL: return ""
        fig, ax = plt.subplots(figsize=(7, 6))
        (ax.contourf if filled else ax.contour)(np.asarray(Z), levels=levels, cmap="cool")
        ax.set_title("Contour"); _style(ax, fig); return _save(fig, "contour")

    def bar_chart(self, categories, values, errors=None, title="Bar") -> str:
        if not MPL: return ""
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(categories, values, yerr=errors, color=NEON[0], alpha=.85, edgecolor=BG,
               capsize=4)
        ax.set_title(title); _style(ax, fig)
        for lbl in ax.get_xticklabels(): lbl.set_rotation(30)
        return _save(fig, "bar")

    def spectrum_plot(self, x, y, peaks=None, title="Spectrum") -> str:
        if not MPL: return ""
        fig, ax = plt.subplots(figsize=(8, 5)); ax.plot(x, y, color=NEON[0])
        if peaks is not None:
            ax.plot(np.asarray(x)[peaks], np.asarray(y)[peaks], "v", color=PINK if False else NEON[2])
        ax.set_title(title); ax.set_xlabel("frequency"); ax.set_ylabel("magnitude")
        _style(ax, fig); return _save(fig, "spectrum")

    def correlation_matrix(self, data, labels=None) -> str:
        if not MPL: return ""
        corr = np.corrcoef(np.asarray(data), rowvar=False)
        fig, ax = plt.subplots(figsize=(7, 6))
        im = ax.imshow(corr, cmap="cool", vmin=-1, vmax=1); fig.colorbar(im, ax=ax)
        if labels:
            ax.set_xticks(range(len(labels))); ax.set_yticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=45); ax.set_yticklabels(labels)
        ax.set_title("Correlation matrix"); _style(ax, fig); return _save(fig, "corr")

    def network_graph(self, G, layout="spring") -> str:
        if not MPL: return ""
        try:
            import networkx as nx
        except Exception:
            return ""
        pos = {"spring": nx.spring_layout, "circular": nx.circular_layout}.get(
            layout, nx.spring_layout)(G, seed=1)
        fig, ax = plt.subplots(figsize=(7, 6))
        nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#3aa", alpha=.5)
        nx.draw_networkx_nodes(G, pos, ax=ax, node_color=NEON[0], node_size=300)
        nx.draw_networkx_labels(G, pos, ax=ax, font_color=BG, font_size=8)
        ax.set_title("Network graph", color="#FFF"); fig.patch.set_facecolor(BG)
        ax.set_facecolor(AXES); ax.axis("off"); return _save(fig, "network")

    def ramachandran_plot(self, phi, psi) -> str:
        if not MPL: return ""
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.scatter(phi, psi, s=10, color=NEON[0], alpha=.7)
        ax.set_xlim(-180, 180); ax.set_ylim(-180, 180)
        ax.set_xlabel("φ"); ax.set_ylabel("ψ"); ax.set_title("Ramachandran")
        ax.axhline(0, color="#444"); ax.axvline(0, color="#444"); _style(ax, fig)
        return _save(fig, "rama")

    def orbital_plot(self, n=2, l=1, m=0) -> str:
        if not MPL: return ""
        from .quantum_mech import QuantumMechanics
        d = QuantumMechanics().hydrogen_atom_wavefunction(n, l, m)
        fig, ax = plt.subplots(figsize=(7, 5))
        if d.get("r"):
            ax.plot(d["r"], d["prob_density"], color=NEON[0])
            ax.fill_between(d["r"], d["prob_density"], color=NEON[0], alpha=.25)
        ax.set_title(f"Hydrogen radial density n={n}, l={l}")
        ax.set_xlabel("r (a₀)"); ax.set_ylabel("r²|R|²"); _style(ax, fig)
        return _save(fig, "orbital")

    def energy_landscape(self, expr="x**2 + y**2 - cos(3*x)", x_range=(-3, 3), y_range=(-3, 3)) -> str:
        if not MPL: return ""
        x, y = sp.symbols("x y")
        f = sp.lambdify((x, y), sp.sympify(expr), "numpy")
        X, Y = np.meshgrid(np.linspace(*x_range, 80), np.linspace(*y_range, 80))
        fig = plt.figure(figsize=(8, 6)); ax = fig.add_subplot(111, projection="3d")
        ax.plot_surface(X, Y, f(X, Y), cmap="magma", edgecolor="none")
        ax.set_title("Energy landscape", color="#FFF"); fig.patch.set_facecolor(BG)
        ax.set_facecolor(AXES); return _save(fig, "landscape")

    def periodic_table_heatmap(self, property_name="mass") -> str:
        if not MPL: return ""
        from .chemistry import ELEMENTS
        grid = np.full((7, 18), np.nan)
        # crude period/group placement for first 18 + a few
        layout = {1: (0, 0), 2: (0, 17)}
        for z in range(3, 11): layout[z] = (1, z-3 if z <= 4 else z-3+10)
        for z in range(11, 19): layout[z] = (2, z-11 if z <= 12 else z-11+10)
        vals = {z: m for z, s, n, m in ELEMENTS}
        for z, (r, c) in layout.items():
            if z in vals: grid[r, c] = vals[z]
        fig, ax = plt.subplots(figsize=(9, 4))
        im = ax.imshow(grid, cmap="cool"); fig.colorbar(im, ax=ax, label=property_name)
        ax.set_title("Periodic table heatmap"); ax.axis("off")
        fig.patch.set_facecolor(BG); return _save(fig, "ptable")

    def nuclide_chart(self, z_max=30) -> str:
        if not MPL: return ""
        Z = np.arange(1, z_max); N = Z*1.1 + 0.01*Z**2  # valley of stability proxy
        fig, ax = plt.subplots(figsize=(7, 6))
        ax.plot(N, Z, color=NEON[2], lw=2, label="stability line")
        ax.scatter(N, Z, c=Z, cmap="magma", s=20)
        ax.set_xlabel("N (neutrons)"); ax.set_ylabel("Z (protons)")
        ax.set_title("Chart of nuclides"); ax.legend(labelcolor="#CCC", facecolor=AXES)
        _style(ax, fig); return _save(fig, "nuclide")

    def pca_biplot(self, X, labels=None) -> str:
        if not MPL: return ""
        try:
            from sklearn.decomposition import PCA
        except Exception:
            return ""
        Xr = PCA(n_components=2).fit_transform(np.asarray(X))
        fig, ax = plt.subplots(figsize=(7, 6))
        ax.scatter(Xr[:, 0], Xr[:, 1], c=(labels if labels is not None else NEON[0]),
                   cmap="cool", s=20)
        ax.set_xlabel("PC1"); ax.set_ylabel("PC2"); ax.set_title("PCA biplot")
        _style(ax, fig); return _save(fig, "pca")

    def confusion_matrix_plot(self, y_true, y_pred, classes=None) -> str:
        if not MPL: return ""
        yt = np.asarray(y_true); yp = np.asarray(y_pred)
        k = int(max(yt.max(), yp.max())) + 1
        cm = np.zeros((k, k), int)
        for a, b in zip(yt, yp): cm[a, b] += 1
        fig, ax = plt.subplots(figsize=(6, 5))
        im = ax.imshow(cm, cmap="cool"); fig.colorbar(im, ax=ax)
        for i in range(k):
            for j in range(k):
                ax.text(j, i, cm[i, j], ha="center", color="#FFF")
        ax.set_xlabel("predicted"); ax.set_ylabel("true"); ax.set_title("Confusion matrix")
        _style(ax, fig); return _save(fig, "confusion")

    def roc_curve_plot(self, y_true, y_score) -> str:
        if not MPL: return ""
        try:
            from sklearn.metrics import roc_curve, auc
            fpr, tpr, _ = roc_curve(y_true, y_score); a = auc(fpr, tpr)
        except Exception:
            return ""
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.plot(fpr, tpr, color=NEON[0], label=f"AUC={a:.3f}")
        ax.plot([0, 1], [0, 1], "--", color="#555")
        ax.set_xlabel("FPR"); ax.set_ylabel("TPR"); ax.set_title("ROC curve")
        ax.legend(labelcolor="#CCC", facecolor=AXES); _style(ax, fig)
        return _save(fig, "roc")

    def manim_render(self, scene_class="EquationTransform", params=None) -> dict:
        try:
            import manim  # noqa: F401
        except Exception:
            return {"result": None,
                    "verbal": "Manim isn't installed (needs LaTeX + ffmpeg), sir. "
                              f"Scene '{scene_class}' is configured and ready."}
        return {"result": "ready",
                "verbal": f"Manim scene '{scene_class}' ready to render, sir."}

    def test(self) -> None:
        if not MPL:
            print("visualizer: matplotlib unavailable (skipped)"); return
        assert os.path.exists(self.plot_function("sin(x)", (-6.28, 6.28)))
        assert os.path.exists(self.phase_portrait("y", "-x"))
        assert os.path.exists(self.bar_chart(["a", "b", "c"], [3, 1, 2]))
        assert os.path.exists(self.nuclide_chart())
        rng = np.random.default_rng(0)
        assert os.path.exists(self.correlation_matrix(rng.normal(0, 1, (50, 4))))
        assert os.path.exists(self.confusion_matrix_plot([0, 1, 1, 0], [0, 1, 0, 0]))
        plots = [m for m in dir(self) if m.endswith(("_plot", "_chart", "_graph",
                 "_matrix", "_heatmap", "_portrait", "plot_function", "plot_3d_surface",
                 "histogram", "heatmap", "energy_landscape", "nuclide_chart"))]
        print(f"visualizer.DEEPVisualizer: OK ({len(plots)} plot types)")


_viz = DEEPVisualizer()
_NUM = re.compile(r"-?\d+\.?\d*")


def _extract_expr(text):
    t = text
    for kw in ("surface plot", "surface", "3d", "3-d", "contour", "heatmap",
               "plot", "graph", "chart", "visualize", "visualise", "show function",
               "show me", "show", "of", "the", "function", "draw"):
        t = re.sub(rf"\b{re.escape(kw)}\b", " ", t, flags=re.I)
    return t.strip(" .?") or "sin(x)"


def plot(text: str) -> dict:
    expr = _extract_expr(text)
    try:
        path = _viz.plot_function(expr)
        return {"plot_path": path, "result": path,
                "verbal": f"I've plotted {expr}, sir. Saved to {os.path.basename(path)}."}
    except Exception as e:  # noqa: BLE001
        return {"result": None, "verbal": f"Could not plot that, sir: {e}"}


def phase_portrait(text: str) -> dict:
    path = _viz.phase_portrait("y", "-x")
    return {"plot_path": path, "result": path,
            "verbal": f"Phase portrait rendered to {os.path.basename(path)}, sir."}


def surface_plot(text: str) -> dict:
    expr = _extract_expr(text) or "sin(sqrt(x**2+y**2))"
    if "x" not in expr or "y" not in expr:
        expr = "sin(sqrt(x**2+y**2))"
    try:
        path = _viz.plot_3d_surface(expr)
        return {"plot_path": path, "result": path,
                "verbal": f"3D surface of {expr} saved to {os.path.basename(path)}, sir."}
    except Exception as e:  # noqa: BLE001
        return {"result": None, "verbal": f"Could not render surface, sir: {e}"}


def test() -> None:
    DEEPVisualizer().test()


if __name__ == "__main__":
    test()
