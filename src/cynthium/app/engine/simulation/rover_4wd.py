"""4-wheel skid-steer rover with rigid rectangular frame.

The chassis is a rigid rectangle with a wheel at each corner and the centre
of mass (CG) at the geometric centre.  Each wheel uses the same wheel-model
physics (power-limited drive, torque limit, friction-circle traction) as the
unicycle.  Steering is achieved by differential thrust between the left and
right sides (skid-steer), so the yaw rate is a *dynamic* state that emerges
from the moment balance about the CG.
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


# ── Chassis geometry ───────────────────────────────────────────────────────────

# Half-dimensions relative to CG
#        ↑ forward
#   FL ───── FR       FL = (+wb/2, -tw/2)   FR = (+wb/2, +tw/2)
#    │  CG  │         RL = (-wb/2, -tw/2)   RR = (-wb/2, +tw/2)
#   RL ───── RR
#        ↓


def _wheel_positions(
    x: float, y: float, heading: float, wb: float, tw: float,
) -> dict[str, tuple[float, float]]:
    """World-coordinate positions of the four wheels."""
    c, s = cos(heading), sin(heading)
    hwb, htw = wb / 2.0, tw / 2.0
    return {
        "FL": (x + hwb * c - htw * s, y + hwb * s + htw * c),
        "FR": (x + hwb * c + htw * s, y + hwb * s - htw * c),
        "RL": (x - hwb * c - htw * s, y - hwb * s + htw * c),
        "RR": (x - hwb * c + htw * s, y - hwb * s - htw * c),
    }


def _yaw_inertia(m: float, wb: float, tw: float) -> float:
    """Yaw moment of inertia of a rectangular thin plate (kg·m²)."""
    return m * (wb * wb + tw * tw) / 12.0


def _skid_steer_resistive_moment(
    f_n_total: float, mu: float, track_width: float, yaw_rate: float,
) -> float:
    """Resistive yaw moment from lateral sliding of the contact patches.

    In skid-steer the wheels must slide laterally to turn.  The resistive
    moment opposes the turn direction and saturates at high yaw rates.
    """
    omega_ref = 0.1  # rad/s — characteristic yaw rate for saturation
    # The resistive force at each wheel acts longitudinally from the CG
    # at half the track width, creating a moment pair.
    max_moment = 0.5 * mu * f_n_total * track_width  # both sides × lever
    return -max_moment * (yaw_rate / max(abs(yaw_rate), omega_ref))


# ── Main simulation ────────────────────────────────────────────────────────────


def simulate_rover_4wd(
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
    yaw_gain: float = 2.0,
) -> dict[str, Any]:
    """Simulate a 4-wheel skid-steer rover with rigid frame.

    The vehicle moves in 2D with state (x, y, heading, speed, yaw_rate).
    A pure-pursuit controller provides a desired yaw rate, while a speed
    controller provides a desired forward thrust.  These are mapped to
    left/right drive forces, each capped by power, torque, and traction
    limits.  The differential thrust produces a yaw moment that accelerates
    the chassis about the CG.

    Returns the same dict format as ``simulate_rover_over_path()``.
    """
    t_start = time.perf_counter()

    if pts_xyz.shape[0] < 2:
        print(f"[simulate_rover_4wd] empty path — returning immediately ({time.perf_counter() - t_start:.3f}s)")
        return _empty_result()

    # ── Vehicle parameters ──
    m = float(rover.mass_kg)
    mu = float(wheel_friction_coeff)
    p_w = float(power_w)
    g = float(g_mps2)
    crr = float(rover.rolling_resistance_coeff)
    wheel_r = float(rover.wheel_radius_m)
    motor_torque = rover.motor_peak_torque_nm

    # Chassis geometry
    tw = float(rover.track_width_m)   # track width
    wb = float(rover.wheelbase_m)     # wheelbase
    I_z = _yaw_inertia(m, wb, tw)     # yaw inertia

    # Power per side (even split)
    p_side = p_w * 0.5

    # Per-side torque limit (2 wheels per side)
    if motor_torque is not None:
        f_torque_max_side = 2.0 * motor_torque / wheel_r
    else:
        f_torque_max_side = float("inf")

    # ── Path setup ──
    path_xy = pts_xyz[:, :2].copy()
    resolution_m = _estimate_resolution(pts_xyz)

    # Cumulative distances
    n_path = len(path_xy)
    cum_dists = np.zeros(n_path)
    for i in range(1, n_path):
        dx = path_xy[i, 0] - path_xy[i - 1, 0]
        dy = path_xy[i, 1] - path_xy[i - 1, 1]
        cum_dists[i] = cum_dists[i - 1] + sqrt(dx * dx + dy * dy)
    path_total_len = float(cum_dists[-1])

    # Corner detection & speed profile
    corner_indices = _detect_corners(path_xy)
    target_speeds = _compute_target_speeds(
        path_xy, cum_dists, corner_indices, rover, p_w, crr, m, g,
    )

    # Initial heading
    heading = 0.0
    if len(pts_xyz) > 1:
        dx = pts_xyz[1, 0] - pts_xyz[0, 0]
        dy = pts_xyz[1, 1] - pts_xyz[0, 1]
        if abs(dx) > 1e-9 or abs(dy) > 1e-9:
            heading = atan2(dy, dx)

    # ── State ──
    x = float(pts_xyz[0, 0])
    y = float(pts_xyz[0, 1])
    speed = float(v0_mps)
    yaw_rate = 0.0  # dynamic state — emerges from moment balance

    # Stats
    braking_events = 0
    max_lateral_accel = 0.0
    max_braking_decel = 0.0

    # Illumination
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
    completed = False

    # Path geometry
    lookahead = max(path_total_len * 0.1, 2.0)
    dt = (
        _clamp(resolution_m / max(v0_mps, 1.0), DT_MIN, DT_MAX)
        if v0_mps > 0
        else DT_MIN
    )

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
            dx_i, dy_i = bx - ax, by - ay
            seg_len_sq = dx_i * dx_i + dy_i * dy_i
            if seg_len_sq < 1e-12:
                t = 0.0
                cx, cy = ax, ay
            else:
                t = _clamp(((x - ax) * dx_i + (y - ay) * dy_i) / seg_len_sq, 0.0, 1.0)
                cx, cy = ax + t * dx_i, ay + t * dy_i
            d_sq = (x - cx) ** 2 + (y - cy) ** 2
            if d_sq < best_d:
                best_d = d_sq
                best_idx = i
                best_cum = (
                    cum_dists[i] + sqrt(dx_i * dx_i + dy_i * dy_i) * t
                    if seg_len_sq > 1e-12
                    else cum_dists[i]
                )
        last_seg = best_idx
        cum_dist = best_cum

        target_speed = _sample_target_speed(cum_dist, target_speeds, path_total_len)

        # ── 2. Terrain slope at CG ──
        pitch = _sample_pitch(x, y, pts_xyz, best_idx)
        cos_pitch = abs(cos(pitch))
        sin_pitch = sin(pitch)

        # ── 3. Path following ──
        yaw_cmd = _pure_pursuit_yaw_rate(
            x, y, heading, speed, path_xy, lookahead, last_seg, win_size,
        )

        # ── 4. Speed control ──
        throttle, brake = _speed_controller(
            speed, target_speed, m, p_w / 2.0, v_min_power_mps, g, crr, pitch, mu,
        )
        if brake > 0:
            braking_events += 1

        # ── 5. Per-side force limits ──
        # Total normal force on all 4 wheels
        f_n_total = m * g * cos_pitch

        # Per-side effective speeds (differential from yaw rate)
        v_left_eff = max(speed - yaw_rate * tw / 2.0, v_min_power_mps)
        v_right_eff = max(speed + yaw_rate * tw / 2.0, v_min_power_mps)

        # Power-limited force per side
        f_power_left = p_side / v_left_eff
        f_power_right = p_side / v_right_eff

        # Traction limit per side (2 wheels per side, each with f_n_total/4 normal)
        f_trac_side = mu * f_n_total * 0.5  # 2 wheels × (f_n_total/4) × μ = μ·f_n_total/2

        # Combined per-side max force (forward)
        f_max_left = min(f_power_left * throttle, f_torque_max_side, f_trac_side)
        f_max_right = min(f_power_right * throttle, f_torque_max_side, f_trac_side)

        # ── 6. Compute left/right forces from speed and yaw demands ──
        # Grade and rolling resistance oppose forward motion
        f_grade = m * g * sin_pitch
        f_roll = crr * f_n_total

        # Desired total forward force from speed controller
        if throttle > 0:
            # Accelerating — use the full available force
            f_desired_total = f_max_left + f_max_right
        elif brake > 0:
            # Braking — apply braking force
            f_desired_total = -(brake * m)
        else:
            # Coasting
            f_desired_total = 0.0

        # Desired yaw moment from yaw rate error (PD controller)
        yaw_error = yaw_cmd - yaw_rate
        m_desired = I_z * yaw_gain * yaw_error

        # Resistive yaw moment from skid-steer
        m_resist = _skid_steer_resistive_moment(f_n_total, mu, tw, yaw_rate)

        # Total yaw moment required from differential thrust
        m_diff_desired = m_desired - m_resist

        # Split into left/right forces
        #   F_right + F_left = F_total
        #   (F_right - F_left) * tw/2 = M_diff
        # ⇒ F_right = F_total/2 + M_diff / tw
        #   F_left  = F_total/2 - M_diff / tw
        f_right = f_desired_total / 2.0 + m_diff_desired / tw
        f_left = f_desired_total / 2.0 - m_diff_desired / tw

        # ── 7. Cap per-side forces ──
        # Each side can push (positive) up to its max, or drag (negative)
        # down to its traction limit (for braking while turning)
        f_left = _clamp(f_left, -f_trac_side, f_max_left)
        f_right = _clamp(f_right, -f_trac_side, f_max_right)

        # ── 8. Net forces and moments ──
        f_total_actual = f_left + f_right
        m_diff_actual = (f_right - f_left) * tw / 2.0
        m_net = m_diff_actual + m_resist

        # Longitudinal acceleration
        f_net = f_total_actual - f_grade - f_roll
        a_long = f_net / m

        # Yaw acceleration
        alpha = m_net / I_z

        # Track peak braking deceleration
        if brake > 0 and a_long < 0:
            max_braking_decel = max(max_braking_decel, abs(a_long))

        # ── 9. Steering limit (friction circle on CG) ──
        max_lat_accel = mu * g * cos_pitch
        max_lateral_accel = max(max_lateral_accel, max_lat_accel)
        if speed > SPEED_EPS:
            yaw_rate_max = max_lat_accel / speed
        else:
            yaw_rate_max = 0.5

        # ── 10. Integrate (semi-implicit Euler) ──
        yaw_rate = _clamp(yaw_rate + alpha * dt, -yaw_rate_max, yaw_rate_max)
        speed = max(0.0, speed + a_long * dt)
        heading = _normalise_angle(heading + yaw_rate * dt)

        x += speed * cos(heading) * dt
        y += speed * sin(heading) * dt

        step_dist = sqrt((x - prev_pos[0]) ** 2 + (y - prev_pos[1]) ** 2)
        total_dist += step_dist
        prev_pos = np.array([x, y])

        # ── 11. Termination ──
        path_end = path_xy[-1]
        dist_to_end = sqrt((x - path_end[0]) ** 2 + (y - path_end[1]) ** 2)
        if dist_to_end < 3.0:
            completed = True
            break

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

        # ── 12. Energy ──
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

        total_time += dt
        if speed > 0:
            min_v = min(min_v, speed)
        max_v = max(max_v, speed)
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
        f"[simulate_rover_4wd] {status} — "
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
