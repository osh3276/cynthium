import numpy as np

from cynthium.app.engine.simulation.rover_dynamics import compute_traversal_dynamics
from cynthium.app.engine.simulation.rover_settings import RoverSettings
from cynthium.app.engine.simulation.stats import calculate_path_stats


def calculate_simulation_stats(
	points: list,
	map_data_bundle: tuple,
	*,
	rover: RoverSettings | None = None,
) -> tuple[dict[str, float], np.ndarray]:
	"""
	Calculates the simulation stats.

	:param points: Point data.
	:type points: list
	:param map_data_bundle: Parameter value.
	:type map_data_bundle: tuple
	:return: The resulting value.
	"""
	(
		map_data,
		map_meta,
		slope_data,
		temperature_data,
		temperature_meta,
		illumination_data,
		illumination_meta,
	) = map_data_bundle
	transform = map_meta.get("transform") if map_meta else None
	temperature_transform = (
		temperature_meta.get("transform") if temperature_meta else None
	)
	illumination_transform = (
		illumination_meta.get("transform") if illumination_meta else None
	)

	points_array = np.array(points)
	stats = calculate_path_stats(
		points_array,
		map_data,
		transform,
		slope_data,
		temperature_data,
		temperature_transform,
		illumination_data,
		illumination_transform,
	)

	if rover is not None:
		stats.update(
			compute_traversal_dynamics(
				waypoints_xyz=points_array,
				elevation_map=map_data,
				transform=transform,
				illumination_map=illumination_data,
				illumination_transform=illumination_transform,
				rover=rover,
			)
		)

	return stats, points_array


def format_simulation_stats(stats: dict[str, float]) -> str:
	"""
	Formats the simulation stats.

	:param stats: Simulation statistics.
	:type stats: dict[str, float]
	:return: The resulting value.
	"""
	return (
		f"Total Displacement: {stats['total_displacement']:.2f} m\n"
		f"Total Distance Travelled: {stats['total_distance_travelled']:.2f} m\n"
		f"Total Climb Distance: {stats['total_elevation_gain']:.2f} m\n"
		f"Net Elevation Change: {stats['net_elevation_change']:.2f} m\n"
		f"Average Slope: {stats['average_slope']:.2f}°\n"
		f"Max Slope: {stats['max_slope']:.2f}°\n"
		f"Min Slope: {stats['min_slope']:.2f}°\n"
		f"Max Temp (avg.): {stats['max_temperature']:.2f} K\n"
		f"Min Temp (avg.): {stats['min_temperature']:.2f} K\n"
		f"Average Temp (avg.): {stats['average_temperature']:.2f} K\n"
		f"Illumination (yearly avg.): {stats['percent_illumination']:.2f}%\n"
		f"Avg Velocity: {stats.get('average_velocity_mps', 0.0):.2f} m/s\n"
		f"Min Velocity: {stats.get('min_velocity_mps', 0.0):.2f} m/s\n"
		f"Max Velocity: {stats.get('max_velocity_mps', 0.0):.2f} m/s\n"
		f"Traversal Time: {stats.get('traversal_time_s', 0.0):.2f} s\n"
		f"Solar Energy (per m²): {stats.get('solar_energy_per_m2_j', 0.0):.2f} J/m²\n"
		f"Avg Solar Illum (time-weighted): {stats.get('avg_solar_illumination_w_per_m2', 0.0):.2f} W/m²\n"
		f"Max Climbable Slope: {stats.get('max_climbable_slope_deg', 0.0):.2f}°"
	)
