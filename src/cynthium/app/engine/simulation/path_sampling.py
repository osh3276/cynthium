import numpy as np
from scipy.ndimage import map_coordinates

from cynthium.app.utils.logger import get_logger

logger = get_logger(__name__)

BICUBIC_RESOLUTION_M = 5.0  # target resolution when bicubic interpolation is enabled


def get_pixel_resolution_m(transform) -> float:
	return float(min(abs(transform.a), abs(transform.e)))


def sample_path_elevations(
	waypoints: np.ndarray,
	elevation_map: np.ndarray,
	transform,
	*,
	use_bicubic: bool = False,
) -> np.ndarray:
	"""Sample (x,y,z) along the waypoint polyline.

	When *use_bicubic* is False (default): samples at ~1 pixel spacing
	using nearest-neighbor lookup.

	When *use_bicubic* is True: samples at 5 m spacing using bicubic
	interpolation for smoother elevation profiles.
	"""
	inverse_transform = ~transform
	pixel_resolution = get_pixel_resolution_m(transform)

	if use_bicubic:
		resolution = BICUBIC_RESOLUTION_M
	else:
		resolution = pixel_resolution

	sampled_points: list[list[float]] = []

	for index in range(len(waypoints) - 1):
		start_point = waypoints[index]
		end_point = waypoints[index + 1]
		horizontal_distance = float(np.linalg.norm(end_point[:2] - start_point[:2]))
		if horizontal_distance == 0:
			segment_sample_count = 1
		else:
			segment_sample_count = int(np.ceil(horizontal_distance / resolution))

		for sample_index in range(segment_sample_count + 1):
			fraction = sample_index / segment_sample_count
			current_xy = start_point[:2] + fraction * (end_point[:2] - start_point[:2])
			sampled_points.append([float(current_xy[0]), float(current_xy[1])])

	if not sampled_points:
		return np.empty((0, 3), dtype=np.float64)

	sampled_xy = np.array(sampled_points, dtype=np.float64)

	# Remove duplicate consecutive XY points
	mask = np.ones(len(sampled_xy), dtype=bool)
	if len(sampled_xy) > 1:
		mask[1:] = ~np.all(np.diff(sampled_xy, axis=0) == 0, axis=1)
	sampled_xy = sampled_xy[mask]

	if len(sampled_xy) == 0:
		return np.empty((0, 3), dtype=np.float64)

	# Convert XY to pixel coordinates
	col, row = inverse_transform * (float(sampled_xy[0, 0]), float(sampled_xy[0, 1]))
	all_cols = np.empty(len(sampled_xy), dtype=np.float64)
	all_rows = np.empty(len(sampled_xy), dtype=np.float64)
	all_cols[0] = float(col)
	all_rows[0] = float(row)
	for i in range(1, len(sampled_xy)):
		col, row = inverse_transform * (float(sampled_xy[i, 0]), float(sampled_xy[i, 1]))
		all_cols[i] = float(col)
		all_rows[i] = float(row)

	if use_bicubic:
		# Bicubic interpolation at sub-pixel positions
		elevations = map_coordinates(
			elevation_map,
			np.vstack([all_rows, all_cols]),
			order=3,
			mode="nearest",
		).astype(np.float64)
	else:
		# Nearest-neighbor: snap to closest integer pixel
		col_i = np.clip(np.round(all_cols).astype(np.int64), 0, elevation_map.shape[1] - 1)
		row_i = np.clip(np.round(all_rows).astype(np.int64), 0, elevation_map.shape[0] - 1)
		elevations = elevation_map[row_i, col_i].astype(np.float64)

	result = np.column_stack([sampled_xy, elevations])
	return result
