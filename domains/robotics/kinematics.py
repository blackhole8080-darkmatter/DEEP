"""
DEEP — Robot Kinematics Engine
Forward kinematics (FK), inverse kinematics (IK), and Jacobian computation
using Denavit-Hartenberg (DH) convention.
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
class DHFrame:
    """
    Denavit-Hartenberg parameters for one joint.
    a     : link length (m)
    alpha : link twist (rad)
    d     : link offset (m)
    theta : joint angle (rad) — variable for revolute, fixed for prismatic
    joint_type: "revolute" | "prismatic"
    """
    a: float
    alpha: float
    d: float
    theta: float
    joint_type: str = "revolute"
    name: str = ""
    theta_min: float = -math.pi
    theta_max: float = math.pi


@dataclass
class KinematicsResult:
    """Result of a FK or IK computation."""
    joint_angles_rad: List[float]
    end_effector_position: Tuple[float, float, float]   # x, y, z in meters
    end_effector_rotation: Optional[List[List[float]]] = None  # 3x3 rotation matrix
    transform_matrix: Optional[List[List[float]]] = None       # 4x4 T matrix
    jacobian: Optional[List[List[float]]] = None               # 6×n Jacobian
    singularity_detected: bool = False
    manipulability: float = 0.0    # sqrt(det(J·Jᵀ)) — 0 = singularity
    error: Optional[str] = None


class RobotArm:
    """
    N-DOF serial robot arm kinematics using DH parameters.
    Supports forward kinematics, geometric Jacobian, and numerical IK (RMRC).
    """

    def __init__(self, frames: List[DHFrame]):
        self.frames = frames
        self.n_dof = len(frames)

    # ── Public API ─────────────────────────────────────────────────────────────

    def forward_kinematics(self, joint_angles: List[float]) -> KinematicsResult:
        """
        Compute end-effector pose from joint angles.
        joint_angles: list of angles in radians (length must match n_dof)
        Returns: 4x4 transformation matrix + position + rotation
        """
        if not _NUMPY_OK:
            return KinematicsResult(
                joint_angles_rad=joint_angles,
                end_effector_position=(0, 0, 0),
                error="numpy required for kinematics. Run: pip install numpy",
            )

        if len(joint_angles) != self.n_dof:
            return KinematicsResult(
                joint_angles_rad=joint_angles,
                end_effector_position=(0, 0, 0),
                error=f"Expected {self.n_dof} joint angles, got {len(joint_angles)}",
            )

        T = np.eye(4)
        for i, (frame, q) in enumerate(zip(self.frames, joint_angles)):
            theta = q + frame.theta if frame.joint_type == "revolute" else frame.theta
            d = frame.d + q if frame.joint_type == "prismatic" else frame.d
            T = T @ self._dh_matrix(frame.a, frame.alpha, d, theta)

        pos = (float(T[0, 3]), float(T[1, 3]), float(T[2, 3]))
        rot = T[:3, :3].tolist()
        J = self.compute_jacobian(joint_angles)
        manip = self._manipulability(J)

        return KinematicsResult(
            joint_angles_rad=list(joint_angles),
            end_effector_position=pos,
            end_effector_rotation=rot,
            transform_matrix=T.tolist(),
            jacobian=J.tolist() if J is not None else None,
            singularity_detected=(manip < 1e-4),
            manipulability=manip,
        )

    def inverse_kinematics(
        self,
        target_pos: Tuple[float, float, float],
        initial_angles: Optional[List[float]] = None,
        max_iterations: int = 200,
        tolerance: float = 1e-4,
        step_size: float = 0.1,
    ) -> KinematicsResult:
        """
        Resolved-Motion Rate Control (RMRC) numerical IK.
        target_pos: desired (x, y, z) of end-effector
        Returns KinematicsResult with joint angles that achieve the target position.
        """
        if not _NUMPY_OK:
            return KinematicsResult(
                joint_angles_rad=[0.0] * self.n_dof,
                end_effector_position=(0, 0, 0),
                error="numpy required for IK",
            )

        q = np.zeros(self.n_dof) if initial_angles is None else np.array(initial_angles, dtype=float)
        target = np.array(target_pos, dtype=float)

        for iteration in range(max_iterations):
            fk = self.forward_kinematics(q.tolist())
            pos = np.array(fk.end_effector_position)
            error_vec = target - pos

            if np.linalg.norm(error_vec) < tolerance:
                break

            J = self.compute_jacobian(q.tolist())
            if J is None:
                break

            # Position-only Jacobian (3×n)
            Jp = J[:3, :]

            # Damped least-squares (DLS)
            lambda2 = 1e-4
            JJt = Jp @ Jp.T + lambda2 * np.eye(3)
            dq = Jp.T @ np.linalg.solve(JJt, error_vec) * step_size

            # Apply joint limits
            q += dq
            for i, frame in enumerate(self.frames):
                q[i] = np.clip(q[i], frame.theta_min, frame.theta_max)

        fk = self.forward_kinematics(q.tolist())
        return fk

    def compute_jacobian(self, joint_angles: List[float]) -> Optional["np.ndarray"]:
        """
        Compute the 6×n geometric Jacobian.
        Rows 0-2: linear velocity, Rows 3-5: angular velocity.
        """
        if not _NUMPY_OK:
            return None

        n = self.n_dof
        J = np.zeros((6, n))

        # Compute all intermediate transforms
        transforms = [np.eye(4)]
        for i, (frame, q) in enumerate(zip(self.frames, joint_angles)):
            theta = q + frame.theta if frame.joint_type == "revolute" else frame.theta
            d = frame.d + q if frame.joint_type == "prismatic" else frame.d
            Ti = self._dh_matrix(frame.a, frame.alpha, d, theta)
            transforms.append(transforms[-1] @ Ti)

        pe = transforms[-1][:3, 3]  # end-effector position

        for i, frame in enumerate(self.frames):
            T_i = transforms[i]
            z_i = T_i[:3, 2]   # z-axis of frame i
            p_i = T_i[:3, 3]   # position of frame i

            if frame.joint_type == "revolute":
                J[:3, i] = np.cross(z_i, pe - p_i)
                J[3:, i] = z_i
            else:  # prismatic
                J[:3, i] = z_i
                J[3:, i] = np.zeros(3)

        return J

    def workspace_sample(
        self,
        n_samples: int = 5000,
    ) -> List[Tuple[float, float, float]]:
        """
        Monte Carlo workspace sampling.
        Returns list of (x, y, z) positions within robot reach.
        """
        if not _NUMPY_OK:
            return []

        import random
        positions = []
        for _ in range(n_samples):
            angles = [
                random.uniform(f.theta_min, f.theta_max)
                for f in self.frames
            ]
            fk = self.forward_kinematics(angles)
            if not fk.error:
                positions.append(fk.end_effector_position)

        return positions

    # ── Private ────────────────────────────────────────────────────────────────

    def _dh_matrix(self, a: float, alpha: float, d: float, theta: float) -> "np.ndarray":
        """Standard DH transformation matrix."""
        ct = math.cos(theta)
        st = math.sin(theta)
        ca = math.cos(alpha)
        sa = math.sin(alpha)
        return np.array([
            [ct,   -st * ca,  st * sa,  a * ct],
            [st,    ct * ca, -ct * sa,  a * st],
            [0.0,   sa,       ca,       d     ],
            [0.0,   0.0,      0.0,      1.0   ],
        ])

    def _manipulability(self, J: Optional["np.ndarray"]) -> float:
        """Yoshikawa manipulability measure: sqrt(det(J·Jᵀ))."""
        if J is None or not _NUMPY_OK:
            return 0.0
        try:
            JJt = J[:3, :] @ J[:3, :].T
            det = np.linalg.det(JJt)
            return float(math.sqrt(max(0.0, det)))
        except Exception:
            return 0.0


# ── Prebuilt robot configurations ─────────────────────────────────────────────

def make_puma560() -> RobotArm:
    """PUMA 560 6-DOF industrial arm (DH parameters)."""
    d60 = 0.4318
    frames = [
        DHFrame(a=0,       alpha=math.pi/2,  d=0,       theta=0, name="J1"),
        DHFrame(a=0.4318,  alpha=0,          d=0.1491,  theta=0, name="J2"),
        DHFrame(a=-0.0203, alpha=math.pi/2,  d=0,       theta=0, name="J3"),
        DHFrame(a=0,       alpha=-math.pi/2, d=0.4331,  theta=0, name="J4"),
        DHFrame(a=0,       alpha=math.pi/2,  d=0,       theta=0, name="J5"),
        DHFrame(a=0,       alpha=0,          d=0.0508,  theta=0, name="J6"),
    ]
    return RobotArm(frames)


def make_ur5() -> RobotArm:
    """Universal Robots UR5 6-DOF (DH parameters, meters)."""
    frames = [
        DHFrame(a=0,        alpha=math.pi/2,   d=0.0892,  theta=0, name="J1"),
        DHFrame(a=-0.4250,  alpha=0,           d=0,       theta=0, name="J2"),
        DHFrame(a=-0.3922,  alpha=0,           d=0,       theta=0, name="J3"),
        DHFrame(a=0,        alpha=math.pi/2,   d=0.1093,  theta=0, name="J4"),
        DHFrame(a=0,        alpha=-math.pi/2,  d=0.0948,  theta=0, name="J5"),
        DHFrame(a=0,        alpha=0,           d=0.0820,  theta=0, name="J6"),
    ]
    return RobotArm(frames)
