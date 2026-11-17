"""Tests for raster loading/selection logic — no file I/O needed for pure functions."""

import numpy as np
import pytest

from cynthium.app.config import ANGLE_BIN_DEG, NUM_ANGLE_BINS
from cynthium.app.services.site_rasters import (
	_fallback_if_missing,
	_normalize_map_key,
	angle_bins_from_azimuths,
	select_display_raster,
)


# ── angle_bins_from_azimuths ─────────────────────────────────────────

class TestAngleBinsFromAzimuths:
	"""Bins must follow the sun's actual azimuth path, in either direction."""

	def test_single_sample(self):
		assert angle_bins_from_azimuths([0.0]) == [0]
		assert angle_bins_from_azimuths([36.0]) == [36]

	def test_increasing_azimuth(self):
		assert angle_bins_from_azimuths([0.0, 12.0, 24.0]) == [0, 12, 24]

	def test_decreasing_azimuth(self):
		# Regression: south-polar sites see the azimuth recede, so the bins
		# must be preloaded downwards, not upwards.
		assert angle_bins_from_azimuths([288.0, 276.0, 264.0]) == [288, 276, 264]

	def test_samples_inside_one_bin_collapse(self):
		assert angle_bins_from_azimuths([1.0, 3.0, 5.0]) == [0]

	def test_wraps_through_north(self):
		assert angle_bins_from_azimuths([348.0, 0.0, 12.0]) == [348, 0, 12]

	def test_wraps_downwards_through_north(self):
		assert angle_bins_from_azimuths([12.0, 0.0, 348.0]) == [12, 0, 348]

	def test_bins_never_repeat(self):
		# Non-monotonic sun (low latitudes) revisits a bin; load it once.
		assert angle_bins_from_azimuths([10.0, 20.0, 10.0]) == [12, 24]

	def test_full_sweep_covers_every_bin(self):
		azimuths = [float(a) for a in range(0, 360, 5)]
		bins = angle_bins_from_azimuths(azimuths)
		assert bins == list(range(0, 360, ANGLE_BIN_DEG))
		assert len(bins) == NUM_ANGLE_BINS


# ── _normalize_map_key ───────────────────────────────────────────────

class TestNormalizeMapKey:
	def test_lowercases(self):
		assert _normalize_map_key("Elevation") == "elevation"

	def test_replaces_spaces(self):
		assert _normalize_map_key("Solar Illumination") == "solar_illumination"

	def test_strips_extra_underscores(self):
		assert _normalize_map_key("Solar   Illumination!!!") == "solar_illumination"

	def test_strips_leading_trailing(self):
		assert _normalize_map_key("  Slope  ") == "slope"

	def test_preserves_numbers(self):
		assert _normalize_map_key("Meteor Flux (mo. avg.)") == "meteor_flux_mo_avg"


# ── _fallback_if_missing ─────────────────────────────────────────────

class TestFallbackIfMissing:
	@pytest.fixture
	def elev(self):
		return np.array([[1.0]]), {"some": "meta"}

	@pytest.fixture
	def requested(self):
		return np.array([[42.0]]), {"key": "val"}

	def test_returns_requested_when_present(self, requested, elev):
		result = _fallback_if_missing(requested, elev, "Test")
		data, meta = result
		assert data is not None
		assert np.all(data == 42.0)

	def test_falls_back_when_none(self, elev):
		result = _fallback_if_missing((None, None), elev, "Test")
		data, meta = result
		assert np.all(data == 1.0)

	def test_falls_back_with_none_meta(self, elev):
		result = _fallback_if_missing((np.array([[99.0]]), None), elev, "Test")
		data, meta = result
		assert meta == {"some": "meta"}
		assert np.all(data == 99.0)


# ── select_display_raster ────────────────────────────────────────────

class TestSelectDisplayRaster:
	@pytest.fixture
	def rasters(self):
		elev = (np.array([[1.0]]), {})
		slope = (np.array([[2.0]]), {})
		illum = (np.array([[3.0]]), {})
		temp = (np.array([[4.0]]), {})
		meteor = (np.array([[5.0]]), {})
		meteor_num = (np.array([[6.0]]), {})
		psr = (np.array([[7.0]]), {})
		return elev, slope, illum, temp, meteor, meteor_num, psr

	def test_elevation(self, rasters):
		elev, slope, illum, temp, meteor, meteor_num, psr = rasters
		result = select_display_raster("Elevation", elev, slope, illum, temp, meteor, meteor_num, psr)
		data, _ = result
		assert np.all(data == 1.0)

	def test_slope(self, rasters):
		elev, slope, illum, temp, meteor, meteor_num, psr = rasters
		result = select_display_raster("Slope", elev, slope, illum, temp, meteor, meteor_num, psr)
		data, _ = result
		assert np.all(data == 2.0)

	def test_hillshade_returns_elevation(self, rasters):
		elev, slope, illum, temp, meteor, meteor_num, psr = rasters
		result = select_display_raster("Hillshade", elev, slope, illum, temp, meteor, meteor_num, psr)
		data, _ = result
		assert np.all(data == 1.0)

	def test_solar_illumination(self, rasters):
		elev, slope, illum, temp, meteor, meteor_num, psr = rasters
		result = select_display_raster("Solar Illumination (mo. avg.)", elev, slope, illum, temp, meteor, meteor_num, psr)
		data, _ = result
		assert np.all(data == 3.0)

	def test_temperature(self, rasters):
		elev, slope, illum, temp, meteor, meteor_num, psr = rasters
		result = select_display_raster("Average Temperature", elev, slope, illum, temp, meteor, meteor_num, psr)
		data, _ = result
		assert np.all(data == 4.0)

	def test_meteor_flux(self, rasters):
		elev, slope, illum, temp, meteor, meteor_num, psr = rasters
		result = select_display_raster("Meteor Flux (mo. avg.)", elev, slope, illum, temp, meteor, meteor_num, psr)
		data, _ = result
		assert np.all(data == 5.0)

	def test_meteor_number(self, rasters):
		elev, slope, illum, temp, meteor, meteor_num, psr = rasters
		result = select_display_raster("Meteor Number (mo. avg.)", elev, slope, illum, temp, meteor, meteor_num, psr)
		data, _ = result
		assert np.all(data == 6.0)

	def test_psr(self, rasters):
		elev, slope, illum, temp, meteor, meteor_num, psr = rasters
		result = select_display_raster("Permanently Shaded Regions", elev, slope, illum, temp, meteor, meteor_num, psr)
		data, _ = result
		assert np.all(data == 7.0)

	def test_psr_short_name(self, rasters):
		elev, slope, illum, temp, meteor, meteor_num, psr = rasters
		result = select_display_raster("psr", elev, slope, illum, temp, meteor, meteor_num, psr)
		data, _ = result
		assert np.all(data == 7.0)

	def test_unknown_type_falls_back_to_elevation(self, rasters):
		elev, slope, illum, temp, meteor, meteor_num, psr = rasters
		result = select_display_raster("Unknown Map Type", elev, slope, illum, temp, meteor, meteor_num, psr)
		data, _ = result
		assert np.all(data == 1.0)

	def test_missing_slope_falls_back_to_elevation(self, rasters):
		elev, slope, illum, temp, meteor, meteor_num, psr = rasters
		slope = (None, None)
		result = select_display_raster("Slope", elev, slope, illum, temp, meteor, meteor_num, psr)
		data, _ = result
		assert np.all(data == 1.0)  # falls back to elevation

	def test_missing_illumination_falls_back_to_elevation(self, rasters):
		elev, slope, illum, temp, meteor, meteor_num, psr = rasters
		illum = (None, None)
		result = select_display_raster("Solar Illumination (mo. avg.)", elev, slope, illum, temp, meteor, meteor_num, psr)
		data, _ = result
		assert np.all(data == 1.0)
