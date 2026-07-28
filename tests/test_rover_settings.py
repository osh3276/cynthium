"""Tests for RoverSettings — physical parameters, presets, validation."""

import pytest

from cynthium.app.engine.simulation.rover_settings import (
	G_MPS2,
	ROVER_PRESETS,
	RoverSettings,
	rover_settings_from_strings,
)


class TestRoverSettingsProperties:
	@pytest.fixture
	def rover(self):
		return RoverSettings(
			mass_kg=200.0,
			power_hp=0.5,
			wheel_friction_coeff=0.6,
			rolling_resistance_coeff=0.02,
			wheel_radius_m=0.4,
			motor_peak_torque_nm=100.0,
			track_width_m=1.2,
			wheelbase_m=1.6,
			battery_capacity_wh=1000.0,
			motor_max_rpm=300.0,
			target_cruise_speed_mps=2.5,
			max_brake_decel_mps2=1.5,
			idle_drain_w=15.0,
		)

	def test_power_w_conversion(self, rover):
		assert rover.power_w == pytest.approx(0.5 * 745.699872)

	def test_battery_capacity_j(self, rover):
		assert rover.battery_capacity_j == pytest.approx(1000.0 * 3600.0)

	def test_max_wheel_speed_mps(self, rover):
		expected = 300.0 * (3.14159 / 30.0) * 0.4
		assert rover.max_wheel_speed_mps == pytest.approx(expected, rel=1e-3)

	def test_max_climbable_slope_traction_limited(self):
		# Traction: atan(0.6 - 0.02) ≈ 30.1°
		rover = RoverSettings(
			mass_kg=1000.0, power_hp=1000.0,
			wheel_friction_coeff=0.6, rolling_resistance_coeff=0.02,
			motor_peak_torque_nm=1e6,
		)
		expected = RoverSettings._solve_slope(1e6 / (0.5 * 1000.0 * G_MPS2), 0.02)
		expected = min(30.1, expected)
		# With enough power and torque, traction is the limit
		assert rover.max_climbable_slope_deg == pytest.approx(30.1, abs=0.5)

	def test_max_climbable_slope_power_limited(self):
		# Very low power should dominate
		rover = RoverSettings(
			mass_kg=1000.0, power_hp=0.01,
			wheel_friction_coeff=0.9, rolling_resistance_coeff=0.02,
			motor_peak_torque_nm=1e6,
		)
		slope = rover.max_climbable_slope_deg
		# Should be a small positive slope (power-limited)
		assert 0.0 < slope < 15.0

	def test_max_climbable_no_torque_limit(self):
		# No torque specified → no torque limit
		rover = RoverSettings(
			mass_kg=200.0, power_hp=1.0,
			wheel_friction_coeff=0.7, rolling_resistance_coeff=0.03,
		)
		assert rover.motor_peak_torque_nm is None
		slope = rover.max_climbable_slope_deg
		assert slope > 0.0


class TestRoverSettingsValidation:
	def test_valid_passes(self):
		rs = RoverSettings(
			mass_kg=100.0, power_hp=1.0,
			wheel_friction_coeff=0.5, rolling_resistance_coeff=0.02,
		)
		rs.validate()  # should not raise

	def test_invalid_mass(self):
		with pytest.raises(ValueError, match="mass"):
			RoverSettings(
				mass_kg=0, power_hp=1.0,
				wheel_friction_coeff=0.5, rolling_resistance_coeff=0.02,
			).validate()

	def test_invalid_power(self):
		with pytest.raises(ValueError, match="power"):
			RoverSettings(
				mass_kg=100.0, power_hp=0,
				wheel_friction_coeff=0.5, rolling_resistance_coeff=0.02,
			).validate()

	def test_invalid_friction(self):
		with pytest.raises(ValueError, match="friction"):
			RoverSettings(
				mass_kg=100.0, power_hp=1.0,
				wheel_friction_coeff=0, rolling_resistance_coeff=0.02,
			).validate()

	def test_invalid_rolling_resistance(self):
		with pytest.raises(ValueError, match="Rolling resistance"):
			RoverSettings(
				mass_kg=100.0, power_hp=1.0,
				wheel_friction_coeff=0.5, rolling_resistance_coeff=-1.0,
			).validate()

	def test_invalid_wheel_radius(self):
		with pytest.raises(ValueError, match="radius"):
			RoverSettings(
				mass_kg=100.0, power_hp=1.0,
				wheel_friction_coeff=0.5, rolling_resistance_coeff=0.02,
				wheel_radius_m=0,
			).validate()

	def test_negative_torque(self):
		with pytest.raises(ValueError, match="torque"):
			RoverSettings(
				mass_kg=100.0, power_hp=1.0,
				wheel_friction_coeff=0.5, rolling_resistance_coeff=0.02,
				motor_peak_torque_nm=-10.0,
			).validate()

	def test_invalid_track_width(self):
		with pytest.raises(ValueError, match="Track width"):
			RoverSettings(
				mass_kg=100.0, power_hp=1.0,
				wheel_friction_coeff=0.5, rolling_resistance_coeff=0.02,
				track_width_m=0,
			).validate()


class TestRoverPresets:
	def test_all_presets_validate(self):
		for name, preset in ROVER_PRESETS.items():
			preset.validate()  # Should not raise

	def test_presets_have_positive_mass(self):
		for name, preset in ROVER_PRESETS.items():
			assert preset.mass_kg > 0, f"{name} has zero mass"

	def test_presets_have_climbable_slope(self):
		for name, preset in ROVER_PRESETS.items():
			assert preset.max_climbable_slope_deg > 0, f"{name} cannot climb"

	def test_curiosity_climbable(self):
		curiosity = ROVER_PRESETS["Curiosity"]
		slope = curiosity.max_climbable_slope_deg
		assert slope > 5.0, "Curiosity should have >5° climbable slope"

	def test_apollo_lrv_climbable(self):
		lrv = ROVER_PRESETS["Apollo LRV"]
		slope = lrv.max_climbable_slope_deg
		assert slope > 5.0

	def test_artemis_sr_has_large_track(self):
		artemis = ROVER_PRESETS["Artemis SR"]
		assert artemis.track_width_m == 1.0
		assert artemis.wheelbase_m == 1.5

	def test_perseverance_properties(self):
		perseverance = ROVER_PRESETS["Perseverance"]
		assert perseverance.power_w == pytest.approx(0.14 * 745.699872, rel=1e-3)


class TestRoverSettingsFromStrings:
	def test_basic_conversion(self):
		rs = rover_settings_from_strings("150", "0.2", "0.5", "0.03")
		assert rs.mass_kg == 150.0
		assert rs.power_hp == 0.2
		assert rs.wheel_friction_coeff == 0.5
		assert rs.rolling_resistance_coeff == 0.03

	def test_optional_torque_none(self):
		rs = rover_settings_from_strings("100", "1.0", "0.6", "0.02")
		assert rs.motor_peak_torque_nm is None

	def test_optional_torque_provided(self):
		rs = rover_settings_from_strings(
			"100", "1.0", "0.6", "0.02",
			motor_peak_torque_nm="200.0",
		)
		assert rs.motor_peak_torque_nm == 200.0

	def test_custom_all_params(self):
		rs = rover_settings_from_strings(
			"500", "0.5", "0.7", "0.015",
			wheel_radius_m="0.45",
			motor_peak_torque_nm="150.0",
			track_width_m="1.5",
			wheelbase_m="2.0",
			battery_capacity_wh="2000.0",
			motor_max_rpm="250.0",
			target_cruise_speed_mps="3.0",
			max_brake_decel_mps2="0.8",
			idle_drain_w="20.0",
		)
		assert rs.mass_kg == 500.0
		assert rs.power_hp == 0.5
		assert rs.wheel_radius_m == 0.45
		assert rs.motor_peak_torque_nm == 150.0
		assert rs.track_width_m == 1.5
		assert rs.wheelbase_m == 2.0
		assert rs.battery_capacity_wh == 2000.0
		assert rs.motor_max_rpm == 250.0
		assert rs.target_cruise_speed_mps == 3.0
		assert rs.max_brake_decel_mps2 == 0.8
		assert rs.idle_drain_w == 20.0
