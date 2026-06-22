"""Science reference endpoints — curated physics constants/formulas and the
periodic table. Self-contained (data comes from core.reasoning oracles); no
shared services needed. Extracted from the server.py monolith.
"""

from fastapi import APIRouter

router = APIRouter(tags=["reference"])


def _formula_latex(formula: str) -> str | None:
    """Convert an ASCII formula (e.g. 'F = G * m1 * m2 / r**2') to LaTeX via
    SymPy so the UI can typeset it with KaTeX. Returns None on any parse error
    so the caller falls back to the raw string."""
    try:
        import sympy as sp
        from sympy.parsing.sympy_parser import parse_expr, standard_transformations
        # NB: no implicit-multiplication transform — these formulas use explicit
        # '*', and implicit mult wrongly splits multi-char/digit names (F1→F*1,
        # KE→K*E, m1*m2→2*m²). Keep names like m1, KE, F_b as whole symbols.
        tr = standard_transformations
        # Force SymPy-reserved single capitals to be ordinary physics variables
        # (E=energy not Euler's e, I=current not imaginary unit, S/N/O/Q likewise).
        local = {c: sp.Symbol(c) for c in ("E", "I", "N", "O", "S", "Q")}
        _p = lambda s: parse_expr(s, transformations=tr, local_dict=local)
        if "=" in formula:
            lhs, rhs = formula.split("=", 1)
            return sp.latex(sp.Eq(_p(lhs), _p(rhs), evaluate=False))
        return sp.latex(_p(formula))
    except Exception:
        return None


@router.get("/api/physics/constants")
async def physics_constants():
    """All curated physical constants (exact CODATA values)."""
    try:
        from core.reasoning import physics_oracle as _phys
        return {"ok": True, "constants": [{"name": k, **v} for k, v in _phys.CONSTANTS.items()]}
    except Exception as e:
        return {"ok": False, "error": str(e), "constants": []}


@router.get("/api/physics/formulas")
async def physics_formulas(era: str | None = None):
    """Curated physics formula library, optionally filtered by era."""
    try:
        from core.reasoning import physics_oracle as _phys
        fs = _phys.FORMULAS
        if era:
            fs = [f for f in fs if f["era"] == era.lower()]
        # Attach render-ready TeX (raw string stays as fallback) without mutating
        # the shared oracle dicts.
        fs = [{**f, "latex": _formula_latex(f.get("formula", ""))} for f in fs]
        return {"ok": True, "formulas": fs}
    except Exception as e:
        return {"ok": False, "error": str(e), "formulas": []}


@router.get("/api/chem/table")
async def chem_table():
    """All 118 elements (minimal data) for the visual periodic table."""
    try:
        from core.reasoning import chem_oracle as _chem
        return {"ok": True, "elements": _chem.table()}
    except Exception as e:
        return {"ok": False, "error": str(e), "elements": []}


@router.get("/api/chem/element/{q}")
async def chem_element(q: str):
    """Full verified metadata for one element (symbol, name, or atomic number)."""
    try:
        from core.reasoning import chem_oracle as _chem
        data = _chem.lookup(q)
        if data:
            return {"ok": True, "element": data}
        return {"ok": False, "error": f"unknown element: {q}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
