"""Tests for multi-angle map swapping during long traversals."""

from __future__ import annotations

import numpy as np
import pytest
from affine import Affine

from cynthium.app.config import LUNAR_DAY_S
from cynthium.app.engine.simulation._sim_utils import (
	_get_linear_angle_bin,
	_round_azimuth_to_nearest_12,
)
from cynthium.app.engine.simulation.rover_4wd import simulate_rover_4wd
from cynthium.app.engine.simulation.rover_settings import RoverSettings


# ── Helpers ──────────────────────────────────────────────────────────────────────


def _slow_rover() -> RoverSettings:
	"""A rover that drives slowly (low power) but can still complete a short path."""
	return RoverSettings(
		mass_kg=200.0,
		power_hp=0.01,
		wheel_friction_coeff=0.6,
		rolling_resistance_coeff=0.02,
		wheel_radius_m=0.5,
		motor_peak_torque_nm=None,
		track_width_m=1.0,
		wheelbase_m=1.5,
		battery_capacity_wh=50000.0,  # big battery so it doesn't die during long pauses
		motor_max_rpm=200.0,
		target_cruise_speed_mps=0.5,
		max_brake_decel_mps2=1.0,
		idle_drain_w=10.0,
	)


# ======================================================================
# Unit tests: _round_azimuth_to_nearest_12
# ======================================================================


class TestRoundAzimuth:
	def test_exact_bin(self):
		assert _round_azimuth_to_nearest_12(0.0) == 0
		assert _round_azimuth_to_nearest_12(12.0) == 12
		assert _round_azimuth_to_nearest_12(24.0) == 24
		assert _round_azimuth_to_nearest_12(348.0) == 348

	def test_rounds_to_nearest(self):
		# 5° is closer to 0° than 12°
		assert _round_azimuth_to_nearest_12(5.0) == 0
		# 7° is closer to 12° than 0°
		assert _round_azimuth_to_nearest_12(7.0) == 12
		# 354° is exactly halfway between 348 and 360 → round up to 0/360
		assert _round_azimuth_to_nearest_12(354.0) == 0
		# 353° is closer to 348° than 360°
		assert _round_azimuth_to_nearest_12(353.0) == 348
		# 357° is closer to 0/360 than 348
		assert _round_azimuth_to_nearest_12(357.0) == 0

	def test_wraps_beyond_360(self):
		# 365° → 5° → rounds to 0°
		assert _round_azimuth_to_nearest_12(365.0) == 0
		# 370° → 10° → rounds to 12°
		assert _round_azimuth_to_nearest_12(370.0) == 12

	def test_negative_angles(self):
		# -5° → 355° → 355 is closer to 360/0 (dist 5) than 348 (dist 7)
		assert _round_azimuth_to_nearest_12(-5.0) == 0
		# -10° → 350° → closer to 348° (dist 2) than 360° (dist 10)
		assert _round_azimuth_to_nearest_12(-10.0) == 348
		# -11° → 349° → closer to 348° (dist 1) than 360° (dist 11)
		assert _round_azimuth_to_nearest_12(-11.0) == 348
		# -1° → 359° → closer to 0/360 (dist 1) than 348 (dist 11)
		assert _round_azimuth_to_nearest_12(-1.0) == 0

	def test_exactly_halfway_goes_up(self):
		# 6° is exactly halfway between 0 and 12 → rounds to 12 (round half up)
		assert _round_azimuth_to_nearest_12(6.0) == 12
		# 354° is exactly halfway between 348 and 360 → rounds to 0 (round half up)
		assert _round_azimuth_to_nearest_12(354.0) == 0


# ======================================================================
# Unit tests: _get_linear_angle_bin (linear fallback used when no SPICE)
# ======================================================================
# ======================================================================

BIN_S = LUNAR_DAY_S / 30  # ~84 960 s


class TestLinearAngleBin:
	def test_starts_at_start_angle(self):
		assert _get_linear_angle_bin(0, 0.0) == 0
		assert _get_linear_angle_bin(36, 0.0) == 36
		assert _get_linear_angle_bin(180, 0.0) == 180

	def test_advances_one_bin_after_one_interval(self):
		assert _get_linear_angle_bin(0, BIN_S * 1.001) == 12
		assert _get_linear_angle_bin(36, BIN_S * 1.001) == 48

	def test_stays_in_start_bin_before_half_interval(self):
		assert _get_linear_angle_bin(0, BIN_S * 0.4) == 0
		assert _get_linear_angle_bin(36, BIN_S * 0.4) == 36

	def test_wraps_after_full_lunar_day(self):
		assert _get_linear_angle_bin(0, LUNAR_DAY_S) == 0
		assert _get_linear_angle_bin(36, LUNAR_DAY_S) == 36

	def test_half_lunar_day_opposite_angle(self):
		assert _get_linear_angle_bin(0, LUNAR_DAY_S / 2) == 180

	def test_wraps_multiple_days(self):
		assert _get_linear_angle_bin(0, LUNAR_DAY_S * 2.5) == 180

	def test_multiple_bin_advance(self):
		assert _get_linear_angle_bin(0, BIN_S * 5.001) == 60

	def test_starts_from_non_zero_mid_day(self):
		assert _get_linear_angle_bin(72, 0.0) == 72
		assert _get_linear_angle_bin(72, BIN_S * 1.001) == 84
		assert _get_linear_angle_bin(72, BIN_S * 2.001) == 96


# ======================================================================
# Shared fixtures for integration tests
# ======================================================================

BIG_BATTERY = RoverSettings(
	mass_kg=200.0,
	power_hp=0.01,
	wheel_friction_coeff=0.6,
	rolling_resistance_coeff=0.02,
	wheel_radius_m=0.5,
	motor_peak_torque_nm=None,
	track_width_m=1.0,
	wheelbase_m=1.5,
	battery_capacity_wh=50000.0,
	motor_max_rpm=200.0,
	target_cruise_speed_mps=0.5,
	max_brake_decel_mps2=1.0,
	idle_drain_w=10.0,
)

MAP_TRANSFORM = Affine(1.0, 0.0, 0.0, 0.0, -1.0, 20.0)
_MAP_SHAPE = (20, 20)


def _constant_map(value: float) -> np.ndarray:
	return np.full(_MAP_SHAPE, value, dtype=np.float64)


# ======================================================================
# Integration tests: multi-angle map swapping in the physics sim
# ======================================================================


class TestMultiAngleIlluminationSwap:
	"""Verify that illumination maps are swapped mid-simulation when total_time
	crosses a 12° bin boundary."""

	@pytest.fixture(params=["two_wp", "three_wp"])
	def path_pair(self, request):
		"""Parametrized fixture: two or three waypoints."""
		if request.param == "two_wp":
			pts = np.zeros((11, 3), dtype=np.float64)
			pts[:, 0] = np.arange(11, dtype=np.float64)
			pts[:, 1] = 5.0
			waypoints_xy = np.array([[0.0, 5.0], [10.0, 5.0]], dtype=np.float64)
			return pts, waypoints_xy, False
		else:
			pts = np.zeros((21, 3), dtype=np.float64)
			pts[:, 0] = np.arange(21, dtype=np.float64)
			pts[:, 1] = 5.0
			waypoints_xy = np.array([[0.0, 5.0], [10.0, 5.0], [20.0, 5.0]], dtype=np.float64)
			return pts, waypoints_xy, True

	@pytest.fixture
	def illum_maps(self):
		"""Three illumination maps with distinct constant values (W/m²).

		- angle 0:  1.0 W/m²
		- angle 12: 2.0 W/m²
		- angle 24: 3.0 W/m²
		"""
		return {
			0: (_constant_map(1.0), MAP_TRANSFORM),
			12: (_constant_map(2.0), MAP_TRANSFORM),
			24: (_constant_map(3.0), MAP_TRANSFORM),
		}

	def test_maps_swap_during_long_pause(self, illum_maps):
		"""Rover drives to middle waypoint, pauses long enough to cross
		one bin boundary. The map swap is verified by showing that:
		1) The simulation crosses the bin boundary in sim time
		2) The energy from the final drive leg is higher because map-12
		   (2.0 W/m²) is used instead of map-0 (1.0).

		Note: energy only accumulates during DRIVE mode (not PAUSE/STOP).
		"""
		# 3 waypoints so pause triggers at the middle one
		pts = np.zeros((21, 3), dtype=np.float64)
		pts[:, 0] = np.arange(21, dtype=np.float64)
		pts[:, 1] = 5.0
		waypoints_xy = np.array([[0.0, 5.0], [10.0, 5.0], [20.0, 5.0]], dtype=np.float64)
		rover = BIG_BATTERY

		# Run IDENTICAL paths but with different pause durations:
		#   SHORT pause: never crosses bin boundary → map-0 throughout
		#   LONG  pause: crosses bin boundary → map-0 then map-12

		short_pause = BIN_S * 0.2  # well inside bin 0 (no swap)
		long_pause  = BIN_S * 0.5 + 400.0  # crosses half-bin → swap to bin 12

		def _run(pause: float) -> dict:
			return simulate_rover_4wd(
				pts_xyz=pts,
				waypoints_xy=waypoints_xy,
				rover=rover,
				wheel_friction_coeff=float(rover.wheel_friction_coeff),
				power_w=float(rover.power_w),
				illumination_maps=illum_maps,
				start_angle_deg=0,
				g_mps2=1.625,
				v0_mps=0.0,
				v_min_power_mps=0.001,
				max_steps=600_000,
				pause_durations=[pause],
			)

		result_no_swap = _run(short_pause)
		result_swap = _run(long_pause)

		assert result_no_swap["traverse_feasible"] == 1.0
		assert result_swap["traverse_feasible"] == 1.0
		assert result_swap["traversal_time_s"] > BIN_S * 0.5, "Didn't cross bin boundary"

		# The initial drive (wp0→wp1) is identical in both runs.
		# The final drive (wp1→wp2) differs:
		#   no-swap: uses map-0 (1.0 W/m²)
		#   swap:    uses map-12 (2.0 W/m²)
		#
		# Since both drives are ~same distance (~10m at ~0.5 m/s ≈ 20s),
		# the energy with the swap should be noticeably higher.
		#
		# E_initial ≈ 20 * 1.0 = 20 J
		# E_final_no_swap ≈ 20 * 1.0 = 20 J  → total ≈ 40 J
		# E_final_swap   ≈ 20 * 2.0 = 40 J  → total ≈ 60 J
		energy_no_swap = result_no_swap["solar_energy_per_m2_j"]
		energy_swap = result_swap["solar_energy_per_m2_j"]

		assert energy_swap > energy_no_swap + 10.0, (
			f"Swap energy {energy_swap:.1f} should be > no-swap {energy_no_swap:.1f} + 10"
		)
		# Ratio should reflect ~1.5x more energy from map-12 vs map-0 on final leg
		ratio = energy_swap / max(energy_no_swap, 0.1)
		assert ratio > 1.2, (
			f"Energy ratio {ratio:.2f} too low — map swap probably didn't happen"
		)

	def test_single_map_fallback(self):
		"""When illumination_maps is None, the original single-map path is used."""
		pts = np.zeros((11, 3), dtype=np.float64)
		pts[:, 0] = np.arange(11, dtype=np.float64)
		pts[:, 1] = 5.0
		waypoints_xy = np.array([[0.0, 5.0], [10.0, 5.0]], dtype=np.float64)
		rover = BIG_BATTERY

		illum_map = _constant_map(42.0)

		result = simulate_rover_4wd(
			pts_xyz=pts,
			waypoints_xy=waypoints_xy,
			rover=rover,
			wheel_friction_coeff=float(rover.wheel_friction_coeff),
			power_w=float(rover.power_w),
			illumination_map=illum_map,
			illumination_transform=MAP_TRANSFORM,
			g_mps2=1.625,
			v0_mps=0.0,
			v_min_power_mps=0.001,
			max_steps=100_000,
		)

		assert result["traverse_feasible"] == 1.0
		assert result["avg_solar_illumination_w_per_m2"] == pytest.approx(42.0, abs=5.0)

	def test_no_swap_with_short_traversal(self, illum_maps):
		"""With a short drive (no pause), the bin doesn't change, only start map used."""
		pts = np.zeros((11, 3), dtype=np.float64)
		pts[:, 0] = np.arange(11, dtype=np.float64)
		pts[:, 1] = 5.0
		waypoints_xy = np.array([[0.0, 5.0], [10.0, 5.0]], dtype=np.float64)
		rover = BIG_BATTERY

		result = simulate_rover_4wd(
			pts_xyz=pts,
			waypoints_xy=waypoints_xy,
			rover=rover,
			wheel_friction_coeff=float(rover.wheel_friction_coeff),
			power_w=float(rover.power_w),
			illumination_maps=illum_maps,
			start_angle_deg=0,
			g_mps2=1.625,
			v0_mps=0.0,
			v_min_power_mps=0.001,
			max_steps=50_000,
		)

		assert result["traverse_feasible"] == 1.0
		total_time = result["traversal_time_s"]
		energy = result["solar_energy_per_m2_j"]
		# Only map 0 (value 1.0) used, so energy ≈ total_time
		assert energy == pytest.approx(total_time * 1.0, abs=total_time * 0.05)

	def test_start_angle_36_uses_correct_initial_map(self):
		"""Starting at angle 36° should use the angle-36 map initially."""
		pts = np.zeros((11, 3), dtype=np.float64)
		pts[:, 0] = np.arange(11, dtype=np.float64)
		pts[:, 1] = 5.0
		waypoints_xy = np.array([[0.0, 5.0], [10.0, 5.0]], dtype=np.float64)
		rover = BIG_BATTERY

		# Only provide map for angle 36 with value 99.0
		maps = {36: (_constant_map(99.0), MAP_TRANSFORM)}

		result = simulate_rover_4wd(
			pts_xyz=pts,
			waypoints_xy=waypoints_xy,
			rover=rover,
			wheel_friction_coeff=float(rover.wheel_friction_coeff),
			power_w=float(rover.power_w),
			illumination_maps=maps,
			start_angle_deg=36,
			g_mps2=1.625,
			v0_mps=0.0,
			v_min_power_mps=0.001,
			max_steps=50_000,
		)

		assert result["traverse_feasible"] == 1.0
		assert result["avg_solar_illumination_w_per_m2"] == pytest.approx(99.0, abs=5.0)


class TestMultiAngleMeteorSwap:
	"""Verify that meteor energy maps are passed through correctly."""

	def test_meteor_maps_dont_crash(self):
		"""Meteor maps can be provided without illumination maps."""
		# 3 waypoints so pause triggers at the middle one
		pts = np.zeros((21, 3), dtype=np.float64)
		pts[:, 0] = np.arange(21, dtype=np.float64)
		pts[:, 1] = 5.0
		waypoints_xy = np.array([[0.0, 5.0], [10.0, 5.0], [20.0, 5.0]], dtype=np.float64)
		rover = BIG_BATTERY

		meteor_maps = {
			0: (_constant_map(10.0), MAP_TRANSFORM),
			12: (_constant_map(20.0), MAP_TRANSFORM),
		}

		# Pause just past the bin boundary
		pause = BIN_S * 0.5 + 200.0
		result = simulate_rover_4wd(
			pts_xyz=pts,
			waypoints_xy=waypoints_xy,
			rover=rover,
			wheel_friction_coeff=float(rover.wheel_friction_coeff),
			power_w=float(rover.power_w),
			meteor_energy_maps=meteor_maps,
			start_angle_deg=0,
			g_mps2=1.625,
			v0_mps=0.0,
			v_min_power_mps=0.001,
			max_steps=600_000,
			pause_durations=[pause],
		)

		assert result["traverse_feasible"] == 1.0
		assert result["traversal_time_s"] > BIN_S * 0.5  # crossed at least half a bin

	def test_both_illumination_and_meteor_maps(self):
		"""Both illumination and meteor maps can be provided simultaneously."""
		pts = np.zeros((11, 3), dtype=np.float64)
		pts[:, 0] = np.arange(11, dtype=np.float64)
		pts[:, 1] = 5.0
		waypoints_xy = np.array([[0.0, 5.0], [10.0, 5.0]], dtype=np.float64)
		rover = BIG_BATTERY

		illum_maps = {0: (_constant_map(5.0), MAP_TRANSFORM)}
		meteor_maps = {0: (_constant_map(50.0), MAP_TRANSFORM)}

		result = simulate_rover_4wd(
			pts_xyz=pts,
			waypoints_xy=waypoints_xy,
			rover=rover,
			wheel_friction_coeff=float(rover.wheel_friction_coeff),
			power_w=float(rover.power_w),
			illumination_maps=illum_maps,
			meteor_energy_maps=meteor_maps,
			start_angle_deg=0,
			g_mps2=1.625,
			v0_mps=0.0,
			v_min_power_mps=0.001,
			max_steps=50_000,
		)

		assert result["traverse_feasible"] == 1.0
		# Illumination should be ~5.0 (from illum map)
		assert result["avg_solar_illumination_w_per_m2"] == pytest.approx(5.0, abs=1.0)
