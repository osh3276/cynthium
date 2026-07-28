"""4-wheel skid-steer rover with simple brake model and stop-pivot-go navigation.

The chassis is a rigid rectangle with a wheel at each corner.  Steering is
by differential thrust between left and right sides.  Braking is modelled
as a direct deceleration (m/s²) — no motor back-EMF or Coulomb friction.

The rover drives toward each waypoint, brakes to a stop, pivots in place
to face the next waypoint, then drives again.
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
	_get_linear_angle_bin,
	_get_spice_angle_bin,
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


def _extract_xform(entry_data) -> Any | None:
	"""Extract the affine transform from a dict (meta) or pass through an Affine."""
	if entry_data is None:
		return None
	if isinstance(entry_data, dict):
		return entry_data.get("transform")
	return entry_data


def _heading_error_to_waypoint(
	x: float, y: float, heading: float, tx: float, ty: float,
) -> float:
	"""Signed heading error (rad) from current heading toward (tx, ty)."""
	return _normalise_angle(atan2(ty - y, tx - x) - heading)


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
	illumination_maps: dict[int, tuple[np.ndarray, Any]] | None = None,
	meteor_energy_maps: dict[int, tuple[np.ndarray, Any]] | None = None,
	meteor_number_maps: dict[int, tuple[np.ndarray, Any]] | None = None,
	start_angle_deg: int = 0,
	center_lat: float | None = None,
	center_lon: float | None = None,
	start_et: float | None = None,
	g_mps2: float,
	v0_mps: float = 0.0,
	v_min_power_mps: float = 0.05,
	max_steps: int = 500000,
	pause_durations: list[float] | None = None,
) -> dict[str, Any]:
	"""Simulate a 4-wheel skid-steer rover with simple brake model."""
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

	# Per-side torque limit (2 wheels per side)
	if motor_torque is not None:
		f_torque_max_side = 2.0 * motor_torque / wheel_r
	else:
		f_torque_max_side = float("inf")

	# ── Waypoint navigation setup ──
	n_wp = len(waypoints_xy)
	current_wp = 1
	mode = 0  # 0 = DRIVE, 1 = STOPPING, 2 = PIVOTING, 3 = PAUSE
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

	# ── Illumination (multi-angle support) ──
	_active_illum_map = illumination_map
	_active_illum_xform = illumination_transform
	_inv_illum = None
	if _active_illum_map is not None and _active_illum_xform is not None:
		_inv_illum = ~_active_illum_xform

	# Resolve the starting bin: use SPICE if geo params are available,
	# otherwise fall back to the linear model with the given start_angle_deg
	_use_spice = (
		center_lat is not None
		and center_lon is not None
		and start_et is not None
	)
	if _use_spice:
		_last_illum_bin = _get_spice_angle_bin(center_lat, center_lon, start_et, 0.0)
	else:
		_last_illum_bin = start_angle_deg

	# Load the starting map from the multi-angle dict (if provided)
	_illum_map_count = 0
	if illumination_maps is not None:
		_illum_map_count = len(illumination_maps)
		entry = illumination_maps.get(_last_illum_bin)
		if entry is not None:
			_active_illum_map, _raw_xform = entry
			_active_illum_xform = _extract_xform(_raw_xform)
			if _active_illum_xform is not None:
				_inv_illum = ~_active_illum_xform

	print(f"[dbg] illum_maps={'None' if illumination_maps is None else f'{_illum_map_count} maps'}, "
		  f"use_spice={_use_spice}, start_bin={_last_illum_bin}, "
		  f"inv_illum={'set' if _inv_illum is not None else 'None'}, "
		  f"active_map_shape={_active_illum_map.shape if _active_illum_map is not None else 'None'}")

	# ── Meteor (multi-angle support) ──
	_active_meteor_map = None
	_active_meteor_xform = None
	_inv_meteor = None
	if _use_spice:
		_last_meteor_bin = _get_spice_angle_bin(center_lat, center_lon, start_et, 0.0)
	else:
		_last_meteor_bin = start_angle_deg
	if meteor_energy_maps is not None:
		entry = meteor_energy_maps.get(_last_meteor_bin)
		if entry is not None:
			_active_meteor_map, _raw_xform = entry
			_active_meteor_xform = _extract_xform(_raw_xform)
			if _active_meteor_xform is not None:
				_inv_meteor = ~_active_meteor_xform

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

	# Check sun angle every 60 sim-seconds to avoid excessive SPICE calls.
	_next_bin_check = 0.0
	BIN_CHECK_INTERVAL = 60.0

	for step in range(max_steps):
		# ── Sun-angle bin check (every 60 sim-seconds) ──
		_do_check = total_time >= _next_bin_check and (
			illumination_maps is not None or meteor_energy_maps is not None
		)
		if _do_check:
			_next_bin_check = total_time + BIN_CHECK_INTERVAL
			_bin = _get_linear_angle_bin(start_angle_deg, total_time)

			# Illumination map swap
			if illumination_maps is not None and _bin != _last_illum_bin:
				if _use_spice:
					_spice_bin = _get_spice_angle_bin(center_lat, center_lon, start_et, total_time)
					if _spice_bin != _last_illum_bin:
						_last_illum_bin = _spice_bin
						_entry = illumination_maps.get(_last_illum_bin)
						if _entry is not None:
							_active_illum_map, _raw_xform = _entry
							_active_illum_xform = _extract_xform(_raw_xform)
							if _active_illum_xform is not None:
								_inv_illum = ~_active_illum_xform
						print(f"[dbg] swapped illum bin {_last_illum_bin} at t={total_time:.0f}s")
				else:
					_last_illum_bin = _bin
					_entry = illumination_maps.get(_last_illum_bin)
					if _entry is not None:
						_active_illum_map, _raw_xform = _entry
						_active_illum_xform = _extract_xform(_raw_xform)
						if _active_illum_xform is not None:
							_inv_illum = ~_active_illum_xform

			# Meteor map swap
			if meteor_energy_maps is not None and _bin != _last_meteor_bin:
				if _use_spice:
					_spice_bin = _get_spice_angle_bin(center_lat, center_lon, start_et, total_time)
					if _spice_bin != _last_meteor_bin:
						_last_meteor_bin = _spice_bin
						_entry = meteor_energy_maps.get(_last_meteor_bin)
						if _entry is not None:
							_active_meteor_map, _raw_xform = _entry
							_active_meteor_xform = _extract_xform(_raw_xform)
							if _active_meteor_xform is not None:
								_inv_meteor = ~_active_meteor_xform
				else:
					_last_meteor_bin = _bin
					_entry = meteor_energy_maps.get(_last_meteor_bin)
					if _entry is not None:
						_active_meteor_map, _raw_xform = _entry
						_active_meteor_xform = _extract_xform(_raw_xform)
						if _active_meteor_xform is not None:
							_inv_meteor = ~_active_meteor_xform

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

		elif mode == 1:  # STOPPING — apply brake
			yaw_cmd = 0.0
			if speed > 0.0:
				speed = max(0.0, speed - rover.max_brake_decel_mps2 * dt)
			if speed <= 0.0:
				speed = 0.0
				_pid.reset()
				# Check if this waypoint has a pause configured
				wp_idx = current_wp - 1  # 0-based index in pause_durations
				wp_pause = (pause_durations[wp_idx] if pause_durations
				            and wp_idx < len(pause_durations) else 0.0)
				if wp_pause > 0:
					_pause_timer = wp_pause
					mode = 3  # PAUSE
				elif current_wp + 1 < n_wp:
					current_wp += 1
					mode = 2
				else:
					completed = True
					break
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
			# Use larger dt during pause (up to 1 s) to avoid exhausting
			# max_steps on long pauses.  The rover is stationary, so the
			# physics does not need micro-stepping.
			_pause_step = min(1.0, _pause_timer)
			_pause_timer -= _pause_step
			total_time += _pause_step
			battery_energy_used_j += rover.idle_drain_w * _pause_step

			# Accumulate solar energy during the pause (rover is stationary
			# but the sun still shines)
			if _inv_illum is not None:
				col, row = _inv_illum * (float(x), float(y))
				ci, ri = int(round(col)), int(round(row))
				if 0 <= ri < _active_illum_map.shape[0] and 0 <= ci < _active_illum_map.shape[1]:
					illum = float(_active_illum_map[ri, ci])
					if np.isfinite(illum):
						energy_j_per_m2 += illum * _pause_step
					else:
						if total_time < 5.0 or int(total_time) % 10000 == 0:
							print(f"[dbg] pause illum not finite at ({x:.1f},{y:.1f}) pix=({ci},{ri}) val={illum}")
				else:
					if total_time < 5.0 or int(total_time) % 10000 == 0:
						print(f"[dbg] pause pix out of bounds ({ci},{ri}) vs {_active_illum_map.shape}")
			else:
				if total_time < 5.0 or int(total_time) % 10000 == 0:
					print(f"[dbg] pause _inv_illum is None, t={total_time:.0f}")

			if _pause_timer <= 0.0:
				if current_wp + 1 < n_wp:
					current_wp += 1
					mode = 2
				else:
					completed = True
					break
			dt = DT_MIN
			continue

		# ═══════════════════════════════════════════════════════════════
		# DRIVE mode — motor drive + PID brake
		# ═══════════════════════════════════════════════════════════════

		target_speed = _sample_target_speed(dist_to_wp, rover)
		throttle, brake_decel = _pid.update(speed, target_speed, dt)

		# ── Wheel speeds per side (accounting for yaw) ──
		v_left = speed - yaw_rate * tw / 2.0
		v_right = speed + yaw_rate * tw / 2.0

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
		f_left = f_drive_left
		f_right = f_drive_right
		# Clamp net to traction limits
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

		# Brake force from PID (applied when overspeed)
		f_brake = brake_decel * m

		f_net = f_total_actual - f_grade - f_roll - f_brake
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
		if _inv_illum is not None:
			col, row = _inv_illum * (float(x), float(y))
			ci, ri = int(round(col)), int(round(row))
			if 0 <= ri < _active_illum_map.shape[0] and 0 <= ci < _active_illum_map.shape[1]:
				illum = float(_active_illum_map[ri, ci])
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
