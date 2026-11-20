import numpy as np
from scipy.ndimage import map_coordinates

from cynthium.app.utils.logger import get_logger

logger = get_logger(__name__)

BICUBIC_RESOLUTION_M = 5.0  # target resolution when bicubic interpolation is enabled


def get_pixel_resolution_m(transform) -> float:
	"""Return the pixel resolution in metres from a rasterio transform."""
	return float(min(abs(transform.a), abs(transform.e)))


def sample_path_elevations(
		waypoints: np.ndarray,
		elevation_map: np.ndarray,
		transform,
		*,
		use_bicubic: bool = False,
) -> np.ndarray:
	"""Sample (x,y,z) along the waypoint polyline.

	Default: ~1 px spacing, bilinear interpolation.
	With bicubic: 5 m spacing, bicubic interpolation (smoother profiles).

	Elevations are interpolated rather than taken from the nearest pixel:
	samples are spaced along the path, not on the pixel grid, so
	nearest-pixel lookup gives a stair-stepped profile whose jumps the
	simulator reads as spurious steep pitches on side slopes.
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

	# Fractional pixel coordinates.  The affine transform maps pixel *corners*
	# to integers (pixel k spans [k, k+1), centre k + 0.5), whereas
	# map_coordinates places pixel centres at integer indices, hence the -0.5.
	inv = inverse_transform
	xs, ys = sampled_xy[:, 0], sampled_xy[:, 1]
	cols = inv.a * xs + inv.b * ys + inv.c
	rows = inv.d * xs + inv.e * ys + inv.f
	coords = np.vstack([rows - 0.5, cols - 0.5])

	elevations = map_coordinates(
		elevation_map,
		coords,
		order=3 if use_bicubic else 1,
		mode="nearest",
	).astype(np.float64)

	result = np.column_stack([sampled_xy, elevations])
	return result
