"""Tests for simulation utility functions — corner detection, speed profiling,
pitch sampling, resolution estimation, and helpers."""

import numpy as np
import pytest

from cynthium.app.engine.simulation._sim_utils import (
	_clamp,
	_compute_target_speeds,
	_detect_corners,
	_empty_result,
	_estimate_resolution,
	_normalise_angle,
	_sample_pitch,
	_sample_target_speed,
)
from cynthium.app.engine.simulation.rover_settings import RoverSettings, G_MPS2


class TestClamp:
	def test_within_range(self):
		assert _clamp(5.0, 0.0, 10.0) == 5.0

	def test_below_min(self):
		assert _clamp(-5.0, 0.0, 10.0) == 0.0

	def test_above_max(self):
		assert _clamp(15.0, 0.0, 10.0) == 10.0

	def test_edge_values(self):
		assert _clamp(0.0, 0.0, 10.0) == 0.0
		assert _clamp(10.0, 0.0, 10.0) == 10.0


class TestNormaliseAngle:
	def test_zero(self):
		assert _normalise_angle(0.0) == 0.0

	def test_positive(self):
		assert _normalise_angle(1.5) == 1.5

	def test_wrap_above_pi(self):
		result = _normalise_angle(4.0)  # 4 > π ≈ 3.14
		assert -np.pi < result < np.pi
		assert result == pytest.approx(4.0 - 2 * np.pi)

	def test_wrap_below_neg_pi(self):
		result = _normalise_angle(-4.0)
		assert -np.pi < result < np.pi
		assert result == pytest.approx(-4.0 + 2 * np.pi)

	def test_multiple_wraps(self):
		result = _normalise_angle(10 * np.pi)
		assert -np.pi < result < np.pi


class TestDetectCorners:
	def test_less_than_three_points(self):
		path = np.array([[0.0, 0.0], [1.0, 0.0]])
		assert _detect_corners(path) == []

	def test_straight_line_no_corners(self):
		path = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 0.0]])
		assert _detect_corners(path) == []

	def test_right_angle_corner(self):
		path = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]])
		corners = _detect_corners(path)
		assert len(corners) == 1
		assert corners[0] == 1  # middle point

	def test_sharp_corner_detected(self):
		path = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [2.0, 1.0], [3.0, 2.0]])
		corners = _detect_corners(path)
		# At index 2, path goes from (2,0) to (2,1) which is a right angle from (1,0)→(2,0)
		assert 2 in corners

	def test_no_false_positive_on_shallow_angle(self):
		# Very shallow angle (< 1° from straight)
		path = np.array([[0.0, 0.0], [100.0, 0.0], [101.0, 0.01]])
		corners = _detect_corners(path)
		assert corners == []  # angle is below threshold

	def test_degenerate_segment_skipped(self):
		"""Zero-length segment causes the corner to be skipped entirely."""
		path = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 0.0], [1.0, 1.0]])
		corners = _detect_corners(path)
		# At i=1: l1=0 → skip. At i=2: v1=(0,0), l1=0 → skip.
		# No corner detected because the degenerate point breaks the chain.
		assert len(corners) == 0


class TestComputeTargetSpeeds:
	@pytest.fixture
	def rover(self):
		return RoverSettings(
			mass_kg=200.0, power_hp=0.5,
			wheel_friction_coeff=0.6, rolling_resistance_coeff=0.02,
		)

	def test_no_corners_constant_speed(self, rover):
		path = np.array([[0.0, 0.0], [10.0, 0.0], [20.0, 0.0]])
		dists = np.array([0.0, 10.0, 20.0])
		table = _compute_target_speeds(path, dists, [], rover, rover.power_w, 0.02, 200.0, G_MPS2)
		assert len(table) == 3
		# All targets should be the same baseline speed
		assert np.allclose(table[:, 1], table[0, 1], rtol=0.01)

	def test_slowdown_at_corner(self, rover):
		path = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0]])
		dists = np.array([0.0, 10.0, np.sqrt(10**2 + 10**2)])
		corners = [1]
		table = _compute_target_speeds(path, dists, corners, rover, rover.power_w, 0.02, 200.0, G_MPS2)
		# Corner speed is floored at 0.3 m/s minimum
		assert table[1, 1] == 0.3  # minimum speed floor
		# Points before/after corner should have higher speed
		assert table[0, 1] >= 0.3
		assert table[0, 1] > 0.0  # non-zero before

	def test_minimum_speed_floor(self, rover):
		"""Targets should floor at 0.3 m/s to avoid complete stop."""
		path = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]])
		dists = np.array([0.0, 1.0, 2.0])
		# No corners, but long approach distance
		table = _compute_target_speeds(path, dists, [], rover, rover.power_w, 0.02, 200.0, G_MPS2)
		assert np.all(table[:, 1] >= 0.3)


class TestSampleTargetSpeed:
	def test_at_start(self):
		table = np.array([[0.0, 1.0], [10.0, 2.0], [20.0, 1.5]])
		assert _sample_target_speed(0.0, table, 20.0) == 1.0

	def test_at_end(self):
		table = np.array([[0.0, 1.0], [10.0, 2.0], [20.0, 1.5]])
		assert _sample_target_speed(20.0, table, 20.0) == 1.5

	def test_interpolation(self):
		table = np.array([[0.0, 0.0], [10.0, 10.0]])
		assert _sample_target_speed(5.0, table, 10.0) == 5.0

	def test_clamps_below(self):
		table = np.array([[5.0, 1.0], [10.0, 2.0]])
		assert _sample_target_speed(0.0, table, 10.0) == 1.0

	def test_clamps_above(self):
		table = np.array([[0.0, 1.0], [10.0, 2.0]])
		assert _sample_target_speed(20.0, table, 10.0) == 2.0

	def test_empty_table(self):
		table = np.empty((0, 2))
		assert _sample_target_speed(5.0, table, 10.0) == 1.0  # default


class TestSamplePitch:
	def test_flat_terrain(self):
		pts = np.array([[0.0, 0.0, 100.0], [10.0, 0.0, 100.0]])
		pitch = _sample_pitch(5.0, 0.0, pts)
		assert pitch == pytest.approx(0.0, abs=1e-6)

	def test_uphill(self):
		pts = np.array([[0.0, 0.0, 100.0], [10.0, 0.0, 110.0]])
		pitch = _sample_pitch(5.0, 0.0, pts)
		# Rise 10 over 10 = 45°
		assert pitch == pytest.approx(np.arctan2(10.0, 10.0))

	def test_downhill_negative(self):
		pts = np.array([[0.0, 0.0, 110.0], [10.0, 0.0, 100.0]])
		pitch = _sample_pitch(5.0, 0.0, pts)
		assert pitch == pytest.approx(np.arctan2(-10.0, 10.0))

	def test_less_than_two_points(self):
		pts = np.array([[5.0, 5.0, 100.0]])
		pitch = _sample_pitch(5.0, 5.0, pts)
		assert pitch == 0.0

	def test_hint_idx_restricts_search(self):
		pts = np.zeros((50, 3), dtype=np.float64)
		pts[:, 0] = np.arange(50, dtype=np.float64)
		pts[:, 2] = 100.0
		# Steep section at index 10
		pts[11, 2] = 110.0
		pitch = _sample_pitch(10.5, 0.0, pts, hint_idx=10)
		assert pitch > 0.0

	def test_hint_idx_out_of_range_no_crash(self):
		pts = np.array([[0.0, 0.0, 100.0], [10.0, 0.0, 100.0]])
		pitch = _sample_pitch(5.0, 0.0, pts, hint_idx=999)
		assert isinstance(pitch, float)


class TestEstimateResolution:
	def test_two_points(self):
		pts = np.array([[0.0, 0.0, 0.0], [5.0, 0.0, 0.0]])
		assert _estimate_resolution(pts) == pytest.approx(5.0)

	def test_multiple_segments(self):
		pts = np.array([
			[0.0, 0.0, 0.0],
			[3.0, 0.0, 0.0],
			[3.0, 7.0, 0.0],
		])
		res = _estimate_resolution(pts)
		assert res == pytest.approx(np.median([3.0, 7.0]))

	def test_fewer_than_two(self):
		pts = np.array([[5.0, 5.0, 100.0]])
		assert _estimate_resolution(pts) == 5.0  # default

	def test_zero_length_segments(self):
		pts = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [5.0, 0.0, 0.0]])
		res = _estimate_resolution(pts)
		assert res == pytest.approx(5.0)


class TestEmptyResult:
	def test_all_keys_present(self):
		result = _empty_result()
		expected_keys = {
			"traverse_feasible", "traversal_time_s", "average_velocity_mps",
			"min_velocity_mps", "max_velocity_mps", "solar_energy_per_m2_j",
			"avg_solar_illumination_w_per_m2", "failure_x", "failure_y",
			"failure_reason", "rollover_occurred", "max_lateral_accel_mps2",
			"braking_events", "max_braking_decel_mps2", "battery_energy_used_j",
			"battery_remaining_pct", "battery_capacity_wh",
		}
		assert set(result.keys()) == expected_keys

	def test_feasible_by_default(self):
		assert _empty_result()["traverse_feasible"] == 1.0
