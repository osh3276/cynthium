"""2D vehicle dynamics — building up from a unicycle to multi-wheel.

This module progressively models the rover as a body moving in 2D (x, y, heading)
on a 3D terrain surface.  We start with the simplest model: a unicycle (the
whole rover is a single driven+steered wheel) and will later add more wheels.

The 2D models are separate from the 1D point-mass model in ``rover_physics.py``
so both can coexist.
"""

from __future__ import annotations

from math import cos, sin, atan2, sqrt, pi
from typing import Any

import numpy as np

from cynthium.app.engine.simulation.rover_settings import RoverSettings


# ── Constants ──────────────────────────────────────────────────────────────────

SPEED_EPS = 0.01
MAX_STEPS = 500_000
DT_MIN = 0.02
DT_MAX = 0.1


# ── Helpers ────────────────────────────────────────────────────────────────────


def _clamp(val: float, lo: float, hi: float) -> float:
	return max(lo, min(hi, val))


def _normalise_angle(a: float) -> float:
	while a > pi:
		a -= 2.0 * pi
	while a < -pi:
		a += 2.0 * pi
	return a


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
) -> dict[str, Any]:
	"""Simulate the rover as a unicycle (single driven+steered wheel).

	The vehicle moves in 2D with state (x, y, heading, speed).  A pure-pursuit
	controller steers toward the path, and the power-limited drivetrain
	accelerates/brakes to follow a target speed.

	Returns the same dict format as ``simulate_rover_over_path()``.
	"""
	if pts_xyz.shape[0] < 2:
		return _empty_result()

	m = float(rover.mass_kg)
	mu = float(wheel_friction_coeff)
	p_w = float(power_w)
	g = float(g_mps2)
	crr = float(rover.rolling_resistance_coeff)

	path_xy = pts_xyz[:, :2].copy()
	resolution_m = _estimate_resolution(pts_xyz)

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
	completed = False  # whether the vehicle reached within 3m of the path end

	# Path geometry
	path_diffs = np.diff(path_xy, axis=0)
	path_total_len = float(np.sum(np.linalg.norm(path_diffs, axis=1)))
	lookahead = max(path_total_len * 0.1, 2.0)

	dt = _clamp(resolution_m / max(v0_mps, 1.0), DT_MIN, DT_MAX) if v0_mps > 0 else DT_MIN

	for step in range(MAX_STEPS):
		# ── 1. Terrain slope under the vehicle ──
		pitch = _sample_pitch(x, y, pts_xyz)

		# ── 2. Path following (pure pursuit) ──
		yaw_cmd = _pure_pursuit_yaw_rate(x, y, heading, speed, path_xy, lookahead)

		# ── 3. Speed control ──
		# Full throttle for now — later replaced by PID speed controller
		throttle = 1.0

		# ── 4. Forces ──
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
		f_net = f_drive - f_grade - f_roll
		a_long = f_net / m

		# ── 5. Steering limit (friction circle) ──
		# Max lateral acceleration from friction
		max_lat_accel = mu * g * abs(cos(pitch))
		# At speed v, max yaw rate is limited by lateral friction:
		# a_lat = v * yaw_rate → yaw_rate_max = max_lat_accel / v
		if speed > SPEED_EPS:
			yaw_rate_max = max_lat_accel / speed
		else:
			yaw_rate_max = 0.5  # low-speed steering limit (rad/s)
		yaw_rate = _clamp(yaw_cmd, -yaw_rate_max, yaw_rate_max)

		# ── 6. Integrate (semi-implicit Euler) ──
		speed = max(0.0, speed + a_long * dt)
		heading = _normalise_angle(heading + yaw_rate * dt)

		vx = speed * cos(heading)
		vy = speed * sin(heading)
		x += vx * dt
		y += vy * dt

		step_dist = sqrt((x - prev_pos[0]) ** 2 + (y - prev_pos[1]) ** 2)
		total_dist += step_dist
		prev_pos = np.array([x, y])

		# ── 7. Termination checks ──
		path_end = path_xy[-1]
		if sqrt((x - path_end[0]) ** 2 + (y - path_end[1]) ** 2) < 3.0:
			completed = True
			break

		if step_dist < 0.0001:
			stagnation += 1
			if stagnation > 5000:
				break
		else:
			stagnation = 0

		# ── 8. Energy ──
		if inv_illum is not None:
			col, row = inv_illum * (float(x), float(y))
			ci, ri = int(round(col)), int(round(row))
			if 0 <= ri < illumination_map.shape[0] and 0 <= ci < illumination_map.shape[1]:
				illum = float(illumination_map[ri, ci])
				if np.isfinite(illum):
					energy_j_per_m2 += illum * dt

		# ── 9. Stats ──
		total_time += dt
		min_v = min(min_v, speed) if speed > 0 else min_v
		max_v = max(max_v, speed)

		# Adaptive dt
		dt = _clamp(resolution_m / max(speed, 0.5), DT_MIN, DT_MAX)

	# ── Assemble result ──
	if total_time <= 0:
		avg_v, avg_illum = 0.0, 0.0
	else:
		avg_v = total_dist / total_time
		avg_illum = energy_j_per_m2 / total_time

	return {
		"traverse_feasible": 1.0 if completed else 0.0,
		"traversal_time_s": float(total_time) if completed else float("inf"),
		"average_velocity_mps": float(avg_v),
		"min_velocity_mps": float(min_v) if min_v != float("inf") else 0.0,
		"max_velocity_mps": float(max_v),
		"solar_energy_per_m2_j": float(energy_j_per_m2),
		"avg_solar_illumination_w_per_m2": float(avg_illum),
	}


# ── Pure pursuit path following ────────────────────────────────────────────────


def _pure_pursuit_yaw_rate(
	x: float, y: float, heading: float, speed: float,
	path_xy: np.ndarray, lookahead: float,
) -> float:
	"""Compute desired yaw rate (rad/s) to follow a path via pure pursuit."""
	if speed < SPEED_EPS or len(path_xy) < 2:
		return 0.0

	# Find look-ahead point on path
	best_err = float("inf")
	best_lx, best_ly = path_xy[-1]

	for i in range(len(path_xy) - 1):
		ax, ay = path_xy[i]
		bx, by = path_xy[i + 1]
		seg_len = sqrt((bx - ax) ** 2 + (by - ay) ** 2)
		if seg_len < 1e-9:
			continue
		n = max(2, int(seg_len / 1.0))
		for j in range(n):
			t = j / n
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


# ── Terrain helpers ────────────────────────────────────────────────────────────


def _sample_pitch(x: float, y: float, pts_xyz: np.ndarray) -> float:
	"""Estimate terrain pitch (rad) under the vehicle from the nearest path point.

	Positive pitch = uphill in the direction of travel.
	"""
	if len(pts_xyz) < 2:
		return 0.0

	# Find closest point on path
	best_d = float("inf")
	best_i = 0
	for i in range(len(pts_xyz) - 1):
		ax, ay = pts_xyz[i, :2]
		bx, by = pts_xyz[i + 1, :2]
		dx, dy = bx - ax, by - ay
		seg_len_sq = dx * dx + dy * dy
		if seg_len_sq < 1e-12:
			cx, cy = ax, ay
		else:
			t = _clamp(((x - ax) * dx + (y - ay) * dy) / seg_len_sq, 0.0, 1.0)
			cx, cy = ax + t * dx, ay + t * dy
		d_sq = (x - cx) ** 2 + (y - cy) ** 2
		if d_sq < best_d:
			best_d = d_sq
			best_i = i

	i = min(best_i, len(pts_xyz) - 2)
	dz = pts_xyz[i + 1, 2] - pts_xyz[i, 2]
	dx = sqrt(
		(pts_xyz[i + 1, 0] - pts_xyz[i, 0]) ** 2
		+ (pts_xyz[i + 1, 1] - pts_xyz[i, 1]) ** 2
	)
	if dx > 0.01:
		return atan2(dz, dx)
	return 0.0


def _estimate_resolution(pts_xyz: np.ndarray) -> float:
	"""Median segment length along the path (m)."""
	if pts_xyz.shape[0] < 2:
		return 5.0
	diffs = np.diff(pts_xyz[:, :2], axis=0)
	lengths = np.linalg.norm(diffs, axis=1)
	valid = lengths[lengths > 1e-9]
	return float(np.median(valid)) if len(valid) > 0 else 5.0




def _empty_result() -> dict[str, Any]:
	return {
		"traverse_feasible": 1.0,
		"traversal_time_s": 0.0,
		"average_velocity_mps": 0.0,
		"min_velocity_mps": 0.0,
		"max_velocity_mps": 0.0,
		"solar_energy_per_m2_j": 0.0,
		"avg_solar_illumination_w_per_m2": 0.0,
	}
