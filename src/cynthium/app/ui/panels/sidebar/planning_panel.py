"""Planning panel with editable waypoint table and per-waypoint pause."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
	QApplication,
	QCheckBox,
	QComboBox,
	QDoubleSpinBox,
	QHBoxLayout,
	QHeaderView,
	QLabel,
	QLineEdit,
	QPushButton,
	QTableWidget,
	QTableWidgetItem,
	QVBoxLayout,
	QWidget,
)

from cynthium.app.config import (
	ALPHA_SLOPE,
	BETA_SHADOW,
	METEOR_FLUX_WEIGHT,
	TEMPERATURE_WEIGHT,
)
from cynthium.app.engine.raster.point_conversion import xy_to_longlat
from cynthium.app.utils.logger import get_logger

logger = get_logger(__name__)


class _FloatItem(QTableWidgetItem):
	"""A table item that stores a float but displays with 1 decimal."""

	def __init__(self, value: float):
		super().__init__(f"{value:.1f}")
		self._float_val = value

	def float_val(self) -> float:
		return self._float_val

	def set_float(self, value: float):
		self._float_val = value
		self.setText(f"{value:.1f}")


class PlanningPanel(QWidget):
	waypoint_added = Signal(float, float)
	waypoint_removed = Signal(int)
	waypoints_cleared = Signal()
	autopath_requested = Signal(object)
	waypoint_edited = Signal(int, float, float)

	def __init__(self):
		super().__init__()
		self._waypoint_data: list[tuple[float, float]] = []
		self._pause_data: list[float] = []
		self._block_table_edit = False
		self._build()

	def _build(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(4)

		layout.addWidget(QLabel("Planning"))

		# ── Manual coordinate entry ──
		coord_row = QHBoxLayout()
		self._coord_field = QLineEdit()
		self._coord_field.setPlaceholderText("x, y")
		coord_row.addWidget(self._coord_field)
		add_btn = QPushButton("Add")
		add_btn.clicked.connect(self._on_add_coord)
		coord_row.addWidget(add_btn)
		layout.addLayout(coord_row)

		# ── Waypoint table (index, x, y, pause, delete) ──
		self._table = QTableWidget(0, 5)
		self._table.setHorizontalHeaderLabels(["#", "X (m)", "Y (m)", "Pause (s)", ""])
		header = self._table.horizontalHeader()
		header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
		header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
		header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
		header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
		header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
		self._table.verticalHeader().setVisible(False)
		self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
		self._table.cellChanged.connect(self._on_cell_changed)
		self._table.setMaximumHeight(200)
		layout.addWidget(self._table)

		# ── Clear ──
		clear_btn = QPushButton("Clear all waypoints")
		clear_btn.clicked.connect(self._on_clear_path)
		layout.addWidget(clear_btn)

		self._info_label = QLabel("")
		self._info_label.setWordWrap(True)
		layout.addWidget(self._info_label)

		# ── Autopath ──
		autopath_btn = QPushButton("Autopath")
		autopath_btn.clicked.connect(self._on_autopath)
		layout.addWidget(autopath_btn)

		layout.addWidget(QLabel("Autopath waypoints:"))
		self._autopath_table = QTableWidget(0, 3)
		self._autopath_table.setHorizontalHeaderLabels(["#", "X (m)", "Y (m)"])
		header = self._autopath_table.horizontalHeader()
		header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
		header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
		header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
		self._autopath_table.verticalHeader().setVisible(False)
		self._autopath_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
		self._autopath_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		self._autopath_table.setMaximumHeight(150)
		layout.addWidget(self._autopath_table)

		# ── Autopath config ──
		layout.addWidget(QLabel("Autopath settings:"))
		cfg2 = QHBoxLayout()
		cfg2.addWidget(QLabel("Slope weight:"))
		self.slope_weight_field = QPushButton(str(ALPHA_SLOPE))
		self.slope_weight_field.setFixedWidth(60)
		cfg2.addWidget(self.slope_weight_field)
		cfg2.addWidget(QLabel("Sun weight:"))
		self.sun_weight_field = QPushButton(str(BETA_SHADOW))
		self.sun_weight_field.setFixedWidth(60)
		cfg2.addWidget(self.sun_weight_field)
		layout.addLayout(cfg2)

		cfg4 = QHBoxLayout()
		cfg4.addWidget(QLabel("Met. flux weight:"))
		self.meteor_flux_weight_field = QPushButton(str(METEOR_FLUX_WEIGHT))
		self.meteor_flux_weight_field.setFixedWidth(60)
		cfg4.addWidget(self.meteor_flux_weight_field)
		cfg4.addWidget(QLabel("Temperature weight:"))
		self.temperature_weight_field = QPushButton(str(TEMPERATURE_WEIGHT))
		self.temperature_weight_field.setFixedWidth(60)
		cfg4.addWidget(self.temperature_weight_field)
		layout.addLayout(cfg4)

		cfg3 = QHBoxLayout()
		cfg3.addWidget(QLabel("Algorithm:"))
		self.algorithm_combo = QComboBox()
		self.algorithm_combo.addItems(["A*", "Dijkstra"])
		cfg3.addWidget(self.algorithm_combo)
		cfg3.addWidget(QLabel("Strategy:"))
		self.cost_strategy_combo = QComboBox()
		self.cost_strategy_combo.addItems(["Weighted cost", "Minimax"])
		cfg3.addWidget(self.cost_strategy_combo)
		layout.addLayout(cfg3)

		cfg5 = QHBoxLayout()
		cfg5.addWidget(QLabel("Path mode:"))
		self.path_mode_combo = QComboBox()
		self.path_mode_combo.addItems(["Waypoint to waypoint", "Start to finish"])
		cfg5.addWidget(self.path_mode_combo)
		layout.addLayout(cfg5)

		self.bicubic_checkbox = QCheckBox("Use bicubic interpolation (5 m/px)")
		layout.addWidget(self.bicubic_checkbox)

		layout.addStretch(1)

	# ── Waypoint management ──

	def add_waypoint_direct(self, x: float, y: float, pause_s: float = 0.0):
		self._waypoint_data.append((x, y))
		self._pause_data.append(pause_s)
		self.waypoint_added.emit(x, y)
		self._refresh_table()
		self._update_info()

	def remove_waypoint_at(self, index: int):
		if 0 <= index < len(self._waypoint_data):
			self._waypoint_data.pop(index)
			self._pause_data.pop(index)
			self.waypoint_removed.emit(index)
			self._refresh_table()
			self._update_info()

	def clear_all_waypoints(self):
		self._waypoint_data.clear()
		self._pause_data.clear()
		self._autopath_table.setRowCount(0)
		self.waypoints_cleared.emit()
		self._refresh_table()

	def set_autopath_waypoints(self, points_xy: list[tuple[float, float]] | None):
		self._autopath_table.setRowCount(0)
		if not points_xy:
			return
		self._autopath_table.setRowCount(len(points_xy))
		for i, (x, y) in enumerate(points_xy):
			num_item = QTableWidgetItem(str(i + 1))
			num_item.setFlags(num_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
			self._autopath_table.setItem(i, 0, num_item)
			self._autopath_table.setItem(i, 1, _FloatItem(x))
			self._autopath_table.setItem(i, 2, _FloatItem(y))

	def set_planning_config(self, config: dict):
		if "slope_weight" in config:
			self.slope_weight_field.setText(str(config["slope_weight"]))
		if "sun_weight" in config:
			self.sun_weight_field.setText(str(config["sun_weight"]))
		if "meteor_flux_weight" in config:
			self.meteor_flux_weight_field.setText(str(config["meteor_flux_weight"]))
		if "temperature_weight" in config:
			self.temperature_weight_field.setText(str(config["temperature_weight"]))
		if "algorithm" in config:
			idx = self.algorithm_combo.findText(config["algorithm"])
			if idx >= 0:
				self.algorithm_combo.setCurrentIndex(idx)
		if "cost_strategy" in config:
			idx = self.cost_strategy_combo.findText(config["cost_strategy"])
			if idx >= 0:
				self.cost_strategy_combo.setCurrentIndex(idx)
		if "path_mode" in config:
			idx = self.path_mode_combo.findText(config["path_mode"])
			if idx >= 0:
				self.path_mode_combo.setCurrentIndex(idx)
		if "use_bicubic" in config:
			self.bicubic_checkbox.setChecked(bool(config["use_bicubic"]))

	def clear_and_set_waypoints(self, waypoints_xy: list[list[float]]) -> list[tuple[float, float]]:
		self._waypoint_data.clear()
		self._pause_data.clear()
		added = []
		for xy in waypoints_xy:
			x, y = float(xy[0]), float(xy[1])
			self._waypoint_data.append((x, y))
			self._pause_data.append(0.0)
			added.append((x, y))
		self._refresh_table()
		self._update_info()
		return added

	def get_planning_settings(self) -> dict:
		waypoints_xy = []
		for x, y in self._waypoint_data:
			waypoints_xy.append([float(x), float(y)])
		return {
			"slope_weight": self.slope_weight_field.text().strip(),
			"sun_weight": self.sun_weight_field.text().strip(),
			"meteor_flux_weight": self.meteor_flux_weight_field.text().strip(),
			"temperature_weight": self.temperature_weight_field.text().strip(),
			"algorithm": self.algorithm_combo.currentText(),
			"cost_strategy": self.cost_strategy_combo.currentText(),
			"path_mode": self.path_mode_combo.currentText(),
			"use_bicubic": self.bicubic_checkbox.isChecked(),
			"waypoints_xy": waypoints_xy,
		}

	def get_pause_durations(self) -> list[float]:
		return list(self._pause_data)

	def get_bicubic_enabled(self) -> bool:
		return self.bicubic_checkbox.isChecked()

	# ── Internal helpers ──

	def _refresh_table(self):
		self._block_table_edit = True
		self._table.setRowCount(len(self._waypoint_data))
		for i in range(len(self._waypoint_data)):
			x, y = self._waypoint_data[i]
			pause = self._pause_data[i] if i < len(self._pause_data) else 0.0

			num_item = QTableWidgetItem(str(i + 1))
			num_item.setFlags(num_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
			self._table.setItem(i, 0, num_item)

			x_item = _FloatItem(x)
			self._table.setItem(i, 1, x_item)

			y_item = _FloatItem(y)
			self._table.setItem(i, 2, y_item)

			pause_item = QTableWidgetItem(f"{pause:.1f}")
			self._table.setItem(i, 3, pause_item)

			del_btn = QPushButton("Delete")
			del_btn.setFixedWidth(60)
			del_btn.clicked.connect(lambda checked, idx=i: self.remove_waypoint_at(idx))
			self._table.setCellWidget(i, 4, del_btn)
		self._block_table_edit = False

	def _on_cell_changed(self, row: int, col: int):
		if self._block_table_edit:
			return
		if row < 0 or row >= len(self._waypoint_data):
			return
		if col == 1:
			try:
				val = float(self._table.item(row, col).text())
			except (ValueError, TypeError):
				self._refresh_table()
				return
			x, y = self._waypoint_data[row]
			self._waypoint_data[row] = (val, y)
			self.waypoint_edited.emit(row, val, y)
		elif col == 2:
			try:
				val = float(self._table.item(row, col).text())
			except (ValueError, TypeError):
				self._refresh_table()
				return
			x, y = self._waypoint_data[row]
			self._waypoint_data[row] = (x, val)
			self.waypoint_edited.emit(row, x, val)
		elif col == 3:
			try:
				pause = float(self._table.item(row, col).text())
			except (ValueError, TypeError):
				self._refresh_table()
				return
			if row < len(self._pause_data):
				self._pause_data[row] = pause
		self._update_info()

	def _update_info(self):
		if not self._waypoint_data:
			self._info_label.setText("")
			return
		parts = []
		for i, (x, y) in enumerate(self._waypoint_data):
			ll = xy_to_longlat(x, y)
			lon, lat = float(ll[0]), float(ll[1])
			lat_dir = "S" if lat < 0 else "N"
			lon_dir = "W" if lon < 0 else "E"
			parts.append(
				f"{i+1}. ({abs(lat):.3f}\u00b0{lat_dir}, {abs(lon):.3f}\u00b0{lon_dir})"
			)
		self._info_label.setText("  ".join(parts))

	def _on_add_coord(self):
		text = self._coord_field.text().strip()
		if not text:
			return
		parts = text.split(",")
		if len(parts) != 2:
			logger.error("Enter coordinates as x, y")
			return
		try:
			x, y = float(parts[0].strip()), float(parts[1].strip())
		except ValueError:
			logger.error("Invalid coordinate values")
			return
		self.add_waypoint_direct(x, y)
		self._coord_field.clear()

	def _on_clear_path(self):
		self.clear_all_waypoints()

	def _on_autopath(self):
		if len(self._waypoint_data) < 2:
			logger.error("Need at least 2 waypoints for autopath")
			return
		try:
			slope_weight = float(self.slope_weight_field.text().strip())
			sun_weight = float(self.sun_weight_field.text().strip())
			meteor_flux_weight = float(self.meteor_flux_weight_field.text().strip())
			temperature_weight = float(self.temperature_weight_field.text().strip())
		except ValueError:
			logger.error("Invalid autopath config values")
			return
		if any(w < 0.0 for w in [slope_weight, sun_weight, meteor_flux_weight, temperature_weight]):
			logger.error("Weights must be >= 0")
			return
		waypoints_xy = self._waypoint_data[:]
		payload = {
			"waypoints_xy": waypoints_xy,
			"slope_weight": slope_weight,
			"sun_weight": sun_weight,
			"meteor_flux_weight": meteor_flux_weight,
			"temperature_weight": temperature_weight,
			"algorithm": self.algorithm_combo.currentText(),
			"cost_strategy": self.cost_strategy_combo.currentText(),
			"path_mode": self.path_mode_combo.currentText(),
			"use_bicubic": self.bicubic_checkbox.isChecked(),
		}
		self._autopath_table.setRowCount(0)
		QApplication.processEvents()
		QApplication.processEvents()
		self.autopath_requested.emit(payload)
