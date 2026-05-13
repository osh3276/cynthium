import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QWidget, QFileDialog

from .ui.map.view_container import ViewContainer
from .ui.map.map_view import MapView
from .ui.map.terrain_view import TerrainView
from craterview.app.ui.panels.sidebar.container import AppSidebar
from .ui.panels.menubar import AppMenuBar

from craterview.app.utils.logger import get_logger
from craterview.app.engine.simulation.stats import calculate_path_stats
from craterview.app.config import SITE_PRESET_PATHS

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
		points = self._view_container.get_waypoint_3d_points()
		if len(points) < 2:
			self._sidebar.set_results("Please add at least two waypoints.")
			return

		map_data, map_meta = self._view_container.get_current_map_data()
		transform = map_meta.get("transform") if map_meta else None

		stats = calculate_path_stats(np.array(points), map_data, transform)

		message = (
			f"Total Distance: {stats['total_distance']:.2f} m\n"
			f"Total Climb Distance: {stats['total_climb_amount']:.2f} m\n"
			f"Net Elevation Change: {stats['net_elevation_change']:.2f} m"
		)
		self._sidebar.set_results(message)

	def _load_site(self, path: str):
		self._view_container.load(path, "elevation")
		self.statusBar().showMessage(f"Site loaded: {path}")

	def _load_site_with_datetime(self, path: str, datetime_str: str):
		self._view_container.load(path, "elevation", datetime_str)
		self.statusBar().showMessage(f"Site loaded: {path} at {datetime_str}")

	def _open_file_dialog(self):
		path, _ = QFileDialog.getOpenFileName(
			self,
			"Open Raster",
			"",
			"GeoTIFF Files (*.tif *.tiff);;All Files (*)"
		)
		if path:
			self._load_site(path)

	def _on_refresh(self):
		pass

	def get_view_container(self):
		return self._view_container


