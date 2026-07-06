from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
	QAbstractItemView,
	QComboBox,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QListWidget,
	QListWidgetItem,
	QMessageBox,
	QPushButton,
	QToolButton,
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
		self._last_active_map_type = None
		self._build()

	def _build(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(4)

		self.setMinimumWidth(180)

		# Layer manager
		layer_label = QLabel("Map layers:")
		layout.addWidget(layer_label)

		layers_layout = QHBoxLayout()
		self.layer_list = QListWidget()
		self.layer_list.setAlternatingRowColors(True)
		self.layer_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.layer_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
		self.layer_list.setDefaultDropAction(Qt.DropAction.MoveAction)
		self.layer_list.setMinimumHeight(170)

		for map_type in MAP_TYPES:
			item = QListWidgetItem(map_type)
			item.setFlags(
				item.flags()
				| Qt.ItemFlag.ItemIsUserCheckable
				| Qt.ItemFlag.ItemIsSelectable
				| Qt.ItemFlag.ItemIsEnabled
				| Qt.ItemFlag.ItemIsDragEnabled
			)
			item.setCheckState(
				Qt.CheckState.Checked
				if map_type == self._default_map_type
				else Qt.CheckState.Unchecked
			)
			self.layer_list.addItem(item)

		default_row = MAP_TYPES.index(self._default_map_type)
		self.layer_list.setCurrentRow(default_row)
		self.layer_list.itemChanged.connect(self._on_layers_changed)
		self.layer_list.model().rowsMoved.connect(self._on_layers_changed)
		layers_layout.addWidget(self.layer_list)

		layer_controls = QVBoxLayout()
		self.layer_up_button = QToolButton()
		self.layer_up_button.setText("Up")
		self.layer_up_button.clicked.connect(lambda: self._move_selected_layer(-1))
		layer_controls.addWidget(self.layer_up_button)

		self.layer_down_button = QToolButton()
		self.layer_down_button.setText("Down")
		self.layer_down_button.clicked.connect(lambda: self._move_selected_layer(1))
		layer_controls.addWidget(self.layer_down_button)
		layer_controls.addStretch(1)
		layers_layout.addLayout(layer_controls)

		layout.addLayout(layers_layout)

		# Preset maps row
		preset_layout = QHBoxLayout()
		preset_label = QLabel("Preset maps:")
		preset_layout.addWidget(preset_label)

		self.preset_chooser = QComboBox()
		self.preset_chooser.addItem("Select a map")
		self.preset_chooser.addItems(sorted(SITE_PRESET_PATHS.keys()))
		self.preset_chooser.currentTextChanged.connect(self._on_preset_changed)
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
		self._request_map_generation(show_errors=True)

	def _request_map_generation(self, *, show_errors: bool):
		site_name = self.preset_chooser.currentText()
		if site_name == "Select a map":
			if show_errors:
				logger.warning("No site selected")
				QMessageBox.critical(self, "Error", "No map has been selected.")
			return

		site_path = str(SITE_PRESET_PATHS[site_name])
		map_type = self._active_map_type()
		if map_type is None:
			if show_errors:
				QMessageBox.critical(
					self,
					"Error",
					"At least one map layer must be visible.",
				)
			return
		date_str = self.date_field.text().strip()
		time_str = self.time_field.text().strip()

		# Simple ISO format construction
		datetime_str = f"{date_str}T{time_str}"

		# Validate date and time
		try:
			datetime.fromisoformat(datetime_str)
		except ValueError:
			if show_errors:
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

	def _active_map_type(self) -> str | None:
		for row in range(self.layer_list.count()):
			item = self.layer_list.item(row)
			if item.checkState() == Qt.CheckState.Checked:
				return item.text()
		return None

	def _move_selected_layer(self, delta: int):
		current_row = self.layer_list.currentRow()
		if current_row < 0:
			return
		new_row = current_row + int(delta)
		if new_row < 0 or new_row >= self.layer_list.count():
			return

		item = self.layer_list.takeItem(current_row)
		self.layer_list.insertItem(new_row, item)
		self.layer_list.setCurrentRow(new_row)
		self._on_layers_changed()

	def _on_layers_changed(self, *args):
		active = self._active_map_type()
		if active != self._last_active_map_type:
			if active is None:
				logger.info("No active map layer selected; waiting for Generate Map")
			else:
				logger.info(f"Active map layer changed: {active}; waiting for Generate Map")
			self._last_active_map_type = active
		self._request_map_generation(show_errors=False)

	def _on_preset_changed(self, preset: str):
		if preset == "Select a map":
			return
		logger.info(f"Preset map changed: {preset}; auto-generating map")
		self._request_map_generation(show_errors=False)
