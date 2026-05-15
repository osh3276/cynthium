from datetime import datetime, timezone

import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
	QApplication,
	QFileDialog,
	QHBoxLayout,
	QMainWindow,
	QWidget,
)

from craterview.app.engine.simulation.stats import calculate_path_stats
from craterview.app.ui.panels.sidebar.container import AppSidebar
from craterview.app.utils.logger import get_logger

from .ui.map.map_view import MapView
from .ui.map.terrain_view import TerrainView
from .ui.map.view_container import ViewContainer
from .ui.panels.menubar import AppMenuBar

logger = get_logger(__name__)


class Window(QMainWindow):
	_menubar: AppMenuBar
	_terrain_view: TerrainView
	_raster_view: MapView

	def __init__(self):
		super().__init__()
		self.setWindowTitle("CraterView")
		self.setGeometry(100, 100, 1600, 900)
		self._resize_timer = QTimer()
		self._resize_timer.setSingleShot(True)
		self._resize_timer.timeout.connect(self._on_resize_done)
		self._current_path = None
		self._current_datetime = datetime.now(timezone.utc).strftime(
			"%Y-%m-%dT%H:%M:%S"
		)
		self._current_map_type = "Elevation"

		# self.addToolBar(create_toolbar(self))

		self._menubar = AppMenuBar(self)
		self.setMenuBar(self._menubar)

		# Create central widget and layout
		content = QWidget()
		self.setCentralWidget(content)

		layout = QHBoxLayout()

		# Add widgets
		self._view_container = ViewContainer(self)
		layout.addWidget(self._view_container, stretch=1)

		self._sidebar = AppSidebar()
		layout.addWidget(self._sidebar, stretch=0)

		content.setLayout(layout)

		self.statusBar().showMessage("Ready")
		self._connect_signals()

		logger.info("Window initialized")

	def on_button_clicked(self):
		logger.info("Button clicked")

	def resizeEvent(self, event):
		super().resizeEvent(event)
		self._resize_timer.start(1500)  # ms delay

	def _on_resize_done(self):
		self._view_container.terrain_view.render()

	def _connect_signals(self):
		self._menubar.action_open.triggered.connect(self._open_file_dialog)
		self._menubar.action_exit.triggered.connect(self.close)
		self._sidebar.map_generation_requested.connect(self._load_site_with_datetime)
		self._sidebar.waypoint_added.connect(self._view_container.add_waypoint)
		self._sidebar.waypoint_removed.connect(self._view_container.remove_waypoint)
		self._sidebar.simulation_started.connect(self._on_start_simulation)

	def _on_start_simulation(self):
		self.statusBar().showMessage("Running simulation...")
		# Process events to ensure status bar updates
		QApplication.processEvents()

		points = self._view_container.get_waypoint_3d_points()
		if len(points) < 2:
			self._sidebar.set_results("Please add at least two waypoints.")
			self.statusBar().showMessage("Ready")
			return

		(
			map_data,
			map_meta,
			slope_data,
			temperature_data,
			temperature_meta,
			illumination_data,
			illumination_meta,
		) = self._view_container.get_current_map_data()
		transform = map_meta.get("transform") if map_meta else None
		temperature_transform = (
			temperature_meta.get("transform") if temperature_meta else None
		)
		illumination_transform = (
			illumination_meta.get("transform") if illumination_meta else None
		)

		stats = calculate_path_stats(
			np.array(points),
			map_data,
			transform,
			slope_data,
			temperature_data,
			temperature_transform,
			illumination_data,
			illumination_transform,
		)

		message = (
			f"Total Displacement: {stats['total_displacement']:.2f} m\n"
			f"Total Distance Travelled: {stats['total_distance_travelled']:.2f} m\n"
			f"Total Climb Distance: {stats['total_elevation_gain']:.2f} m\n"
			f"Net Elevation Change: {stats['net_elevation_change']:.2f} m\n"
			f"Average Slope: {stats['average_slope']:.2f}°\n"
			f"Max Slope: {stats['max_slope']:.2f}°\n"
			f"Min Slope: {stats['min_slope']:.2f}°\n"
			f"Max Temp (avg.): {stats['max_temperature']:.2f} K\n"
			f"Min Temp (avg.): {stats['min_temperature']:.2f} K\n"
			f"Average Temp (avg.): {stats['average_temperature']:.2f} K\n"
			f"Illumination (yearly avg.): {stats['percent_illumination']:.2f}%"
		)
		self._sidebar.set_results(message)
		self.statusBar().showMessage("Simulation complete")

	def _open_file_dialog(self):
		path, _ = QFileDialog.getOpenFileName(
			self,
			"Open GeoTIFF",
			"",
			"GeoTIFF files (*.tif *.tiff);;All files (*)",
		)
		if path:
			self._load_site_with_datetime(
				path, self._current_datetime, self._current_map_type
			)

	def _load_site(self, path: str):
		self._load_site_with_datetime(
			path, self._current_datetime, self._current_map_type
		)

	def _load_site_with_datetime(
		self, path: str, datetime_str: str, map_type: str = "Elevation"
	):
		only_map_type_changed = (
			self._current_path == path
			and self._current_datetime == datetime_str
			and self._current_map_type != map_type
		)

		if only_map_type_changed and self._view_container.display_map_type(map_type):
			self._current_map_type = map_type
			self.statusBar().showMessage(
				f"Loaded {map_type} raster map without regenerating 3D terrain"
			)
			return

		self.statusBar().showMessage(
			f"Loading {map_type} map for {path} at {datetime_str}..."
		)
		QApplication.processEvents()
		self._view_container.load(path, map_type, datetime_str)
		self._current_path = path
		self._current_datetime = datetime_str
		self._current_map_type = map_type
		self.statusBar().showMessage(f"Loaded {map_type} map: {path} at {datetime_str}")

	def _on_refresh(self):
		pass

	def get_view_container(self):
		return self._view_container
