# deep/science/compute.py — Symbolic & Numerical Mathematics (Bible Section 5.1)
"""Foundational mathematics engine.

Wraps sympy (symbolic), numpy/scipy (numerical) under a unified interface.
Every method returns a dict including a human-readable ``verbal`` summary so the
orchestrator can speak the result.
"""
from __future__ import annotations

import re
from typing import Optional

import sympy as sp

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

try:
    from scipy import integrate as _scipy_integrate
    from scipy import linalg as _scipy_linalg
    from scipy import optimize as _scipy_optimize
    SCIPY = True
except Exception:  # pragma: no cover
    SCIPY = False


# ── helpers ──────────────────────────────────────────────────────────────
def _sym(name: str):
    return sp.Symbol(name)


def _parse(expr: str):
    """Parse a math string into a sympy expression (safe, no eval)."""
    expr = expr.strip()
    # common natural-language cleanups
    expr = expr.replace("^", "**")
    return sp.sympify(expr)


def _latex(obj) -> str:
    try:
        return sp.latex(obj)
    except Exception:
        return str(obj)


class ComputeEngine:
    def __init__(self, config=None):
        self.config = config

    # ── 5.1.1 core ──────────────────────────────────────────────────
    def compute(self, expression: str) -> dict:
        """Parse, detect type, evaluate. Returns symbolic/numeric/latex/verbal."""
        expr = _parse(expression)
        simplified = sp.simplify(expr)
        numeric = None
        try:
            val = sp.N(simplified)
            if val.is_number:
                numeric = float(val)
        except Exception:
            numeric = None
        verbal = f"{expression} simplifies to {simplified}"
        if numeric is not None:
            verbal += f" ≈ {numeric:.6g}"
        return {"symbolic": str(simplified), "numeric": numeric,
                "latex": _latex(simplified), "verbal": verbal, "result": str(simplified)}

    def simplify(self, expr: str) -> dict:
        e = sp.simplify(_parse(expr))
        return {"symbolic": str(e), "latex": _latex(e),
                "verbal": f"Simplified: {e}", "result": str(e)}

    def expand(self, expr: str) -> dict:
        e = sp.expand(_parse(expr))
        return {"symbolic": str(e), "latex": _latex(e),
                "verbal": f"Expanded: {e}", "result": str(e)}

    def factor(self, expr: str) -> dict:
        e = sp.factor(_parse(expr))
        return {"symbolic": str(e), "latex": _latex(e),
                "verbal": f"Factored: {e}", "result": str(e)}

    def substitute(self, expr: str, var: str, val) -> dict:
        e = _parse(expr).subs(_sym(var), val)
        return {"symbolic": str(e), "numeric": _safe_float(e), "latex": _latex(e),
                "verbal": f"Substituting {var}={val} gives {e}", "result": str(e)}

    # ── 5.1.2 calculus ──────────────────────────────────────────────
    def differentiate(self, expr: str, var: str = "x", order: int = 1) -> dict:
        x = _sym(var)
        d = sp.diff(_parse(expr), x, order)
        ord_txt = {1: "derivative", 2: "second derivative"}.get(order, f"{order}th derivative")
        return {"symbolic": str(d), "latex": _latex(d),
                "verbal": f"The {ord_txt} of {expr} with respect to {var} is {d}",
                "result": str(d)}

    def integrate(self, expr: str, var: str = "x",
                  lower=None, upper=None) -> dict:
        x = _sym(var)
        e = _parse(expr)
        if lower is not None and upper is not None:
            res = sp.integrate(e, (x, sp.sympify(lower), sp.sympify(upper)))
            numeric = _safe_float(res)
            if numeric is None and SCIPY:
                f = sp.lambdify(x, e, "numpy")
                numeric, _ = _scipy_integrate.quad(f, float(lower), float(upper))
            return {"symbolic": str(res), "numeric": numeric, "latex": _latex(res),
                    "verbal": f"The definite integral of {expr} from {lower} to {upper} is "
                              f"{numeric if numeric is not None else res}",
                    "result": str(res)}
        res = sp.integrate(e, x)
        return {"symbolic": str(res), "latex": _latex(res),
                "verbal": f"The integral of {expr} with respect to {var} is {res} + C",
                "result": str(res)}

    def limit(self, expr: str, var: str = "x", point=0, direction: str = "+") -> dict:
        x = _sym(var)
        pt = sp.oo if str(point) in ("oo", "inf", "infinity") else sp.sympify(point)
        dir_map = {"+": "+", "-": "-", "+-": "+-"}
        res = sp.limit(_parse(expr), x, pt, dir_map.get(direction, "+"))
        return {"symbolic": str(res), "numeric": _safe_float(res), "latex": _latex(res),
                "verbal": f"The limit of {expr} as {var} → {point} is {res}",
                "result": str(res)}

    def series(self, expr: str, var: str = "x", point=0, n: int = 6) -> dict:
        x = _sym(var)
        s = sp.series(_parse(expr), x, point, n)
        poly = s.removeO()
        coeffs = [str(poly.coeff(x, i)) for i in range(n)]
        return {"series_str": str(s), "coefficients": coeffs, "latex": _latex(s),
                "verbal": f"The Taylor series of {expr} about {var}={point} is {s}",
                "result": str(s)}

    def gradient(self, expr: str, variables: list) -> dict:
        syms = [_sym(v) for v in variables]
        e = _parse(expr)
        grad = [sp.diff(e, s) for s in syms]
        return {"gradient": [str(g) for g in grad], "latex": _latex(sp.Matrix(grad)),
                "verbal": f"The gradient is ({', '.join(str(g) for g in grad)})",
                "result": [str(g) for g in grad]}

    def hessian(self, expr: str, variables: list) -> dict:
        syms = [_sym(v) for v in variables]
        H = sp.hessian(_parse(expr), syms)
        return {"matrix": str(H), "latex": _latex(H),
                "verbal": f"The Hessian matrix is {H}", "result": str(H)}

    def jacobian(self, exprs: list, variables: list) -> dict:
        syms = [_sym(v) for v in variables]
        M = sp.Matrix([_parse(e) for e in exprs])
        J = M.jacobian(syms)
        return {"matrix": str(J), "latex": _latex(J),
                "verbal": f"The Jacobian matrix is {J}", "result": str(J)}

    # ── 5.1.3 algebra & equations ───────────────────────────────────
    def solve(self, equation: str, variable: str = "x") -> dict:
        x = _sym(variable)
        if "=" in equation:
            lhs, rhs = equation.split("=", 1)
            eq = sp.Eq(_parse(lhs), _parse(rhs))
        else:
            eq = _parse(equation)
        sols = sp.solve(eq, x)
        numeric = [_safe_float(s) for s in sols]
        return {"solutions": [str(s) for s in sols], "numeric": numeric,
                "latex": _latex(sols),
                "verbal": f"The solutions for {variable} are: " +
                          (", ".join(str(s) for s in sols) if sols else "none found"),
                "result": [str(s) for s in sols]}

    def solve_system(self, equations: list, variables: list) -> dict:
        syms = [_sym(v) for v in variables]
        eqs = []
        for e in equations:
            if "=" in e:
                l, r = e.split("=", 1)
                eqs.append(sp.Eq(_parse(l), _parse(r)))
            else:
                eqs.append(_parse(e))
        sol = sp.solve(eqs, syms, dict=True)
        return {"solutions": [{str(k): str(v) for k, v in s.items()} for s in sol],
                "verbal": f"System solution: {sol}", "result": str(sol)}

    def roots(self, polynomial: str, variable: str = "x") -> dict:
        x = _sym(variable)
        p = sp.Poly(_parse(polynomial), x)
        rts = sp.roots(p)
        return {"roots": [str(r) for r in rts], "multiplicities": {str(k): v for k, v in rts.items()},
                "verbal": f"The roots are: {', '.join(str(r) for r in rts)}",
                "result": [str(r) for r in rts]}

    def solve_ode(self, ode_expr: str, func: str = "f", var: str = "x", ics=None) -> dict:
        x = _sym(var)
        f = sp.Function(func)
        eq = _parse(ode_expr.replace(func, f"{func}"))
        try:
            sol = sp.dsolve(sp.Eq(eq, 0), f(x), ics=ics or {})
        except Exception:
            sol = sp.dsolve(sp.Eq(eq, 0), f(x))
        return {"solution": str(sol), "latex": _latex(sol),
                "verbal": f"The ODE solution is {sol}", "result": str(sol)}

    def solve_ode_numerical(self, f, t_span, y0, method="RK45") -> dict:
        if not SCIPY:
            return {"verbal": "scipy not available, sir.", "result": None}
        sol = _scipy_integrate.solve_ivp(f, t_span, y0, method=method, dense_output=True)
        return {"t": sol.t.tolist(), "y": sol.y.tolist(),
                "verbal": f"Integrated {len(sol.t)} steps over {t_span}.",
                "result": "ok"}

    # ── 5.1.4 linear algebra ────────────────────────────────────────
    def matrix_ops(self, A, operation: str = "determinant", B=None) -> dict:
        M = sp.Matrix(A)
        op = operation.lower()
        if op in ("multiply", "matmul") and B is not None:
            res = M * sp.Matrix(B)
        elif op in ("transpose", "t"):
            res = M.T
        elif op in ("inverse", "inv"):
            res = M.inv()
        elif op in ("determinant", "det"):
            res = M.det()
        elif op == "rank":
            res = M.rank()
        elif op == "trace":
            res = M.trace()
        elif op == "norm":
            res = M.norm()
        else:
            res = M
        return {"result": str(res), "latex": _latex(res),
                "verbal": f"The {operation} is {res}"}

    def eigenvalues(self, A) -> dict:
        M = sp.Matrix(A)
        evals = M.eigenvals()
        evecs = M.eigenvects()
        char = M.charpoly().as_expr()
        return {"eigenvalues": {str(k): v for k, v in evals.items()},
                "eigenvectors": str(evecs), "char_poly": str(char),
                "verbal": f"Eigenvalues: {', '.join(str(k) for k in evals)}",
                "result": {str(k): v for k, v in evals.items()}}

    def svd(self, A) -> dict:
        if np is None:
            return {"verbal": "numpy not available, sir.", "result": None}
        U, s, Vt = np.linalg.svd(np.array(A, dtype=float))
        cond = float(s.max() / s.min()) if s.min() != 0 else float("inf")
        return {"U": U.tolist(), "s": s.tolist(), "Vt": Vt.tolist(),
                "rank": int(np.sum(s > 1e-10)), "condition_number": cond,
                "verbal": f"Singular values: {', '.join(f'{v:.4g}' for v in s)}",
                "result": s.tolist()}

    def lu_decompose(self, A) -> dict:
        if not SCIPY:
            return {"verbal": "scipy not available, sir.", "result": None}
        P, L, U = _scipy_linalg.lu(np.array(A, dtype=float))
        return {"P": P.tolist(), "L": L.tolist(), "U": U.tolist(),
                "verbal": "LU decomposition complete.", "result": "ok"}

    def solve_linear_system(self, A, b) -> dict:
        if np is None:
            return {"verbal": "numpy not available, sir.", "result": None}
        A = np.array(A, dtype=float); b = np.array(b, dtype=float)
        x = np.linalg.solve(A, b)
        residual = float(np.linalg.norm(A @ x - b))
        return {"x": x.tolist(), "residual": residual,
                "verbal": f"Solution x = {x.tolist()} (residual {residual:.2e})",
                "result": x.tolist()}

    # ── 5.1.5 transforms ────────────────────────────────────────────
    def fourier_transform(self, expr: str, t: str = "t", omega: str = "w") -> dict:
        T, W = _sym(t), _sym(omega)
        ft = sp.fourier_transform(_parse(expr), T, W)
        return {"transform": str(ft), "latex": _latex(ft),
                "verbal": f"The Fourier transform is {ft}", "result": str(ft)}

    def laplace_transform(self, expr: str, t: str = "t", s: str = "s") -> dict:
        T, S = _sym(t), _sym(s)
        res = sp.laplace_transform(_parse(expr), T, S, noconds=False)
        transform = res[0] if isinstance(res, tuple) else res
        roc = res[1] if isinstance(res, tuple) and len(res) > 1 else None
        return {"transform": str(transform), "roc": str(roc), "latex": _latex(transform),
                "verbal": f"The Laplace transform is {transform}", "result": str(transform)}

    def fft_numerical(self, signal, sample_rate: float) -> dict:
        if np is None:
            return {"verbal": "numpy not available, sir.", "result": None}
        sig = np.asarray(signal, dtype=float)
        spec = np.fft.rfft(sig)
        freqs = np.fft.rfftfreq(len(sig), d=1.0 / sample_rate)
        return {"freqs": freqs.tolist(), "magnitude": np.abs(spec).tolist(),
                "phase": np.angle(spec).tolist(),
                "verbal": f"FFT computed over {len(sig)} samples; peak at "
                          f"{freqs[np.argmax(np.abs(spec))]:.3g} Hz.",
                "result": "ok"}

    def z_transform(self, expr: str, n: str = "n", z: str = "z") -> dict:
        N, Z = _sym(n), _sym(z)
        # Z-transform of common sequences via geometric-series identities
        e = _parse(expr)
        try:
            from sympy import summation, oo
            res = summation(e * Z**(-N), (N, 0, oo))
        except Exception:
            res = sp.sympify("ZTransform(%s)" % expr)
        return {"transform": str(res), "latex": _latex(res),
                "verbal": f"The Z-transform of {expr} is {res}", "result": str(res)}

    def wavelet_transform(self, signal, wavelet="db4", level=3) -> dict:
        try:
            import pywt
        except Exception:
            return {"result": None, "verbal": "PyWavelets not installed, sir."}
        coeffs = pywt.wavedec(np.asarray(signal, float), wavelet, level=level)
        return {"coefficients": [c.tolist() for c in coeffs], "n_levels": len(coeffs),
                "result": len(coeffs),
                "verbal": f"Discrete wavelet transform ({wavelet}) gave "
                          f"{len(coeffs)} coefficient bands."}

    def pca_decompose(self, X, n_components=2) -> dict:
        if np is None:
            return {"verbal": "numpy unavailable, sir.", "result": None}
        X = np.asarray(X, float); Xc = X - X.mean(0)
        U, s, Vt = np.linalg.svd(Xc, full_matrices=False)
        var = (s**2) / (len(X) - 1); evr = var / var.sum()
        proj = Xc @ Vt[:n_components].T
        return {"components": Vt[:n_components].tolist(),
                "explained_variance_ratio": evr[:n_components].tolist(),
                "projected": proj.tolist(), "result": {"explained_variance": float(evr[:n_components].sum())},
                "verbal": f"PCA: first {n_components} components explain "
                          f"{100*evr[:n_components].sum():.1f}% of variance."}

    def solve_pde_fd(self, pde_type="heat", L=1.0, T=0.1, nx=50, nt=500, alpha=0.5) -> dict:
        """Finite-difference PDE solver (heat/wave) with sin initial condition."""
        if np is None:
            return {"verbal": "numpy unavailable, sir.", "result": None}
        dx = L / (nx - 1); dt = T / nt; x = np.linspace(0, L, nx)
        u = np.sin(np.pi * x / L)
        if pde_type == "heat":
            r = alpha * dt / dx**2
            for _ in range(nt):
                u[1:-1] += r * (u[2:] - 2 * u[1:-1] + u[:-2])
        else:  # wave
            c = alpha; r = (c * dt / dx)**2; u_prev = u.copy()
            for _ in range(nt):
                u_new = np.zeros_like(u)
                u_new[1:-1] = 2*u[1:-1] - u_prev[1:-1] + r*(u[2:]-2*u[1:-1]+u[:-2])
                u_prev, u = u, u_new
        return {"solution": u.tolist(), "x": x.tolist(), "result": {"max": float(u.max())},
                "verbal": f"Finite-difference {pde_type} equation solved on {nx} points "
                          f"over {nt} timesteps; peak value {np.max(np.abs(u)):.4f}."}

    def test(self) -> None:
        assert self.differentiate("x**2", "x")["symbolic"] == "2*x"
        assert self.pca_decompose([[1, 0], [2, 0], [3, 0], [4, 0]])["explained_variance_ratio"][0] > 0.99
        assert self.solve_pde_fd("heat")["result"]["max"] < 1.0
        assert "x**3/3" in self.integrate("x**2", "x")["symbolic"]
        assert self.solve("x**2 - 4", "x")["solutions"]
        print("compute.ComputeEngine: OK")


def _safe_float(e):
    try:
        v = complex(sp.N(e))
        return v.real if abs(v.imag) < 1e-12 else (v.real, v.imag)
    except Exception:
        return None


# ── module-level routing functions (called by INTENT_MAP) ────────────────
_engine = ComputeEngine()


def _extract_expr(text: str) -> str:
    """Pull a math expression out of a natural-language command."""
    t = text
    for kw in ("differentiate", "derivative of", "derivative", "integrate",
               "integral of", "integral", "antiderivative", "compute", "calculate",
               "evaluate", "simplify", "expand", "factorise", "factorize", "factor",
               "the number", "the", "solve equation", "solve", "equation",
               "find roots of", "find roots", "roots of", "zero of",
               "limit of", "limit", "series of", "series", "taylor", "maclaurin",
               "expansion", "with respect to x", "value of", "dx", "d/dx"):
        t = re.sub(rf"\b{re.escape(kw)}\b", " ", t, flags=re.I)
    t = t.strip(" .?")
    return t or text


def compute(text: str) -> dict:
    return _engine.compute(_extract_expr(text))


def differentiate(text: str) -> dict:
    return _engine.differentiate(_extract_expr(text))


def integrate(text: str) -> dict:
    m = re.search(r"from\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)", text, re.I)
    expr = _extract_expr(re.sub(r"from\s+.*", "", text, flags=re.I))
    if m:
        return _engine.integrate(expr, lower=m.group(1), upper=m.group(2))
    return _engine.integrate(expr)


def solve(text: str) -> dict:
    return _engine.solve(_extract_expr(text))


def limit(text: str) -> dict:
    var, point = "x", 0
    m = re.search(r"as\s+([a-zA-Z]\w*)\s+(?:approaches|tends to|->|→)\s+"
                  r"(-?\d+\.?\d*|oo|inf(?:inity)?|-?inf)", text, re.I)
    if m:
        var = m.group(1)
        point = m.group(2)
    expr_text = re.sub(r"\bas\b.*", "", text, flags=re.I)
    return _engine.limit(_extract_expr(expr_text), var=var, point=point)


def series(text: str) -> dict:
    return _engine.series(_extract_expr(text))


def transform(text: str) -> dict:
    if "laplace" in text.lower():
        return _engine.laplace_transform(_extract_expr(text))
    return _engine.fourier_transform(_extract_expr(text))


def matrix_ops(text: str) -> dict:
    return {"result": None,
            "verbal": "Provide a matrix, sir — e.g. ComputeEngine().matrix_ops([[1,2],[3,4]], 'determinant')."}


def test() -> None:
    ComputeEngine().test()


if __name__ == "__main__":
    test()
