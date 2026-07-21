"""Orchestrates path sampling, physics simulation, and result assembly."""

from typing import Any

import numpy as np

from cynthium.app.config import LUNAR_GRAVITY
from cynthium.app.engine.simulation.path_sampling import (
	BICUBIC_RESOLUTION_M,
	get_pixel_resolution_m,
	sample_path_elevations,
)
from cynthium.app.engine.simulation.rover_physics import simulate_rover_over_path
from cynthium.app.engine.simulation.rover_settings import RoverSettings


def compute_traversal_dynamics(
	*,
	waypoints_xyz: np.ndarray,
	elevation_map: np.ndarray | None,
	transform,
	illumination_map: np.ndarray | None = None,
	illumination_transform=None,
	rover: RoverSettings,
	use_bicubic: bool = False,
) -> dict[str, Any]:
	"""Run the physics simulation once and return results."""

	mu = float(rover.wheel_friction_coeff)
	crr = float(rover.rolling_resistance_coeff)
	max_climbable = float(np.degrees(np.arctan(max(0.001, mu - crr))))

	if waypoints_xyz.shape[0] < 2:
		return {
			"average_velocity_mps": 0.0,
			"min_velocity_mps": 0.0,
			"max_velocity_mps": 0.0,
			"traversal_time_s": 0.0,
			"solar_energy_per_m2_j": 0.0,
			"avg_solar_illumination_w_per_m2": 0.0,
			"max_climbable_slope_deg": max_climbable,
			"traverse_feasible": 1.0,
			"failure_x": None,
			"failure_y": None,
			"failure_reason": None,
			"simulation_resolution_m": 0.0,
			"rollover_occurred": False,
			"max_lateral_accel_mps2": 0.0,
			"braking_events": 0,
			"max_braking_decel_mps2": 0.0,
		}

	if elevation_map is not None and transform is not None:
		pts = sample_path_elevations(waypoints_xyz, elevation_map, transform, use_bicubic=use_bicubic)
		resolution_m = float(BICUBIC_RESOLUTION_M) if use_bicubic else float(get_pixel_resolution_m(transform))
	else:
		pts = waypoints_xyz.astype(np.float64, copy=False)
		resolution_m = 0.0

	physics = simulate_rover_over_path(
		pts_xyz=pts,
		rover=rover,
		wheel_friction_coeff=mu,
		power_w=float(rover.power_w),
		illumination_map=illumination_map,
		illumination_transform=illumination_transform,
		g_mps2=float(LUNAR_GRAVITY),
		v0_mps=0.0,
		v_min_power_mps=0.001,
	)

	return {
		"average_velocity_mps": float(physics["average_velocity_mps"]),
		"min_velocity_mps": float(physics["min_velocity_mps"]),
		"max_velocity_mps": float(physics["max_velocity_mps"]),
		"traversal_time_s": float(physics["traversal_time_s"]),
		"solar_energy_per_m2_j": float(physics["solar_energy_per_m2_j"]),
		"avg_solar_illumination_w_per_m2": float(physics["avg_solar_illumination_w_per_m2"]),
		"max_climbable_slope_deg": max_climbable,
		"traverse_feasible": float(physics["traverse_feasible"]),
		"failure_x": physics.get("failure_x"),
		"failure_y": physics.get("failure_y"),
		"failure_reason": physics.get("failure_reason"),
		"simulation_resolution_m": float(resolution_m),
		"rollover_occurred": bool(physics.get("rollover_occurred", False)),
		"max_lateral_accel_mps2": float(physics.get("max_lateral_accel_mps2", 0.0)),
		"braking_events": int(physics.get("braking_events", 0)),
		"max_braking_decel_mps2": float(physics.get("max_braking_decel_mps2", 0.0)),
	}
