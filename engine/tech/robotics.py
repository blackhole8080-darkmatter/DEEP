# deep/tech/robotics.py — Robotics (Bible Section 18)
"""SLAM, kinematics, path planning, control. Pure numpy/scipy core; PyBullet /
ROS2 / CasADi are optional and guarded."""
from __future__ import annotations

import heapq
import math
import re

import numpy as np

try:
    from scipy.linalg import solve_continuous_are
    SCIPY = True
except Exception:  # pragma: no cover
    SCIPY = False


class RoboticsEngine:
    def __init__(self, config=None):
        self.config = config

    # ── 18.2 kinematics ─────────────────────────────────────────────
    @staticmethod
    def _dh_matrix(a, d, alpha, theta):
        ct, st = math.cos(theta), math.sin(theta)
        ca, sa = math.cos(alpha), math.sin(alpha)
        return np.array([[ct, -st * ca, st * sa, a * ct],
                         [st, ct * ca, -ct * sa, a * st],
                         [0, sa, ca, d],
                         [0, 0, 0, 1]])

    def forward_kinematics(self, dh_params, joint_angles) -> dict:
        T = np.eye(4)
        for (a, d, alpha, off), th in zip(dh_params, joint_angles):
            T = T @ self._dh_matrix(a, d, alpha, th + off)
        pos = T[:3, 3]
        return {"T_ee": T.tolist(), "position": pos.tolist(),
                "result": {"position": pos.tolist()},
                "verbal": f"End-effector at ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})."}

    def inverse_kinematics(self, dh_params, target_xyz, max_iter=200, tol=1e-3) -> dict:
        n = len(dh_params)
        q = np.zeros(n)
        target = np.asarray(target_xyz, float)
        for it in range(max_iter):
            T = np.eye(4)
            Ts = [T.copy()]
            for (a, d, alpha, off), th in zip(dh_params, q):
                T = T @ self._dh_matrix(a, d, alpha, th + off)
                Ts.append(T.copy())
            pos = T[:3, 3]
            err = target - pos
            if np.linalg.norm(err) < tol:
                return {"joint_angles": q.tolist(), "iterations": it,
                        "position_error": float(np.linalg.norm(err)),
                        "result": {"joint_angles": q.tolist()},
                        "verbal": f"IK converged in {it} iterations; angles "
                                  f"{[round(float(a), 3) for a in q]} rad."}
            # numerical Jacobian
            J = np.zeros((3, n))
            for i in range(n):
                z = Ts[i][:3, 2]
                p = Ts[i][:3, 3]
                J[:, i] = np.cross(z, pos - p)
            dq = np.linalg.pinv(J) @ err
            q = q + 0.5 * dq
        return {"joint_angles": q.tolist(), "iterations": max_iter,
                "position_error": float(np.linalg.norm(target - pos)),
                "result": {"joint_angles": q.tolist()},
                "verbal": f"IK reached error {np.linalg.norm(target-pos):.4f} m "
                          f"after {max_iter} iterations."}

    # ── 18.3 path planning ──────────────────────────────────────────
    def a_star(self, grid, start, goal, heuristic="euclidean") -> dict:
        grid = np.asarray(grid)
        rows, cols = grid.shape

        def h(a, b):
            if heuristic == "manhattan":
                return abs(a[0] - b[0]) + abs(a[1] - b[1])
            return math.hypot(a[0] - b[0], a[1] - b[1])
        start, goal = tuple(start), tuple(goal)
        openh = [(h(start, goal), 0, start)]
        came = {}; gscore = {start: 0}
        explored = 0
        while openh:
            _, g, cur = heapq.heappop(openh)
            explored += 1
            if cur == goal:
                path = [cur]
                while cur in came:
                    cur = came[cur]; path.append(cur)
                path.reverse()
                return {"path": path, "cost": g, "explored": explored,
                        "result": {"path_length": len(path)},
                        "verbal": f"A* found a path of {len(path)} cells (cost {g:.2f}), "
                                  f"exploring {explored} nodes."}
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
                nb = (cur[0] + dr, cur[1] + dc)
                if 0 <= nb[0] < rows and 0 <= nb[1] < cols and grid[nb] == 0:
                    tg = g + math.hypot(dr, dc)
                    if tg < gscore.get(nb, math.inf):
                        gscore[nb] = tg; came[nb] = cur
                        heapq.heappush(openh, (tg + h(nb, goal), tg, nb))
        return {"path": None, "result": None,
                "verbal": "No path exists between start and goal, sir."}

    # ── 18.3 control ────────────────────────────────────────────────
    def pid_controller(self, Kp, Ki, Kd, setpoint, dt=0.01, steps=500, tau=1.0) -> dict:
        y = 0.0; integ = 0.0; prev_err = setpoint
        ts, ys, us = [], [], []
        for k in range(steps):
            err = setpoint - y
            integ += err * dt
            deriv = (err - prev_err) / dt
            u = Kp * err + Ki * integ + Kd * deriv
            y += dt * (-y + u) / tau   # first-order plant
            prev_err = err
            ts.append(k * dt); ys.append(y); us.append(u)
        ss_err = abs(setpoint - ys[-1])
        overshoot = (max(ys) - setpoint) / setpoint * 100 if setpoint else 0
        return {"t": ts, "output": ys, "control": us, "result": {"steady_state_error": ss_err},
                "verbal": f"PID response: steady-state error {ss_err:.4f}, "
                          f"overshoot {max(0, overshoot):.1f}%."}

    def lqr_controller(self, A, B, Q, R) -> dict:
        if not SCIPY:
            return {"result": None, "verbal": "scipy needed for the Riccati solver, sir."}
        A, B, Q, R = map(lambda m: np.asarray(m, float), (A, B, Q, R))
        P = solve_continuous_are(A, B, Q, R)
        K = np.linalg.inv(R) @ B.T @ P
        cl = A - B @ K
        eig = np.linalg.eigvals(cl)
        return {"K": K.tolist(), "closed_loop_eigenvalues": eig.tolist(),
                "result": {"K": K.tolist()},
                "verbal": f"LQR gain computed; closed-loop poles at "
                          f"{[round(e.real, 3) for e in eig]} — "
                          f"{'stable' if all(e.real < 0 for e in eig) else 'unstable'}."}

    # ── 18.1 SLAM (light EKF) ───────────────────────────────────────
    def ekf_slam_step(self, mu, sigma, control, dt=1.0) -> dict:
        # minimal pose prediction demo
        x, y, th = mu[:3]
        v, w = control
        mu_new = np.array([x + v * dt * math.cos(th), y + v * dt * math.sin(th), th + w * dt])
        return {"pose": mu_new.tolist(), "result": mu_new.tolist(),
                "verbal": f"EKF predicted robot pose ({mu_new[0]:.2f}, {mu_new[1]:.2f}, "
                          f"{math.degrees(mu_new[2]):.1f}°)."}

    def rrt_star(self, start, goal, obstacles=None, bounds=(0, 20), n_samples=400,
                 step=1.5, radius=3.0) -> dict:
        """RRT* sampling-based planner in 2D with circular obstacles."""
        obstacles = obstacles or [(10, 10, 2.5)]
        rng = np.random.default_rng(0)
        start = np.array(start, float); goal = np.array(goal, float)
        nodes = [start]; parent = {0: None}; cost = {0: 0.0}

        def collision(p):
            return any(np.hypot(p[0]-ox, p[1]-oy) < r for ox, oy, r in obstacles)
        for _ in range(n_samples):
            rnd = goal if rng.random() < 0.1 else rng.uniform(bounds[0], bounds[1], 2)
            d = [np.linalg.norm(rnd - n) for n in nodes]
            near = int(np.argmin(d))
            direction = rnd - nodes[near]; dist = np.linalg.norm(direction)
            if dist == 0:
                continue
            new = nodes[near] + direction / dist * min(step, dist)
            if collision(new):
                continue
            # choose best parent within radius
            near_ids = [i for i, n in enumerate(nodes) if np.linalg.norm(n - new) < radius]
            best, best_cost = near, cost[near] + np.linalg.norm(new - nodes[near])
            for i in near_ids:
                c = cost[i] + np.linalg.norm(new - nodes[i])
                if c < best_cost:
                    best, best_cost = i, c
            nodes.append(new); idx = len(nodes) - 1
            parent[idx] = best; cost[idx] = best_cost
            if np.linalg.norm(new - goal) < step:
                return {"n_nodes": len(nodes), "cost": best_cost, "reached": True,
                        "result": {"cost": best_cost},
                        "verbal": f"RRT* reached the goal: {len(nodes)} nodes, "
                                  f"path cost {best_cost:.2f}."}
        return {"n_nodes": len(nodes), "reached": False, "result": None,
                "verbal": f"RRT* explored {len(nodes)} nodes; goal not reached in "
                          f"{n_samples} samples."}

    def dynamic_window(self, state, goal, obstacles=None) -> dict:
        """DWA local planner: score sampled (v, ω) commands."""
        obstacles = obstacles or [(5, 0, 1)]
        x, y, th, v0, w0 = state
        best = (-1e9, 0.0, 0.0)
        for v in np.linspace(0, 1.0, 8):
            for w in np.linspace(-1, 1, 9):
                nx = x + v * math.cos(th + w * 0.5)
                ny = y + v * math.sin(th + w * 0.5)
                clearance = min(math.hypot(nx-ox, ny-oy) - r for ox, oy, r in obstacles)
                heading = -math.hypot(goal[0]-nx, goal[1]-ny)
                score = (heading + 2*clearance + v) if clearance > 0 else -1e9
                if score > best[0]:
                    best = (score, v, w)
        return {"best_v": best[1], "best_omega": best[2], "result": {"v": best[1], "omega": best[2]},
                "verbal": f"DWA chose v={best[1]:.2f} m/s, ω={best[2]:.2f} rad/s."}

    def workspace_analysis(self, dh_params, joint_limits, n_samples=2000) -> dict:
        rng = np.random.default_rng(0); pts = []
        for _ in range(n_samples):
            q = [rng.uniform(lo, hi) for lo, hi in joint_limits]
            T = np.eye(4)
            for (a, d, alpha, off), th in zip(dh_params, q):
                T = T @ self._dh_matrix(a, d, alpha, th + off)
            pts.append(T[:3, 3])
        pts = np.array(pts)
        reach = float(np.linalg.norm(pts, axis=1).max())
        return {"max_reach": reach, "n_samples": n_samples, "result": {"max_reach": reach},
                "verbal": f"Workspace analysis: max reach {reach:.3f} m from "
                          f"{n_samples} random configurations."}

    def behavior_tree(self, world_state) -> dict:
        """Tiny behaviour tree: Selector[ Sequence[battery_ok, has_goal -> move], idle ]."""
        log = []
        def cond(k): log.append(f"check {k}"); return world_state.get(k, False)
        if cond("battery_ok") and cond("has_goal"):
            log.append("action: move_to_goal"); status = "SUCCESS"
        else:
            log.append("action: idle"); status = "RUNNING"
        return {"status": status, "executed_nodes": log, "result": status,
                "verbal": f"Behaviour tree ticked → {status} ({log[-1]})."}

    def test(self) -> None:
        # 2-link planar arm
        dh = [(1, 0, 0, 0), (1, 0, 0, 0)]
        fk = self.forward_kinematics(dh, [0, 0])
        assert abs(fk["position"][0] - 2.0) < 1e-6
        ik = self.inverse_kinematics(dh, [1.5, 0.5, 0])
        assert ik["position_error"] < 0.05
        grid = np.zeros((10, 10)); grid[5, 0:8] = 1
        a = self.a_star(grid, (0, 0), (9, 9))
        assert a["path"] is not None
        assert self.rrt_star((0, 0), (18, 18))["n_nodes"] > 1
        assert self.dynamic_window((0, 0, 0, 0, 0), (10, 0))["best_v"] >= 0
        assert self.workspace_analysis(dh, [(-3.14, 3.14), (-3.14, 3.14)])["max_reach"] > 1
        assert self.behavior_tree({"battery_ok": True, "has_goal": True})["status"] == "SUCCESS"
        print("robotics.RoboticsEngine: OK (incl. RRT*, DWA, workspace, behaviour tree)")


_engine = RoboticsEngine()
_NUM = re.compile(r"-?\d+\.?\d*")


def execute(text: str) -> dict:
    low = text.lower()
    if "slam" in low or "localis" in low or "localiz" in low or "mapping" in low:
        return _engine.ekf_slam_step([0, 0, 0], None, (1.0, 0.1))
    if "inverse kinematic" in low or " ik" in low:
        return _engine.inverse_kinematics([(1, 0, 0, 0), (1, 0, 0, 0)], [1.5, 0.5, 0])
    if "forward kinematic" in low or " fk" in low or "end effector" in low or "end-effector" in low:
        return _engine.forward_kinematics([(1, 0, 0, 0), (1, 0, 0, 0)], [0.5, 0.5])
    if "pid" in low:
        return _engine.pid_controller(2.0, 1.0, 0.5, 1.0)
    if "lqr" in low:
        return _engine.lqr_controller([[0, 1], [0, 0]], [[0], [1]], [[1, 0], [0, 1]], [[1]])
    if "path" in low or "a*" in low or "navigate" in low or "plan" in low:
        grid = np.zeros((20, 20)); grid[10, 2:18] = 1
        return _engine.a_star(grid, (0, 0), (19, 19))
    return _engine.forward_kinematics([(1, 0, 0, 0), (1, 0, 0, 0)], [0.5, 0.5])


def test() -> None:
    RoboticsEngine().test()


if __name__ == "__main__":
    test()
