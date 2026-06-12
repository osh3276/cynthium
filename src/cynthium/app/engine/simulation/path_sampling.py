import numpy as np

from cynthium.app.utils.logger import get_logger

logger = get_logger(__name__)


def get_pixel_resolution_m(transform) -> float:
	return float(min(abs(transform.a), abs(transform.e)))


def sample_path_elevations(
	waypoints: np.ndarray,
	elevation_map: np.ndarray,
	transform,
) -> np.ndarray:
	"""Sample (x,y,z) along the waypoint polyline at ~1 pixel spacing."""
	inverse_transform = ~transform
	pixel_resolution = get_pixel_resolution_m(transform)
	sampled_points: list[list[float]] = []

	for index in range(len(waypoints) - 1):
		start_point = waypoints[index]
		end_point = waypoints[index + 1]
		horizontal_distance = float(np.linalg.norm(end_point[:2] - start_point[:2]))
		if horizontal_distance == 0:
			segment_sample_count = 1
		else:
			segment_sample_count = int(np.ceil(horizontal_distance / pixel_resolution))

		for sample_index in range(segment_sample_count + 1):
			fraction = sample_index / segment_sample_count
			current_xy = start_point[:2] + fraction * (end_point[:2] - start_point[:2])

			col, row = inverse_transform * (float(current_xy[0]), float(current_xy[1]))
			col_i = _clamp_index(int(round(col)), elevation_map.shape[1])
			row_i = _clamp_index(int(round(row)), elevation_map.shape[0])

			elevation = float(elevation_map[row_i, col_i])
			sampled_points.append([float(current_xy[0]), float(current_xy[1]), elevation])

	sampled_points_arr = np.array(sampled_points, dtype=np.float64)
	if len(sampled_points_arr) > 1:
		mask = np.any(np.diff(sampled_points_arr, axis=0) != 0, axis=1)
		mask = np.append(mask, True)
		sampled_points_arr = sampled_points_arr[mask]

	return sampled_points_arr


def _clamp_index(index: int, size: int) -> int:
	return max(0, min(index, size - 1))
