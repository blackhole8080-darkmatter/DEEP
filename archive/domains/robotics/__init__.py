"""
DEEP — Robotics Domain
Forward/inverse kinematics, trajectory planning, Jacobian computation.
Uses: numpy (required), sympy (optional for symbolic Jacobian).
"""
from .kinematics import RobotArm, DHFrame, KinematicsResult
from .path_planner import PathPlanner, Waypoint, TrajectoryResult

__all__ = ["RobotArm", "DHFrame", "KinematicsResult", "PathPlanner", "Waypoint", "TrajectoryResult"]
