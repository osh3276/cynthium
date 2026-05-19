import numpy as np

from craterview.app.engine.simulation.stats import calculate_path_stats


def calculate_simulation_stats(
	points: list, map_data_bundle: tuple
) -> tuple[dict[str, float], np.ndarray]:
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
	return stats, points_array


def format_simulation_stats(stats: dict[str, float]) -> str:
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
		f"Illumination (yearly avg.): {stats['percent_illumination']:.2f}%"
	)
