from dataclasses import dataclass
from math import atan, degrees

_HP_TO_W = 745.699872


@dataclass(frozen=True)
class RoverSettings:
	mass_kg: float
	power_hp: float
	wheel_friction_coeff: float
	rolling_resistance_coeff: float

	@property
	def power_w(self) -> float:
		return float(self.power_hp) * _HP_TO_W

	@property
	def max_climbable_slope_deg(self) -> float:
		"""Maximum climbable slope derived from friction coefficient."""
		return float(degrees(atan(self.wheel_friction_coeff)))

	def validate(self):
		if not (self.mass_kg > 0):
			raise ValueError("Rover mass must be > 0")
		if not (self.power_hp > 0):
			raise ValueError("Rover power must be > 0")
		if not (self.wheel_friction_coeff > 0):
			raise ValueError("Wheel friction coefficient must be > 0")
		if not (self.rolling_resistance_coeff >= 0):
			raise ValueError("Rolling resistance coefficient must be >= 0")


ROVER_PRESETS: dict[str, RoverSettings] = {
	"Custom": RoverSettings(
		mass_kg=150.0,
		power_hp=0.2,
		wheel_friction_coeff=0.6,
		rolling_resistance_coeff=0.1,
	),
	"Apollo LRV": RoverSettings(
		mass_kg=210.0,
		power_hp=1.0,
		wheel_friction_coeff=0.6,
		rolling_resistance_coeff=0.021,
	),
}


def rover_settings_from_strings(
	mass_kg: str,
	power_hp: str,
	wheel_friction_coeff: str,
	rolling_resistance_coeff: str,
) -> RoverSettings:
	m = float(mass_kg)
	p = float(power_hp)
	mu = float(wheel_friction_coeff)
	crr = float(rolling_resistance_coeff)
	settings = RoverSettings(
		mass_kg=m,
		power_hp=p,
		wheel_friction_coeff=mu,
		rolling_resistance_coeff=crr,
	)
	settings.validate()
	return settings
