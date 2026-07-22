"""4-wheel skid-steer rover with stop-pivot-go waypoint navigation.

The chassis is a rigid rectangle with a wheel at each corner and the centre
of mass (CG) at the geometric centre.  Steering is achieved by differential
thrust between the left and right sides (skid-steer).

Unlike smooth path following, the rover drives toward each waypoint, stops,
pivots in place to face the next waypoint, then drives again.
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


def _pivot_thrust(mu: float, m: float, g: float, cos_pitch: float) -> float:
	"""Thrust per side for in-place pivot (opposite directions)."""
	return 0.3 * mu * m * g * cos_pitch


def _heading_error_to_waypoint(
	x: float, y: float, heading: float, tx: float, ty: float,
) -> float:
	"""Signed heading error (rad) from current heading toward (tx, ty)."""
	return _normalise_angle(atan2(ty - y, tx - x) - heading)


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
) -> dict[str, Any]:
	"""Simulate a 4-wheel skid-steer rover with stop-pivot-go navigation.

	The rover drives toward each waypoint in sequence, stops when it arrives,
	pivots to face the next one, then drives again.

	Parameters
	----------
	pts_xyz : np.ndarray
		Full interpolated path with elevation (used for terrain sampling).
	waypoints_xy : np.ndarray
		Original user waypoints (N, 2) — the rover will stop at each one.
	"""
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

	# Chassis geometry
	tw = float(rover.track_width_m)
	wb = float(rover.wheelbase_m)
	I_z = m * (wb * wb + tw * tw) / 12.0  # yaw inertia

	# Power per side
	p_side = p_w * 0.5

	# Per-side torque limit
	if motor_torque is not None:
		f_torque_max_side = 2.0 * motor_torque / wheel_r
	else:
		f_torque_max_side = float("inf")

	# ── Waypoint navigation setup ──
	n_wp = len(waypoints_xy)
	current_wp = 1  # index of the waypoint we're driving toward
	# State: 0 = DRIVE, 1 = STOPPING, 2 = PIVOTING
	mode = 0
	path_xy = pts_xyz[:, :2].copy()
	resolution_m = _estimate_resolution(pts_xyz)

	# Initial heading toward first waypoint
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
		battery_energy_used_j = 0.0
	min_v = float("inf") if v0_mps > 0 else 0.0
	max_v = float(v0_mps)
	prev_pos = np.array([x, y])
	stagnation = 0
	completed = False
	failure_reason: str | None = None

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
			# Drive toward the current waypoint
			heading_err = _heading_error_to_waypoint(x, y, heading, tx, ty)
			yaw_cmd = _HEADING_K * heading_err

			if dist_to_wp < _WP_ARRIVE_DIST:
				# Arrived — start stopping
				mode = 1
				continue

		elif mode == 1:  # STOPPING
			# Brake to zero
			yaw_cmd = 0.0
			target_speed = 0.0
			throttle, brake = _pid.update(speed, target_speed, dt)
			if brake > 0:
				braking_events += 1

			# Force stopping
			brake = min(brake, rover.max_brake_decel_mps2)
			f_desired_total = -(brake * m)
			f_grade = m * g * sin_pitch
			f_roll = crr * m * g * cos_pitch
			f_net = f_desired_total - f_grade - f_roll
			a_long = f_net / m
			speed = max(0.0, speed + a_long * dt)
			if speed < 0.01:
				speed = 0.0
				_pid.reset()
				# Check if there's another waypoint
				if current_wp + 1 < n_wp:
					current_wp += 1
					mode = 2  # pivot
				else:
					completed = True
					break
			continue  # skip force/yaw integration while stopping

		elif mode == 2:  # PIVOTING
			# Rotate in place to face next waypoint
			tx, ty = waypoints_xy[current_wp]
			heading_err = _heading_error_to_waypoint(x, y, heading, tx, ty)

			if abs(heading_err) < _HEADING_ACCEPT_DEG * (3.14159 / 180.0):
				# Heading aligned — start driving
				mode = 0
				continue

			# Apply opposing thrusts for in-place rotation
			f_n_total = m * g * cos_pitch
			f_trac_side = mu * f_n_total * 0.5
			pivot_f = _pivot_thrust(mu, m, g, cos_pitch)

			# Direction of turn
			sign = 1.0 if heading_err > 0 else -1.0
			f_left = -sign * pivot_f
			f_right = sign * pivot_f

			# Cap by traction
			f_left = _clamp(f_left, -f_trac_side, f_trac_side)
			f_right = _clamp(f_right, -f_trac_side, f_trac_side)

			m_diff = (f_right - f_left) * tw / 2.0
			alpha = m_diff / I_z

			# Limit yaw rate
			yaw_rate = _clamp(yaw_rate + alpha * dt, -_PIVOT_YAW_RATE_MAX, _PIVOT_YAW_RATE_MAX)
			heading = _normalise_angle(heading + yaw_rate * dt)

			# No forward motion during pivot
			speed = 0.0
			yaw_rate *= 0.95  # damping

			# Battery drain during pivot (power used by opposing thrusts)
			battery_energy_used_j += p_w * 0.3 * dt

			total_time += dt
			dt = _clamp(resolution_m / max(speed, 0.5), DT_MIN, DT_MAX)
			continue

		# ── DRIVE mode force calculations ──
		target_speed = _sample_target_speed_waypoint(dist_to_wp, p_w, crr, m, g)
		throttle, brake = _pid.update(speed, target_speed, dt)
		brake = min(brake, rover.max_brake_decel_mps2)

		# ── Battery drain ──
		battery_energy_used_j += p_w * throttle * dt
		if brake > 0:
			braking_events += 1

		f_n_total = m * g * cos_pitch

		# Per-side effective speeds
		v_left_eff = max(speed - yaw_rate * tw / 2.0, v_min_power_mps)
		v_right_eff = max(speed + yaw_rate * tw / 2.0, v_min_power_mps)

		f_power_left = p_side / v_left_eff
		f_power_right = p_side / v_right_eff
		f_trac_side = mu * f_n_total * 0.5

		f_max_left = min(f_power_left * throttle, f_torque_max_side, f_trac_side)
		f_max_right = min(f_power_right * throttle, f_torque_max_side, f_trac_side)

		f_grade = m * g * sin_pitch
		f_roll = crr * f_n_total

		if throttle > 0:
			f_desired_total = f_max_left + f_max_right
		elif brake > 0:
			f_desired_total = -(brake * m)
		else:
			f_desired_total = 0.0

		# Yaw control from heading error
		heading_err = _heading_error_to_waypoint(x, y, heading, tx, ty)
		yaw_cmd = _HEADING_K * heading_err
		yaw_error = yaw_cmd - yaw_rate
		m_desired = I_z * 2.0 * yaw_error
		m_resist = _skid_steer_resistive_moment(f_n_total, mu, tw, yaw_rate)
		m_diff_desired = m_desired - m_resist

		f_right = f_desired_total / 2.0 + m_diff_desired / tw
		f_left = f_desired_total / 2.0 - m_diff_desired / tw

		f_left = _clamp(f_left, -f_trac_side, f_max_left)
		f_right = _clamp(f_right, -f_trac_side, f_max_right)

		f_total_actual = f_left + f_right
		m_diff_actual = (f_right - f_left) * tw / 2.0
		m_net = m_diff_actual + m_resist

		f_net = f_total_actual - f_grade - f_roll
		a_long = f_net / m
		alpha = m_net / I_z

		if brake > 0 and a_long < 0:
			max_braking_decel = max(max_braking_decel, abs(a_long))

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

	# Battery stats
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
		"braking_events": braking_events,
		"max_braking_decel_mps2": float(max_braking_decel),
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


def _sample_target_speed_waypoint(
	dist_to_wp: float, p_w: float, crr: float, m: float, g: float,
) -> float:
	"""Target speed based on distance to waypoint.

	Slows down when approaching the waypoint for a smooth stop.
	"""
	f_roll_ref = max(crr * m * g, 1.0)
	full_speed = p_w / f_roll_ref
	if dist_to_wp > 10.0:
		return float(full_speed)
	# Linear ramp down over the last 10m
	return float(full_speed * max(0.3, dist_to_wp / 10.0))
