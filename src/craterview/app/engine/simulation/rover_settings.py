from dataclasses import dataclass

_HP_TO_W = 745.699872


@dataclass(frozen=True)
class RoverSettings:
	mass_kg: float
	power_hp: float
	wheel_friction_coeff: float

	@property
	def power_w(self) -> float:
		return float(self.power_hp) * _HP_TO_W

	def validate(self):
		if not (self.mass_kg > 0):
			raise ValueError("Rover mass must be > 0")
		if not (self.power_hp > 0):
			raise ValueError("Rover power must be > 0")
		if not (self.wheel_friction_coeff > 0):
			raise ValueError("Wheel friction coefficient must be > 0")


def rover_settings_from_strings(
	mass_kg: str,
	power_hp: str,
	wheel_friction_coeff: str,
) -> RoverSettings:
	m = float(mass_kg)
	p = float(power_hp)
	mu = float(wheel_friction_coeff)
	settings = RoverSettings(mass_kg=m, power_hp=p, wheel_friction_coeff=mu)
	settings.validate()
	return settings
