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
