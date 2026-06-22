"""
DEEP — Path Planner
Simple trajectory generation for robot arms.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

try:
    import numpy as np
    _NUMPY_OK = True
except ImportError:
    _NUMPY_OK = False


@dataclass
class Waypoint:
    joint_angles: List[float]   # radians
    time: float                 # seconds from start
    velocity: Optional[List[float]] = None  # rad/s (optional)


@dataclass
class TrajectoryResult:
    waypoints: List[Waypoint] = field(default_factory=list)
    total_duration: float = 0.0
    joint_velocity_profiles: List[List[float]] = field(default_factory=list)
    max_velocities: List[float] = field(default_factory=list)
    error: Optional[str] = None


class PathPlanner:
    """
    Polynomial trajectory planner for robot arms.
    Generates smooth joint-space trajectories (cubic spline or 5th-order polynomial).
    """

    def cubic_trajectory(
        self,
        q_start: List[float],
        q_end: List[float],
        duration: float,
        n_points: int = 50,
    ) -> TrajectoryResult:
        """
        Cubic polynomial trajectory from q_start to q_end.
        Zero initial and final velocities.
        """
        if not _NUMPY_OK:
            return TrajectoryResult(error="numpy required for trajectory planning")

        n = len(q_start)
        q_start = np.array(q_start)
        q_end = np.array(q_end)
        t = np.linspace(0, duration, n_points)

        # Cubic polynomial coefficients (zero velocity BCs)
        # q(t) = a0 + a1*t + a2*t^2 + a3*t^3
        # a0=q0, a1=0, a2=3*(qf-q0)/T^2, a3=-2*(qf-q0)/T^3
        T = duration
        a2 = 3 * (q_end - q_start) / T**2
        a3 = -2 * (q_end - q_start) / T**3

        waypoints = []
        vel_profiles = [[] for _ in range(n)]
        max_vels = []

        for ti in t:
            qi = q_start + a2 * ti**2 + a3 * ti**3
            vi = 2 * a2 * ti + 3 * a3 * ti**2
            waypoints.append(Waypoint(
                joint_angles=qi.tolist(),
                time=float(ti),
                velocity=vi.tolist(),
            ))
            for j in range(n):
                vel_profiles[j].append(float(vi[j]))

        for j in range(n):
            max_vels.append(float(max(abs(v) for v in vel_profiles[j])))

        return TrajectoryResult(
            waypoints=waypoints,
            total_duration=duration,
            joint_velocity_profiles=vel_profiles,
            max_velocities=max_vels,
        )

    def via_points_trajectory(
        self,
        via_points: List[List[float]],
        times: List[float],
        n_points_per_segment: int = 20,
    ) -> TrajectoryResult:
        """
        Multi-segment cubic trajectory through via points.
        via_points: list of joint angle vectors
        times: list of times for each via point
        """
        if len(via_points) < 2:
            return TrajectoryResult(error="Need at least 2 via points")
        if len(times) != len(via_points):
            return TrajectoryResult(error="times and via_points must have the same length")

        all_waypoints = []
        for i in range(len(via_points) - 1):
            seg_dur = times[i + 1] - times[i]
            seg = self.cubic_trajectory(via_points[i], via_points[i + 1], seg_dur, n_points_per_segment)
            if seg.error:
                return seg
            # Offset timestamps
            for wp in seg.waypoints:
                wp.time += times[i]
            all_waypoints.extend(seg.waypoints)

        return TrajectoryResult(
            waypoints=all_waypoints,
            total_duration=times[-1],
        )
