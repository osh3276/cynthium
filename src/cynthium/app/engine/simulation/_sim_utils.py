"""Shared constants and helpers for rover simulations."""

from __future__ import annotations

from math import atan2, floor, pi, sqrt
from typing import Any

import numpy as np

from cynthium.app.engine.simulation.rover_settings import RoverSettings


SPEED_EPS = 0.01
MAX_STEPS = 500_000
DT_MIN = 0.02
DT_MAX = 0.1
CORNER_ANGLE_THRESHOLD_DEG = 5.0
STOP_APPROACH_DIST_M = 5.0


def _round_azimuth_to_nearest_12(azimuth_deg: float) -> int:
	"""Round sun azimuth to nearest 12-deg bin (0, 12, 24, ... 348)."""
	az = float(azimuth_deg) % 360.0
	n = floor((az + 6.0) / 12.0) * 12
	return 0 if n == 360 else n


def _get_linear_angle_bin(start_angle_deg: int, elapsed_s: float) -> int:
	"""Return 12-deg bin using linear approximation (no SPICE needed)."""
	from cynthium.app.config import LUNAR_DAY_S
	angle_offset = (elapsed_s / LUNAR_DAY_S) * 360.0
	current = (start_angle_deg + angle_offset) % 360.0
	return _round_azimuth_to_nearest_12(current)


def _get_spice_angle_bin(
	center_lat: float,
	center_lon: float,
	start_et: float,
	elapsed_s: float,
) -> int:
	"""Return 12-deg bin via SPICE at start_et + elapsed_s."""
	from cynthium.app.engine.illumination.sun_position import (
		_sun_azimuth_at_et,
		round_azimuth_to_nearest_12,
	)
	az = _sun_azimuth_at_et(center_lat, center_lon, start_et + elapsed_s)
	return round_azimuth_to_nearest_12(az)


def _clamp(val: float, lo: float, hi: float) -> float:
	return max(lo, min(hi, val))


def _normalise_angle(a: float) -> float:
	while a > pi:
		a -= 2.0 * pi
	while a < -pi:
		a += 2.0 * pi
	return a


class SpeedPIDController:
	"""PID speed controller: maps error to throttle (0-1) or brake decel (0-2 m/s^2)."""

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
		"""Reset integral/derivative state (e.g. after corner stop)."""
		self._integral = 0.0
		self._prev_error = 0.0

	def update(self, speed: float, target: float, dt: float) -> tuple[float, float]:
		"""Compute (throttle, brake_decel) for one timestep.

		Params: speed (m/s), target (m/s), dt (s).
		Returns: throttle 0-1, brake_decel (m/s^2).
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
	"""Build (cum_dist, target_speed) table with linear slowdowns at corners."""
	n = len(path_xy)
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


def _sample_pitch(
	x: float, y: float, pts_xyz: np.ndarray, hint_idx: int | None = None
) -> float:
	"""Estimate terrain pitch (rad) under vehicle from nearest path point (uphill = positive)."""
	if len(pts_xyz) < 2:
		return 0.0

	n_seg = len(pts_xyz) - 1

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
		"battery_energy_used_j": 0.0,
		"battery_remaining_pct": 100.0,
		"battery_capacity_wh": 0.0,
	}
