from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
	QComboBox,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QPushButton,
	QTextEdit,
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


def _on_map_type_changed(map_type: str):
	logger.info(f"Map type changed: {map_type}")


class PlanningPanel(QWidget):
	waypoint_added = Signal(float, float)
	waypoint_removed = Signal(int)
	autopath_requested = Signal(object)

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

		# Autopath
		autopath_button = QPushButton("Autopath")
		autopath_button.clicked.connect(self._on_autopath)
		layout.addWidget(autopath_button)

		layout.addWidget(QLabel("Autopath waypoints:"))
		self.autopath_text = QTextEdit()
		self.autopath_text.setReadOnly(True)
		self.autopath_text.setPlaceholderText("(autopath output will appear here)")
		layout.addWidget(self.autopath_text)

		# Autopath config
		cfg2 = QHBoxLayout()
		cfg2.addWidget(QLabel("Slope weight:"))
		self.slope_weight_field = QLineEdit()
		self.slope_weight_field.setFixedWidth(60)
		self.slope_weight_field.setText(str(ALPHA_SLOPE))
		cfg2.addWidget(self.slope_weight_field)

		cfg2.addWidget(QLabel("Sun weight:"))
		self.sun_weight_field = QLineEdit()
		self.sun_weight_field.setFixedWidth(60)
		self.sun_weight_field.setText(str(BETA_SHADOW))
		cfg2.addWidget(self.sun_weight_field)
		layout.addLayout(cfg2)

		cfg4 = QHBoxLayout()
		cfg4.addWidget(QLabel("Met. flux weight:"))
		self.meteor_flux_weight_field = QLineEdit()
		self.meteor_flux_weight_field.setFixedWidth(60)
		self.meteor_flux_weight_field.setText(str(METEOR_FLUX_WEIGHT))
		cfg4.addWidget(self.meteor_flux_weight_field)

		cfg4.addWidget(QLabel("Temperature weight:"))
		self.temperature_weight_field = QLineEdit()
		self.temperature_weight_field.setFixedWidth(60)
		self.temperature_weight_field.setText(str(TEMPERATURE_WEIGHT))
		cfg4.addWidget(self.temperature_weight_field)
		layout.addLayout(cfg4)

		cfg3 = QHBoxLayout()
		cfg3.addWidget(QLabel("Algorithm:"))
		self.algorithm_combo = QComboBox()
		self.algorithm_combo.addItems(["Theta*", "Dijkstra"])
		cfg3.addWidget(self.algorithm_combo)

		cfg3.addWidget(QLabel("Strategy:"))
		self.cost_strategy_combo = QComboBox()
		self.cost_strategy_combo.addItems(["Weighted cost", "Minimax"])
		self.cost_strategy_combo.setToolTip(
			"Weighted cost: trade-off between distance, grade, and sunlight.\n"
			"Minimax: avoid steep grade and deep shadows at all costs."
		)
		cfg3.addWidget(self.cost_strategy_combo)
		layout.addLayout(cfg3)

		layout.addStretch(1)

	def add_waypoint_direct(self, x: float, y: float):
		"""
		Adds a waypoint directly from coordinates (e.g. from a map click)
		without reading from the text field.

		:param x: X coordinate.
		:type x: float
		:param y: Y coordinate.
		:type y: float
		:return: None
		"""
		longlat = xy_to_longlat(x, y)
		self._waypoint_data.append((x, y, longlat))
		if hasattr(self, "autopath_text"):
			self.autopath_text.clear()
		self.waypoint_added.emit(x, y)
		self._refresh_waypoints_display()

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

		self.add_waypoint_direct(x, y)

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
			if hasattr(self, "autopath_text"):
				self.autopath_text.clear()
			self.waypoint_removed.emit(idx)
			self._refresh_waypoints_display()
		else:
			logger.error(f"Waypoint index {idx + 1} out of range")

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

		if slope_weight < 0.0 or sun_weight < 0.0 or meteor_flux_weight < 0.0 or temperature_weight < 0.0:
			logger.error("Weights must be >= 0")
			return

		waypoints_xy = [(float(x), float(y)) for (x, y, _ll) in self._waypoint_data]
		payload = {
			"waypoints_xy": waypoints_xy,
			"slope_weight": float(slope_weight),
			"sun_weight": float(sun_weight),
			"meteor_flux_weight": float(meteor_flux_weight),
			"temperature_weight": float(temperature_weight),
			"algorithm": self.algorithm_combo.currentText(),
			"cost_strategy": self.cost_strategy_combo.currentText(),
		}
		self.autopath_text.setPlainText("Running autopath...")
		self.autopath_requested.emit(payload)

	def set_autopath_waypoints(self, points_xy: list[tuple[float, float]] | None):
		self.autopath_text.clear()
		if not points_xy:
			return
		for i, (x, y) in enumerate(points_xy):
			self.autopath_text.append(f"({i + 1}). ({x:.2f}, {y:.2f})m")

	def _refresh_waypoints_display(self):
		self.waypoints_text.clear()
		for i, (x, y, longlat) in enumerate(self._waypoint_data):
			display_text = (
				f"({i + 1}). ({x:.2f}, {y:.2f})m, ({longlat[0]:.3f}°N, {longlat[1]:.3f}°E)\n"
			)
			self.waypoints_text.append(display_text)
