"""Vehicle geometry, wheel configuration, braking, and soil parameters.

Holds vehicle-level configuration: wheel count/layout, body dimensions,
braking model, physics engine selection, and terrain soil type.  This is
composed orthogonally with ``RoverSettings`` (mass, power, μ, Crr) which
lives in ``rover_settings.py``.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from math import pi
from typing import Literal

# Engine options
ENGINE_2D = "2d"
ENGINE_MUJOCO = "mujoco"
ENGINE_CHOICES = [ENGINE_2D, ENGINE_MUJOCO]

# Soil presets (inline here to avoid circular imports with wheel_terrain)
SOIL_PRESETS: dict[str, dict] = {
	"Hard rock (no sinkage)": dict(
		cohesion_pa=1e6, friction_angle_deg=45.0, sinkage_exponent_n=0.5,
		cohesive_modulus=1e8, frictional_modulus=1e8, shear_modulus_k_m=0.001,
	),
	"Compacted lunar regolith": dict(
		cohesion_pa=500.0, friction_angle_deg=40.0, sinkage_exponent_n=0.8,
		cohesive_modulus=0.0, frictional_modulus=5_000_000.0, shear_modulus_k_m=0.015,
	),
	"Loose lunar regolith": dict(
		cohesion_pa=100.0, friction_angle_deg=30.0, sinkage_exponent_n=1.0,
		cohesive_modulus=0.0, frictional_modulus=1_000_000.0, shear_modulus_k_m=0.04,
	),
	"Soft soil": dict(
		cohesion_pa=50.0, friction_angle_deg=25.0, sinkage_exponent_n=1.2,
		cohesive_modulus=10.0, frictional_modulus=300_000.0, shear_modulus_k_m=0.08,
	),
}
DEFAULT_SOIL = "Compacted lunar regolith"


@dataclass
class WheelConfig:
	"""Configuration for a single wheel."""

	name: str
	position_x: float  # longitudinal offset from body centre (m, +forward)
	position_y: float  # lateral offset from body centre (m, +right)
	radius: float = 0.3
	steerable: bool = False
	max_steer_angle_deg: float = 30.0
	actuated: bool = True
	max_torque_nm: float | None = None


@dataclass
class VehicleConfig:
	"""Detailed vehicle geometry and dynamics configuration.

	Composed orthogonally with :class:`RoverSettings` (mass, power, μ, Crr).
	"""

	# --- Body geometry ---
	body_length: float = 2.0
	body_width: float = 1.5
	body_height: float = 1.2
	wheelbase: float = 1.8
	track_width: float = 1.2
	ground_clearance: float = 0.3

	# --- Centre of mass ---
	com_height: float = 0.5
	com_long_offset: float = 0.0

	# --- Wheel layout ---
	num_wheels: Literal[4, 6] = 4
	wheels: list[WheelConfig] = field(default_factory=list)

	# --- Steering model ---
	steering_mode: Literal["ackermann", "skid_steer", "articulated"] = "skid_steer"

	# --- Soil / terrain type ---
	soil_name: str = DEFAULT_SOIL

	@property
	def soil(self) -> dict:
		return deepcopy(SOIL_PRESETS.get(self.soil_name, SOIL_PRESETS[DEFAULT_SOIL]))

	# --- Physics engine ---
	engine: str = ENGINE_2D

	# --- Braking ---
	braking_deceleration_mps2: float = 3.0
	target_max_speed_mps: float = 5.0
	autonomous_braking_enabled: bool = True

	# --- Rollover ---
	rollover_lateral_g: float = 0.0
	yaw_inertia_factor: float = 0.4

	preset_name: str | None = None

	def __post_init__(self):
		if not self.wheels:
			self.wheels = self._default_wheels()
		if self.rollover_lateral_g <= 0.0:
			self.rollover_lateral_g = self.track_width / (2.0 * max(self.com_height, 0.01))

	@property
	def half_track(self) -> float:
		return self.track_width / 2.0

	@property
	def half_wheelbase(self) -> float:
		return self.wheelbase / 2.0

	@property
	def rollover_lateral_accel_mps2(self) -> float:
		return self.rollover_lateral_g * 9.81

	def _default_wheels(self) -> list[WheelConfig]:
		hb = self.half_wheelbase
		ht = self.half_track
		if self.num_wheels == 4:
			return [
				WheelConfig("front_left", hb, -ht, steerable=True),
				WheelConfig("front_right", hb, ht, steerable=True),
				WheelConfig("rear_left", -hb, -ht, steerable=False),
				WheelConfig("rear_right", -hb, ht, steerable=False),
			]
		# 6 wheels — 3 axles
		axles = [("front", hb), ("mid", 0.0), ("rear", -hb)]
		return [
			WheelConfig(f"{name}_left", off, -ht, steerable=(i == 0),
						max_steer_angle_deg=25.0 if i == 0 else 0.0)
			for i, (name, off) in enumerate(axles)
			for side in (-1, 1)
		] + [
			WheelConfig(f"{name}_right", off, ht, steerable=(i == 0),
						max_steer_angle_deg=25.0 if i == 0 else 0.0)
			for i, (name, off) in enumerate(axles)
		]

	def validate(self) -> None:
		if self.num_wheels not in (4, 6):
			raise ValueError(f"num_wheels must be 4 or 6, got {self.num_wheels}")
		for attr in ("body_length", "body_width", "wheelbase", "track_width", "com_height"):
			if getattr(self, attr) <= 0:
				raise ValueError(f"{attr} must be > 0")
		if self.braking_deceleration_mps2 < 0:
			raise ValueError("braking_deceleration_mps2 must be >= 0")
		if self.target_max_speed_mps <= 0:
			raise ValueError("target_max_speed_mps must be > 0")
		if len(self.wheels) != self.num_wheels:
			raise ValueError(f"Expected {self.num_wheels} wheels, got {len(self.wheels)}")

	def compute_yaw_inertia(self, mass_kg: float) -> float:
		L = self.body_length
		W = self.body_width
		return self.yaw_inertia_factor * mass_kg * (L * L + W * W) / 12.0


# ── Presets ──

VEHICLE_PRESETS: dict[str, VehicleConfig] = {
	"4-Wheel Skid Steer (Apollo LRV style)": VehicleConfig(
		body_length=3.1, body_width=1.8, body_height=1.1,
		wheelbase=2.3, track_width=1.5, ground_clearance=0.35,
		com_height=0.55, num_wheels=4,
		braking_deceleration_mps2=2.5, target_max_speed_mps=5.0,
		preset_name="4-Wheel Skid Steer (Apollo LRV style)",
	),
	"6-Wheel Rover (Curiosity style)": VehicleConfig(
		body_length=3.0, body_width=2.8, body_height=2.2,
		wheelbase=2.0, track_width=2.4, ground_clearance=0.6,
		com_height=0.7, num_wheels=6,
		braking_deceleration_mps2=1.5, target_max_speed_mps=3.0,
		preset_name="6-Wheel Rover (Curiosity style)",
	),
}


def vehicle_config_from_dict(data: dict) -> VehicleConfig:
	"""Deserialize a VehicleConfig from a dict (e.g. loaded from JSON)."""
	wheel_dicts = data.pop("wheels", [])
	vc = VehicleConfig(**data)
	vc.wheels = [WheelConfig(**wd) for wd in wheel_dicts]
	vc.validate()
	return vc
