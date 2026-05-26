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

		planning_section = PlanningPanel()
		planning_section.waypoint_added.connect(self.waypoint_added.emit)
		planning_section.waypoint_removed.connect(self.waypoint_removed.emit)
		layout.addWidget(planning_section)

		self._rover_settings_panel = RoverSettingsPanel()
		layout.addWidget(self._rover_settings_panel)

		start_simulation_button = QPushButton("Start simulation")
		start_simulation_button.clicked.connect(self.simulation_started.emit)
		layout.addWidget(start_simulation_button)

		layout.addStretch(1)

	def get_rover_settings(self) -> RoverSettings:
		mass, power, mu, crr = self._rover_settings_panel.get_values()
		return rover_settings_from_strings(mass, power, mu, crr)
