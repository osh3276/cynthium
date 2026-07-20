"""Rover physical parameters and preset configurations."""

from __future__ import annotations

from dataclasses import dataclass
from math import atan, degrees

_HP_TO_W = 745.699872


@dataclass(frozen=True)
class RoverSettings:
    mass_kg: float
    power_hp: float
    wheel_friction_coeff: float
    rolling_resistance_coeff: float
    wheel_radius_m: float = 0.5
    motor_peak_torque_nm: float | None = None
    track_width_m: float = 1.0
    wheelbase_m: float = 1.5

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
        if not (self.wheel_radius_m > 0):
            raise ValueError("Wheel radius must be > 0")
        if self.motor_peak_torque_nm is not None and self.motor_peak_torque_nm <= 0:
            raise ValueError("Motor peak torque must be > 0 when provided")
        if not (self.track_width_m > 0):
            raise ValueError("Track width must be > 0")
        if not (self.wheelbase_m > 0):
            raise ValueError("Wheelbase must be > 0")


ROVER_PRESETS: dict[str, RoverSettings] = {
    "Curiosity": RoverSettings(
        mass_kg=899.0,
        power_hp=0.13,
        wheel_friction_coeff=0.5,
        rolling_resistance_coeff=0.02,
        wheel_radius_m=0.25,
        motor_peak_torque_nm=None,
    ),
    "Apollo LRV": RoverSettings(
        mass_kg=210.0,
        power_hp=1.0,
        wheel_friction_coeff=0.6,
        rolling_resistance_coeff=0.021,
        wheel_radius_m=0.41,
        motor_peak_torque_nm=None,
    ),
    "Perseverance": RoverSettings(
        mass_kg=1025.0,
        power_hp=0.14,
        wheel_friction_coeff=0.5,
        rolling_resistance_coeff=0.02,
        wheel_radius_m=0.2625,
        motor_peak_torque_nm=None,
    ),
    "Artemis SR": RoverSettings(
        mass_kg=530.0,
        power_hp=0.72,
        wheel_friction_coeff=0.7,
        rolling_resistance_coeff=0.15,
        wheel_radius_m=0.5,
        motor_peak_torque_nm=None,
    ),
}


def rover_settings_from_strings(
    mass_kg: str,
    power_hp: str,
    wheel_friction_coeff: str,
    rolling_resistance_coeff: str,
    wheel_radius_m: str = "0.5",
    motor_peak_torque_nm: str | None = None,
) -> RoverSettings:
    m = float(mass_kg)
    p = float(power_hp)
    mu = float(wheel_friction_coeff)
    crr = float(rolling_resistance_coeff)
    r = float(wheel_radius_m)
    torque = float(motor_peak_torque_nm) if motor_peak_torque_nm is not None else None
    settings = RoverSettings(
        mass_kg=m,
        power_hp=p,
        wheel_friction_coeff=mu,
        rolling_resistance_coeff=crr,
        wheel_radius_m=r,
        motor_peak_torque_nm=torque,
    )
    settings.validate()
    return settings
