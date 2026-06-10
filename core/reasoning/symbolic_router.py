"""
core/reasoning/symbolic_router.py

Neuro-Symbolic Integration (element #1).

Detects when a query is a *deterministic* math/logic problem and solves it with
SymPy — a symbolic solver bound by exact mathematical rules — instead of letting
the LLM guess a probable answer. The verified result is then handed back to the
LLM to narrate in natural language. This eliminates arithmetic/algebra
hallucination: the number is computed, not predicted.

Returns None when the query isn't a clean symbolic problem, so the normal neural
path handles everything else.
"""

from __future__ import annotations

import re
from typing import Optional, Dict, Any

try:
    import sympy as sp
    from sympy.parsing.sympy_parser import (
        parse_expr, standard_transformations, implicit_multiplication_application,
    )
    SYMPY_OK = True
    _TRANSFORMS = standard_transformations + (implicit_multiplication_application,)
except Exception:  # pragma: no cover
    SYMPY_OK = False
    _TRANSFORMS = None


# Words that strongly signal a deterministic computation.
_MATH_CUE = re.compile(
    r"\b(solve|simplify|factor|expand|derivative|differentiate|integrate|integral|"
    r"evaluate|compute|calculate|roots?|limit|factorial|gcd|lcm)\b", re.I)

# A blob that looks like math: digits/operators/variables, few letters.
_MATH_BLOB = re.compile(r"[-+*/^=().0-9xyzeπ\s]{3,}")


def _clean_expr(text: str) -> str:
    """Pull a likely math expression out of free text."""
    t = text.strip()
    # strip trailing question marks / punctuation and leading verbs
    t = re.sub(r"^(what\s+is|whats|what's|compute|calculate|evaluate|find|the\s+value\s+of)\s+",
               "", t, flags=re.I).strip(" ?.!")
    t = t.replace("^", "**").replace("×", "*").replace("÷", "/").replace("π", "pi")
    return t


def _looks_mathy(text: str) -> bool:
    if _MATH_CUE.search(text):
        return True
    # mostly symbols/numbers, at least one operator
    blob = _clean_expr(text)
    if len(blob) < 2:
        return False
    has_op = any(c in blob for c in "+-*/=")
    digits = sum(c.isdigit() for c in blob)
    letters = sum(c.isalpha() for c in blob)
    return has_op and digits >= 1 and letters <= max(3, digits)


def solve(text: str) -> Optional[Dict[str, Any]]:
    """
    Attempt a deterministic solution. Returns a dict describing the verified
    result, or None if this isn't a clean symbolic problem.
    """
    if not SYMPY_OK or not text or not _looks_mathy(text):
        return None
    low = text.lower()
    x, y, z = sp.symbols("x y z")
    local = {"x": x, "y": y, "z": z, "e": sp.E, "pi": sp.pi}

    def P(s: str):
        return parse_expr(s, transformations=_TRANSFORMS, local_dict=local)

    try:
        # ── Calculus: derivative ──────────────────────────────────────────
        m = re.search(r"(?:derivative|differentiate)\s+(?:of\s+)?(.+)", low)
        if m:
            expr = P(_clean_expr(m.group(1)))
            res = sp.diff(expr, x)
            return _result("derivative", f"d/dx[{expr}]", res)

        # ── Calculus: integral ────────────────────────────────────────────
        m = re.search(r"(?:integrate|integral)\s+(?:of\s+)?(.+)", low)
        if m:
            expr = P(_clean_expr(m.group(1)))
            res = sp.integrate(expr, x)
            return _result("integral", f"∫({expr})dx", f"{res} + C")

        # ── Solve equation(s) ─────────────────────────────────────────────
        m = re.search(r"solve\s+(?:for\s+\w+\s+(?:in|:)?\s*)?(.+)", low)
        if m or "=" in text:
            raw = (m.group(1) if m else text)
            raw = _clean_expr(raw)
            if "=" in raw:
                lhs, rhs = raw.split("=", 1)
                eq = sp.Eq(P(lhs), P(rhs))
            else:
                eq = P(raw)
            syms = list(eq.free_symbols) if hasattr(eq, "free_symbols") else [x]
            sym = x if x in syms else (syms[0] if syms else x)
            sol = sp.solve(eq, sym)
            return _result("solve", f"{eq}", sol)

        # ── Simplify / factor / expand ────────────────────────────────────
        for kw, fn in (("simplify", sp.simplify), ("factor", sp.factor), ("expand", sp.expand)):
            m = re.search(rf"{kw}\s+(.+)", low)
            if m:
                expr = P(_clean_expr(m.group(1)))
                return _result(kw, f"{kw}({expr})", fn(expr))

        # ── Plain evaluation of an arithmetic/symbolic expression ─────────
        expr = P(_clean_expr(text))
        val = sp.simplify(expr)
        # For exact integers/rationals, show only the exact value. For irrational
        # results (pi, sqrt, etc.), append a numeric approximation for usefulness.
        if val.is_number and not val.is_rational:
            try:
                result = f"{val} ≈ {sp.N(val, 12)}"
            except Exception:
                result = str(val)
        else:
            result = str(val)
        return _result("evaluate", f"{expr}", result)

    except Exception:
        return None


def _result(kind: str, expression: str, result: Any) -> Dict[str, Any]:
    return {
        "solved": True,
        "kind": kind,
        "expression": str(expression),
        "result": str(result),
        "engine": "sympy",
    }


def verified_context(res: Dict[str, Any]) -> str:
    """Format a solved result as a context block the LLM must narrate faithfully."""
    return (
        "\n=== VERIFIED SYMBOLIC RESULT (computed deterministically by SymPy — "
        "state this EXACTLY, do not recompute) ===\n"
        f"Operation: {res['kind']}\n"
        f"Input: {res['expression']}\n"
        f"Verified answer: {res['result']}\n"
    )
