import PySide6
from PySide6.QtWidgets import QToolButton, QPushButton, QLabel, QLineEdit, QComboBox, QWidget, QFrame
from PySide6.QtWidgets import QVBoxLayout

from craterview.app.config import SITE_PRESET_PATHS


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

		mapchooser = QComboBox()
		mapchooser.addItems(SITE_PRESET_PATHS.keys())
		mapchooser.currentTextChanged.connect(self._on_path_changed)
		layout.addWidget(mapchooser)

		preset_label = QLabel("Preset maps:")
		layout.addWidget(preset_label)

		mapchooser = QComboBox()
		mapchooser.addItems(SITE_PRESET_PATHS.keys())
		mapchooser.currentTextChanged.connect(self._on_path_changed)
		layout.addWidget(mapchooser)

		separator = QFrame()
		separator.setFrameShape(QFrame.HLine)
		separator.setFrameShadow(QFrame.Shadow.Sunken)
		layout.addWidget(separator)

		layout.addWidget(QLabel("Planning"))

		coord_label = QLabel("Coordinate:")
		layout.addWidget(coord_label)

		coord_field = QLineEdit()
		coord_field.setWindowTitle("hi")
		coord_field.setPlaceholderText("x,y")
		layout.addWidget(coord_field)

		button = QPushButton("Add waypoint")
		layout.addWidget(button)

		layout.addStretch(1)

	def _on_path_changed(self, site_name: str):
		print(f"Site selected: {site_name}")
		site_path = SITE_PRESET_PATHS[site_name]
		self.map_selected.emit(str(site_path))

	def _on_add_coordinate(self):
		print("Add coordinate clicked")