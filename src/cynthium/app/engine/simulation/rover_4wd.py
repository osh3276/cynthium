"""4-wheel skid-steer rover with resistive motor model and stop-pivot-go navigation.

The chassis is a rigid rectangle with a wheel at each corner.  Each wheel
has a DC motor directly coupled to it.  The motor provides drive torque
when powered, and resistive torque from back-EMF (b * omega) and Coulomb
friction (tau_c) when coasting or overspeed — no separate brake.

The rover drives toward each waypoint, stops via motor resistance, pivots
in place to face the next waypoint, then drives again.
"""

from __future__ import annotations

import time
from math import atan2, cos, sin, sqrt
from typing import Any

import numpy as np

from cynthium.app.engine.simulation._sim_utils import (
	DT_MAX,
	DT_MIN,
	SPEED_EPS,
	_clamp,
	_empty_result,
	_estimate_resolution,
	_normalise_angle,
	_sample_pitch,
	SpeedPIDController,
)
from cynthium.app.engine.simulation.rover_settings import RoverSettings

# ── Tuning ──
_PIVOT_YAW_RATE_MAX = 0.4  # rad/s during pivot
_HEADING_K = 2.0  # proportional gain for heading-while-driving
_HEADING_ACCEPT_DEG = 3.0  # degrees of tolerance before pivot considered done
_WP_ARRIVE_DIST = 3.0  # distance to waypoint considered "arrived"
_OMEGA_EPS = 0.01  # rad/s — below this, wheel considered stopped


def _heading_error_to_waypoint(
	x: float, y: float, heading: float, tx: float, ty: float,
) -> float:
	"""Signed heading error (rad) from current heading toward (tx, ty)."""
	return _normalise_angle(atan2(ty - y, tx - x) - heading)


def _resistive_torque(
	omega: float, rover: RoverSettings,
) -> float:
	"""Resistive torque (N·m) opposing wheel motion.

	I * d(omega)/dt = -b * omega - tau_c * sign(omega)

	Parameters
	----------
	omega : float
		Wheel angular velocity (rad/s), positive = forward.
	rover : RoverSettings
		Rover parameters (motor_damping, coulomb_friction_nm).
	"""
	b = rover.motor_damping
	tau_c = rover.coulomb_friction_nm
	if abs(omega) < _OMEGA_EPS:
		return 0.0
	return b * omega + tau_c * (1.0 if omega > 0 else -1.0)


def _resistive_force(
	omega: float, rover: RoverSettings,
) -> float:
	"""Resistive force (N) at the wheel contact patch opposing motion."""
	return _resistive_torque(omega, rover) / max(rover.wheel_radius_m, 0.01)


def _sample_target_speed(dist_to_wp: float, rover: RoverSettings) -> float:
	"""Target speed ramping down near waypoint."""
	cruise = rover.target_cruise_speed_mps
	if dist_to_wp > 10.0:
		return float(cruise)
	return float(cruise * max(0.3, dist_to_wp / 10.0))


def simulate_rover_4wd(
	*,
	pts_xyz: np.ndarray,
	waypoints_xy: np.ndarray,
	rover: RoverSettings,
	wheel_friction_coeff: float,
	power_w: float,
	illumination_map: np.ndarray | None = None,
	illumination_transform=None,
	g_mps2: float,
	v0_mps: float = 0.0,
	v_min_power_mps: float = 0.05,
	max_steps: int = 500000,
	pause_durations: list[float] | None = None,
) -> dict[str, Any]:
	"""Simulate a 4-wheel skid-steer rover with resistive motor model."""
	t_start = time.perf_counter()

	if pts_xyz.shape[0] < 2 or len(waypoints_xy) < 2:
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
	I_w = float(rover.wheel_inertia_kgm2)  # rotational inertia per wheel

	# Chassis geometry
	tw = float(rover.track_width_m)
	wb = float(rover.wheelbase_m)
	I_z = m * (wb * wb + tw * tw) / 12.0  # yaw inertia

	# Power per side
	p_side = p_w * 0.5

	# Per-side torque limit (2 wheels per side)
	if motor_torque is not None:
		f_torque_max_side = 2.0 * motor_torque / wheel_r
	else:
		f_torque_max_side = float("inf")

	# ── Waypoint navigation setup ──
	n_wp = len(waypoints_xy)
	current_wp = 1
	mode = 0  # 0 = DRIVE, 1 = STOPPING, 2 = PIVOTING
	resolution_m = _estimate_resolution(pts_xyz)

	# Initial heading
	heading = atan2(
		waypoints_xy[1, 1] - waypoints_xy[0, 1],
		waypoints_xy[1, 0] - waypoints_xy[0, 0],
	)

	# ── State ──
	x = float(pts_xyz[0, 0])
	y = float(pts_xyz[0, 1])
	speed = float(v0_mps)
	yaw_rate = 0.0

	# Stats
	max_lateral_accel = 0.0

	# Illumination
	inv_illum = None
	if illumination_map is not None and illumination_transform is not None:
		inv_illum = ~illumination_transform

	# Accumulators
	total_time = 0.0
	total_dist = 0.0
	energy_j_per_m2 = 0.0
	battery_energy_used_j = 0.0
	min_v = float("inf") if v0_mps > 0 else 0.0
	max_v = float(v0_mps)
	prev_pos = np.array([x, y])
	stagnation = 0
	completed = False
	failure_reason: str | None = None
	_pause_timer = 0.0  # seconds of pause remaining at waypoint

	dt = DT_MIN
	_pid = SpeedPIDController()

	for step in range(max_steps):
		tx, ty = waypoints_xy[current_wp]
		dist_to_wp = sqrt((tx - x) ** 2 + (ty - y) ** 2)

		# ── Terrain slope at current position ──
		pitch = _sample_pitch(x, y, pts_xyz)
		cos_pitch = abs(cos(pitch))
		sin_pitch = sin(pitch)

		# ── State machine ──
		if mode == 0:  # DRIVE
			heading_err = _heading_error_to_waypoint(x, y, heading, tx, ty)
			yaw_cmd = _HEADING_K * heading_err

			if dist_to_wp < _WP_ARRIVE_DIST:
				mode = 1
				continue

		elif mode == 1:  # STOPPING — coast down via motor resistance
			yaw_cmd = 0.0
			# Wheel omega = speed / r; resistive torque does the stopping
			omega = speed / max(wheel_r, 0.01)
			tau_resist = _resistive_torque(omega, rover)
			# Apply resistive torque to wheel inertia (4 wheels, per-wheel update)
			omega -= tau_resist / I_w * dt
			if abs(omega) < _OMEGA_EPS:
				omega = 0.0
			speed = omega * wheel_r
			if speed < 0.01:
				speed = 0.0
				_pid.reset()
				# Check if this waypoint has a pause configured
				wp_idx = current_wp - 1  # 0-based index in pause_durations
				wp_pause = (pause_durations[wp_idx] if pause_durations
				            and wp_idx < len(pause_durations) else 0.0)
				if wp_pause > 0 and current_wp < n_wp - 1:
					_pause_timer = wp_pause
					mode = 3  # PAUSE
				elif current_wp + 1 < n_wp:
					current_wp += 1
					mode = 2
				else:
					completed = True
					break

			# Still need to update position and energy
			total_time += dt
			battery_energy_used_j += rover.idle_drain_w * dt
			dt = _clamp(resolution_m / max(speed, 0.5), DT_MIN, DT_MAX)
			continue

		elif mode == 2:  # PIVOTING
			tx, ty = waypoints_xy[current_wp]
			heading_err = _heading_error_to_waypoint(x, y, heading, tx, ty)

			if abs(heading_err) < _HEADING_ACCEPT_DEG * (3.14159 / 180.0):
				mode = 0
				continue

			f_n_total = m * g * cos_pitch
			f_trac_side = mu * f_n_total * 0.5
			pivot_f = 0.3 * mu * m * g * cos_pitch
			sign = 1.0 if heading_err > 0 else -1.0
			f_left = _clamp(-sign * pivot_f, -f_trac_side, f_trac_side)
			f_right = _clamp(sign * pivot_f, -f_trac_side, f_trac_side)

			m_diff = (f_right - f_left) * tw / 2.0
			alpha = m_diff / I_z
			yaw_rate = _clamp(yaw_rate + alpha * dt, -_PIVOT_YAW_RATE_MAX, _PIVOT_YAW_RATE_MAX)
			heading = _normalise_angle(heading + yaw_rate * dt)
			speed = 0.0
			yaw_rate *= 0.95

			battery_energy_used_j += p_w * 0.3 * dt
			battery_energy_used_j += rover.idle_drain_w * dt

			total_time += dt
			dt = _clamp(resolution_m / max(speed, 0.5), DT_MIN, DT_MAX)
			continue

		elif mode == 3:  # PAUSE — wait at waypoint
					speed = 0.0
					yaw_rate = 0.0
					_pause_timer -= dt
					total_time += dt
					battery_energy_used_j += rover.idle_drain_w * dt
					if _pause_timer <= 0.0:
						if current_wp + 1 < n_wp:
							current_wp += 1
							mode = 2
						else:
							completed = True
							break
					dt = _clamp(resolution_m / max(speed, 0.5), DT_MIN, DT_MAX)
					continue

		# ═══════════════════════════════════════════════════════════════
		# DRIVE mode — motor drive + resistive torque
		# ═══════════════════════════════════════════════════════════════

		target_speed = _sample_target_speed(dist_to_wp, rover)
		throttle, _brake = _pid.update(speed, target_speed, dt)

		# ── Wheel angular velocity per side (accounting for yaw) ──
		v_left = speed - yaw_rate * tw / 2.0
		v_right = speed + yaw_rate * tw / 2.0
		omega_left = v_left / max(wheel_r, 0.01)
		omega_right = v_right / max(wheel_r, 0.01)

		# ── Resistive force per side (from motor back-EMF + friction) ──
		# Each side has 2 wheels, resistive torque per wheel * 2
		f_resist_left = 2.0 * _resistive_force(omega_left, rover)
		f_resist_right = 2.0 * _resistive_force(omega_right, rover)
		# Resistive force always opposes motion (positive = opposing forward)
		# sign: if wheel is rolling forward (omega > 0), force is negative (backward)

		# ── Drive torque from motor ──
		f_n_total = m * g * cos_pitch
		f_trac_side = mu * f_n_total * 0.5

		if throttle > 0 and speed < rover.max_wheel_speed_mps:
			f_power_left = p_side / max(v_left, v_min_power_mps)
			f_power_right = p_side / max(v_right, v_min_power_mps)
			f_drive_left = min(f_power_left * throttle, f_torque_max_side, f_trac_side)
			f_drive_right = min(f_power_right * throttle, f_torque_max_side, f_trac_side)
		else:
			f_drive_left = 0.0
			f_drive_right = 0.0

		# ── Battery drain (only when motors are driving) ──
		battery_energy_used_j += p_w * throttle * dt

		# ── Net force per side ──
		# Resistive force sign: positive omega → resists forward → subtract from drive
		f_left = f_drive_left - f_resist_left
		f_right = f_drive_right - f_resist_right
		# Clamp net to traction limits (don't exceed friction circle in either direction)
		f_left = _clamp(f_left, -f_trac_side, f_trac_side)
		f_right = _clamp(f_right, -f_trac_side, f_trac_side)

		# ── Yaw differential ──
		heading_err = _heading_error_to_waypoint(x, y, heading, tx, ty)
		yaw_cmd = _HEADING_K * heading_err
		yaw_error = yaw_cmd - yaw_rate
		m_desired = I_z * 2.0 * yaw_error
		m_resist = _skid_steer_resistive_moment(f_n_total, mu, tw, yaw_rate)
		m_diff_desired = m_desired - m_resist

		f_left += -m_diff_desired / tw
		f_right += m_diff_desired / tw
		f_left = _clamp(f_left, -f_trac_side, f_trac_side)
		f_right = _clamp(f_right, -f_trac_side, f_trac_side)

		f_total_actual = f_left + f_right
		m_diff_actual = (f_right - f_left) * tw / 2.0
		m_net = m_diff_actual + m_resist

		# ── Integrate ──
		f_grade = m * g * sin_pitch
		f_roll = crr * f_n_total
		f_net = f_total_actual - f_grade - f_roll
		a_long = f_net / m
		alpha = m_net / I_z

		max_lat_accel = mu * g * cos_pitch
		max_lateral_accel = max(max_lateral_accel, max_lat_accel)
		yaw_rate_max = max_lat_accel / max(speed, SPEED_EPS) if speed > SPEED_EPS else 0.5

		yaw_rate = _clamp(yaw_rate + alpha * dt, -yaw_rate_max, yaw_rate_max)
		speed = max(0.0, speed + a_long * dt)
		heading = _normalise_angle(heading + yaw_rate * dt)
		x += speed * cos(heading) * dt
		y += speed * sin(heading) * dt

		step_dist = sqrt((x - prev_pos[0]) ** 2 + (y - prev_pos[1]) ** 2)
		total_dist += step_dist
		prev_pos = np.array([x, y])

		# ── Termination checks ──
		if current_wp >= n_wp - 1 and dist_to_wp < _WP_ARRIVE_DIST:
			completed = True
			break

		if step_dist < 0.0001 and mode == 0:
			stagnation += 1
			if stagnation > 5000:
				failure_reason = "Insufficient traction — rover cannot make progress"
				break
		else:
			stagnation = 0

		# ── Energy ──
		if inv_illum is not None:
			col, row = inv_illum * (float(x), float(y))
			ci, ri = int(round(col)), int(round(row))
			if 0 <= ri < illumination_map.shape[0] and 0 <= ci < illumination_map.shape[1]:
				illum = float(illumination_map[ri, ci])
				if np.isfinite(illum):
					energy_j_per_m2 += illum * dt

		total_time += dt
		battery_energy_used_j += rover.idle_drain_w * dt
		if speed > 0:
			min_v = min(min_v, speed)
		max_v = max(max_v, speed)
		dt = _clamp(resolution_m / max(speed, 0.5), DT_MIN, DT_MAX)

	if failure_reason is None and not completed:
		failure_reason = "Could not complete traverse in time"

	# ── Assemble result ──
	if total_time <= 0:
		avg_v, avg_illum = 0.0, 0.0
	else:
		avg_v = total_dist / total_time
		avg_illum = energy_j_per_m2 / total_time

	batt_cap_j = rover.battery_capacity_j
	batt_remaining_pct = max(0.0, (batt_cap_j - battery_energy_used_j) / max(batt_cap_j, 1.0) * 100.0) if batt_cap_j > 0 else 100.0

	t_elapsed = time.perf_counter() - t_start
	status = "completed" if completed else "failed"
	print(
		f"[simulate_rover_4wd] {status} — "
		f"{t_elapsed:.3f}s wall time, {total_time:.1f}s sim time, "
		f"{step + 1} steps, {total_dist:.0f}m travelled, "
		f"battery {batt_remaining_pct:.0f}%"
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
		"failure_reason": failure_reason,
		"rollover_occurred": False,
		"max_lateral_accel_mps2": float(max_lateral_accel),
		"braking_events": 0,
		"max_braking_decel_mps2": 0.0,
		"battery_energy_used_j": float(battery_energy_used_j),
		"battery_remaining_pct": float(batt_remaining_pct),
		"battery_capacity_wh": float(rover.battery_capacity_wh),
	}


def _skid_steer_resistive_moment(
	f_n_total: float, mu: float, track_width: float, yaw_rate: float,
) -> float:
	"""Resistive yaw moment from lateral sliding of the contact patches."""
	omega_ref = 0.1
	max_moment = 0.5 * mu * f_n_total * track_width
	return -max_moment * (yaw_rate / max(abs(yaw_rate), omega_ref))
