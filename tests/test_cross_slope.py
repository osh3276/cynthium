"""Tests for the cross-slope (side tilt) limit in the rover settings, planner and simulator."""

import math
from dataclasses import replace

import numpy as np
import pytest
from affine import Affine

from cynthium.app.engine.pathfinding.astar import _cross_slope_deg, a_star
from cynthium.app.engine.simulation.rover_settings import (
	ROVER_PRESETS,
	RoverSettings,
	rover_settings_from_strings,
)
from cynthium.app.engine.simulation.sim_orchestrator import (
	compute_traversal_dynamics,
	path_cross_slopes_deg,
)


def tilted_plane(slope_deg, n=40, res=1.0):
	"""Elevation rising eastward (+x, i.e. along columns) at ``slope_deg``."""
	cols = (np.arange(n) + 0.5) * res
	return np.tile(math.tan(math.radians(slope_deg)) * cols, (n, 1)).astype(np.float64)


SLOW_ROVER = RoverSettings(
	mass_kg=200.0,
	power_hp=0.01,
	wheel_friction_coeff=0.6,  # sideslip limit atan(0.6) = 31.0 deg
	rolling_resistance_coeff=0.02,
	battery_capacity_wh=50000.0,
	target_cruise_speed_mps=0.5,
)


# ── rover settings ──────────────────────────────────────────────────────

class TestCrossSlopeSetting:
	def test_default_is_sideslip_limit(self):
		rover = ROVER_PRESETS["Curiosity"]
		assert rover.max_cross_slope_deg is None
		assert rover.cross_slope_limit_deg == pytest.approx(math.degrees(math.atan(0.5)))

	def test_explicit_value(self):
		assert replace(SLOW_ROVER, max_cross_slope_deg=20.0).cross_slope_limit_deg == 20.0

	def test_zero_disables(self):
		assert replace(SLOW_ROVER, max_cross_slope_deg=0.0).cross_slope_limit_deg == 0.0

	def test_validate_rejects_90(self):
		with pytest.raises(ValueError):
			replace(SLOW_ROVER, max_cross_slope_deg=90.0).validate()

	def test_from_strings(self):
		s = rover_settings_from_strings("100", "1", "0.5", "0.02", max_cross_slope_deg="22.5")
		assert s.max_cross_slope_deg == 22.5
		assert rover_settings_from_strings("100", "1", "0.5", "0.02").max_cross_slope_deg is None


# ── planner ─────────────────────────────────────────────────────────────

class TestCrossSlopeDeg:
	def test_side_slope_equals_slope_angle(self):
		elev = tilted_plane(20.0)
		gr, gc = np.gradient(elev)
		# heading north/south (along rows) is along the contour
		assert _cross_slope_deg(gr, gc, (5, 5), 1.0, 0.0) == pytest.approx(20.0, abs=1e-6)

	def test_fall_line_has_no_tilt(self):
		elev = tilted_plane(20.0)
		gr, gc = np.gradient(elev)
		assert _cross_slope_deg(gr, gc, (5, 5), 0.0, 1.0) == pytest.approx(0.0, abs=1e-9)


def _plan(elev, start, goal, cross):
	return a_star(
		start_rc=start, goal_rc=goal, traversable=np.ones(elev.shape, bool),
		cell_cost=np.ones(elev.shape, np.float32), elev=elev, res_x=1.0, res_y=1.0,
		max_slope_deg=25.6, slope_weight=1.0, grade_power=1.0, max_cross_slope_deg=cross,
	)


def _max_roll(elev, path):
	gr, gc = np.gradient(elev)
	worst = 0.0
	for (r0, c0), (r1, c1) in zip(path[:-1], path[1:]):
		step = math.hypot(r1 - r0, c1 - c0)
		u = ((r1 - r0) / step, (c1 - c0) / step)
		worst = max(worst, _cross_slope_deg(gr, gc, (r0, c0), *u), _cross_slope_deg(gr, gc, (r1, c1), *u))
	return worst


class TestPlannerCrossSlope:
	def test_contour_route_allowed_without_limit(self):
		elev = tilted_plane(35.0)
		res = _plan(elev, (5, 20), (35, 20), cross=0.0)
		assert res is not None
		assert all(c == 20 for _, c in res.path_rc)  # straight along the contour

	def test_steep_side_slope_blocked(self):
		# On a 35 deg plane no grid heading keeps both the grade <= 25.6 deg
		# and the side tilt <= 26.6 deg, so there is no route.
		elev = tilted_plane(35.0)
		assert _plan(elev, (5, 20), (35, 20), cross=26.6) is None

	def test_route_zigzags_within_limit(self):
		# On a 30 deg plane diagonal headings satisfy both limits.
		elev = tilted_plane(30.0)
		res = _plan(elev, (5, 20), (35, 20), cross=26.6)
		assert res is not None
		p = np.asarray(res.path_rc, float)
		assert np.hypot(*np.diff(p, axis=0).T).sum() > 31.0  # longer than the 30-cell contour line
		assert not any(c0 == c1 for (_, c0), (_, c1) in zip(res.path_rc[:-1], res.path_rc[1:]))  # no contour steps
		assert _max_roll(elev, res.path_rc) <= 26.6 + 1e-9


# ── simulator ───────────────────────────────────────────────────────────

class TestSimulatorCrossSlope:
	N = 60
	TRANSFORM = Affine(1.0, 0.0, 0.0, 0.0, -1.0, 60.0)

	def _contour_route(self):
		# x = 30.5 (constant elevation), y from 5.5 to 54.5
		return np.array([[30.5, 5.5, 0.0], [30.5, 54.5, 0.0]], dtype=np.float64)

	def test_path_cross_slopes(self):
		elev = tilted_plane(35.0, n=self.N)
		roll = path_cross_slopes_deg(
			np.array([[30.5, 5.5, 0], [30.5, 30.5, 0], [50.5, 30.5, 0]], float), elev, self.TRANSFORM)
		assert roll[0] == pytest.approx(35.0, abs=1e-6)  # along the contour
		assert roll[1] == pytest.approx(0.0, abs=1e-6)   # up the fall line

	def test_fails_on_steep_side_slope(self):
		elev = tilted_plane(35.0, n=self.N)
		res = compute_traversal_dynamics(
			waypoints_xyz=self._contour_route(), elevation_map=elev, transform=self.TRANSFORM, rover=SLOW_ROVER)
		assert res["traverse_feasible"] < 0.5
		assert "Cross-slope" in res["failure_reason"]
		assert res["cross_slope_limit_deg"] == pytest.approx(math.degrees(math.atan(0.6)))
		assert res["max_cross_slope_deg"] == pytest.approx(35.0, abs=0.1)

	def test_disabled_limit_completes(self):
		elev = tilted_plane(35.0, n=self.N)
		res = compute_traversal_dynamics(
			waypoints_xyz=self._contour_route(), elevation_map=elev, transform=self.TRANSFORM,
			rover=replace(SLOW_ROVER, max_cross_slope_deg=0.0))
		assert res["traverse_feasible"] >= 0.5
		assert res["max_cross_slope_deg"] == pytest.approx(35.0, abs=0.1)

	def test_gentle_side_slope_completes(self):
		elev = tilted_plane(20.0, n=self.N)
		res = compute_traversal_dynamics(
			waypoints_xyz=self._contour_route(), elevation_map=elev, transform=self.TRANSFORM, rover=SLOW_ROVER)
		assert res["traverse_feasible"] >= 0.5
