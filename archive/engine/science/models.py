# deep/science/models.py — Scientific Simulation Models (Bible Section 1 tree)
"""Discrete dynamical systems & agent models: Conway's Game of Life, cellular
automata (Wolfram rules), the logistic map (chaos), random walks, percolation."""
from __future__ import annotations

import numpy as np


class SimulationModels:
    def __init__(self, config=None):
        self.config = config

    def game_of_life(self, size=32, steps=20, seed=0) -> dict:
        rng = np.random.default_rng(seed)
        grid = (rng.random((size, size)) > 0.7).astype(int)
        alive_history = [int(grid.sum())]
        for _ in range(steps):
            nbrs = sum(np.roll(np.roll(grid, i, 0), j, 1)
                       for i in (-1, 0, 1) for j in (-1, 0, 1) if (i, j) != (0, 0))
            grid = ((nbrs == 3) | ((grid == 1) & (nbrs == 2))).astype(int)
            alive_history.append(int(grid.sum()))
        return {"final_alive": alive_history[-1], "alive_history": alive_history,
                "result": alive_history[-1],
                "verbal": f"Game of Life: {alive_history[0]} → {alive_history[-1]} live "
                          f"cells over {steps} generations."}

    def elementary_ca(self, rule=30, width=101, steps=50) -> dict:
        row = np.zeros(width, int); row[width // 2] = 1
        rows = [row.copy()]
        rule_bits = [(rule >> i) & 1 for i in range(8)]
        for _ in range(steps):
            left = np.roll(row, 1); right = np.roll(row, -1)
            idx = (left << 2) | (row << 1) | right
            row = np.array([rule_bits[i] for i in idx])
            rows.append(row.copy())
        density = float(np.mean(rows[-1]))
        return {"rule": rule, "final_density": density, "result": density,
                "verbal": f"Wolfram rule {rule} ran {steps} steps; "
                          f"final density {density:.3f}."}

    def logistic_map(self, r=3.9, x0=0.5, n=100) -> dict:
        x = x0; traj = [x]
        for _ in range(n):
            x = r * x * (1 - x); traj.append(x)
        # crude Lyapunov estimate
        lyap = float(np.mean(np.log(np.abs(r - 2 * r * np.array(traj[:-1])) + 1e-12)))
        return {"trajectory": traj, "lyapunov": lyap, "result": lyap,
                "verbal": f"Logistic map (r={r}): Lyapunov exponent {lyap:.3f} — "
                          f"{'chaotic' if lyap > 0 else 'stable'}."}

    def random_walk(self, n_steps=1000, dim=2, seed=0) -> dict:
        rng = np.random.default_rng(seed)
        steps = rng.choice([-1, 1], size=(n_steps, dim))
        path = np.cumsum(steps, axis=0)
        dist = float(np.linalg.norm(path[-1]))
        return {"final_distance": dist, "expected": np.sqrt(n_steps), "result": dist,
                "verbal": f"{dim}D random walk: end displacement {dist:.1f} "
                          f"(√N ≈ {np.sqrt(n_steps):.1f})."}

    def percolation(self, size=50, p=0.6, seed=0) -> dict:
        rng = np.random.default_rng(seed)
        grid = rng.random((size, size)) < p
        # flood fill from top row, check if reaches bottom
        from collections import deque
        seen = np.zeros_like(grid, bool); q = deque()
        for j in range(size):
            if grid[0, j]:
                q.append((0, j)); seen[0, j] = True
        percolates = False
        while q:
            i, j = q.popleft()
            if i == size - 1:
                percolates = True; break
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ni, nj = i + di, j + dj
                if 0 <= ni < size and 0 <= nj < size and grid[ni, nj] and not seen[ni, nj]:
                    seen[ni, nj] = True; q.append((ni, nj))
        return {"percolates": percolates, "p": p, "result": percolates,
                "verbal": f"Percolation at p={p}: cluster "
                          f"{'spans' if percolates else 'does not span'} the grid."}

    def test(self) -> None:
        assert "final_alive" in self.game_of_life(16, 5)
        assert self.elementary_ca(30, 51, 10)["rule"] == 30
        assert self.logistic_map(3.9)["lyapunov"] > 0  # chaotic regime
        assert self.random_walk(500)["final_distance"] >= 0
        print("models.SimulationModels: OK")


def test() -> None:
    SimulationModels().test()


if __name__ == "__main__":
    test()
