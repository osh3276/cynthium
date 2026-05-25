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
	("max_temp_avg_k", "max_temperature"),
	("min_temp_avg_k", "min_temperature"),
	("average_temp_avg_k", "average_temperature"),
	("illumination_yearly_avg_percent", "percent_illumination"),
	("average_velocity_mps", "average_velocity_mps"),
	("min_velocity_mps", "min_velocity_mps"),
	("max_velocity_mps", "max_velocity_mps"),
	("max_climbable_slope_deg", "max_climbable_slope_deg"),
]


def write_simulation_csv(
	path: str | Path,
	metadata: dict[str, str],
	stats: dict[str, float],
	points: np.ndarray | None,
):
	"""
	Writes the simulation csv.

	:param path: Path to the file.
	:type path: str | Path
	:param metadata: Parameter value.
	:type metadata: dict[str, str]
	:param stats: Simulation statistics.
	:type stats: dict[str, float]
	:param points: Point data.
	:type points: np.ndarray | None
	:return: The resulting value.
	"""
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

		writer.writerow(["waypoint_index", "x", "y", "z"])
		if points is not None:
			for index, point in enumerate(points, start=1):
				writer.writerow([index, point[0], point[1], point[2]])
