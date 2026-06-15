import numpy as np

from cynthium.app.config import LUNAR_GRAVITY
from cynthium.app.engine.simulation.path_sampling import sample_path_elevations
from cynthium.app.engine.simulation.rover_physics import simulate_rover_over_path
from cynthium.app.engine.simulation.rover_settings import RoverSettings


def _compute_required_mu_dynamic(
	*,
	pts_xyz: np.ndarray,
	rover: RoverSettings,
	power_w: float,
	g_mps2: float,
	mu_upper_hint: float,
	tol: float = 1e-3,
	max_iter: int = 30,
) -> float:
	"""Find the minimum μ that makes the traverse feasible under the same physics model."""
	def feasible(mu_test: float) -> bool:
		out = simulate_rover_over_path(
			pts_xyz=pts_xyz,
			rover=rover,
			wheel_friction_coeff=float(mu_test),
			power_w=float(power_w),
			illumination_map=None,
			illumination_transform=None,
			g_mps2=float(g_mps2),
			v0_mps=0.0,
			v_min_power_mps=0.001,
		)
		return float(out.get("traverse_feasible", 0.0)) >= 0.5

	lo = 0.0
	if feasible(lo):
		return 0.0

	hi = float(max(mu_upper_hint, 1e-6))
	grow = 0
	while not feasible(hi):
		hi *= 2.0
		grow += 1
		if hi > 50.0 or grow > 20:
			return float("inf")

	for _ in range(int(max_iter)):
		mid = 0.5 * (lo + hi)
		if hi - lo <= float(tol):
			break
		if feasible(mid):
			hi = mid
		else:
			lo = mid

	return float(hi)


def compute_traversal_dynamics(
	*,
	waypoints_xyz: np.ndarray,
	elevation_map: np.ndarray | None,
	transform,
	illumination_map: np.ndarray | None = None,
	illumination_transform=None,
	rover: RoverSettings,
) -> dict[str, float]:
	"""Physics-style rover traversal simulation.

	- Max throttle, power-limited drive (F = P / v), capped by traction (μN).
	- Gravity-assisted downhill acceleration; velocity carries into later segments.
	- Uses the illumination map to integrate energy: E = ∫ I dt (J/m²).
	"""
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
			"required_wheel_friction_coeff": 0.0,
			"required_climb_slope_deg": 0.0,
		}

	if elevation_map is not None and transform is not None:
		pts = sample_path_elevations(waypoints_xyz, elevation_map, transform)
	else:
		pts = waypoints_xyz.astype(np.float64, copy=False)

	diffs = np.diff(pts, axis=0)
	dist = np.linalg.norm(diffs, axis=1).astype(np.float64)
	horiz = np.linalg.norm(diffs[:, :2], axis=1).astype(np.float64)
	dz = diffs[:, 2].astype(np.float64)

	valid = (dist > 1e-9) & (horiz > 1e-9)
	theta = np.zeros(dist.shape, dtype=np.float64)
	theta[valid] = np.arctan2(dz[valid], horiz[valid])

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

	required_mu_dynamic = _compute_required_mu_dynamic(
		pts_xyz=pts,
		rover=rover,
		power_w=float(rover.power_w),
		g_mps2=float(LUNAR_GRAVITY),
		mu_upper_hint=mu,
	)

	return {
		"average_velocity_mps": float(physics["average_velocity_mps"]),
		"min_velocity_mps": float(physics["min_velocity_mps"]),
		"max_velocity_mps": float(physics["max_velocity_mps"]),
		"traversal_time_s": float(physics["traversal_time_s"]),
		"solar_energy_per_m2_j": float(physics["solar_energy_per_m2_j"]),
		"avg_solar_illumination_w_per_m2": float(
			physics["avg_solar_illumination_w_per_m2"]
		),
		"max_climbable_slope_deg": max_climbable,
		"traverse_feasible": float(physics["traverse_feasible"]),
		"required_wheel_friction_coeff": float(required_mu_dynamic),
		"required_climb_slope_deg": float(
			np.degrees(np.arctan(required_mu_dynamic))
		),
		"failure_x": physics.get("failure_x"),
		"failure_y": physics.get("failure_y"),
	}
