from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
	QComboBox,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QMessageBox,
	QPushButton,
	QVBoxLayout,
	QWidget,
)

from cynthium.app.config import MAP_TYPES, SITE_PRESET_PATHS
from cynthium.app.utils.logger import get_logger

logger = get_logger(__name__)


class MapSelectionPanel(QWidget):
	map_generation_requested = Signal(str, str, str)

	def __init__(self):
		super().__init__()
		self._last_path = None
		self._last_datetime = None
		self._last_map_type = None
		self._default_map_type = "Elevation"
		self._build()

	def _build(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(4)

		self.setMinimumWidth(180)

		# Map types row
		type_layout = QHBoxLayout()
		type_label = QLabel("Map type:")
		type_layout.addWidget(type_label)

		self.type_chooser = QComboBox()
		self.type_chooser.addItems(MAP_TYPES)
		self.type_chooser.setCurrentText(self._default_map_type)
		self.type_chooser.currentTextChanged.connect(self._on_map_type_changed)
		type_layout.addWidget(self.type_chooser)
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
		self.date_field.setText("2026-05-13")
		date_container.addWidget(self.date_field)
		datetime_layout.addLayout(date_container)

		# Time section
		time_container = QVBoxLayout()
		time_container.addWidget(QLabel("Time"))
		self.time_field = QLineEdit()
		self.time_field.setPlaceholderText("hh:mm:ss")
		self.time_field.setText("16:50:00")
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
		map_type = self.type_chooser.currentText()
		date_str = self.date_field.text().strip()
		time_str = self.time_field.text().strip()

		# Simple ISO format construction
		datetime_str = f"{date_str}T{time_str}"

		# Validate date and time
		try:
			datetime.fromisoformat(datetime_str)
		except ValueError:
			logger.error(f"Invalid date/time format: {datetime_str}")
			QMessageBox.critical(
				self,
				"Error",
				f"Invalid date or time format: {datetime_str}\nPlease use yyyy-mm-dd and hh:mm:ss",
			)
			return

		if (
			site_path == self._last_path
			and datetime_str == self._last_datetime
			and map_type == self._last_map_type
		):
			logger.info("No changes in settings, ignoring generate request.")
			return

		logger.info(f"Generating {map_type} map for {site_name} at {datetime_str}")
		self._last_path = site_path
		self._last_datetime = datetime_str
		self._last_map_type = map_type
		self.map_generation_requested.emit(site_path, datetime_str, map_type)

	def _on_map_type_changed(self, map_type: str):
		logger.info(f"Map type changed: {map_type}; waiting for Generate Map")
