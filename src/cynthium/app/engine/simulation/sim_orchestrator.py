"""Orchestrates path sampling, physics simulation, and result assembly."""

import threading
from typing import Any

import numpy as np
from scipy.ndimage import map_coordinates

from cynthium.app.config import LUNAR_GRAVITY
from cynthium.app.engine.simulation.path_sampling import (
	BICUBIC_RESOLUTION_M,
	get_pixel_resolution_m,
	sample_path_elevations,
)
from cynthium.app.engine.simulation.rover_4wd import simulate_rover_4wd
from cynthium.app.engine.simulation.rover_settings import RoverSettings


def path_cross_slopes_deg(pts_xyz: np.ndarray, elevation_map: np.ndarray, transform) -> np.ndarray:
	"""Side tilt (roll, deg) of the rover on each segment of a sampled path.

	The elevation gradient (central differences, as for the sites' slope
	rasters) is interpolated bilinearly at each segment's midpoint; for a
	heading u and gradient G the roll is asin(|G . n| / sqrt(1 + |G|^2)),
	with n perpendicular to u.  Returns one value per segment.
	"""
	n_seg = len(pts_xyz) - 1
	if n_seg < 1 or elevation_map is None or min(elevation_map.shape) < 2:
		return np.zeros(max(n_seg, 0))
	g_row, g_col = np.gradient(np.asarray(elevation_map, dtype=np.float64))
	gx_map = g_col / float(transform.a)  # dz/dx (m/m)
	gy_map = g_row / float(transform.e)  # dz/dy (m/m); rows run along -y
	inv = ~transform
	mid = 0.5 * (pts_xyz[:-1, :2] + pts_xyz[1:, :2])
	cols = inv.a * mid[:, 0] + inv.b * mid[:, 1] + inv.c
	rows = inv.d * mid[:, 0] + inv.e * mid[:, 1] + inv.f
	coords = [rows - 0.5, cols - 0.5]
	gx = map_coordinates(gx_map, coords, order=1, mode="nearest")
	gy = map_coordinates(gy_map, coords, order=1, mode="nearest")
	d = np.diff(pts_xyz[:, :2], axis=0)
	length = np.hypot(d[:, 0], d[:, 1])
	with np.errstate(invalid="ignore", divide="ignore"):
		ux, uy = d[:, 0] / length, d[:, 1] / length
		lateral = np.abs(-gx * uy + gy * ux)
		roll = np.degrees(np.arcsin(np.clip(lateral / np.sqrt(1.0 + gx * gx + gy * gy), 0.0, 1.0)))
	roll[~np.isfinite(roll) | (length < 1e-9)] = 0.0
	return roll


def compute_traversal_dynamics(
	*,
	waypoints_xyz: np.ndarray,
	elevation_map: np.ndarray | None,
	transform,
	illumination_map: np.ndarray | None = None,
	illumination_transform=None,
	illumination_maps: dict[int, tuple[np.ndarray, Any]] | None = None,
	meteor_energy_maps: dict[int, tuple[np.ndarray, Any]] | None = None,
	meteor_number_maps: dict[int, tuple[np.ndarray, Any]] | None = None,
	start_angle_deg: int = 0,
	center_lat: float | None = None,
	center_lon: float | None = None,
	start_et: float | None = None,
	rover: RoverSettings,
	use_bicubic: bool = False,
	pause_durations: list[float] | None = None,
	cancel_event: threading.Event | None = None,
) -> dict[str, Any]:
	"""Run the physics simulation once and return results."""

	mu = float(rover.wheel_friction_coeff)
	crr = float(rover.rolling_resistance_coeff)
	max_climbable = float(np.degrees(np.arctan(max(0.001, mu - crr))))
	cross_limit = float(rover.cross_slope_limit_deg)

	if waypoints_xyz.shape[0] < 2:
		return {
			"average_velocity_mps": 0.0,
			"min_velocity_mps": 0.0,
			"max_velocity_mps": 0.0,
			"traversal_time_s": 0.0,
			"solar_energy_per_m2_j": 0.0,
			"avg_solar_illumination_w_per_m2": 0.0,
			"max_climbable_slope_deg": max_climbable,
			"cross_slope_limit_deg": cross_limit,
			"max_cross_slope_deg": 0.0,
			"traverse_feasible": 1.0,
			"failure_x": None,
			"failure_y": None,
			"failure_reason": None,
			"simulation_resolution_m": 0.0,
			"rollover_occurred": False,
			"max_lateral_accel_mps2": 0.0,
			"braking_events": 0,
			"max_braking_decel_mps2": 0.0,
			"battery_energy_used_j": 0.0,
			"battery_remaining_pct": 100.0,
			"battery_capacity_wh": 0.0,
		}

	if elevation_map is not None and transform is not None:
		pts = sample_path_elevations(waypoints_xyz, elevation_map, transform, use_bicubic=use_bicubic)
		resolution_m = float(BICUBIC_RESOLUTION_M) if use_bicubic else float(get_pixel_resolution_m(transform))
		cross_slopes = path_cross_slopes_deg(pts, elevation_map, transform)
	else:
		pts = waypoints_xyz.astype(np.float64, copy=False)
		resolution_m = 0.0
		cross_slopes = None

	physics = simulate_rover_4wd(
			pts_xyz=pts,
			waypoints_xy=waypoints_xyz[:, :2],
			rover=rover,
			wheel_friction_coeff=mu,
			power_w=float(rover.power_w),
			illumination_map=illumination_map,
			illumination_transform=illumination_transform,
			illumination_maps=illumination_maps,
			meteor_energy_maps=meteor_energy_maps,
			meteor_number_maps=meteor_number_maps,
			start_angle_deg=start_angle_deg,
			center_lat=center_lat,
			center_lon=center_lon,
			start_et=start_et,
			g_mps2=float(LUNAR_GRAVITY),
			v0_mps=0.0,
			v_min_power_mps=0.001,
			pause_durations=pause_durations,
			cancel_event=cancel_event,
			cross_slope_deg=cross_slopes,
			max_cross_slope_deg=cross_limit,
		)

	return {
		"average_velocity_mps": float(physics["average_velocity_mps"]),
		"min_velocity_mps": float(physics["min_velocity_mps"]),
		"max_velocity_mps": float(physics["max_velocity_mps"]),
		"traversal_time_s": float(physics["traversal_time_s"]),
		"solar_energy_per_m2_j": float(physics["solar_energy_per_m2_j"]),
		"avg_solar_illumination_w_per_m2": float(physics["avg_solar_illumination_w_per_m2"]),
		"max_climbable_slope_deg": max_climbable,
		"cross_slope_limit_deg": cross_limit,
		"max_cross_slope_deg": float(physics.get("max_cross_slope_deg", 0.0)),
		"traverse_feasible": float(physics["traverse_feasible"]),
		"failure_x": physics.get("failure_x"),
		"failure_y": physics.get("failure_y"),
		"failure_reason": physics.get("failure_reason"),
		"simulation_resolution_m": float(resolution_m),
		"rollover_occurred": bool(physics.get("rollover_occurred", False)),
		"max_lateral_accel_mps2": float(physics.get("max_lateral_accel_mps2", 0.0)),
		"braking_events": int(physics.get("braking_events", 0)),
		"max_braking_decel_mps2": float(physics.get("max_braking_decel_mps2", 0.0)),
		"battery_energy_used_j": float(physics.get("battery_energy_used_j", 0.0)),
		"battery_remaining_pct": float(physics.get("battery_remaining_pct", 100.0)),
		"battery_capacity_wh": float(physics.get("battery_capacity_wh", 0.0)),
	}
