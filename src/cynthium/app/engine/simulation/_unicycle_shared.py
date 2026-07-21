"""Shared constants and helper functions for the unicycle rover models.

This module consolidates all common logic used by ``rover_2d.py`` and
``rover_physics.py`` so that bug-fixes and improvements automatically
benefit both simulation paths.
"""

from __future__ import annotations

from math import atan2, pi, sin, sqrt
from typing import Any

import numpy as np

from cynthium.app.engine.simulation.rover_settings import RoverSettings


# ── Constants ──────────────────────────────────────────────────────────────────

SPEED_EPS = 0.01
MAX_STEPS = 500_000
DT_MIN = 0.02
DT_MAX = 0.1
CORNER_ANGLE_THRESHOLD_DEG = 5.0
STOP_APPROACH_DIST_M = 5.0


# ── Generic helpers ────────────────────────────────────────────────────────────


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def _normalise_angle(a: float) -> float:
    while a > pi:
        a -= 2.0 * pi
    while a < -pi:
        a += 2.0 * pi
    return a


# ── PID speed controller ──────────────────────────────────────────────────────


class SpeedPIDController:
    """PID speed controller for rover throttle/brake.

    Maps speed error to throttle (0-1) when below target, or brake
    deceleration (0-2 m/s²) when above target.
    """

    def __init__(
        self,
        Kp: float = 8.0,
        Ki: float = 0.4,
        Kd: float = 0.6,
        integral_limit: float = 5.0,
    ):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.integral_limit = integral_limit
        self._integral = 0.0
        self._prev_error = 0.0

    def reset(self) -> None:
        """Reset integral and derivative state (e.g. after a corner stop)."""
        self._integral = 0.0
        self._prev_error = 0.0

    def update(self, speed: float, target: float, dt: float) -> tuple[float, float]:
        """Compute (throttle, brake_decel) for one timestep.

        Parameters
        ----------
        speed : float
            Current rover speed (m/s).
        target : float
            Desired speed (m/s).
        dt : float
            Time delta for this step (s).

        Returns
        -------
        throttle : float
            Throttle 0-1 applied to drive force.
        brake_decel : float
            Braking deceleration (m/s²), 0 when throttling.
        """
        error = target - speed

        # Integrate with anti-windup
        self._integral += error * dt
        self._integral = max(
            -self.integral_limit, min(self.integral_limit, self._integral)
        )

        # Derivative on error (filtered)
        derivative = (error - self._prev_error) / max(dt, 1e-6)
        self._prev_error = error

        # PID output
        output = (
            self.Kp * error
            + self.Ki * self._integral
            + self.Kd * derivative
        )

        # Map to throttle (positive) or brake (negative)
        if output >= 0.0:
            return min(1.0, output), 0.0
        else:
            return 0.0, min(2.0, -output * 2.0)


# ── Pure pursuit path following ────────────────────────────────────────────────


def _pure_pursuit_yaw_rate(
    x: float,
    y: float,
    heading: float,
    speed: float,
    path_xy: np.ndarray,
    lookahead: float,
    last_seg: int,
    win_size: int,
) -> float:
    """Compute desired yaw rate (rad/s) to follow a path via pure pursuit."""
    if speed < SPEED_EPS or len(path_xy) < 2:
        return 0.0

    n = len(path_xy)
    best_err = float("inf")
    best_lx, best_ly = path_xy[-1]

    start_i = max(0, last_seg - 2)
    end_i = min(n - 1, last_seg + win_size)
    for i in range(start_i, end_i):
        ax, ay = path_xy[i]
        bx, by = path_xy[i + 1]
        seg_len = sqrt((bx - ax) ** 2 + (by - ay) ** 2)
        if seg_len < 1e-9:
            continue
        n_subsamples = max(2, min(10, int(seg_len / 1.0)))
        for j in range(n_subsamples):
            t = j / n_subsamples
            lx, ly = ax + t * (bx - ax), ay + t * (by - ay)
            err = abs(sqrt((lx - x) ** 2 + (ly - y) ** 2) - lookahead)
            if err < best_err:
                best_err = err
                best_lx, best_ly = lx, ly

    # Yaw rate from pure pursuit: yaw = 2 * v * sin(delta) / L
    tx, ty = best_lx - x, best_ly - y
    target_angle = atan2(ty, tx)
    delta = _normalise_angle(target_angle - heading)

    yaw = 2.0 * speed * sin(delta) / max(lookahead, 0.1)
    return _clamp(yaw, -1.5, 1.5)


# ── Corner detection & speed profiling ────────────────────────────────────────


def _detect_corners(path_xy: np.ndarray) -> list[int]:
    """Return indices of path waypoints that are sharp corners."""
    if len(path_xy) < 3:
        return []
    indices = []
    for i in range(1, len(path_xy) - 1):
        v1 = path_xy[i] - path_xy[i - 1]
        v2 = path_xy[i + 1] - path_xy[i]
        l1 = np.linalg.norm(v1)
        l2 = np.linalg.norm(v2)
        if l1 < 1e-6 or l2 < 1e-6:
            continue
        cos_ang = float(np.dot(v1, v2) / (l1 * l2))
        cos_ang = _clamp(cos_ang, -1.0, 1.0)
        angle = float(np.degrees(np.arccos(cos_ang)))
        if angle > CORNER_ANGLE_THRESHOLD_DEG:
            indices.append(i)
    return indices


def _compute_target_speeds(
    path_xy: np.ndarray,
    cum_dists: np.ndarray,
    corner_indices: list[int],
    rover: RoverSettings,
    p_w: float,
    crr: float,
    m: float,
    g: float,
) -> np.ndarray:
    """Build a (cum_dist, target_speed) table with slowdowns at corners.

    The baseline speed is the power-limited speed at which drive power
    matches rolling resistance.  At each corner the target drops to zero
    with a linear ramp over ``STOP_APPROACH_DIST_M`` on both sides.
    """
    n = len(path_xy)
    # Baseline: speed at which drive power equals rolling resistance force
    f_roll_ref = max(crr * m * g, 1.0)
    full_speed = p_w / f_roll_ref
    targets = np.full(n, full_speed)

    for ci in corner_indices:
        targets[ci] = 0.0
        d_at = cum_dists[ci]
        # Ramp down on approach
        for j in range(ci - 1, -1, -1):
            d = d_at - cum_dists[j]
            if d > STOP_APPROACH_DIST_M:
                break
            targets[j] = min(targets[j], full_speed * d / STOP_APPROACH_DIST_M)
        # Ramp up on exit
        for j in range(ci + 1, n):
            d = cum_dists[j] - d_at
            if d > STOP_APPROACH_DIST_M:
                break
            targets[j] = min(targets[j], full_speed * d / STOP_APPROACH_DIST_M)

    targets = np.maximum(targets, 0.3)
    return np.column_stack([cum_dists, targets])


def _sample_target_speed(
    cum_dist: float, speed_table: np.ndarray, path_total_len: float
) -> float:
    """Interpolate target speed at a given cumulative distance."""
    if len(speed_table) == 0:
        return 1.0
    d = _clamp(cum_dist, speed_table[0, 0], speed_table[-1, 0])
    return float(np.interp(d, speed_table[:, 0], speed_table[:, 1]))


# ── Terrain helpers ────────────────────────────────────────────────────────────


def _sample_pitch(
    x: float, y: float, pts_xyz: np.ndarray, hint_idx: int | None = None
) -> float:
    """Estimate terrain pitch (rad) under the vehicle from the nearest path point.

    Positive pitch = uphill in the direction of travel.

    Parameters
    ----------
    hint_idx : int or None
        If provided, only segments near this index are searched (sliding window).
    """
    if len(pts_xyz) < 2:
        return 0.0

    n_seg = len(pts_xyz) - 1

    # Determine search range
    if hint_idx is not None:
        start_i = max(0, hint_idx - 5)
        end_i = min(n_seg, hint_idx + 20)
    else:
        start_i = 0
        end_i = min(n_seg, 200)

    best_d = float("inf")
    best_i = 0
    for i in range(start_i, end_i):
        ax, ay = pts_xyz[i, :2]
        bx, by = pts_xyz[i + 1, :2]
        dx, dy = bx - ax, by - ay
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq < 1e-12:
            cx, cy = ax, ay
        else:
            t = _clamp(
                ((x - ax) * dx + (y - ay) * dy) / seg_len_sq, 0.0, 1.0
            )
            cx, cy = ax + t * dx, ay + t * dy
        d_sq = (x - cx) ** 2 + (y - cy) ** 2
        if d_sq < best_d:
            best_d = d_sq
            best_i = i

    i_clamped = min(max(best_i, 0), len(pts_xyz) - 2)
    dz = pts_xyz[i_clamped + 1, 2] - pts_xyz[i_clamped, 2]
    dhoriz = sqrt(
        (pts_xyz[i_clamped + 1, 0] - pts_xyz[i_clamped, 0]) ** 2
        + (pts_xyz[i_clamped + 1, 1] - pts_xyz[i_clamped, 1]) ** 2
    )
    if dhoriz > 0.01:
        return atan2(dz, dhoriz)
    return 0.0


def _estimate_resolution(pts_xyz: np.ndarray) -> float:
    """Median segment length along the path (m)."""
    if pts_xyz.shape[0] < 2:
        return 5.0
    diffs = np.diff(pts_xyz[:, :2], axis=0)
    lengths = np.linalg.norm(diffs, axis=1)
    valid = lengths[lengths > 1e-9]
    return float(np.median(valid)) if len(valid) > 0 else 5.0


# ── Empty result ───────────────────────────────────────────────────────────────


def _empty_result() -> dict[str, Any]:
    return {
        "traverse_feasible": 1.0,
        "traversal_time_s": 0.0,
        "average_velocity_mps": 0.0,
        "min_velocity_mps": 0.0,
        "max_velocity_mps": 0.0,
        "solar_energy_per_m2_j": 0.0,
        "avg_solar_illumination_w_per_m2": 0.0,
        "failure_x": None,
        "failure_y": None,
        "failure_reason": None,
        "rollover_occurred": False,
        "max_lateral_accel_mps2": 0.0,
        "braking_events": 0,
        "max_braking_decel_mps2": 0.0,
    }
