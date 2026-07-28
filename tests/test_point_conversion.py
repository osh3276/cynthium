"""Tests for coordinate system conversions (stereographic ↔ lon/lat)."""

import math

import pytest

from cynthium.app.engine.raster.point_conversion import (
	longlat_to_xy,
	xy_to_longlat,
)


# The moon radius is ~1737400m, so 1° ≈ 30319 m at the equator.
# At -89° latitude (south pole region), 1° lon ≈ 30319 * cos(89°) ≈ 529 m.
# We test round-trip and basic sanity.

LON_TOL = 1e-4  # degrees
LAT_TOL = 1e-4
XY_TOL = 5.0  # meters — stereographic projection near pole is sensitive


class TestXYToLongLat:
	def test_origin(self):
		# The stereographic origin is at lat=-90, lon=0
		lon, lat = xy_to_longlat(0.0, 0.0)
		assert lat == pytest.approx(-90.0, abs=LAT_TOL)
		assert lon == pytest.approx(0.0, abs=LON_TOL)

	def test_point_near_south_pole(self):
		lon, lat = xy_to_longlat(10000.0, 10000.0)
		assert lat < -80.0  # should still be in the south polar region
		assert isinstance(lon, float)
		assert isinstance(lat, float)


class TestLongLatToXY:
	def test_south_pole_origin(self):
		x, y = longlat_to_xy(0.0, -90.0)
		assert x == pytest.approx(0.0, abs=XY_TOL)
		assert y == pytest.approx(0.0, abs=XY_TOL)

	def test_point_returns_float(self):
		x, y = longlat_to_xy(0.0, -89.0)
		assert isinstance(x, float)
		assert isinstance(y, float)


class TestRoundTrip:
	def test_round_trip_near_pole(self):
		"""xy → lon/lat → xy should be approximately identity."""
		xy_pairs = [
			(0.0, 0.0),
			(10000.0, 0.0),
			(0.0, -10000.0),
			(5000.0, -5000.0),
			(-2000.0, 3000.0),
		]
		for x, y in xy_pairs:
			lon, lat = xy_to_longlat(x, y)
			x2, y2 = longlat_to_xy(lon, lat)
			assert x2 == pytest.approx(x, abs=XY_TOL), f"x mismatch for ({x}, {y})"
			assert y2 == pytest.approx(y, abs=XY_TOL), f"y mismatch for ({x}, {y})"

	def test_round_trip_longlat(self):
		"""lon/lat → xy → lon/lat should be approximately identity."""
		ll_pairs = [
			(0.0, -90.0),
			(10.0, -89.5),
			(-30.0, -88.0),
			(180.0, -89.0),
			(-150.0, -87.0),
		]
		for lon, lat in ll_pairs:
			x, y = longlat_to_xy(lon, lat)
			lon2, lat2 = xy_to_longlat(x, y)
			assert lon2 == pytest.approx(lon, abs=0.5), f"lon mismatch for ({lon}, {lat})"
			assert lat2 == pytest.approx(lat, abs=0.1), f"lat mismatch for ({lon}, {lat})"

	def test_swap_operations_dont_error(self):
		"""Calling xy→lon/lat then lon/lat→xy twice should not crash."""
		lon, lat = xy_to_longlat(7500.0, -3200.0)
		x2, y2 = longlat_to_xy(lon, lat)
		lon2, lat2 = xy_to_longlat(x2, y2)
		assert math.isfinite(lon2)
		assert math.isfinite(lat2)
