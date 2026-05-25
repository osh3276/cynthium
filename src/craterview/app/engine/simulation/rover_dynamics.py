import numpy as np

from craterview.app.config import LUNAR_GRAVITY, LUNAR_REGOLITH_FRICTION
from craterview.app.engine.simulation.path_sampling import sample_path_elevations
from craterview.app.engine.simulation.rover_settings import RoverSettings


def compute_velocity_stats(
	*,
	waypoints_xyz: np.ndarray,
	elevation_map: np.ndarray | None,
	transform,
	rover: RoverSettings,
) -> dict[str, float]:
	"""Compute velocity stats along the path using a simple power/grade model."""
	if waypoints_xyz.shape[0] < 2:
		return {
			"average_velocity_mps": 0.0,
			"min_velocity_mps": 0.0,
			"max_velocity_mps": 0.0,
			"max_climbable_slope_deg": float(np.degrees(np.arctan(rover.wheel_friction_coeff))),
		}

	if elevation_map is not None and transform is not None:
		pts = sample_path_elevations(waypoints_xyz, elevation_map, transform)
	else:
		pts = waypoints_xyz.astype(np.float64, copy=False)

	diffs = np.diff(pts, axis=0)
	dist = np.linalg.norm(diffs, axis=1).astype(np.float64)
	horiz = np.linalg.norm(diffs[:, :2], axis=1).astype(np.float64)
	dz = diffs[:, 2].astype(np.float64)

	valid = (dist > 0) & (horiz > 0)
	if not np.any(valid):
		return {
			"average_velocity_mps": 0.0,
			"min_velocity_mps": 0.0,
			"max_velocity_mps": 0.0,
			"max_climbable_slope_deg": float(np.degrees(np.arctan(rover.wheel_friction_coeff))),
		}

	theta = np.zeros(dist.shape, dtype=np.float64)
	theta[valid] = np.arctan2(dz[valid], horiz[valid])
	theta_abs = np.abs(theta)

	max_climbable = float(np.degrees(np.arctan(rover.wheel_friction_coeff)))
	climbable = np.tan(theta_abs) <= float(rover.wheel_friction_coeff)

	m = float(rover.mass_kg)
	g = float(LUNAR_GRAVITY)
	c_rr = float(LUNAR_REGOLITH_FRICTION)
	p_w = float(rover.power_w)

	f_req = m * g * (np.sin(theta_abs) + c_rr * np.cos(theta_abs))
	f_req = np.maximum(f_req, 1e-9)

	v = np.zeros(dist.shape, dtype=np.float64)
	v[climbable] = p_w / f_req[climbable]

	min_v = float(np.min(v))
	max_v = float(np.max(v))

	if np.any(v <= 0):
		avg_v = 0.0
	else:
		t = dist / v
		t_total = float(np.sum(t))
		d_total = float(np.sum(dist))
		avg_v = (d_total / t_total) if t_total > 0 else 0.0

	return {
		"average_velocity_mps": avg_v,
		"min_velocity_mps": min_v,
		"max_velocity_mps": max_v,
		"max_climbable_slope_deg": max_climbable,
	}
