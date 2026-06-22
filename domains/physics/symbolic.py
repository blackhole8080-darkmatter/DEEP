# domains/physics/symbolic.py
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

HAS_SYMPY = False
try:
    import sympy
    from sympy.parsing.sympy_parser import parse_expr
    HAS_SYMPY = True
except ImportError:
    logger.warning("sympy not available. Symbolic math will fall back to string heuristics.")

class SymbolicMathSolver:
    """Wrapper around Sympy for analytical solutions and derivations."""
    
    def __init__(self):
        self.enabled = HAS_SYMPY

    def solve_equation(self, eq_str: str, var_str: str = "x") -> Dict[str, Any]:
        """
        Solve an equation analytically.
        eq_str: equation string, e.g., "x**2 - 4" or "Eq(x**2, 4)"
        var_str: variable to solve for
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "Sympy not installed on server. Cannot solve analytically.",
                "solution": None,
                "latex": None
            }
            
        try:
            var = sympy.Symbol(var_str)
            # Parse equation
            if "=" in eq_str and "Eq" not in eq_str:
                parts = eq_str.split("=")
                eq = sympy.Eq(parse_expr(parts[0].strip()), parse_expr(parts[1].strip()))
            else:
                eq = parse_expr(eq_str.strip())
                
            solutions = sympy.solve(eq, var)
            solutions_str = [str(sol) for sol in solutions]
            solutions_latex = [sympy.latex(sol) for sol in solutions]
            
            return {
                "success": True,
                "solution": solutions_str,
                "latex": ", ".join([f"${l}$" for l in solutions_latex]),
                "raw_solutions": solutions
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "solution": None,
                "latex": None
            }

    def derive(self, expr_str: str, var_str: str = "x", order: int = 1) -> Dict[str, Any]:
        """Compute analytical derivative."""
        if not self.enabled:
            return {"success": False, "error": "Sympy not installed."}
            
        try:
            expr = parse_expr(expr_str)
            var = sympy.Symbol(var_str)
            diff_expr = sympy.diff(expr, var, order)
            
            return {
                "success": True,
                "result": str(diff_expr),
                "latex": f"$${sympy.latex(diff_expr)}$$",
                "input_latex": f"$${sympy.latex(expr)}$$"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def integrate(self, expr_str: str, var_str: str = "x", 
                  lower: Optional[str] = None, upper: Optional[str] = None) -> Dict[str, Any]:
        """Compute analytical integral (definite or indefinite)."""
        if not self.enabled:
            return {"success": False, "error": "Sympy not installed."}
            
        try:
            expr = parse_expr(expr_str)
            var = sympy.Symbol(var_str)
            
            if lower is not None and upper is not None:
                l_val = parse_expr(lower)
                u_val = parse_expr(upper)
                integral = sympy.integrate(expr, (var, l_val, u_val))
            else:
                integral = sympy.integrate(expr, var)
                
            return {
                "success": True,
                "result": str(integral),
                "latex": f"$${sympy.latex(integral)}$$",
                "input_latex": f"$${sympy.latex(expr)}$$"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def simplify(self, expr_str: str) -> Dict[str, Any]:
        """Simplify a mathematical expression."""
        if not self.enabled:
            return {"success": False, "error": "Sympy not installed."}
            
        try:
            expr = parse_expr(expr_str)
            simplified = sympy.simplify(expr)
            return {
                "success": True,
                "result": str(simplified),
                "latex": f"$${sympy.latex(simplified)}$$"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ── Compatibility aliases for engine.py ───────────────────────────────────────
from dataclasses import dataclass, field
from typing import List, Any as _Any


@dataclass
class SymbolicResult:
    """Result type returned by SymbolicSolver.solve_expression()."""
    expression: _Any = None           # SymPy expression object (or None)
    latex_str: str = ""
    steps: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    error: str = ""


class SymbolicSolver:
    """
    Thin wrapper that adapts SymbolicMathSolver to the API expected by engine.py.
    engine.py calls: solver.solve_expression(expression_string) -> SymbolicResult
    """
    def __init__(self):
        self._inner = SymbolicMathSolver()

    def solve_expression(self, expression: str) -> SymbolicResult:
        result = SymbolicResult()
        if not self._inner.enabled:
            result.error = "SymPy not available"
            return result

        try:
            from sympy.parsing.sympy_parser import (
                parse_expr, standard_transformations,
                implicit_multiplication_application,
            )
            import sympy as _sp

            transformations = standard_transformations + (implicit_multiplication_application,)
            expr = parse_expr(expression, transformations=transformations)
            simplified = _sp.simplify(expr)

            result.expression = simplified
            result.latex_str = _sp.latex(simplified)
            result.steps = [
                f"Parsed: {expression}",
                f"Simplified: {simplified}",
            ]
        except Exception as exc:
            result.error = str(exc)

        return result

