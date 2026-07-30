"""Tests for path statistics calculations.

Tests cover:
- calculate_path_stats with raw points (no rasters)
- calculate_path_stats with elevation map integration
- _calculate_stats_from_points
- _sample_raster_values
- _add_context_stats
"""

import numpy as np
import pytest
from affine import Affine

from cynthium.app.engine.simulation.stats import (
	_add_context_stats,
	_calculate_stats_from_points,
	_sample_raster_values,
	calculate_path_stats,
)


# ── _calculate_stats_from_points ─────────────────────────────────────

class TestCalculateStatsFromPoints:
	def test_two_points_flat(self):
		pts = np.array([[0.0, 0.0, 100.0], [10.0, 0.0, 100.0]])
		stats = _calculate_stats_from_points(pts)
		assert stats["total_distance"] == pytest.approx(10.0)
		assert stats["total_distance_travelled"] == pytest.approx(10.0)
		assert stats["total_displacement"] == pytest.approx(10.0)
		assert stats["total_elevation_gain"] == 0.0
		assert stats["net_elevation_change"] == 0.0

	def test_uphill_path(self):
		pts = np.array([[0.0, 0.0, 100.0], [10.0, 0.0, 110.0]])
		stats = _calculate_stats_from_points(pts)
		assert stats["total_distance"] == pytest.approx(np.sqrt(10**2 + 10**2))
		assert stats["total_elevation_gain"] == 10.0
		assert stats["net_elevation_change"] == 10.0

	def test_downhill_path(self):
		pts = np.array([[0.0, 0.0, 110.0], [10.0, 0.0, 100.0]])
		stats = _calculate_stats_from_points(pts)
		assert stats["total_elevation_gain"] == 0.0  # no gain
		assert stats["net_elevation_change"] == -10.0

	def test_multi_segment(self):
		pts = np.array([
			[0.0, 0.0, 100.0],
			[5.0, 0.0, 102.0],
			[5.0, 5.0, 98.0],
			[10.0, 10.0, 105.0],
		])
		stats = _calculate_stats_from_points(pts)
		assert stats["total_distance_travelled"] > stats["total_displacement"]
		assert stats["total_elevation_gain"] == pytest.approx(2.0 + 7.0)  # 102-100 + 105-98
		assert stats["net_elevation_change"] == 5.0

	def test_single_point(self):
		pts = np.array([[5.0, 5.0, 100.0]])
		stats = _calculate_stats_from_points(pts)
		assert stats["total_distance"] == 0.0
		assert stats["total_displacement"] == 0.0

	def test_zero_length_segment(self):
		pts = np.array([[0.0, 0.0, 100.0], [0.0, 0.0, 100.0]])
		stats = _calculate_stats_from_points(pts)
		assert stats["total_distance"] == 0.0
		assert stats["total_elevation_gain"] == 0.0


# ── _sample_raster_values ────────────────────────────────────────────

class TestSampleRasterValues:
	@pytest.fixture
	def raster(self):
		return np.array([
			[1.0, 2.0, 3.0],
			[4.0, 5.0, 6.0],
			[7.0, 8.0, 9.0],
		], dtype=np.float32)

	@pytest.fixture
	def transform(self):
		# 1m pixel, top-left corner at (0, 3).
		# x = col, y = -row + 3
		# So col = x, row = 3 - y
		# Pixel (0,0) center at (0.5, 2.5)
		return Affine(1.0, 0.0, 0.0, 0.0, -1.0, 3.0)

	def test_sample_single_point(self, raster, transform):
		pts = np.array([[0.4, 2.6]])  # col=0.4→0, row=0.4→0
		values = _sample_raster_values(pts, raster, transform)
		assert len(values) == 1
		assert values[0] == 1.0

	def test_sample_multiple(self, raster, transform):
		pts = np.array([
			[0.4, 2.6],  # col=0.4→0, row=0.4→0 → 1.0
			[1.4, 1.6],  # col=1.4→1, row=1.4→1 → 5.0
			[2.4, 0.6],  # col=2.4→2, row=2.4→2 → 9.0
		])
		values = _sample_raster_values(pts, raster, transform)
		assert len(values) == 3
		assert values[0] == 1.0
		assert values[1] == 5.0
		assert values[2] == 9.0

	def test_out_of_bounds_skipped(self, raster, transform):
		pts = np.array([[-10.0, -10.0]])
		values = _sample_raster_values(pts, raster, transform)
		assert len(values) == 0

	# Partial out of bounds: some in, some out
	def test_mixed_bounds(self, raster, transform):
		pts = np.array([
			[0.4, 2.6],  # in
			[100.0, 100.0],  # out
		])
		values = _sample_raster_values(pts, raster, transform)
		assert len(values) == 1

	def test_none_raster_returns_empty(self):
		pts = np.array([[0.4, 2.6]])
		values = _sample_raster_values(pts, None, Affine(1.0, 0.0, 0.0, 0.0, -1.0, 3.0))
		assert len(values) == 0

	def test_none_transform_returns_empty(self, raster):
		pts = np.array([[0.4, 2.6]])
		values = _sample_raster_values(pts, raster, None)
		assert len(values) == 0

	def test_empty_points(self, raster, transform):
		pts = np.empty((0, 2))
		values = _sample_raster_values(pts, raster, transform)
		assert len(values) == 0

	def test_nan_values_excluded(self, raster, transform):
		raster[0, 0] = float("nan")
		pts = np.array([[0.4, 2.6]])
		values = _sample_raster_values(pts, raster, transform)
		assert len(values) == 0


# ── _add_context_stats ───────────────────────────────────────────────

class TestAddContextStats:
	@pytest.fixture
	def empty_stats(self):
		return {
			"max_temperature": 0.0, "min_temperature": 0.0, "average_temperature": 0.0,
			"percent_illumination": 0.0,
			"average_meteor_flux": 0.0, "max_meteor_flux": 0.0, "min_meteor_flux": 0.0,
			"average_meteor_number": 0.0, "max_meteor_number": 0.0, "min_meteor_number": 0.0,
		}

	@pytest.fixture
	def transform_2x2(self):
		# 2x2 raster: Affine(1, 0, 0, 0, -1, 2)
		# x = col, y = -row + 2  →  col = x, row = 2 - y
		# Pixel (0,0) top row → point near (0.4, 1.6)
		# Pixel (1,1) bottom-right → point near (1.4, 0.6)
		return Affine(1.0, 0.0, 0.0, 0.0, -1.0, 2.0)

	def test_temperature_stats(self, empty_stats, transform_2x2):
		temp_map = np.array([[250.0, 260.0], [270.0, 280.0]], dtype=np.float32)
		pts = np.array([
			[0.4, 1.6],  # (0, 0) → 250
			[1.4, 1.6],  # (1, 0) → 260
			[0.4, 0.6],  # (0, 1) → 270
		])
		_add_context_stats(empty_stats, pts, temp_map, transform_2x2)
		assert empty_stats["max_temperature"] == 270.0
		assert empty_stats["min_temperature"] == 250.0
		assert empty_stats["average_temperature"] == pytest.approx(260.0, abs=0.1)

	def test_illumination_percent(self, empty_stats, transform_2x2):
		illum_map = np.array([[0.0, 0.0], [1.0, 1.0]], dtype=np.float32)
		pts = np.array([
			[0.4, 1.6],  # (0, 0) → 0.0
			[0.4, 0.6],  # (0, 1) → 1.0
			[1.4, 0.6],  # (1, 1) → 1.0
		])
		_add_context_stats(empty_stats, pts, None, None, illum_map, transform_2x2)
		# 3 points: illum values [0, 1, 1] → 2/3 ≈ 66.7%
		assert empty_stats["percent_illumination"] == pytest.approx(66.67, abs=0.1)

	def test_meteor_flux_stats(self, empty_stats, transform_2x2):
		meteor_map = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
		pts = np.array([
			[1.4, 0.6],  # (1, 1) → 4.0
			[0.4, 0.6],  # (0, 1) → 3.0
		])
		_add_context_stats(empty_stats, pts, None, None, None, None, meteor_map, transform_2x2)
		assert empty_stats["average_meteor_flux"] == pytest.approx(3.5)
		assert empty_stats["max_meteor_flux"] == 4.0
		assert empty_stats["min_meteor_flux"] == 3.0

	def test_all_none_maps_no_crash(self, empty_stats):
		pts = np.array([[0.4, 1.6]])
		_add_context_stats(empty_stats, pts, None, None, None, None, None, None)
		assert empty_stats["max_temperature"] == 0.0
		assert empty_stats["percent_illumination"] == 0.0
		assert empty_stats["average_meteor_flux"] == 0.0


# ── calculate_path_stats (integration-level) ────────────────────────

class TestCalculatePathStats:
	def test_less_than_two_points_returns_empty(self):
		pts = np.array([[0.0, 0.0, 100.0]])
		stats = calculate_path_stats(pts)
		assert stats["total_distance"] == 0.0
		assert stats["percent_illumination"] == 0.0

	def test_no_maps_basic_stats(self):
		pts = np.array([[0.0, 0.0, 100.0], [10.0, 0.0, 110.0], [20.0, 5.0, 105.0]])
		stats = calculate_path_stats(pts)
		assert stats["total_distance_travelled"] > 0.0
		assert stats["total_displacement"] > 0.0
		assert stats["total_elevation_gain"] > 0.0

	def test_with_elevation_map(self):
		"""When elevation map is provided, integrated stats are calculated."""
		elev = np.ones((10, 10), dtype=np.float32) * 100.0
		elev[0, :] = 90.0
		transform = Affine(1.0, 0.0, 0.0, 0.0, -1.0, 10.0)
		pts = np.array([[0.5, 9.5, 0.0], [9.5, 0.5, 0.0]], dtype=np.float64)
		stats = calculate_path_stats(pts, elevation_map=elev, transform=transform)
		assert stats["total_distance_travelled"] > 0.0
		assert "average_slope" in stats
		assert "surface_average_slope" in stats

	def test_with_slope_map(self):
		elev = np.ones((10, 10), dtype=np.float32) * 100.0
		slope = np.full((10, 10), 5.0, dtype=np.float32)  # 5° everywhere
		transform = Affine(1.0, 0.0, 0.0, 0.0, -1.0, 10.0)
		pts = np.array([[0.5, 9.5, 0.0], [9.5, 0.5, 0.0]], dtype=np.float64)
		stats = calculate_path_stats(pts, elev, transform, slope_map=slope)
		assert stats["surface_average_slope"] == pytest.approx(5.0, abs=0.1)
		assert stats["surface_max_slope"] == pytest.approx(5.0, abs=0.1)
		assert stats["surface_min_slope"] == pytest.approx(5.0, abs=0.1)

	def test_with_temperature_map(self):
		elev = np.ones((10, 10), dtype=np.float32) * 100.0
		temp = np.full((10, 10), 250.0, dtype=np.float32)
		transform = Affine(1.0, 0.0, 0.0, 0.0, -1.0, 10.0)
		pts = np.array([[0.5, 9.5, 0.0], [9.5, 0.5, 0.0]], dtype=np.float64)
		stats = calculate_path_stats(
			pts, elev, transform,
			temperature_map=temp, temperature_transform=transform,
		)
		assert stats["average_temperature"] == pytest.approx(250.0, abs=0.5)

	def test_multiple_context_maps(self):
		elev = np.ones((10, 10), dtype=np.float32) * 100.0
		illum = np.ones((10, 10), dtype=np.float32)
		illum[0:5, :] = 0.0  # half shadowed
		transform = Affine(1.0, 0.0, 0.0, 0.0, -1.0, 10.0)
		pts = np.array([[0.5, 9.5, 0.0], [9.5, 0.5, 0.0]], dtype=np.float64)
		stats = calculate_path_stats(
			pts, elev, transform,
			illumination_map=illum, illumination_transform=transform,
		)
		assert 0.0 < stats["percent_illumination"] < 100.0
