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
