"""Tests for cooperative cancellation of long-running computations."""

import threading
import time

import numpy as np
import pytest

from cynthium.app.engine.pathfinding.astar import a_star
from cynthium.app.engine.simulation.rover_settings import RoverSettings
from cynthium.app.engine.simulation.sim_orchestrator import compute_traversal_dynamics
from cynthium.app.services.autopath_service import compute_validated_path
from cynthium.app.ui.panels.progress_popup import Worker
from cynthium.app.utils.cancellation import CancelledError


class TestAStarCancellation:
	def test_pre_set_event_raises(self):
		event = threading.Event()
		event.set()
		with pytest.raises(CancelledError):
			a_star(
				start_rc=(0, 0), goal_rc=(9, 9),
				traversable=np.ones((10, 10), dtype=bool),
				cell_cost=np.ones((10, 10), dtype=np.float64),
				elev=np.zeros((10, 10), dtype=np.float64),
				res_x=1.0, res_y=1.0,
				max_slope_deg=20.0, slope_weight=1.0, grade_power=2.0,
				cancel_event=event,
			)

	def test_no_event_is_unchanged_behavior(self):
		result = a_star(
			start_rc=(5, 1), goal_rc=(5, 8),
			traversable=np.ones((10, 10), dtype=bool),
			cell_cost=np.ones((10, 10), dtype=np.float64),
			elev=np.zeros((10, 10), dtype=np.float64),
			res_x=1.0, res_y=1.0,
			max_slope_deg=20.0, slope_weight=1.0, grade_power=2.0,
		)
		assert result is not None


class TestSimulationCancellation:
	ROVER = RoverSettings(
		mass_kg=200.0, power_hp=0.01, wheel_friction_coeff=0.6,
		rolling_resistance_coeff=0.02,
	)

	def test_pre_set_event_raises(self):
		event = threading.Event()
		event.set()
		waypoints = np.array(
			[[0.0, 0.0, 100.0], [10.0, 0.0, 105.0]], dtype=np.float64
		)
		with pytest.raises(CancelledError):
			compute_traversal_dynamics(
				waypoints_xyz=waypoints,
				elevation_map=None, transform=None,
				rover=self.ROVER,
				cancel_event=event,
			)


class TestAutopathCancellation:
	def test_pre_set_event_raises(self):
		event = threading.Event()
		event.set()
		with pytest.raises(CancelledError):
			compute_validated_path(
				waypoints_xy=[(0.0, 0.0), (10.0, 10.0)],
				path_mode="Start to finish",
				rover=TestSimulationCancellation.ROVER,
				map_data_bundle=(
					None, None, None, None, None, None, None, None, None,
				),
				pathfind_fn=lambda *args, **kwargs: [(0.0, 0.0), (10.0, 10.0)],
				cancel_event=event,
			)


class TestWorkerCancellation:
	def test_worker_emits_cancelled_not_failed(self):
		"""The cancel kwarg must reach the callable, and CancelledError must
		be reported through the cancelled signal, not failed."""

		def _spin_until_cancelled(cancel_event=None):
			while cancel_event is None or not cancel_event.is_set():
				time.sleep(0.001)
			raise CancelledError

		event = threading.Event()
		worker = Worker(_spin_until_cancelled, cancel_event=event)

		flags = {"cancelled": False, "finished": False, "failed": False}
		worker.cancelled.connect(lambda: flags.__setitem__("cancelled", True))
		worker.finished.connect(lambda *a: flags.__setitem__("finished", True))
		worker.failed.connect(lambda *a: flags.__setitem__("failed", True))

		# Set the event in a side thread while the worker spins.
		def _cancel():
			time.sleep(0.05)
			event.set()

		threading.Thread(target=_cancel, daemon=True).start()
		worker.run()

		assert event.is_set()
		assert flags["cancelled"], "cancelled signal was never delivered"
		assert not flags["finished"]
		assert not flags["failed"]
