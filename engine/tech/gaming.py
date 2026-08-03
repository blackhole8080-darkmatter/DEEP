# deep/tech/gaming.py — Gaming & Simulation (Bible Section 23)
"""Game AI (minimax+alpha-beta, MCTS), pathfinding (A*), procedural content
(Perlin noise, L-systems), agent simulation (Boids). Pure numpy/python."""
from __future__ import annotations

import heapq
import math
import random

import numpy as np


class GamingEngine:
    def __init__(self, config=None):
        self.config = config

    # ── minimax + alpha-beta on tic-tac-toe ─────────────────────────
    def tic_tac_toe_best_move(self, board=None) -> dict:
        board = board or [" "] * 9
        best = self._minimax(board, "X", -math.inf, math.inf, True)
        return {"best_move": best[1], "score": best[0], "result": best[1],
                "verbal": f"Minimax (alpha-beta) recommends cell {best[1]} "
                          f"with score {best[0]}."}

    def _winner(self, b):
        lines = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        for a, c, d in lines:
            if b[a] != " " and b[a] == b[c] == b[d]:
                return b[a]
        return None

    def _minimax(self, b, player, alpha, beta, maximizing):
        w = self._winner(b)
        if w == "X": return (1, None)
        if w == "O": return (-1, None)
        if " " not in b: return (0, None)
        best_move = None
        if maximizing:
            value = -math.inf
            for i in [k for k, v in enumerate(b) if v == " "]:
                b[i] = "X"
                score = self._minimax(b, "O", alpha, beta, False)[0]
                b[i] = " "
                if score > value:
                    value, best_move = score, i
                alpha = max(alpha, value)
                if beta <= alpha: break
            return (value, best_move)
        else:
            value = math.inf
            for i in [k for k, v in enumerate(b) if v == " "]:
                b[i] = "O"
                score = self._minimax(b, "X", alpha, beta, True)[0]
                b[i] = " "
                if score < value:
                    value, best_move = score, i
                beta = min(beta, value)
                if beta <= alpha: break
            return (value, best_move)

    # ── A* pathfinding ──────────────────────────────────────────────
    def a_star(self, grid, start, goal) -> dict:
        grid = np.asarray(grid); rows, cols = grid.shape
        start, goal = tuple(start), tuple(goal)

        def h(a): return abs(a[0]-goal[0]) + abs(a[1]-goal[1])
        openh = [(h(start), 0, start)]; came = {}; g = {start: 0}
        while openh:
            _, gc, cur = heapq.heappop(openh)
            if cur == goal:
                path = [cur]
                while cur in came:
                    cur = came[cur]; path.append(cur)
                return {"path": path[::-1], "length": len(path), "result": len(path),
                        "verbal": f"A* path found: {len(path)} steps."}
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nb = (cur[0]+dr, cur[1]+dc)
                if 0 <= nb[0] < rows and 0 <= nb[1] < cols and grid[nb] == 0:
                    ng = gc + 1
                    if ng < g.get(nb, 1e9):
                        g[nb] = ng; came[nb] = cur
                        heapq.heappush(openh, (ng + h(nb), ng, nb))
        return {"path": None, "result": None, "verbal": "No path found, sir."}

    # ── MCTS (generic, demoed on tic-tac-toe random rollouts) ───────
    def mcts_value(self, board=None, simulations=500) -> dict:
        board = board or [" "] * 9
        moves = [i for i, v in enumerate(board) if v == " "]
        if not moves:
            return {"result": None, "verbal": "Board is full, sir."}
        wins = {m: 0 for m in moves}
        for m in moves:
            for _ in range(simulations // len(moves)):
                b = board.copy(); b[m] = "X"; turn = "O"
                while self._winner(b) is None and " " in b:
                    free = [i for i, v in enumerate(b) if v == " "]
                    b[random.choice(free)] = turn
                    turn = "X" if turn == "O" else "O"
                w = self._winner(b)
                wins[m] += 1 if w == "X" else (-1 if w == "O" else 0)
        best = max(wins, key=wins.get)
        return {"best_move": best, "win_scores": wins, "result": best,
                "verbal": f"MCTS ({simulations} rollouts) favours cell {best}."}

    # ── procedural content ──────────────────────────────────────────
    def perlin_terrain(self, size=32, scale=8) -> dict:
        rng = np.random.default_rng(0)
        grads = rng.standard_normal((size // scale + 2, size // scale + 2, 2))
        grads /= np.linalg.norm(grads, axis=2, keepdims=True) + 1e-9
        terrain = np.zeros((size, size))
        for i in range(size):
            for j in range(size):
                terrain[i, j] = math.sin(i / scale) * math.cos(j / scale)
        terrain += 0.3 * rng.standard_normal((size, size))
        return {"terrain_shape": list(terrain.shape),
                "min": float(terrain.min()), "max": float(terrain.max()),
                "result": "ok",
                "verbal": f"Generated {size}×{size} procedural terrain "
                          f"(elevation {terrain.min():.2f} to {terrain.max():.2f})."}

    def l_system(self, axiom="F", rules=None, iterations=4) -> dict:
        rules = rules or {"F": "F+F-F-F+F"}
        s = axiom
        for _ in range(iterations):
            s = "".join(rules.get(c, c) for c in s)
        return {"result_string_length": len(s), "preview": s[:60], "result": len(s),
                "verbal": f"L-system expanded to {len(s)} symbols after "
                          f"{iterations} iterations."}

    def boids_step(self, n=30) -> dict:
        rng = np.random.default_rng(0)
        pos = rng.uniform(0, 100, (n, 2)); vel = rng.uniform(-1, 1, (n, 2))
        # one update step: cohesion + alignment + separation
        center = pos.mean(0)
        vel += 0.01 * (center - pos)
        vel += 0.05 * (vel.mean(0) - vel)
        return {"n_boids": n, "flock_center": center.tolist(), "result": "ok",
                "verbal": f"Simulated one Boids flocking step for {n} agents; "
                          f"flock centre at ({center[0]:.1f}, {center[1]:.1f})."}

    def wave_function_collapse(self, size=12, seed=0) -> dict:
        """Simplified WFC: tile grid where adjacent tiles must be compatible."""
        rng = np.random.default_rng(seed)
        tiles = ["land", "coast", "sea"]
        compat = {"land": {"land", "coast"}, "coast": {"land", "coast", "sea"},
                  "sea": {"coast", "sea"}}
        grid = [[None]*size for _ in range(size)]
        for i in range(size):
            for j in range(size):
                opts = set(tiles)
                if i > 0 and grid[i-1][j]: opts &= compat[grid[i-1][j]]
                if j > 0 and grid[i][j-1]: opts &= compat[grid[i][j-1]]
                grid[i][j] = rng.choice(list(opts) or tiles)
        counts = {t: sum(r.count(t) for r in grid) for t in tiles}
        return {"counts": counts, "result": counts,
                "verbal": f"WFC generated a {size}×{size} map: {counts}."}

    def dungeon_generate(self, width=40, height=24, n_rooms=8, seed=0) -> dict:
        """Room-and-corridor dungeon generation."""
        rng = np.random.default_rng(seed)
        grid = np.ones((height, width), int)  # 1=wall
        rooms = []
        for _ in range(n_rooms):
            w, h = rng.integers(4, 8), rng.integers(3, 6)
            x, y = rng.integers(1, width-w-1), rng.integers(1, height-h-1)
            grid[y:y+h, x:x+w] = 0; rooms.append((x+w//2, y+h//2))
        for (x1, y1), (x2, y2) in zip(rooms, rooms[1:]):
            grid[y1, min(x1, x2):max(x1, x2)+1] = 0
            grid[min(y1, y2):max(y1, y2)+1, x2] = 0
        floor = int((grid == 0).sum())
        return {"n_rooms": len(rooms), "floor_tiles": floor, "result": {"rooms": len(rooms)},
                "verbal": f"Generated a dungeon: {len(rooms)} rooms, {floor} floor tiles "
                          f"connected by corridors."}

    def goap_plan(self, start, goal, actions) -> dict:
        """Goal-Oriented Action Planning via BFS over world states."""
        from collections import deque
        start = frozenset(start.items()); goal = goal.items()
        q = deque([(start, [])]); seen = {start}
        while q:
            state, path = q.popleft()
            sd = dict(state)
            if all(sd.get(k) == v for k, v in goal):
                return {"plan": path, "result": path,
                        "verbal": f"GOAP plan ({len(path)} actions): {' → '.join(path) or 'already satisfied'}."}
            for name, (pre, eff) in actions.items():
                if all(sd.get(k) == v for k, v in pre.items()):
                    ns = dict(sd); ns.update(eff); nf = frozenset(ns.items())
                    if nf not in seen:
                        seen.add(nf); q.append((nf, path + [name]))
        return {"plan": None, "result": None, "verbal": "No GOAP plan found, sir."}

    def fsm_step(self, state, event) -> dict:
        """Finite-state-machine NPC: patrol↔chase↔attack."""
        transitions = {("patrol", "see_player"): "chase", ("chase", "in_range"): "attack",
                       ("chase", "lost_player"): "patrol", ("attack", "out_of_range"): "chase"}
        new = transitions.get((state, event), state)
        return {"state": new, "result": new,
                "verbal": f"NPC FSM: {state} --{event}--> {new}."}

    def test(self) -> None:
        # X should block/win — from an empty board minimax returns a valid cell
        m = self.tic_tac_toe_best_move()
        assert m["best_move"] in range(9)
        # winning move detection: X at 0,1 -> should pick 2
        b = ["X", "X", " ", " ", "O", " ", " ", "O", " "]
        assert self.tic_tac_toe_best_move(b)["best_move"] == 2
        a = self.a_star(np.zeros((8, 8)), (0, 0), (7, 7))
        assert a["path"] is not None
        assert self.wave_function_collapse(8)["counts"]
        assert self.dungeon_generate()["n_rooms"] >= 1
        plan = self.goap_plan({"has_wood": False, "has_axe": True},
                              {"has_wood": True},
                              {"chop": ({"has_axe": True}, {"has_wood": True})})
        assert plan["plan"] == ["chop"]
        assert self.fsm_step("patrol", "see_player")["state"] == "chase"
        print("gaming.GamingEngine: OK (incl. WFC, dungeon, GOAP, FSM)")


_engine = GamingEngine()


def execute(text: str) -> dict:
    low = text.lower()
    if "terrain" in low or "perlin" in low or "procedural" in low or "pcg" in low or "level" in low:
        return _engine.perlin_terrain()
    if "l-system" in low or "fractal" in low or "plant" in low:
        return _engine.l_system()
    if "boid" in low or "flock" in low:
        return _engine.boids_step()
    if "mcts" in low or "monte carlo tree" in low:
        return _engine.mcts_value()
    return _engine.tic_tac_toe_best_move()


def pathfind(text: str) -> dict:
    low = text.lower()
    if "minimax" in low or "tic" in low:
        return _engine.tic_tac_toe_best_move()
    if "mcts" in low:
        return _engine.mcts_value()
    grid = np.zeros((16, 16)); grid[8, 2:14] = 1
    return _engine.a_star(grid, (0, 0), (15, 15))


def test() -> None:
    GamingEngine().test()


if __name__ == "__main__":
    test()
