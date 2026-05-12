import PySide6
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget, QFrame

from craterview.app.utils.logger import get_logger
from craterview.app.config import SITE_PRESET_PATHS

logger = get_logger(__name__)
from craterview.app.ui.panels.sidebar.map_selection_panel import MapSelectionPanel
from craterview.app.ui.panels.sidebar.planning_panel import PlanningPanel


def _on_map_type_changed(map_type: str):
	logger.info(f"Map type changed: {map_type}")


class AppSidebar(QWidget):
	map_selected = PySide6.QtCore.Signal(str)
	waypoint_added = PySide6.QtCore.Signal(float, float)
	waypoint_removed = PySide6.QtCore.Signal(int)

	def __init__(self):
		super().__init__()
		self._build()
		self.map_selected.emit(str(SITE_PRESET_PATHS["Haworth"]))

	def _build(self):
		layout = QVBoxLayout(self)

		map_selection_panel = MapSelectionPanel()
		map_selection_panel.map_selected.connect(self.map_selected.emit)
		layout.addWidget(map_selection_panel)

		separator = QFrame()
		separator.setFrameShape(QFrame.HLine)
		separator.setFrameShadow(QFrame.Shadow.Sunken)
		layout.addWidget(separator)

		planning_section = PlanningPanel()
		planning_section.waypoint_added.connect(self.waypoint_added.emit)
		planning_section.waypoint_removed.connect(self.waypoint_removed.emit)
		layout.addWidget(planning_section)

		layout.addStretch(1)