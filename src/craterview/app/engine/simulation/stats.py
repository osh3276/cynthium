import numpy as np
from craterview.app.utils.logger import get_logger

logger = get_logger(__name__)

EMPTY_PATH_STATS = {
	"total_distance": 0.0,
	"total_elevation_gain": 0.0,
	"net_elevation_change": 0.0,
	"average_slope": 0.0,
	"max_slope": 0.0,
	"min_slope": 0.0,
}


def calculate_path_stats(
		points: np.ndarray,
		elevation_map: np.ndarray | None = None,
		transform=None,
		slope_map: np.ndarray | None = None,
) -> dict[str, float]:
	"""
	Calculate statistics for a path of 3D points.

	If elevation_map and transform are provided, it integrates over the path
	by sampling elevation at every pixel step along the segments.
	If slope_map is provided, it also calculates slope statistics.

	:param points: np.ndarray of shape (N, 3) representing (x, y, z) coordinates.
	:param elevation_map: 2D numpy array of elevation data.
	:param transform: affine.Affine transform (rasterio style) from pixel to world.
	:param slope_map: 2D numpy array of slope data (in degrees).
	:return: dict with keys including 'total_distance', 'total_elevation_gain',
			 'average_slope', etc.
	"""
	if len(points) < 2:
		return EMPTY_PATH_STATS.copy()

	if elevation_map is not None and transform is not None:
		return _calculate_integrated_stats(points, elevation_map, transform, slope_map)

	return _calculate_stats_from_points(points)


def _calculate_integrated_stats(
		waypoints: np.ndarray,
		elevation_map: np.ndarray,
		transform,
		slope_map: np.ndarray | None = None,
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

	return stats


def _calculate_stats_from_points(points: np.ndarray) -> dict[str, float]:
	diffs = np.diff(points, axis=0)
	distances = np.linalg.norm(diffs, axis=1)
	z_diffs = diffs[:, 2]

	return {
		"total_distance": float(np.sum(distances)),
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
	sampled_slopes = [] if slope_map is not None else None

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
