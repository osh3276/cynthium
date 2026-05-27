from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
	QFrame,
	QLabel,
	QPushButton,
	QVBoxLayout,
	QWidget,
)

from craterview.app.engine.simulation.rover_settings import (
	RoverSettings,
	rover_settings_from_strings,
)
from craterview.app.ui.panels.sidebar.map_selection_panel import MapSelectionPanel
from craterview.app.ui.panels.sidebar.planning_panel import PlanningPanel
from craterview.app.ui.panels.sidebar.rover_settings_panel import RoverSettingsPanel


class AppSidebar(QWidget):
	map_selected = Signal(str)
	map_generation_requested = Signal(str, str, str)
	waypoint_added = Signal(float, float)
	waypoint_removed = Signal(int)
	autopath_requested = Signal(object)
	simulation_started = Signal()

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

		map_selection_label = QLabel("Map Selection")
		layout.addWidget(map_selection_label)

		map_selection_panel = MapSelectionPanel()
		map_selection_panel.map_generation_requested.connect(
			self.map_generation_requested.emit
		)
		layout.addWidget(map_selection_panel)

		separator = QFrame()
		separator.setFrameShape(QFrame.Shape.HLine)
		separator.setFrameShadow(QFrame.Shadow.Sunken)
		layout.addWidget(separator)

		self._planning_panel = PlanningPanel()
		self._planning_panel.waypoint_added.connect(self.waypoint_added.emit)
		self._planning_panel.waypoint_removed.connect(self.waypoint_removed.emit)
		self._planning_panel.autopath_requested.connect(self.autopath_requested.emit)
		layout.addWidget(self._planning_panel)

		self._rover_settings_panel = RoverSettingsPanel()
		layout.addWidget(self._rover_settings_panel)

		start_simulation_button = QPushButton("Start simulation")
		start_simulation_button.clicked.connect(self.simulation_started.emit)
		layout.addWidget(start_simulation_button)

		layout.addStretch(1)

	def set_autopath_waypoints(self, points_xy: list[tuple[float, float]] | None):
		if hasattr(self, "_planning_panel") and self._planning_panel is not None:
			self._planning_panel.set_autopath_waypoints(points_xy)

	def get_rover_settings(self) -> RoverSettings:
		mass, power, mu, crr = self._rover_settings_panel.get_values()
		return rover_settings_from_strings(mass, power, mu, crr)
