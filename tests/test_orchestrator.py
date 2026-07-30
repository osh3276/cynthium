"""Tests for the simulation orchestrator — compute_traversal_dynamics."""

import numpy as np
import pytest

from cynthium.app.engine.simulation.sim_orchestrator import compute_traversal_dynamics
from cynthium.app.engine.simulation.rover_settings import RoverSettings


SLOW_ROVER = RoverSettings(
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


class TestComputeTraversalDynamics:
	def test_less_than_two_waypoints(self):
		waypoints = np.array([[0.0, 0.0, 100.0]], dtype=np.float64)
		result = compute_traversal_dynamics(
			waypoints_xyz=waypoints,
			elevation_map=None, transform=None,
			rover=SLOW_ROVER,
		)
		assert result["average_velocity_mps"] == 0.0
		assert result["traversal_time_s"] == 0.0
		assert result["traverse_feasible"] == 1.0
		assert result["failure_reason"] is None

	def test_empty_waypoints(self):
		waypoints = np.empty((0, 3), dtype=np.float64)
		result = compute_traversal_dynamics(
			waypoints_xyz=waypoints,
			elevation_map=None, transform=None,
			rover=SLOW_ROVER,
		)
		assert result["traversal_time_s"] == 0.0
		assert result["traverse_feasible"] == 1.0

	def test_no_elevation_map_still_runs(self):
		waypoints = np.array([[0.0, 0.0, 100.0], [10.0, 0.0, 105.0]], dtype=np.float64)
		result = compute_traversal_dynamics(
			waypoints_xyz=waypoints,
			elevation_map=None, transform=None,
			rover=SLOW_ROVER,
		)
		assert result["traverse_feasible"] >= 0.5
		assert result["traversal_time_s"] > 0.0
		assert result["average_velocity_mps"] > 0.0
		assert result["max_climbable_slope_deg"] > 0.0

	def test_result_keys_present(self):
		waypoints = np.array([[0.0, 0.0, 100.0], [5.0, 0.0, 102.0]], dtype=np.float64)
		result = compute_traversal_dynamics(
			waypoints_xyz=waypoints,
			elevation_map=None, transform=None,
			rover=SLOW_ROVER,
		)
		expected_keys = {
			"average_velocity_mps", "min_velocity_mps", "max_velocity_mps",
			"traversal_time_s", "solar_energy_per_m2_j",
			"avg_solar_illumination_w_per_m2", "max_climbable_slope_deg",
			"traverse_feasible", "failure_x", "failure_y", "failure_reason",
			"simulation_resolution_m", "rollover_occurred",
			"max_lateral_accel_mps2", "braking_events", "max_braking_decel_mps2",
			"battery_energy_used_j", "battery_remaining_pct", "battery_capacity_wh",
		}
		assert set(result.keys()) == expected_keys

	def test_with_elevation_map(self):
		elev = np.ones((10, 10), dtype=np.float32) * 100.0
		from affine import Affine
		transform = Affine(1.0, 0.0, 0.0, 0.0, -1.0, 10.0)
		waypoints = np.array(
			[[0.5, 9.5, 0.0], [9.5, 0.5, 0.0]], dtype=np.float64
		)
		result = compute_traversal_dynamics(
			waypoints_xyz=waypoints,
			elevation_map=elev, transform=transform,
			rover=SLOW_ROVER,
		)
		assert result["traverse_feasible"] >= 0.5
		assert result["simulation_resolution_m"] > 0.0

	def test_with_pause_durations(self):
		waypoints = np.array(
			[[0.0, 0.0, 100.0], [5.0, 0.0, 102.0]], dtype=np.float64
		)
		result = compute_traversal_dynamics(
			waypoints_xyz=waypoints,
			elevation_map=None, transform=None,
			rover=SLOW_ROVER,
			pause_durations=[100.0],
		)
		assert result["traverse_feasible"] >= 0.5
		# With a 100s pause, traversal should be > 100s
		assert result["traversal_time_s"] > 100.0

	def test_max_climbable_slope_in_result(self):
		waypoints = np.array(
			[[0.0, 0.0, 100.0], [10.0, 0.0, 100.0]], dtype=np.float64
		)
		# Use a rover with known friction
		rover = RoverSettings(
			mass_kg=200.0, power_hp=1.0,
			wheel_friction_coeff=0.5, rolling_resistance_coeff=0.02,
		)
		result = compute_traversal_dynamics(
			waypoints_xyz=waypoints,
			elevation_map=None, transform=None,
			rover=rover,
		)
		# max_climbable = atan(0.5 - 0.02) ≈ 25.5°
		assert result["max_climbable_slope_deg"] == pytest.approx(25.5, abs=1.0)
