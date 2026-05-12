from PySide6.QtWidgets import QPushButton, QLabel, QLineEdit, QWidget, QHBoxLayout, \
	QTextEdit
from PySide6.QtWidgets import QVBoxLayout

from craterview.app.engine.raster.point_conversion import xy_to_longlat
from craterview.app.utils.logger import get_logger

logger = get_logger(__name__)


def _on_map_type_changed(map_type: str):
	logger.info(f"Map type changed: {map_type}")


class PlanningPanel(QWidget):
	def __init__(self):
		super().__init__()
		self._build()

	def _build(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(4)

		layout.addWidget(QLabel("Planning"))

		# Create a horizontal layout for date and time
		datetime_layout = QHBoxLayout()

		# Date section
		date_container = QVBoxLayout()
		date_container.addWidget(QLabel("Date"))
		date_field = QLineEdit()
		date_field.setPlaceholderText("yyyy-mm-dd")
		date_container.addWidget(date_field)
		datetime_layout.addLayout(date_container)

		# Time section
		time_container = QVBoxLayout()
		time_container.addWidget(QLabel("Time"))
		time_field = QLineEdit()
		time_field.setPlaceholderText("hh:mm:ss")
		time_container.addWidget(time_field)
		datetime_layout.addLayout(time_container)

		# Add the horizontal layout to the main layout
		layout.addLayout(datetime_layout)

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

		layout.addStretch(1)

	def _on_add_waypoint(self):
		coordinates = self.coord_field.text().split(",")
		coordinates[0] = coordinates[0].strip()
		coordinates[1] = coordinates[1].strip()
		waypoint_num = len(self.waypoints_text.toPlainText().splitlines()) + 1

		if len(coordinates) != 2:
			logger.error("Invalid coordinate format")
			# TODO: popup an error dialog
			return

		longlat = xy_to_longlat(float(coordinates[0]), float(coordinates[1]))

		display_text = f"({waypoint_num}). ({coordinates[0]}, {coordinates[1]})m, ({longlat[0]:.3f}°N, {longlat[1]:.3f}°E)\n"
		logger.info(display_text)

		self.waypoints_text.append(display_text)
