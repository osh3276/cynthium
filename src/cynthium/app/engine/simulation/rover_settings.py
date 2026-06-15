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
		"""Maximum sustainable slope accounting for rolling resistance.

		Steady-state force balance:  μ·m·g·cos(θ) = m·g·sin(θ) + Crr·m·g·cos(θ)
		Simplifies to:  tan(θ) = μ − Crr
		"""
		mu = self.wheel_friction_coeff
		crr = self.rolling_resistance_coeff
		return float(degrees(atan(max(0.001, mu - crr))))

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
	"Curiosity": RoverSettings(
		mass_kg=899.0,
		power_hp=0.13,
		wheel_friction_coeff=0.5,
		rolling_resistance_coeff=0.02,
	),
	"Apollo LRV": RoverSettings(
		mass_kg=210.0,
		power_hp=1.0,
		wheel_friction_coeff=0.6,
		rolling_resistance_coeff=0.021,
	),
	"Perseverance": RoverSettings(
		mass_kg=1025.0,
		power_hp=0.14,
		wheel_friction_coeff=0.5,
		rolling_resistance_coeff=0.02,
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
