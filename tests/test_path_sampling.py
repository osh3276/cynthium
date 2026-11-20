"""Tests for path sampling — elevation sampling along waypoint polylines."""

import numpy as np
import pytest
from affine import Affine

from cynthium.app.engine.simulation.path_sampling import (
	get_pixel_resolution_m,
	sample_path_elevations,
)


class TestGetPixelResolution:
	def test_from_affine(self):
		t = Affine(5.0, 0.0, 0.0, 0.0, -5.0, 100.0)
		assert get_pixel_resolution_m(t) == 5.0

	def test_non_square_pixels(self):
		t = Affine(10.0, 0.0, 0.0, 0.0, -5.0, 100.0)
		assert get_pixel_resolution_m(t) == 5.0  # min of 10, 5

	def test_negative_resolution(self):
		t = Affine(-2.0, 0.0, 0.0, 0.0, 2.0, 100.0)
		assert get_pixel_resolution_m(t) == 2.0  # abs value


class TestSamplePathElevations:
	@pytest.fixture
	def flat_elevation(self):
		"""10x10 elevation map all at 100m."""
		return np.full((10, 10), 100.0, dtype=np.float32)

	@pytest.fixture
	def transform(self):
		"""1m pixel, origin at (0,0), top-left at y=10."""
		return Affine(1.0, 0.0, 0.0, 0.0, -1.0, 10.0)

	def test_two_waypoints_horizontal(self, flat_elevation, transform):
		waypoints = np.array([[0.0, 9.0, 0.0], [9.0, 9.0, 0.0]], dtype=np.float64)
		result = sample_path_elevations(waypoints, flat_elevation, transform)
		assert len(result) > 2  # at least start + end
		assert result[0, 0] == 0.0
		assert result[0, 1] == 9.0
		assert result[-1, 0] == 9.0
		assert result[-1, 1] == 9.0
		# Elevation should be ~100 everywhere
		assert np.allclose(result[:, 2], 100.0, atol=0.1)

	def test_elevation_sampled_correctly(self, flat_elevation, transform):
		flat_elevation[0, 0] = 500.0  # top-left corner at (0, 10)
		# Need at least 2 waypoints; single waypoint returns empty
		waypoints = np.array([[0.5, 9.5, 0.0], [1.5, 9.5, 0.0]], dtype=np.float64)
		result = sample_path_elevations(waypoints, flat_elevation, transform)
		assert len(result) > 0
		# First point at (0.5, 9.5): col=0, row=0 → elev[0,0]=500
		assert result[0, 2] == 500.0  # nearest neighbor

	def test_single_waypoint_returns_empty(self, flat_elevation, transform):
		waypoints = np.array([[5.0, 5.0, 0.0]], dtype=np.float64)
		result = sample_path_elevations(waypoints, flat_elevation, transform)
		assert len(result) == 0

	def test_duplicate_consecutive_xy_removed(self, flat_elevation, transform):
		waypoints = np.array([
			[0.0, 9.0, 0.0],
			[0.0, 9.0, 0.0],  # duplicate
			[5.0, 9.0, 0.0],
		], dtype=np.float64)
		result = sample_path_elevations(waypoints, flat_elevation, transform)
		# Should not crash; duplicates are removed
		assert len(result) >= 2

	def test_bicubic_interpolation(self, flat_elevation, transform):
		waypoints = np.array([[0.0, 9.0, 0.0], [9.0, 9.0, 0.0]], dtype=np.float64)
		result = sample_path_elevations(
			waypoints, flat_elevation, transform, use_bicubic=True,
		)
		assert len(result) > 2
		# Bicubic mode produces ~5m spacing, so ~10/5 = ~2 steps + endpoints
		assert result[0, 2] == pytest.approx(100.0, abs=1.0)

	def test_bicubic_resolution(self, flat_elevation, transform):
		"""With bicubic, step size should be ~5m."""
		waypoints = np.array([[0.0, 9.0, 0.0], [100.0, 9.0, 0.0]], dtype=np.float64)
		result = sample_path_elevations(
			waypoints, flat_elevation, transform, use_bicubic=True,
		)
		# 100m / 5m = ~20 intervals = ~21 points
		assert len(result) > 10

	def test_vertical_path(self, flat_elevation, transform):
		waypoints = np.array([[5.0, 9.0, 0.0], [5.0, 1.0, 0.0]], dtype=np.float64)
		result = sample_path_elevations(waypoints, flat_elevation, transform)
		assert len(result) >= 2
		assert result[0, 1] == 9.0
		assert result[-1, 1] == 1.0

	def test_elevation_variation(self):
		"""3x3 elevation grid with pixel size 1, origin top-left at y=3."""
		elev = np.array([
			[90, 91, 92],
			[93, 94, 95],
			[96, 97, 98],
		], dtype=np.float32)
		# Transform: pixel(0,0) center at (0.5, 2.5)
		t = Affine(1.0, 0.0, 0.0, 0.0, -1.0, 3.0)
		# (0.5, 2.5) → pixel (0, 0) → elevation 90
		# (2.5, 0.5) → pixel (2, 2) → elevation 98
		waypoints = np.array([[0.5, 2.5, 0.0], [2.5, 0.5, 0.0]], dtype=np.float64)
		result = sample_path_elevations(waypoints, elev, t)
		assert result[0, 2] == 90.0  # top-left
		assert result[-1, 2] == 98.0  # bottom-right
		# Intermediate points should sample different elevations
		assert len(np.unique(result[:, 2])) > 1

	@pytest.fixture
	def small_transform(self):
		return Affine(0.5, 0.0, 0.0, 0.0, -0.5, 5.0)

	def test_sub_pixel_resolution(self, flat_elevation, small_transform):
		"""0.5m pixel resolution means more samples per meter."""
		waypoints = np.array([[0.0, 4.5, 0.0], [5.0, 4.5, 0.0]], dtype=np.float64)
		result = sample_path_elevations(waypoints, flat_elevation, small_transform)
		# 5m / 0.5m = 10 intervals = 11 points
		assert len(result) >= 10


class TestSamplingOnTiltedPlane:
	"""Elevations must follow the terrain exactly, with no stair-steps or offsets.

	Regression for nearest-pixel sampling with ``np.round`` on corner-based
	pixel coordinates: diagonal paths across a side slope produced
	stair-stepped profiles that the simulator read as spurious steep pitches.
	"""

	RES = 20.0
	X0, Y0 = 1000.0, 5000.0
	GX, GY = 0.3, -0.45  # dz/dx, dz/dy (side slope ~28 deg)

	@pytest.fixture
	def plane(self):
		n = 40
		t = Affine(self.RES, 0.0, self.X0, 0.0, -self.RES, self.Y0)
		cols, rows = np.meshgrid(np.arange(n), np.arange(n))
		xc = self.X0 + (cols + 0.5) * self.RES  # pixel centres
		yc = self.Y0 - (rows + 0.5) * self.RES
		elev = (self.GX * xc + self.GY * yc).astype(np.float64)
		return elev, t

	def _z(self, x, y):
		return self.GX * x + self.GY * y

	@pytest.mark.parametrize("use_bicubic", [False, True])
	@pytest.mark.parametrize("end", [(1600.0, 4410.0), (1390.0, 4380.0), (1700.0, 4730.0)])
	def test_profile_matches_plane(self, plane, use_bicubic, end):
		elev, t = plane
		start = (1110.0, 4870.0)
		wps = np.array([[*start, 0.0], [*end, 0.0]])
		pts = sample_path_elevations(wps, elev, t, use_bicubic=use_bicubic)
		expected = self._z(pts[:, 0], pts[:, 1])
		assert np.allclose(pts[:, 2], expected, atol=1e-6 if not use_bicubic else 1e-3)

	@pytest.mark.parametrize("end", [(1600.0, 4410.0), (1150.0, 4790.0), (1700.0, 4870.0)])
	def test_grade_constant_along_segment(self, plane, end):
		"""Every sample-to-sample grade equals the plane's directional grade."""
		elev, t = plane
		start = np.array([1110.0, 4870.0])
		wps = np.array([[*start, 0.0], [*end, 0.0]])
		pts = sample_path_elevations(wps, elev, t)
		u = (np.array(end) - start) / np.hypot(*(np.array(end) - start))
		grade = np.diff(pts[:, 2]) / np.hypot(*np.diff(pts[:, :2], axis=0).T)
		assert np.allclose(grade, self.GX * u[0] + self.GY * u[1], atol=1e-9)

	def test_pixel_centre_returns_pixel_value(self):
		elev = np.arange(25, dtype=np.float64).reshape(5, 5)
		t = Affine(1.0, 0.0, 0.0, 0.0, -1.0, 5.0)
		# centres of pixels (row 1, col 3) and (row 3, col 1)
		wps = np.array([[3.5, 3.5, 0.0], [1.5, 1.5, 0.0]])
		pts = sample_path_elevations(wps, elev, t)
		assert pts[0, 2] == pytest.approx(elev[1, 3])
		assert pts[-1, 2] == pytest.approx(elev[3, 1])
