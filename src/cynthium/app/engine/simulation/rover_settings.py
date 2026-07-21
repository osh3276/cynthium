"""Rover physical parameters and preset configurations."""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, atan, atan2, cos, degrees, radians, sin, sqrt

G_MPS2 = 1.625  # lunar gravity
_HP_TO_W = 745.699872
_MIN_CLIMB_V_MPS = 0.1  # minimum speed for power-limited climb


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
        """Maximum sustainable slope considering traction, power-to-mass, and torque.

        Returns the minimum of three limits:
          1. Traction:  wheels slip when tan(θ) > μ − Crr
          2. Power:     P / v ≥ m·g·(sin(θ) + Crr·cos(θ))  at v = 0.1 m/s
          3. Torque:    T / r ≥ m·g·(sin(θ) + Crr·cos(θ))
        """
        mu = self.wheel_friction_coeff
        crr = self.rolling_resistance_coeff
        m = self.mass_kg
        g = G_MPS2

        # ── 1. Traction limit ──
        traction = degrees(atan(max(0.001, mu - crr)))

        # ── 2. Power limit ──
        # P / (v·m·g) = sin(θ) + Crr·cos(θ)
        p_w = self.power_w
        a_power = p_w / (_MIN_CLIMB_V_MPS * m * g)
        power = self._solve_slope(a_power, crr) if a_power > 0 else 0.0

        # ── 3. Torque limit ──
        # T / (r·m·g) = sin(θ) + Crr·cos(θ)
        torque = 90.0  # no torque limit
        if self.motor_peak_torque_nm is not None and self.motor_peak_torque_nm > 0:
            a_torque = self.motor_peak_torque_nm / (self.wheel_radius_m * m * g)
            torque = self._solve_slope(a_torque, crr) if a_torque > 0 else 0.0

        return float(min(traction, power, torque))

    @staticmethod
    def _solve_slope(a: float, crr: float) -> float:
        """Solve  A = sin(θ) + Crr·cos(θ)  for θ in degrees.

        Uses the identity  sin(θ) + k·cos(θ) = R·sin(θ + φ)
        where  R = √(1 + k²)  and  φ = atan2(k, 1).
        """
        r = sqrt(1.0 + crr * crr)
        phi = atan2(crr, 1.0)
        clipped = max(-1.0, min(1.0, a / r))
        return float(degrees(asin(clipped) - phi))

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
    track_width_m: str = "1.0",
    wheelbase_m: str = "1.5",
) -> RoverSettings:
    m = float(mass_kg)
    p = float(power_hp)
    mu = float(wheel_friction_coeff)
    crr = float(rolling_resistance_coeff)
    r = float(wheel_radius_m)
    torque = float(motor_peak_torque_nm) if motor_peak_torque_nm is not None else None
    tw = float(track_width_m)
    wb = float(wheelbase_m)
    settings = RoverSettings(
        mass_kg=m,
        power_hp=p,
        wheel_friction_coeff=mu,
        rolling_resistance_coeff=crr,
        wheel_radius_m=r,
        motor_peak_torque_nm=torque,
        track_width_m=tw,
        wheelbase_m=wb,
    )
    settings.validate()
    return settings
