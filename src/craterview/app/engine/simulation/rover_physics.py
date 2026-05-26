import numpy as np

from craterview.app.engine.simulation.rover_settings import RoverSettings


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
) -> dict[str, float]:
	"""Simple 1D dynamics along a polyline.

	Assumptions:
	- Rover is always at max throttle (power-limited: F = P/v).
	- Tractive force is capped by wheel/ground friction: F <= μN.
	- Downhill can accelerate from gravity; velocity carries into later segments.
	- No braking and no speed cap.
	- Illumination energy integrates E = ∫ I dt (J/m^2) using segment midpoints.
	"""
	if pts_xyz.shape[0] < 2:
		return {
			"traverse_feasible": 1.0,
			"traversal_time_s": 0.0,
			"average_velocity_mps": 0.0,
			"min_velocity_mps": 0.0,
			"max_velocity_mps": 0.0,
			"solar_energy_per_m2_j": 0.0,
			"avg_solar_illumination_w_per_m2": 0.0,
		}

	m = float(rover.mass_kg)
	mu = float(wheel_friction_coeff)
	p_w = float(power_w)
	g = float(g_mps2)

	diffs = np.diff(pts_xyz.astype(np.float64, copy=False), axis=0)
	ds = np.linalg.norm(diffs, axis=1).astype(np.float64)
	horiz = np.linalg.norm(diffs[:, :2], axis=1).astype(np.float64)
	dz = diffs[:, 2].astype(np.float64)

	valid = (ds > 1e-9) & (horiz > 1e-9)
	theta = np.zeros(ds.shape, dtype=np.float64)
	theta[valid] = np.arctan2(dz[valid], horiz[valid])

	inv_illum = None
	if illumination_map is not None and illumination_transform is not None:
		inv_illum = ~illumination_transform

	v = float(v0_mps)
	t_total = 0.0
	d_total = 0.0
	energy_j_per_m2 = 0.0

	min_v = float("inf")
	max_v = 0.0

	for i in range(ds.size):
		s = float(ds[i])
		if not (s > 0):
			continue

		th = float(theta[i])

		# Normal force magnitude.
		f_n = m * g * abs(np.cos(th))
		f_trac_max = mu * f_n

		# Power-limited force, with a minimum effective velocity to avoid singularity.
		v_eff = max(float(v), float(v_min_power_mps))
		f_power = p_w / v_eff
		f_drive = min(f_power, f_trac_max)

		# Gravity component along travel direction: + uphill resists, - downhill assists.
		f_grade = m * g * np.sin(th)

		# Rolling resistance always opposes motion
		c_rr = float(rover.rolling_resistance_coeff)
		f_roll = c_rr * f_n

		f_net = f_drive - f_grade - f_roll
		a = f_net / m

		v_sq_next = (v * v) + (2.0 * a * s)
		if v_sq_next <= 0.0:
			# Stop occurs before completing this segment.
			if a >= 0.0:
				v_next = 0.0
				dt = 0.0
			else:
				s_stop = (v * v) / (-2.0 * a) if v > 0.0 else 0.0
				dt = (v / (-a)) if v > 0.0 else 0.0
				d_total += float(s_stop)
				t_total += float(dt)

				if inv_illum is not None and dt > 0.0:
					xy_mid = 0.5 * (pts_xyz[i, :2] + pts_xyz[i + 1, :2])
					col, row = inv_illum * (float(xy_mid[0]), float(xy_mid[1]))
					ci = int(round(col))
					ri = int(round(row))
					if (
						0 <= ri < illumination_map.shape[0]
						and 0 <= ci < illumination_map.shape[1]
					):
						illum = float(illumination_map[ri, ci])
						if np.isfinite(illum):
							energy_j_per_m2 += illum * float(dt)

				min_v = min(min_v, 0.0)
				max_v = max(max_v, float(v))

				return {
					"traverse_feasible": 0.0,
					"traversal_time_s": float("inf"),
					"average_velocity_mps": 0.0,
					"min_velocity_mps": 0.0 if min_v == float("inf") else float(min_v),
					"max_velocity_mps": float(max_v),
					"solar_energy_per_m2_j": float(energy_j_per_m2),
					"avg_solar_illumination_w_per_m2": 0.0,
				}

		v_next = float(np.sqrt(v_sq_next))
		den = float(v + v_next)
		dt = (2.0 * s / den) if den > 0.0 else 0.0

		d_total += s
		t_total += float(dt)

		v_mid = 0.5 * (float(v) + float(v_next))
		min_v = min(min_v, float(v_mid))
		max_v = max(max_v, float(v_mid))

		if inv_illum is not None and dt > 0.0:
			xy_mid = 0.5 * (pts_xyz[i, :2] + pts_xyz[i + 1, :2])
			col, row = inv_illum * (float(xy_mid[0]), float(xy_mid[1]))
			ci = int(round(col))
			ri = int(round(row))
			if 0 <= ri < illumination_map.shape[0] and 0 <= ci < illumination_map.shape[1]:
				illum = float(illumination_map[ri, ci])
				if np.isfinite(illum):
					energy_j_per_m2 += illum * float(dt)

		v = v_next

	if t_total <= 0.0:
		avg_v = 0.0
		avg_illum = 0.0
	else:
		avg_v = float(d_total / t_total)
		avg_illum = float(energy_j_per_m2 / t_total)

	if min_v == float("inf"):
		min_v = 0.0

	return {
		"traverse_feasible": 1.0,
		"traversal_time_s": float(t_total),
		"average_velocity_mps": float(avg_v),
		"min_velocity_mps": float(min_v),
		"max_velocity_mps": float(max_v),
		"solar_energy_per_m2_j": float(energy_j_per_m2),
		"avg_solar_illumination_w_per_m2": float(avg_illum),
	}
