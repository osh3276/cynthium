import csv
from pathlib import Path

import numpy as np

SIMULATION_STAT_EXPORT_KEYS = [
	("total_displacement_m", "total_displacement"),
	("total_distance_travelled_m", "total_distance_travelled"),
	("total_elevation_gain_m", "total_elevation_gain"),
	("net_elevation_change_m", "net_elevation_change"),
	("average_slope_deg", "average_slope"),
	("max_slope_deg", "max_slope"),
	("min_slope_deg", "min_slope"),
	("surface_average_slope_deg", "surface_average_slope"),
	("surface_max_slope_deg", "surface_max_slope"),
	("surface_min_slope_deg", "surface_min_slope"),
	("average_meteor_flux", "average_meteor_flux"),
	("max_meteor_flux", "max_meteor_flux"),
	("min_meteor_flux", "min_meteor_flux"),
	("max_temp_avg_k", "max_temperature"),
	("min_temp_avg_k", "min_temperature"),
	("average_temp_avg_k", "average_temperature"),
	("illumination_yearly_avg_percent", "percent_illumination"),
	("average_velocity_mps", "average_velocity_mps"),
	("min_velocity_mps", "min_velocity_mps"),
	("max_velocity_mps", "max_velocity_mps"),
	("max_climbable_slope_deg", "max_climbable_slope_deg"),
	("traversal_time_s", "traversal_time_s"),
	("solar_energy_per_m2_j", "solar_energy_per_m2_j"),
	("avg_solar_illumination_w_per_m2", "avg_solar_illumination_w_per_m2"),
	("battery_energy_used_j", "battery_energy_used_j"),
	("battery_remaining_pct", "battery_remaining_pct"),
	("battery_capacity_wh", "battery_capacity_wh"),
	("traverse_feasible", "traverse_feasible"),
	("failure_reason", "failure_reason"),
	("required_wheel_friction_coeff", "required_wheel_friction_coeff"),
	("required_climb_slope_deg", "required_climb_slope_deg"),
]


def write_simulation_csv(
	path: str | Path,
	metadata: dict[str, str],
	stats: dict[str, float],
	points: np.ndarray | None,
	pause_durations: list[float] | None = None,
):
	"""Write simulation stats and waypoint data to a CSV file."""
	with open(path, "w", newline="") as csv_file:
		writer = csv.writer(csv_file)
		writer.writerow(["metadata_key", "metadata_value"])
		for key, value in metadata.items():
			writer.writerow([key, value])
		writer.writerow([])

		writer.writerow(["stat", "value"])
		for export_key, stats_key in SIMULATION_STAT_EXPORT_KEYS:
			writer.writerow([export_key, stats.get(stats_key, 0.0)])
		writer.writerow([])

		writer.writerow(["waypoint_index", "x", "y", "z", "pause_s"])
		if points is not None:
			for index, point in enumerate(points, start=1):
				pause = float(pause_durations[index - 2]) if pause_durations and index > 1 and (index - 2) < len(pause_durations) else 0.0
				writer.writerow([index, point[0], point[1], point[2], pause])
