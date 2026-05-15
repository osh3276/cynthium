from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QPushButton,
	QTextEdit,
	QVBoxLayout,
	QWidget,
)

from craterview.app.engine.raster.point_conversion import xy_to_longlat
from craterview.app.utils.logger import get_logger

logger = get_logger(__name__)


def _on_map_type_changed(map_type: str):
	logger.info(f"Map type changed: {map_type}")


class PlanningPanel(QWidget):
	waypoint_added = Signal(float, float)
	waypoint_removed = Signal(int)

	def __init__(self):
		super().__init__()
		self._waypoint_data = []
		self._build()

	def _build(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(4)

		layout.addWidget(QLabel("Planning"))

		coord_label = QLabel("Coordinate:")
		layout.addWidget(coord_label)

		self.coord_field = QLineEdit()
		self.coord_field.setWindowTitle("hi")
		self.coord_field.setPlaceholderText("x,y")
		layout.addWidget(self.coord_field)

		button = QPushButton("Add waypoint")
		button.clicked.connect(self._on_add_waypoint)
		layout.addWidget(button)

		waypoints_label = QLabel("Waypoints:")
		layout.addWidget(waypoints_label)

		self.waypoints_text = QTextEdit()
		self.waypoints_text.setReadOnly(True)
		layout.addWidget(self.waypoints_text)

		# Delete waypoint section
		delete_layout = QHBoxLayout()
		delete_layout.addWidget(QLabel("Delete waypoint:"))
		self.delete_idx_field = QLineEdit()
		self.delete_idx_field.setPlaceholderText("Num")
		self.delete_idx_field.setFixedWidth(50)
		delete_layout.addWidget(self.delete_idx_field)

		delete_button = QPushButton("Delete")
		delete_button.clicked.connect(self._on_delete_waypoint)
		delete_layout.addWidget(delete_button)
		layout.addLayout(delete_layout)

		layout.addStretch(1)

	def _on_add_waypoint(self):
		coordinates = self.coord_field.text().split(",")
		if len(coordinates) != 2:
			logger.error("Invalid coordinate format")
			return

		coordinates[0] = coordinates[0].strip()
		coordinates[1] = coordinates[1].strip()

		try:
			x, y = float(coordinates[0]), float(coordinates[1])
		except ValueError:
			logger.error("Invalid coordinate values")
			return

		longlat = xy_to_longlat(x, y)
		self._waypoint_data.append((x, y, longlat))
		self.waypoint_added.emit(x, y)
		self._refresh_waypoints_display()

	def _on_delete_waypoint(self):
		text = self.delete_idx_field.text().strip()
		if not text:
			return
		try:
			idx = int(text) - 1  # 1-based to 0-based
		except ValueError:
			logger.error("Invalid waypoint number")
			return

		if 0 <= idx < len(self._waypoint_data):
			self._waypoint_data.pop(idx)
			self.waypoint_removed.emit(idx)
			self._refresh_waypoints_display()
		else:
			logger.error(f"Waypoint index {idx + 1} out of range")

	def _refresh_waypoints_display(self):
		self.waypoints_text.clear()
		for i, (x, y, longlat) in enumerate(self._waypoint_data):
			display_text = (
				f"({i + 1}). ({x}, {y})m, ({longlat[0]:.3f}°N, {longlat[1]:.3f}°E)\n"
			)
			self.waypoints_text.append(display_text)
