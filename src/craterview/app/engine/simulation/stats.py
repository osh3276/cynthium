import numpy as np
from craterview.app.utils.logger import get_logger

logger = get_logger(__name__)

EMPTY_PATH_STATS = {
	"total_distance": 0.0,
	"total_elevation_gain": 0.0,
	"net_elevation_change": 0.0,
}


def calculate_path_stats(
		points: np.ndarray,
		elevation_map: np.ndarray | None = None,
		transform=None,
) -> dict[str, float]:
	"""
	Calculate statistics for a path of 3D points.

	If elevation_map and transform are provided, it integrates over the path
	by sampling elevation at every pixel step along the segments.

	:param points: np.ndarray of shape (N, 3) representing (x, y, z) coordinates.
	:param elevation_map: 2D numpy array of elevation data.
	:param transform: affine.Affine transform (rasterio style) from pixel to world.
	:return: dict with keys 'total_distance', 'total_elevation_gain', 'net_elevation_change'
	"""
	if len(points) < 2:
		return EMPTY_PATH_STATS.copy()

	if elevation_map is not None and transform is not None:
		return _calculate_integrated_stats(points, elevation_map, transform)

	return _calculate_stats_from_points(points)


def _calculate_integrated_stats(
		waypoints: np.ndarray,
		elevation_map: np.ndarray,
		transform,
) -> dict[str, float]:
	sampled_points = _sample_path_points(waypoints, elevation_map, transform)
	stats = _calculate_stats_from_points(sampled_points)
	stats["average_resolution"] = _get_pixel_resolution(transform)

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


def _sample_path_points(
		waypoints: np.ndarray,
		elevation_map: np.ndarray,
		transform,
) -> np.ndarray:
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

		logger.info(f"Number of samples: {segment_sample_count}")

		for sample_index in range(segment_sample_count):
			fraction = sample_index / segment_sample_count
			current_xy = start_point[:2] + fraction * (end_point[:2] - start_point[:2])
			elevation = _sample_elevation_at_point(
				current_xy,
				elevation_map,
				inverse_transform,
			)
			sampled_points.append([current_xy[0], current_xy[1], elevation])

	sampled_points.append(waypoints[-1])

	return np.array(sampled_points)


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


def _sample_elevation_at_point(
		pt: np.ndarray,
		elevation_map: np.ndarray,
		inverse_transform,
) -> float:
	# Rasterio transform: x = a*col + b*row + c, y = d*col + e*row + f.
	# The inverse transform converts world coordinates to pixel coordinates.
	col, row = inverse_transform * (pt[0], pt[1])
	col = _clamp_index(int(round(col)), elevation_map.shape[1])
	row = _clamp_index(int(round(row)), elevation_map.shape[0])

	return elevation_map[row, col]


def _clamp_index(index: int, size: int) -> int:
	return max(0, min(index, size - 1))
