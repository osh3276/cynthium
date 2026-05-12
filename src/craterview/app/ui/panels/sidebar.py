import PySide6
from PySide6.QtWidgets import QToolButton, QPushButton, QLabel, QLineEdit, QComboBox, QWidget, QFrame, QHBoxLayout, \
	QTextEdit
from PySide6.QtWidgets import QVBoxLayout

from craterview.app.config import SITE_PRESET_PATHS, MAP_TYPES


def _on_map_type_changed(map_type: str):
	print(f"Map type changed: {map_type}")


class AppSidebar(QWidget):
	map_selected = PySide6.QtCore.Signal(str)

	def __init__(self):
		super().__init__()
		self.map_selected.emit(str(SITE_PRESET_PATHS["Haworth"]))
		self._build()

	def _build(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(4)

		self.setMinimumWidth(180)
		preset_label = QLabel("Map types:")
		layout.addWidget(preset_label)

		type_chooser = QComboBox()
		type_chooser.addItems(MAP_TYPES)
		type_chooser.currentTextChanged.connect(_on_map_type_changed)
		layout.addWidget(type_chooser)

		preset_label = QLabel("Preset maps:")
		layout.addWidget(preset_label)

		preset_chooser = QComboBox()
		preset_chooser.addItems(SITE_PRESET_PATHS.keys())
		preset_chooser.currentTextChanged.connect(self._on_path_changed)
		layout.addWidget(preset_chooser)

		separator = QFrame()
		separator.setFrameShape(QFrame.HLine)
		separator.setFrameShadow(QFrame.Shadow.Sunken)
		layout.addWidget(separator)

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

	def _on_path_changed(self, site_name: str):
		print(f"Site selected: {site_name}")
		site_path = SITE_PRESET_PATHS[site_name]
		self.map_selected.emit(str(site_path))

	def _on_add_waypoint(self):
		self.waypoints_text.append(self.coord_field.text())