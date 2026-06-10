# deep/science/math_engine.py — Advanced Mathematics (Bible Section 5.2)
"""Number theory, graph theory, combinatorics, geometry, linear programming."""
from __future__ import annotations

import math
import re
from functools import reduce
from itertools import combinations, permutations

import sympy as sp

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

try:
    import networkx as nx
    NX = True
except Exception:  # pragma: no cover
    NX = False

try:
    from scipy.optimize import linprog
    from scipy.spatial import ConvexHull
    SCIPY = True
except Exception:  # pragma: no cover
    SCIPY = False


class MathEngine:
    def __init__(self, config=None):
        self.config = config

    # ── 5.2.1 number theory ─────────────────────────────────────────
    def is_prime(self, n: int) -> dict:
        n = int(n)
        res = sp.isprime(n)
        return {"is_prime": bool(res), "result": bool(res),
                "verbal": f"{n} is {'a prime' if res else 'not a prime'} number."}

    def prime_list(self, n: int) -> dict:
        n = int(n)
        primes = list(sp.primerange(2, n + 1))
        return {"primes": primes, "result": primes,
                "verbal": f"There are {len(primes)} primes up to {n}; "
                          f"largest is {primes[-1] if primes else 'none'}."}

    def factorize(self, n: int) -> dict:
        n = int(n)
        factors = sp.factorint(n)
        pretty = " × ".join(f"{p}^{e}" if e > 1 else f"{p}" for p, e in factors.items())
        return {"factors": {int(k): int(v) for k, v in factors.items()}, "latex": pretty,
                "result": {int(k): int(v) for k, v in factors.items()},
                "verbal": f"{n} factorises as {pretty}."}

    def gcd(self, a: int, b: int) -> dict:
        g = math.gcd(int(a), int(b))
        return {"result": g, "verbal": f"The GCD of {a} and {b} is {g}."}

    def lcm(self, a: int, b: int) -> dict:
        l = abs(int(a) * int(b)) // math.gcd(int(a), int(b)) if a and b else 0
        return {"result": l, "verbal": f"The LCM of {a} and {b} is {l}."}

    def extended_gcd(self, a: int, b: int) -> dict:
        a, b = int(a), int(b)
        old_r, r = a, b
        old_s, s = 1, 0
        old_t, t = 0, 1
        while r:
            q = old_r // r
            old_r, r = r, old_r - q * r
            old_s, s = s, old_s - q * s
            old_t, t = t, old_t - q * t
        return {"gcd": old_r, "x": old_s, "y": old_t, "result": (old_r, old_s, old_t),
                "verbal": f"gcd({a},{b})={old_r} = {old_s}·{a} + {old_t}·{b}."}

    def modular_inverse(self, a: int, m: int) -> dict:
        try:
            inv = pow(int(a), -1, int(m))
            return {"inverse": inv, "result": inv,
                    "verbal": f"The modular inverse of {a} mod {m} is {inv}."}
        except ValueError:
            return {"inverse": None, "result": None,
                    "verbal": f"{a} has no inverse mod {m} (not coprime)."}

    def chinese_remainder(self, remainders: list, moduli: list) -> dict:
        M = reduce(lambda x, y: x * y, (int(m) for m in moduli))
        total = 0
        for r, m in zip(remainders, moduli):
            m = int(m); p = M // m
            total += int(r) * pow(p, -1, m) * p
        sol = total % M
        return {"solution": sol, "modulus": M, "result": sol,
                "verbal": f"x ≡ {sol} (mod {M})."}

    def euler_totient(self, n: int) -> dict:
        phi = int(sp.totient(int(n)))
        return {"phi": phi, "result": phi,
                "verbal": f"Euler's totient φ({n}) = {phi}."}

    def collatz(self, n: int) -> dict:
        n = int(n); seq = [n]; peak = n
        while n != 1:
            n = n // 2 if n % 2 == 0 else 3 * n + 1
            seq.append(n); peak = max(peak, n)
        return {"sequence": seq, "steps": len(seq) - 1, "peak": peak, "result": seq,
                "verbal": f"Collatz from {seq[0]} reaches 1 in {len(seq)-1} steps; peak {peak}."}

    def fibonacci(self, n: int) -> dict:
        n = int(n)
        val = int(sp.fibonacci(n))
        seq = [int(sp.fibonacci(i)) for i in range(min(n + 1, 30))]
        return {"value": val, "sequence": seq, "result": val,
                "verbal": f"The {n}th Fibonacci number is {val}."}

    def lucas(self, n: int) -> dict:
        n = int(n); val = int(sp.lucas(n))
        return {"value": val, "result": val, "verbal": f"The {n}th Lucas number is {val}."}

    def partition_function(self, n: int) -> dict:
        c = int(sp.partition(int(n)))
        return {"count": c, "result": c,
                "verbal": f"There are {c} integer partitions of {n}."}

    # ── 5.2.2 graph theory ──────────────────────────────────────────
    def shortest_path(self, G, source, target, algorithm="dijkstra") -> dict:
        if not NX:
            return _no_nx()
        path = nx.shortest_path(G, source, target, weight="weight")
        weight = nx.shortest_path_length(G, source, target, weight="weight")
        return {"path": path, "weight": weight, "result": path,
                "verbal": f"Shortest path {source}→{target}: {' → '.join(map(str, path))} (cost {weight})."}

    def minimum_spanning_tree(self, G, algorithm="kruskal") -> dict:
        if not NX:
            return _no_nx()
        T = nx.minimum_spanning_tree(G, algorithm=algorithm)
        edges = list(T.edges(data="weight"))
        total = sum(w or 1 for *_, w in edges)
        return {"edges": edges, "total_weight": total, "result": edges,
                "verbal": f"MST has {len(edges)} edges, total weight {total}."}

    def centrality(self, G, measure="degree") -> dict:
        if not NX:
            return _no_nx()
        fn = {"degree": nx.degree_centrality, "betweenness": nx.betweenness_centrality,
              "closeness": nx.closeness_centrality, "eigenvector": nx.eigenvector_centrality,
              "pagerank": nx.pagerank}.get(measure, nx.degree_centrality)
        scores = fn(G)
        top = sorted(scores, key=scores.get, reverse=True)[:5]
        return {"scores": scores, "top_nodes": top, "result": scores,
                "verbal": f"Top {measure} centrality nodes: {top}."}

    def graph_coloring(self, G) -> dict:
        if not NX:
            return _no_nx()
        coloring = nx.greedy_color(G)
        k = len(set(coloring.values()))
        return {"coloring": coloring, "num_colors": k, "result": coloring,
                "verbal": f"Graph coloured with {k} colours."}

    # ── 5.2.3 combinatorics ─────────────────────────────────────────
    def nCr(self, n: int, r: int) -> dict:
        v = math.comb(int(n), int(r))
        return {"result": v, "verbal": f"C({n},{r}) = {v}."}

    def nPr(self, n: int, r: int) -> dict:
        v = math.perm(int(n), int(r))
        return {"result": v, "verbal": f"P({n},{r}) = {v}."}

    def list_permutations(self, items: list, r=None) -> dict:
        perms = list(permutations(items, r))
        return {"count": len(perms), "permutations": perms[:50], "result": len(perms),
                "verbal": f"{len(perms)} permutations."}

    def list_combinations(self, items: list, r: int) -> dict:
        combs = list(combinations(items, r))
        return {"count": len(combs), "combinations": combs[:50], "result": len(combs),
                "verbal": f"{len(combs)} combinations."}

    # ── 5.2.4 computational geometry ────────────────────────────────
    def polygon_area(self, vertices: list) -> dict:
        """Shoelace formula."""
        n = len(vertices)
        area = 0.0
        for i in range(n):
            x1, y1 = vertices[i]; x2, y2 = vertices[(i + 1) % n]
            area += x1 * y2 - x2 * y1
        area = abs(area) / 2.0
        return {"area": area, "result": area, "verbal": f"Polygon area is {area:.6g}."}

    def convex_hull(self, points: list) -> dict:
        if not SCIPY or np is None:
            return {"result": None, "verbal": "scipy not available, sir."}
        pts = np.array(points, dtype=float)
        hull = ConvexHull(pts)
        return {"vertices": hull.vertices.tolist(), "area": float(hull.volume),
                "result": hull.vertices.tolist(),
                "verbal": f"Convex hull has {len(hull.vertices)} vertices."}

    # ── 5.2.5 linear programming ────────────────────────────────────
    def linear_programming(self, c, A_ub=None, b_ub=None, A_eq=None, b_eq=None,
                           bounds=None, maximize=False) -> dict:
        if not SCIPY:
            return {"result": None, "verbal": "scipy not available, sir."}
        cc = [-x for x in c] if maximize else c
        res = linprog(cc, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds)
        opt = (-res.fun if maximize else res.fun) if res.success else None
        return {"success": bool(res.success), "x": res.x.tolist() if res.success else None,
                "optimum": opt, "result": opt,
                "verbal": (f"Optimal value {opt:.6g} at x={res.x.tolist()}."
                           if res.success else f"LP failed: {res.message}")}

    def test(self) -> None:
        assert self.is_prime(17)["is_prime"]
        assert self.factorize(60)["factors"] == {2: 2, 3: 1, 5: 1}
        assert self.gcd(48, 18)["result"] == 6
        assert self.fibonacci(10)["value"] == 55
        print("math_engine.MathEngine: OK")


def _no_nx():
    return {"result": None, "verbal": "networkx not available, sir."}


# ── module-level routing functions ───────────────────────────────────────
_engine = MathEngine()
_INT = re.compile(r"-?\d+")


def number_theory(text: str) -> dict:
    nums = [int(x) for x in _INT.findall(text)]
    low = text.lower()
    if "prime" in low and nums:
        return _engine.is_prime(nums[0])
    if ("factor" in low) and nums:
        return _engine.factorize(nums[0])
    if "gcd" in low and len(nums) >= 2:
        return _engine.gcd(nums[0], nums[1])
    if "lcm" in low and len(nums) >= 2:
        return _engine.lcm(nums[0], nums[1])
    if "totient" in low and nums:
        return _engine.euler_totient(nums[0])
    if "collatz" in low and nums:
        return _engine.collatz(nums[0])
    if "fibonacci" in low and nums:
        return _engine.fibonacci(nums[0])
    if nums:
        return _engine.factorize(nums[0])
    return {"result": None, "verbal": "Give me a number, sir."}


def graph_theory(text: str) -> dict:
    return {"result": None,
            "verbal": "Provide a graph object, sir — e.g. MathEngine().shortest_path(G, s, t)."}


def combinatorics(text: str) -> dict:
    nums = [int(x) for x in _INT.findall(text)]
    low = text.lower()
    if "permutation" in low and len(nums) >= 2:
        return _engine.nPr(nums[0], nums[1])
    if len(nums) >= 2:
        return _engine.nCr(nums[0], nums[1])
    return {"result": None, "verbal": "Give me n and r, sir."}


def geometry(text: str) -> dict:
    return {"result": None,
            "verbal": "Provide vertices, sir — e.g. MathEngine().polygon_area([(0,0),(4,0),(4,3)])."}


def linear_programming(text: str) -> dict:
    return {"result": None,
            "verbal": "Provide objective c and constraints, sir — "
                      "MathEngine().linear_programming(c, A_ub, b_ub, maximize=True)."}


def test() -> None:
    MathEngine().test()


if __name__ == "__main__":
    test()
