from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
	QFrame,
	QLabel,
	QScrollArea,
	QVBoxLayout,
	QWidget,
)

from cynthium.app.engine.simulation.rover_settings import (
	RoverSettings,
	rover_settings_from_strings,
)
from cynthium.app.ui.panels.sidebar.map_selection_panel import MapSelectionPanel
from cynthium.app.ui.panels.sidebar.planning_panel import PlanningPanel
from cynthium.app.ui.panels.sidebar.rover_settings_panel import RoverSettingsPanel


class AppSidebar(QWidget):
	map_selected = Signal(str)
	map_generation_requested = Signal(str, str, str)
	waypoint_added = Signal(float, float)
	waypoint_removed = Signal(int)
	waypoints_cleared = Signal()
	autopath_requested = Signal(object)

	def __init__(self):
		"""
		Initializes the AppSidebar instance.

		:return: None
		"""
		super().__init__()
		self._build()

	def _build(self):
		"""
		Builds the result.

		:return: The resulting value.
		"""
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)

		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QFrame.Shape.NoFrame)

		scroll_content = QWidget()
		scroll_layout = QVBoxLayout(scroll_content)

		map_selection_label = QLabel("Map Selection")
		scroll_layout.addWidget(map_selection_label)

		map_selection_panel = MapSelectionPanel()
		map_selection_panel.map_generation_requested.connect(
			self.map_generation_requested.emit
		)
		scroll_layout.addWidget(map_selection_panel)

		separator = QFrame()
		separator.setFrameShape(QFrame.Shape.HLine)
		separator.setFrameShadow(QFrame.Shadow.Sunken)
		scroll_layout.addWidget(separator)

		self._planning_panel = PlanningPanel()
		self._planning_panel.waypoint_added.connect(self.waypoint_added.emit)
		self._planning_panel.waypoint_removed.connect(self.waypoint_removed.emit)
		self._planning_panel.waypoints_cleared.connect(self.waypoints_cleared.emit)
		self._planning_panel.autopath_requested.connect(self.autopath_requested.emit)
		scroll_layout.addWidget(self._planning_panel)
		scroll_layout.addWidget(separator)
		self._rover_settings_panel = RoverSettingsPanel()
		scroll_layout.addWidget(self._rover_settings_panel)

		scroll_layout.addStretch(1)
		scroll.setWidget(scroll_content)
		layout.addWidget(scroll)

	def add_waypoint_direct(self, x: float, y: float):
		"""
		Adds a waypoint directly from map click coordinates,
		routing through the planning panel's full data flow.

		:param x: X coordinate.
		:type x: float
		:param y: Y coordinate.
		:type y: float
		:return: None
		"""
		self._planning_panel.add_waypoint_direct(x, y)

	def set_autopath_waypoints(self, points_xy: list[tuple[float, float]] | None):
		if hasattr(self, "_planning_panel") and self._planning_panel is not None:
			self._planning_panel.set_autopath_waypoints(points_xy)

	def get_rover_settings(self) -> RoverSettings:
		mass, power, mu, crr = self._rover_settings_panel.get_values()
		return rover_settings_from_strings(mass, power, mu, crr)

	def get_bicubic_enabled(self) -> bool:
		return self._planning_panel.get_bicubic_enabled() if hasattr(self, "_planning_panel") else False

	def export_settings(self) -> dict:
		"""Collect all current sidebar settings into a serialisable dict."""
		rover_raw = self._rover_settings_panel.get_values()
		rover_preset = self._rover_settings_panel.get_preset_name()
		planning = self._planning_panel.get_planning_settings()

		return {
			"rover": {
				"preset": rover_preset,
				"mass_kg": rover_raw[0],
				"power_hp": rover_raw[1],
				"wheel_friction_coeff": rover_raw[2],
				"rolling_resistance_coeff": rover_raw[3],
			},
			"autopath": {
				"slope_weight": planning["slope_weight"],
				"sun_weight": planning["sun_weight"],
				"meteor_flux_weight": planning["meteor_flux_weight"],
				"temperature_weight": planning["temperature_weight"],
				"algorithm": planning["algorithm"],
				"cost_strategy": planning["cost_strategy"],
				"path_mode": planning["path_mode"],
				"use_bicubic": planning["use_bicubic"],
			},
			"waypoints": planning["waypoints_xy"],
		}

	def import_settings(self, settings: dict) -> list[tuple[float, float]]:
		"""Apply imported settings to the sidebar widgets.

		Returns the list of (x, y) waypoint pairs that were added,
		so the caller can sync the view container.
		"""
		# --- Rover ---
		rover_data = settings.get("rover", {})
		if rover_data.get("preset"):
			self._rover_settings_panel.set_preset(str(rover_data["preset"]))
		# Always set raw values so custom tweaks are also applied
		self._rover_settings_panel.set_values(
			rover_data.get("mass_kg", ""),
			rover_data.get("power_hp", ""),
			rover_data.get("wheel_friction_coeff", ""),
			rover_data.get("rolling_resistance_coeff", ""),
		)

		# --- Autopath config ---
		autopath_data = settings.get("autopath", {})
		self._planning_panel.set_planning_config(autopath_data)

		# --- Waypoints ---
		waypoints_data = settings.get("waypoints", [])
		# Emit waypoints_cleared so view container removes old 3D markers
		self.waypoints_cleared.emit()
		added = self._planning_panel.clear_and_set_waypoints(waypoints_data)

		return added
