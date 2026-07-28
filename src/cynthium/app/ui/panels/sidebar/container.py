from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
	QFrame,
	QLabel,
	QPushButton,
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
	waypoint_edited = Signal(int, float, float)
	waypoints_cleared = Signal()
	autopath_requested = Signal(object)
	rover_settings_requested = Signal()

	def __init__(self):
		super().__init__()
		self._build()

	def _build(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)

		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QFrame.Shape.NoFrame)

		scroll_content = QWidget()
		scroll_layout = QVBoxLayout(scroll_content)

		map_selection_label = QLabel("Map Selection")
		scroll_layout.addWidget(map_selection_label)

		self._map_selection_panel = MapSelectionPanel()
		self._map_selection_panel.map_generation_requested.connect(
			self.map_generation_requested.emit
		)
		scroll_layout.addWidget(self._map_selection_panel)

		sep1 = QFrame()
		sep1.setFrameShape(QFrame.Shape.HLine)
		sep1.setFrameShadow(QFrame.Shadow.Sunken)
		scroll_layout.addWidget(sep1)

		self._planning_panel = PlanningPanel()
		self._planning_panel.waypoint_added.connect(self.waypoint_added.emit)
		self._planning_panel.waypoint_removed.connect(self.waypoint_removed.emit)
		self._planning_panel.waypoints_cleared.connect(self.waypoints_cleared.emit)
		self._planning_panel.autopath_requested.connect(self.autopath_requested.emit)
		self._planning_panel.waypoint_edited.connect(self.waypoint_edited.emit)
		scroll_layout.addWidget(self._planning_panel)

		sep2 = QFrame()
		sep2.setFrameShape(QFrame.Shape.HLine)
		sep2.setFrameShadow(QFrame.Shadow.Sunken)
		scroll_layout.addWidget(sep2)

		rover_btn = QPushButton("Rover Settings...")
		rover_btn.clicked.connect(self.rover_settings_requested.emit)
		scroll_layout.addWidget(rover_btn)

		self._rover_settings_panel = RoverSettingsPanel()
		self._rover_settings_panel.setVisible(False)
		scroll_layout.addWidget(self._rover_settings_panel)

		scroll_layout.addStretch(1)
		scroll.setWidget(scroll_content)
		layout.addWidget(scroll)

	def add_waypoint_direct(self, x: float, y: float):
		self._planning_panel.add_waypoint_direct(x, y)

	def set_autopath_waypoints(self, points_xy: list[tuple[float, float]] | None):
		if hasattr(self, "_planning_panel") and self._planning_panel is not None:
			self._planning_panel.set_autopath_waypoints(points_xy)

	def get_rover_settings(self) -> RoverSettings:
		mass, power, mu, crr = self._rover_settings_panel.get_values()
		return rover_settings_from_strings(mass, power, mu, crr)

	def get_bicubic_enabled(self) -> bool:
		return self._planning_panel.get_bicubic_enabled() if hasattr(self, "_planning_panel") else False

	def get_pause_durations(self) -> list[float]:
		return self._planning_panel.get_pause_durations() if hasattr(self, "_planning_panel") else []

	def get_datetime(self) -> str:
		"""Return the current date/time from the UI as 'yyyy-mm-ddTHH:MM:SS'."""
		if hasattr(self, "_map_selection_panel"):
			date_str = self._map_selection_panel.date_field.text().strip()
			time_str = self._map_selection_panel.time_field.text().strip()
			return f"{date_str}T{time_str}"
		return ""

	def export_settings(self) -> dict:
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
		rover_data = settings.get("rover", {})
		if rover_data.get("preset"):
			self._rover_settings_panel.set_preset(str(rover_data["preset"]))
		self._rover_settings_panel.set_values(
			rover_data.get("mass_kg", ""),
			rover_data.get("power_hp", ""),
			rover_data.get("wheel_friction_coeff", ""),
			rover_data.get("rolling_resistance_coeff", ""),
		)
		autopath_data = settings.get("autopath", {})
		self._planning_panel.set_planning_config(autopath_data)
		waypoints_data = settings.get("waypoints", [])
		self.waypoints_cleared.emit()
		added = self._planning_panel.clear_and_set_waypoints(waypoints_data)
		return added
