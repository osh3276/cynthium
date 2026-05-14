import PySide6
from PySide6.QtWidgets import QLabel, QComboBox, QWidget, QLineEdit, QPushButton, QHBoxLayout, QMessageBox
from PySide6.QtWidgets import QVBoxLayout
from datetime import datetime

from craterview.app.utils.logger import get_logger
from craterview.app.config import SITE_PRESET_PATHS, MAP_TYPES

logger = get_logger(__name__)


class MapSelectionPanel(QWidget):
	map_generation_requested = PySide6.QtCore.Signal(str, str)

	def __init__(self):
		super().__init__()
		self._last_path = str(SITE_PRESET_PATHS["Haworth"])
		self._last_datetime = "2026-05-13T16:50:00"
		self._build()

	def _build(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(4)

		self.setMinimumWidth(180)
		
		# Map types row
		type_layout = QHBoxLayout()
		type_label = QLabel("Map types:")
		type_layout.addWidget(type_label)

		type_chooser = QComboBox()
		type_chooser.addItem("Select a map")
		type_chooser.addItems(MAP_TYPES)
		type_chooser.currentTextChanged.connect(self._on_map_type_changed)
		type_layout.addWidget(type_chooser)
		layout.addLayout(type_layout)

		# Preset maps row
		preset_layout = QHBoxLayout()
		preset_label = QLabel("Preset maps:")
		preset_layout.addWidget(preset_label)

		self.preset_chooser = QComboBox()
		self.preset_chooser.addItem("Select a map")
		self.preset_chooser.addItems(sorted(SITE_PRESET_PATHS.keys()))
		preset_layout.addWidget(self.preset_chooser)
		layout.addLayout(preset_layout)

		# Create a horizontal layout for date and time
		datetime_layout = QHBoxLayout()

		# Date section
		date_container = QVBoxLayout()
		date_container.addWidget(QLabel("Date"))
		self.date_field = QLineEdit()
		self.date_field.setPlaceholderText("yyyy-mm-dd")
		date_container.addWidget(self.date_field)
		datetime_layout.addLayout(date_container)

		# Time section
		time_container = QVBoxLayout()
		time_container.addWidget(QLabel("Time"))
		self.time_field = QLineEdit()
		self.time_field.setPlaceholderText("hh:mm:ss")
		time_container.addWidget(self.time_field)
		datetime_layout.addLayout(time_container)

		layout.addLayout(datetime_layout)

		self.generate_button = QPushButton("Generate Map")
		self.generate_button.clicked.connect(self._on_generate_clicked)
		layout.addWidget(self.generate_button)

		layout.addStretch(1)

	def _on_generate_clicked(self):
		site_name = self.preset_chooser.currentText()
		if site_name == "Select a map":
			logger.warning("No site selected")
			QMessageBox.critical(self, "Error", "No map has been selected.")
			return
		
		site_path = str(SITE_PRESET_PATHS[site_name])
		date_str = self.date_field.text().strip()
		time_str = self.time_field.text().strip()

		# Simple ISO format construction
		datetime_str = f"{date_str}T{time_str}"

		# Validate date and time
		try:
			datetime.fromisoformat(datetime_str)
		except ValueError:
			logger.error(f"Invalid date/time format: {datetime_str}")
			QMessageBox.critical(self, "Error", f"Invalid date or time format: {datetime_str}\nPlease use yyyy-mm-dd and hh:mm:ss")
			return

		if site_path == self._last_path and datetime_str == self._last_datetime:
			logger.info("No changes in settings, ignoring generate request.")
			return

		logger.info(f"Generating map for {site_name} at {datetime_str}")
		self._last_path = site_path
		self._last_datetime = datetime_str
		self.map_generation_requested.emit(site_path, datetime_str)

	def _on_path_changed(self, site_name: str):
		# No longer used for immediate updates
		pass

	def _on_map_type_changed(self, map_type: str):
		logger.info(f"Map type changed: {map_type}")
