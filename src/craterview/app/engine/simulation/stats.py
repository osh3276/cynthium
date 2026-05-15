import numpy as np

from craterview.app.utils.logger import get_logger

logger = get_logger(__name__)

EMPTY_PATH_STATS = {
	"total_distance": 0.0,
	"total_distance_travelled": 0.0,
	"total_displacement": 0.0,
	"total_elevation_gain": 0.0,
	"net_elevation_change": 0.0,
	"average_slope": 0.0,
	"max_slope": 0.0,
	"min_slope": 0.0,
	"max_temperature": 0.0,
	"min_temperature": 0.0,
	"average_temperature": 0.0,
	"percent_illumination": 0.0,
}


def calculate_path_stats(
	points: np.ndarray,
	elevation_map: np.ndarray | None = None,
	transform=None,
	slope_map: np.ndarray | None = None,
	temperature_map: np.ndarray | None = None,
	temperature_transform=None,
	illumination_map: np.ndarray | None = None,
	illumination_transform=None,
) -> dict[str, float]:
	"""
	Calculate statistics for a path of 3D points.

	If elevation_map and transform are provided, it integrates over the path
	by sampling elevation at every pixel step along the segments.
	If slope_map is provided, it also calculates slope statistics.
	If temperature_map or illumination_map are provided, it samples them along
	the traversed path using their own raster transforms.
	"""
	if len(points) < 2:
		return EMPTY_PATH_STATS.copy()

	if elevation_map is not None and transform is not None:
		return _calculate_integrated_stats(
			points,
			elevation_map,
			transform,
			slope_map,
			temperature_map,
			temperature_transform,
			illumination_map,
			illumination_transform,
		)

	stats = _calculate_stats_from_points(points)
	_add_context_stats(
		stats,
		points[:, :2],
		temperature_map,
		temperature_transform,
		illumination_map,
		illumination_transform,
	)
	return stats


def _calculate_integrated_stats(
	waypoints: np.ndarray,
	elevation_map: np.ndarray,
	transform,
	slope_map: np.ndarray | None = None,
	temperature_map: np.ndarray | None = None,
	temperature_transform=None,
	illumination_map: np.ndarray | None = None,
	illumination_transform=None,
) -> dict[str, float]:
	sampled_points, _ = _sample_path_data(waypoints, elevation_map, transform, None)
	stats = _calculate_stats_from_points(sampled_points)
	stats["average_resolution"] = _get_pixel_resolution(transform)

	# Calculate directional slope (grade) between consecutive samples
	if len(sampled_points) > 1:
		diffs = np.diff(sampled_points, axis=0)
		horizontal_distances = np.linalg.norm(diffs[:, :2], axis=1)
		z_diffs = diffs[:, 2]

		# Avoid division by zero for identical consecutive points (though sampling should prevent this)
		mask = horizontal_distances > 0
		if np.any(mask):
			# slope in degrees: atan(rise/run)
			slopes = np.degrees(np.arctan2(z_diffs[mask], horizontal_distances[mask]))
			stats["average_slope"] = float(np.mean(slopes))
			stats["max_slope"] = float(np.max(slopes))
			stats["min_slope"] = float(np.min(slopes))
		else:
			stats["average_slope"] = 0.0
			stats["max_slope"] = 0.0
			stats["min_slope"] = 0.0
	else:
		stats["average_slope"] = 0.0
		stats["max_slope"] = 0.0
		stats["min_slope"] = 0.0

	_add_context_stats(
		stats,
		sampled_points[:, :2],
		temperature_map,
		temperature_transform,
		illumination_map,
		illumination_transform,
	)
	return stats


def _add_context_stats(
	stats: dict[str, float],
	points_xy: np.ndarray,
	temperature_map: np.ndarray | None,
	temperature_transform,
	illumination_map: np.ndarray | None,
	illumination_transform,
):
	temperature_values = _sample_raster_values(
		points_xy,
		temperature_map,
		temperature_transform,
	)
	if temperature_values.size:
		stats["max_temperature"] = float(np.max(temperature_values))
		stats["min_temperature"] = float(np.min(temperature_values))
		stats["average_temperature"] = float(np.mean(temperature_values))
	else:
		stats["max_temperature"] = 0.0
		stats["min_temperature"] = 0.0
		stats["average_temperature"] = 0.0

	illumination_values = _sample_raster_values(
		points_xy,
		illumination_map,
		illumination_transform,
	)
	if illumination_values.size:
		illuminated_count = np.count_nonzero(illumination_values > 0)
		stats["percent_illumination"] = float(
			illuminated_count / illumination_values.size * 100.0
		)
	else:
		stats["percent_illumination"] = 0.0


def _sample_raster_values(
	points_xy: np.ndarray,
	raster: np.ndarray | None,
	transform,
) -> np.ndarray:
	if raster is None or transform is None or points_xy.size == 0:
		return np.array([], dtype=np.float32)

	inverse_transform = ~transform
	values = []
	for x, y in points_xy:
		col, row = inverse_transform * (float(x), float(y))
		col = int(round(col))
		row = int(round(row))
		if 0 <= row < raster.shape[0] and 0 <= col < raster.shape[1]:
			value = raster[row, col]
			if np.isfinite(value):
				values.append(float(value))

	return np.array(values, dtype=np.float32)


def _calculate_stats_from_points(points: np.ndarray) -> dict[str, float]:
	diffs = np.diff(points, axis=0)
	step_distances = np.linalg.norm(diffs, axis=1)
	z_diffs = diffs[:, 2]
	total_distance_travelled = float(np.sum(step_distances))
	total_displacement = float(np.linalg.norm(points[-1] - points[0]))

	return {
		# Keep total_distance as a compatibility alias for existing tests/callers.
		"total_distance": total_distance_travelled,
		"total_distance_travelled": total_distance_travelled,
		"total_displacement": total_displacement,
		"total_elevation_gain": float(np.sum(z_diffs[z_diffs > 0])),
		"net_elevation_change": float(points[-1, 2] - points[0, 2]),
	}


def _sample_path_data(
	waypoints: np.ndarray,
	elevation_map: np.ndarray,
	transform,
	slope_map: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray | None]:
	inverse_transform = ~transform
	pixel_resolution = _get_pixel_resolution(transform)
	sampled_points = []

	logger.info(f"Pixel resolution: {pixel_resolution} metres per pixel")

	for index in range(len(waypoints) - 1):
		start_point = waypoints[index]
		end_point = waypoints[index + 1]
		segment_sample_count = _calculate_segment_sample_count(
			start_point,
			end_point,
			pixel_resolution,
		)

		logger.info(f"Number of samples in segment {index}: {segment_sample_count}")

		for sample_index in range(segment_sample_count + 1):
			fraction = sample_index / segment_sample_count
			current_xy = start_point[:2] + fraction * (end_point[:2] - start_point[:2])

			col, row = inverse_transform * (current_xy[0], current_xy[1])
			col = _clamp_index(int(round(col)), elevation_map.shape[1])
			row = _clamp_index(int(round(row)), elevation_map.shape[0])

			elevation = elevation_map[row, col]
			sampled_points.append([current_xy[0], current_xy[1], elevation])

	# Remove duplicates if consecutive segments share a waypoint
	sampled_points_arr = np.array(sampled_points)
	if len(sampled_points_arr) > 1:
		# Keep points where the next point is different
		mask = np.any(np.diff(sampled_points_arr, axis=0) != 0, axis=1)
		# Always keep the last point
		mask = np.append(mask, True)
		sampled_points_arr = sampled_points_arr[mask]

	return sampled_points_arr, None


def _get_pixel_resolution(transform) -> float:
	return min(abs(transform.a), abs(transform.e))


def _calculate_segment_sample_count(
	start_point: np.ndarray,
	end_point: np.ndarray,
	pixel_resolution: float,
) -> int:
	horizontal_distance = np.linalg.norm(end_point[:2] - start_point[:2])

	if horizontal_distance == 0:
		return 1

	return int(np.ceil(horizontal_distance / pixel_resolution))


def _clamp_index(index: int, size: int) -> int:
	return max(0, min(index, size - 1))
