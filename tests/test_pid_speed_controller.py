"""Tests for the PID speed controller."""
import math

from cynthium.app.engine.simulation._sim_utils import SpeedPIDController


def _convergence_time(
    pid: SpeedPIDController,
    target: float,
    dt: float = 0.02,
    max_steps: int = 5000,
    tol: float = 0.01,
) -> tuple[int, float]:
    """Run the PID until it converges to target. Returns (steps, final_speed)."""
    speed = 0.0
    pid.reset()
    for step in range(max_steps):
        throttle, brake = pid.update(speed, target, dt)
        accel = throttle * 2.0 - brake  # crude acceleration model
        speed = max(0.0, speed + accel * dt)
        if abs(speed - target) < tol:
            return step + 1, speed
    return max_steps, speed


def _max_overshoot(
    pid: SpeedPIDController,
    target: float,
    dt: float = 0.02,
    max_steps: int = 5000,
) -> float:
    """Return the maximum speed reached during a step-response test."""
    speed = 0.0
    pid.reset()
    peak = 0.0
    for _ in range(max_steps):
        throttle, brake = pid.update(speed, target, dt)
        accel = throttle * 2.0 - brake
        speed = max(0.0, speed + accel * dt)
        peak = max(peak, speed)
        if abs(speed - target) < 0.01:
            break
    return peak


# ── Default gains ──


class TestDefaults:
    def test_converges_to_target(self):
        pid = SpeedPIDController()
        steps, final = _convergence_time(pid, 2.0)
        assert steps < 3000, f"did not converge within 3000 steps ({steps})"
        assert abs(final - 2.0) < 0.02

    def test_converges_to_zero(self):
        pid = SpeedPIDController()
        # Start at speed 2.0, target 0.0
        speed = 2.0
        pid.reset()
        for _ in range(2000):
            throttle, brake = pid.update(speed, 0.0, 0.02)
            accel = throttle * 2.0 - brake
            speed = max(0.0, speed + accel * 0.02)
        assert speed < 0.05, f"speed did not converge to zero: {speed}"

    def test_overshoot_within_reason(self):
        pid = SpeedPIDController()
        peak = _max_overshoot(pid, 2.0)
        # Allow 50 % overshoot at most (conservative for default gains)
        assert peak < 3.0, f"overshoot too large: peak={peak}"

    def test_throttle_output_range(self):
        pid = SpeedPIDController()
        pid.reset()
        t, b = pid.update(0.0, 2.0, 0.02)
        assert 0.0 <= t <= 1.0
        assert b == 0.0

    def test_brake_output_range(self):
        pid = SpeedPIDController()
        pid.reset()
        t, b = pid.update(5.0, 2.0, 0.02)
        assert t == 0.0
        assert 0.0 <= b <= 2.0

    def test_reset_clears_state(self):
        pid = SpeedPIDController()
        pid.update(0.0, 2.0, 0.02)  # accumulate integral
        pid.reset()
        assert pid._integral == 0.0
        assert pid._prev_error == 0.0


# ── Response to step changes ──


class TestStepResponse:
    def test_speeds_up_under_target(self):
        pid = SpeedPIDController(Kp=10.0, Ki=0.0, Kd=0.0)
        pid.reset()
        # Well below target → full throttle
        t, b = pid.update(0.0, 5.0, 0.02)
        assert t == 1.0
        assert b == 0.0

    def test_brakes_above_target(self):
        pid = SpeedPIDController(Kp=10.0, Ki=0.0, Kd=0.0)
        pid.reset()
        # Well above target → brake
        t, b = pid.update(5.0, 2.0, 0.02)
        assert t == 0.0
        assert b > 0.0

    def test_derivative_dampens_overshoot(self):
        """Adding derivative gain should reduce overshoot vs P-only."""
        p_only = SpeedPIDController(Kp=8.0, Ki=0.0, Kd=0.0)
        pid = SpeedPIDController(Kp=8.0, Ki=0.0, Kd=0.5)
        peak_p = _max_overshoot(p_only, 2.0)
        peak = _max_overshoot(pid, 2.0)
        assert peak <= peak_p + 0.1, (
            f"derivative did not reduce overshoot: "
            f"P-only peak={peak_p}, PID peak={peak}"
        )

    def test_integral_reduces_steady_state_error(self):
        """I term should eliminate steady-state error under load."""
        p_only = SpeedPIDController(Kp=8.0, Ki=0.0, Kd=0.0)
        pid = SpeedPIDController(Kp=8.0, Ki=0.2, Kd=0.0)

        def _simulate(controller, load_accel=0.0):
            speed = 0.0
            controller.reset()
            for _ in range(5000):
                t, b = controller.update(speed, 2.0, 0.02)
                accel = t * 2.0 - b - load_accel
                speed = max(0.0, speed + accel * 0.02)
            return speed

        final_p = _simulate(p_only, load_accel=0.5)
        final = _simulate(pid, load_accel=0.5)
        # With load, P-only has steady-state error; PID should be closer
        assert abs(final - 2.0) < abs(final_p - 2.0), (
            f"I term did not reduce error: P-only error={2.0 - final_p:.3f}, "
            f"PID error={2.0 - final:.3f}"
        )


# ── Edge cases ──


class TestEdgeCases:
    def test_zero_target_at_rest(self):
        pid = SpeedPIDController()
        pid.reset()
        t, b = pid.update(0.0, 0.0, 0.02)
        assert 0.0 <= t <= 1.0
        assert b == 0.0

    def test_small_dt_no_nan(self):
        pid = SpeedPIDController()
        pid.reset()
        t, b = pid.update(0.0, 1.0, 1e-8)
        assert math.isfinite(t)
        assert math.isfinite(b)

    def test_large_error_clamps(self):
        pid = SpeedPIDController(Kp=100.0)
        pid.reset()
        t, b = pid.update(0.0, 100.0, 0.02)
        assert t == 1.0  # throttle saturates at 1.0
        assert b == 0.0

    def test_integral_anti_windup(self):
        pid = SpeedPIDController(Kp=1.0, Ki=10.0, integral_limit=5.0)
        pid.reset()
        # Large sustained error should wind up integral but cap at limit
        for _ in range(1000):
            pid.update(0.0, 10.0, 1.0)
        assert abs(pid._integral) <= 5.0 + 1e-9

    def test_consecutive_calls_same_result(self):
        pid = SpeedPIDController()
        pid.reset()
        r1 = pid.update(1.0, 2.0, 0.02)
        pid.reset()
        r2 = pid.update(1.0, 2.0, 0.02)
        assert r1 == r2
