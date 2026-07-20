"""2D vehicle dynamics — building up from a unicycle to multi-wheel.

This module progressively models the rover as a body moving in 2D (x, y, heading)
on a 3D terrain surface.  We start with the simplest model: a unicycle (the
whole rover is a single driven+steered wheel) and will later add more wheels.
"""

from __future__ import annotations

import time
from math import atan2, cos, sin, sqrt
from typing import Any

import numpy as np

from cynthium.app.engine.simulation._unicycle_shared import (
    DT_MAX,
    DT_MIN,
    SPEED_EPS,
    _clamp,
    _compute_target_speeds,
    _detect_corners,
    _empty_result,
    _estimate_resolution,
    _normalise_angle,
    _pure_pursuit_yaw_rate,
    _sample_pitch,
    _sample_target_speed,
    _speed_controller,
)
from cynthium.app.engine.simulation.rover_settings import RoverSettings


# ── Unicycle model ─────────────────────────────────────────────────────────────


def simulate_unicycle(
    *,
    pts_xyz: np.ndarray,
    rover: RoverSettings,
    wheel_friction_coeff: float,
    power_w: float,
    illumination_map: np.ndarray | None = None,
    illumination_transform=None,
    g_mps2: float,
    v0_mps: float = 0.0,
    v_min_power_mps: float = 0.05,
    max_steps: int = 500000,
) -> dict[str, Any]:
    """Simulate the rover as a unicycle (single driven+steered wheel).

    The vehicle moves in 2D with state (x, y, heading, speed).  A pure-pursuit
    controller steers toward the path, and the power-limited drivetrain
    accelerates/brakes to follow a target speed.  The rover slows at sharp
    corners (waypoints) for realistic traverse behaviour.

    Returns the same dict format as ``simulate_rover_over_path()``.
    """
    t_start = time.perf_counter()

    if pts_xyz.shape[0] < 2:
        print(f"[simulate_unicycle] empty path — returning immediately ({time.perf_counter() - t_start:.3f}s)")
        return _empty_result()

    m = float(rover.mass_kg)
    mu = float(wheel_friction_coeff)
    p_w = float(power_w)
    g = float(g_mps2)
    crr = float(rover.rolling_resistance_coeff)

    path_xy = pts_xyz[:, :2].copy()
    resolution_m = _estimate_resolution(pts_xyz)

    # ── Pre-compute cumulative distances ──
    n_path = len(path_xy)
    cum_dists = np.zeros(n_path)
    for i in range(1, n_path):
        dx = path_xy[i, 0] - path_xy[i - 1, 0]
        dy = path_xy[i, 1] - path_xy[i - 1, 1]
        cum_dists[i] = cum_dists[i - 1] + sqrt(dx * dx + dy * dy)
    path_total_len = float(cum_dists[-1])

    # ── Detect corners and build target speed profile ──
    corner_indices = _detect_corners(path_xy)
    target_speeds = _compute_target_speeds(
        path_xy, cum_dists, corner_indices, rover, p_w, crr, m, g
    )

    # Initial heading: direction of first path segment
    heading = 0.0
    if len(pts_xyz) > 1:
        dx = pts_xyz[1, 0] - pts_xyz[0, 0]
        dy = pts_xyz[1, 1] - pts_xyz[0, 1]
        if abs(dx) > 1e-9 or abs(dy) > 1e-9:
            heading = atan2(dy, dx)

    # State
    x = float(pts_xyz[0, 0])
    y = float(pts_xyz[0, 1])
    speed = float(v0_mps)
    braking_events = 0
    max_lateral_accel = 0.0
    max_braking_decel = 0.0

    # Illumination transform
    inv_illum = None
    if illumination_map is not None and illumination_transform is not None:
        inv_illum = ~illumination_transform

    # Accumulators
    total_time = 0.0
    total_dist = 0.0
    energy_j_per_m2 = 0.0
    min_v = float("inf") if v0_mps > 0 else 0.0
    max_v = float(v0_mps)
    prev_pos = np.array([x, y])
    stagnation = 0
    diverge_counter = 0
    last_dist_to_end = cum_dists[-1]
    completed = False  # whether the vehicle reached within 3m of the path end

    # Path geometry
    lookahead = max(path_total_len * 0.1, 2.0)
    dt = (
        _clamp(resolution_m / max(v0_mps, 1.0), DT_MIN, DT_MAX)
        if v0_mps > 0
        else DT_MIN
    )

    # Sliding window: the rover moves forward along the path,
    # so we only search a few segments around the last known one.
    win_size = 20
    last_seg = 0

    step = 0
    for step in range(max_steps):
        # ── 1. Nearest point on path (sliding window) ──
        best_d = float("inf")
        best_idx, best_cum = 0, 0.0
        start_i = max(0, last_seg - 5)
        end_i = min(n_path - 1, last_seg + win_size)
        for i in range(start_i, end_i):
            ax, ay = path_xy[i]
            bx, by = path_xy[i + 1]
            dx, dy = bx - ax, by - ay
            seg_len_sq = dx * dx + dy * dy
            if seg_len_sq < 1e-12:
                t = 0.0
                cx, cy = ax, ay
            else:
                t = _clamp(
                    ((x - ax) * dx + (y - ay) * dy) / seg_len_sq, 0.0, 1.0
                )
                cx, cy = ax + t * dx, ay + t * dy
            d_sq = (x - cx) ** 2 + (y - cy) ** 2
            if d_sq < best_d:
                best_d = d_sq
                best_idx = i
                best_cum = (
                    cum_dists[i] + sqrt(dx * dx + dy * dy) * t
                    if seg_len_sq > 1e-12
                    else cum_dists[i]
                )
        last_seg = best_idx
        cum_dist = best_cum

        target_speed = _sample_target_speed(
            cum_dist, target_speeds, path_total_len
        )

        # ── 2. Terrain slope under the vehicle ──
        pitch = _sample_pitch(x, y, pts_xyz, best_idx)

        # ── 3. Path following (pure pursuit, sliding window) ──
        yaw_cmd = _pure_pursuit_yaw_rate(
            x, y, heading, speed, path_xy, lookahead, last_seg, win_size
        )

        # ── 4. Speed control (braking at corners) ──
        throttle, brake = _speed_controller(
            speed, target_speed, m, p_w, v_min_power_mps, g, crr, pitch, mu
        )
        if brake > 0:
            braking_events += 1

        # ── 5. Forces ──
        # Normal force
        f_n = m * g * abs(cos(pitch))
        f_trac_max = mu * f_n

        # Power-limited drive force
        v_eff = max(speed, v_min_power_mps)
        f_power = p_w / v_eff
        f_drive = min(f_power * throttle, f_trac_max)

        # Grade resistance (+ uphill, - downhill)
        f_grade = m * g * sin(pitch)

        # Rolling resistance
        f_roll = crr * f_n

        # Net longitudinal acceleration
        f_net = f_drive - f_grade - f_roll - brake * m
        a_long = f_net / m

        # Track peak braking deceleration
        if brake > 0:
            decel = abs(a_long) if a_long < 0 else 0.0
            max_braking_decel = max(max_braking_decel, decel)

        # ── 6. Steering limit (friction circle) ──
        # Max lateral acceleration from friction
        max_lat_accel = mu * g * abs(cos(pitch))
        max_lateral_accel = max(max_lateral_accel, max_lat_accel)

        # At speed v, max yaw rate is limited by lateral friction:
        # a_lat = v * yaw_rate → yaw_rate_max = max_lat_accel / v
        if speed > SPEED_EPS:
            yaw_rate_max = max_lat_accel / speed
        else:
            yaw_rate_max = 0.5  # low-speed steering limit (rad/s)
        yaw_rate = _clamp(yaw_cmd, -yaw_rate_max, yaw_rate_max)

        # ── 7. Integrate (semi-implicit Euler) ──
        speed = max(0.0, speed + a_long * dt)
        heading = _normalise_angle(heading + yaw_rate * dt)

        vx = speed * cos(heading)
        vy = speed * sin(heading)
        x += vx * dt
        y += vy * dt

        step_dist = sqrt((x - prev_pos[0]) ** 2 + (y - prev_pos[1]) ** 2)
        total_dist += step_dist
        prev_pos = np.array([x, y])

        # ── 8. Termination checks ──
        path_end = path_xy[-1]
        dist_to_end = sqrt((x - path_end[0]) ** 2 + (y - path_end[1]) ** 2)
        if dist_to_end < 3.0:
            completed = True
            break

        # Diverge detection: getting farther from the path end
        if dist_to_end > last_dist_to_end + 0.5:
            diverge_counter += 1
        else:
            diverge_counter = 0
        last_dist_to_end = dist_to_end
        if diverge_counter > 50:
            break

        if step_dist < 0.0001:
            stagnation += 1
            if stagnation > 5000:
                break
        else:
            stagnation = 0

        # ── 9. Energy ──
        if inv_illum is not None:
            col, row = inv_illum * (float(x), float(y))
            ci, ri = int(round(col)), int(round(row))
            if (
                0 <= ri < illumination_map.shape[0]
                and 0 <= ci < illumination_map.shape[1]
            ):
                illum = float(illumination_map[ri, ci])
                if np.isfinite(illum):
                    energy_j_per_m2 += illum * dt

        # ── 10. Stats ──
        total_time += dt
        if speed > 0:
            min_v = min(min_v, speed)
        max_v = max(max_v, speed)

        # Adaptive dt
        dt = _clamp(resolution_m / max(speed, 0.5), DT_MIN, DT_MAX)

    # ── Assemble result ──
    if total_time <= 0:
        avg_v, avg_illum = 0.0, 0.0
    else:
        avg_v = total_dist / total_time
        avg_illum = energy_j_per_m2 / total_time

    t_elapsed = time.perf_counter() - t_start
    status = "completed" if completed else "failed"
    print(
        f"[simulate_unicycle] {status} — "
        f"{t_elapsed:.3f}s wall time, {total_time:.1f}s sim time, "
        f"{step + 1} steps, {total_dist:.0f}m travelled"
    )

    return {
        "traverse_feasible": 1.0 if completed else 0.0,
        "traversal_time_s": float(total_time) if completed else float("inf"),
        "average_velocity_mps": float(avg_v),
        "min_velocity_mps": float(min_v) if min_v != float("inf") else 0.0,
        "max_velocity_mps": float(max_v),
        "solar_energy_per_m2_j": float(energy_j_per_m2),
        "avg_solar_illumination_w_per_m2": float(avg_illum),
        "failure_x": float(x) if not completed else None,
        "failure_y": float(y) if not completed else None,
        "rollover_occurred": False,
        "max_lateral_accel_mps2": float(max_lateral_accel),
        "braking_events": braking_events,
        "max_braking_decel_mps2": float(max_braking_decel),
    }
