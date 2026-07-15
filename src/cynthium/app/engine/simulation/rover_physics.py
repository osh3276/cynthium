"""Unicycle 2D vehicle dynamics — the rover as a single driven+steered wheel.

The vehicle moves in 2D (x, y, heading) on the terrain surface with
power-limited drive, friction-circle steering limits, and grade resistance.
The rover stops at sharp turns (waypoints) for realistic traverse behaviour.
"""

from __future__ import annotations

from math import cos, sin, atan2, sqrt, pi
from typing import Any

import numpy as np

from cynthium.app.engine.simulation.rover_settings import RoverSettings


SPEED_EPS = 0.01
MAX_STEPS = 500_000
DT_MIN = 0.02
DT_MAX = 0.1
CORNER_ANGLE_THRESHOLD_DEG = 5.0
STOP_APPROACH_DIST_M = 5.0


def _clamp(val: float, lo: float, hi: float) -> float:
	return max(lo, min(hi, val))


def _normalise_angle(a: float) -> float:
	while a > pi:
		a -= 2.0 * pi
	while a < -pi:
		a += 2.0 * pi
	return a


# ── Main simulation ────────────────────────────────────────────────────────────


def simulate_rover_over_path(
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
	if pts_xyz.shape[0] < 2:
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
		dx = path_xy[i, 0] - path_xy[i-1, 0]
		dy = path_xy[i, 1] - path_xy[i-1, 1]
		cum_dists[i] = cum_dists[i-1] + sqrt(dx*dx + dy*dy)
	path_total_len = float(cum_dists[-1])

	# ── Detect corners and build target speed profile ──
	corner_indices = _detect_corners(path_xy)
	target_speeds = _compute_target_speeds(path_xy, cum_dists, corner_indices, rover, p_w, crr, m, g)

	# Initial heading
	heading = 0.0
	if len(pts_xyz) > 1:
		dx = pts_xyz[1, 0] - pts_xyz[0, 0]
		dy = pts_xyz[1, 1] - pts_xyz[0, 1]
		if abs(dx) > 1e-9 or abs(dy) > 1e-9:
			heading = atan2(dy, dx)

	x = float(pts_xyz[0, 0])
	y = float(pts_xyz[0, 1])
	speed = float(v0_mps)
	braking_events = 0

	inv_illum = None
	if illumination_map is not None and illumination_transform is not None:
		inv_illum = ~illumination_transform

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

	lookahead = max(path_total_len * 0.1, 2.0)
	dt = _clamp(resolution_m / max(v0_mps, 1.0), DT_MIN, DT_MAX) if v0_mps > 0 else DT_MIN

	# Sliding window: the rover moves forward along the path,
	# so we only search a few segments around the last known one.
	win_size = 20
	last_seg = 0

	for step in range(max_steps):
		# ── 1. Nearest point on path (sliding window) ──
		best_d = float("inf")
		best_idx, best_t, best_cum = 0, 0.0, 0.0
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
				t = _clamp(((x - ax) * dx + (y - ay) * dy) / seg_len_sq, 0.0, 1.0)
				cx, cy = ax + t * dx, ay + t * dy
			d_sq = (x - cx) ** 2 + (y - cy) ** 2
			if d_sq < best_d:
				best_d = d_sq
				best_idx = i
				best_t = t
				best_cum = cum_dists[i] + sqrt(dx*dx + dy*dy) * t if seg_len_sq > 1e-12 else cum_dists[i]
		last_seg = best_idx
		cum_dist = best_cum

		target_speed = _sample_target_speed(cum_dist, target_speeds, path_total_len)
		path_end = path_xy[-1]

		# ── 2. Terrain slope ──
		pitch = _sample_pitch(x, y, pts_xyz)

		# ── 3. Pure pursuit (sliding window) ──
		yaw_cmd = _pure_pursuit_yaw_rate(x, y, heading, speed, path_xy, lookahead, last_seg, win_size)

		# ── 4. Speed control ──
		throttle, brake = _speed_controller(speed, target_speed, m, p_w, v_min_power_mps, g, crr, pitch, mu)
		if brake > 0:
			braking_events += 1

		# ── 5. Forces ──
		f_n = m * g * abs(cos(pitch))
		f_trac_max = mu * f_n
		v_eff = max(speed, v_min_power_mps)
		f_power = p_w / v_eff
		f_drive = min(f_power * throttle, f_trac_max)
		f_grade = m * g * sin(pitch)
		f_roll = crr * f_n
		f_net = f_drive - f_grade - f_roll - brake * m
		a_long = f_net / m

		# ── 6. Steering limit ──
		max_lat_accel = mu * g * abs(cos(pitch))
		if speed > SPEED_EPS:
			yaw_rate_max = max_lat_accel / speed
		else:
			yaw_rate_max = 0.5
		yaw_rate = _clamp(yaw_cmd, -yaw_rate_max, yaw_rate_max)

		# ── 7. Integrate ──
		speed = max(0.0, speed + a_long * dt)
		heading = _normalise_angle(heading + yaw_rate * dt)
		x += speed * cos(heading) * dt
		y += speed * sin(heading) * dt
		step_dist = sqrt((x - prev_pos[0]) ** 2 + (y - prev_pos[1]) ** 2)
		total_dist += step_dist
		prev_pos = np.array([x, y])

		# ── 8. Termination ──
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

		# ── 9. Energy ──
		if inv_illum is not None:
			col, row = inv_illum * (float(x), float(y))
			ci, ri = int(round(col)), int(round(row))
			if 0 <= ri < illumination_map.shape[0] and 0 <= ci < illumination_map.shape[1]:
				illum = float(illumination_map[ri, ci])
				if np.isfinite(illum):
					energy_j_per_m2 += illum * dt

		total_time += dt
		min_v = min(min_v, speed) if speed > 0 else min_v
		max_v = max(max_v, speed)
		dt = _clamp(resolution_m / max(speed, 0.3), DT_MIN, DT_MAX)

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
		"failure_x": float(x) if not completed else None,
		"failure_y": float(y) if not completed else None,
		"rollover_occurred": False,
		"max_lateral_accel_mps2": 0.0,
		"braking_events": braking_events,
		"max_braking_decel_mps2": 0.0,
	}


# ── Speed controller ──────────────────────────────────────────────────────────


def _speed_controller(
	speed: float, target: float, m: float, p_w: float, v_min: float,
	g: float, crr: float, pitch: float, mu: float,
) -> tuple[float, float]:
	if speed <= target:
		return 1.0, 0.0
	brake_needed = (speed - target) * 0.5 + 0.5
	brake_needed = min(brake_needed, 2.0)
	return 0.0, brake_needed


# ── Path helpers ──────────────────────────────────────────────────────────────


def _detect_corners(path_xy: np.ndarray) -> list[int]:
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
	path_xy: np.ndarray, cum_dists: np.ndarray,
	corner_indices: list[int],
	rover: RoverSettings, p_w: float, crr: float, m: float, g: float,
) -> np.ndarray:
	n = len(path_xy)
	full_speed = p_w / max(crr * m * g, 1.0)
	targets = np.full(n, full_speed)

	for ci in corner_indices:
		targets[ci] = 0.0
		d_at = cum_dists[ci]
		for j in range(ci - 1, -1, -1):
			d = d_at - cum_dists[j]
			if d > STOP_APPROACH_DIST_M:
				break
			targets[j] = min(targets[j], full_speed * d / STOP_APPROACH_DIST_M)
		for j in range(ci + 1, n):
			d = cum_dists[j] - d_at
			if d > STOP_APPROACH_DIST_M:
				break
			targets[j] = min(targets[j], full_speed * d / STOP_APPROACH_DIST_M)

	targets = np.maximum(targets, 0.3)
	return np.column_stack([cum_dists, targets])


def _sample_target_speed(cum_dist: float, speed_table: np.ndarray, path_total_len: float) -> float:
	if len(speed_table) == 0:
		return 1.0
	d = _clamp(cum_dist, speed_table[0, 0], speed_table[-1, 0])
	return float(np.interp(d, speed_table[:, 0], speed_table[:, 1]))


def _pure_pursuit_yaw_rate(
	x: float, y: float, heading: float, speed: float,
	path_xy: np.ndarray, lookahead: float, last_seg: int, win_size: int,
) -> float:
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

	tx, ty = best_lx - x, best_ly - y
	target_angle = atan2(ty, tx)
	delta = _normalise_angle(target_angle - heading)
	yaw = 2.0 * speed * sin(delta) / max(lookahead, 0.1)
	return _clamp(yaw, -1.5, 1.5)


def _sample_pitch(x: float, y: float, pts_xyz: np.ndarray) -> float:
	if len(pts_xyz) < 2:
		return 0.0
	# Quick nearest-point using only the first and last few segments
	# (the vehicle should be near the path)
	best_d = float("inf")
	best_i = 0
	search_range = min(len(pts_xyz) - 1, 200)
	for i in range(search_range):
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
	dhoriz = sqrt(
		(pts_xyz[i + 1, 0] - pts_xyz[i, 0]) ** 2
		+ (pts_xyz[i + 1, 1] - pts_xyz[i, 1]) ** 2
	)
	if dhoriz > 0.01:
		return atan2(dz, dhoriz)
	return 0.0


def _estimate_resolution(pts_xyz: np.ndarray) -> float:
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
		"failure_x": None,
		"failure_y": None,
		"rollover_occurred": False,
		"max_lateral_accel_mps2": 0.0,
		"braking_events": 0,
		"max_braking_decel_mps2": 0.0,
	}
