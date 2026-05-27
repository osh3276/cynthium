from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
	QApplication,
	QFileDialog,
	QMainWindow,
	QMessageBox,
	QSplitter,
	QVBoxLayout,
	QWidget,
)

from craterview.app.io.export.simulation_csv import write_simulation_csv
from craterview.app.services.simulation_service import calculate_simulation_stats
from craterview.app.ui.panels.sidebar.container import AppSidebar
from craterview.app.utils.logger import get_logger

from .ui.map.map_view import MapView
from .ui.map.terrain_view import TerrainView
from .ui.map.view_container import ViewContainer
from .ui.panels.menubar import AppMenuBar
from .ui.panels.simulation_results_panel import SimulationResultsPanel

logger = get_logger(__name__)


class Window(QMainWindow):
	_menubar: AppMenuBar
	_terrain_view: TerrainView
	_raster_view: MapView

	def __init__(self):
		"""
		Initializes the Window instance.

		:return: None
		"""
		super().__init__()
		self.setWindowTitle("CraterView")
		self.setGeometry(100, 100, 1600, 900)

		self._current_path = None
		self._current_datetime = datetime.now(timezone.utc).strftime(
			"%Y-%m-%dT%H:%M:%S"
		)
		self._current_map_type = "Elevation"
		self._last_simulation_stats = None
		self._last_simulation_points = None

		# self.addToolBar(create_toolbar(self))

		self._menubar = AppMenuBar(self)
		self.setMenuBar(self._menubar)

		# Create central widget and layout
		content = QWidget()
		self.setCentralWidget(content)

		root = QVBoxLayout(content)
		root.setContentsMargins(0, 0, 0, 0)

		# Add widgets
		self._view_container = ViewContainer(self)
		self._results_panel = SimulationResultsPanel(self)
		self._sidebar = AppSidebar()

		left_splitter = QSplitter(Qt.Orientation.Vertical)
		left_splitter.addWidget(self._view_container)
		left_splitter.addWidget(self._results_panel)
		left_splitter.setSizes([700, 200])

		main_splitter = QSplitter(Qt.Orientation.Horizontal)
		main_splitter.addWidget(left_splitter)
		main_splitter.addWidget(self._sidebar)
		main_splitter.setStretchFactor(0, 1)
		main_splitter.setStretchFactor(1, 0)
		main_splitter.setSizes([1200, 400])

		root.addWidget(main_splitter)

		self.statusBar().showMessage("Ready")
		self._connect_signals()

		logger.info("Window initialized")

	def on_button_clicked(self):
		"""
		Handles button clicked.

		:return: None
		"""
		logger.info("Button clicked")



	def _connect_signals(self):
		"""
		Performs connect signals.

		:return: The resulting value.
		"""
		self._menubar.action_open.triggered.connect(self._open_file_dialog)
		self._menubar.action_export_simulation_data.triggered.connect(
			self._export_simulation_data
		)
		self._menubar.action_exit.triggered.connect(self.close)
		self._sidebar.map_generation_requested.connect(self._load_site_with_datetime)
		self._sidebar.waypoint_added.connect(self._view_container.add_waypoint)
		self._sidebar.waypoint_removed.connect(self._view_container.remove_waypoint)
		self._sidebar.autopath_requested.connect(self._on_autopath_requested)
		self._sidebar.simulation_started.connect(self._on_start_simulation)

	def _on_autopath_requested(self, payload: dict):
		if self._current_path is None:
			QMessageBox.warning(self, "Autopath", "Load a site map first.")
			self._sidebar.set_autopath_waypoints(None)
			return

		start_xy = payload.get("start_xy")
		goal_xy = payload.get("goal_xy")
		if not (
			isinstance(start_xy, (list, tuple))
			and isinstance(goal_xy, (list, tuple))
			and len(start_xy) == 2
			and len(goal_xy) == 2
		):
			QMessageBox.warning(self, "Autopath", "Invalid start/goal waypoints.")
			self._sidebar.set_autopath_waypoints(None)
			return

		try:
			points_xy = self._view_container.compute_autopath_theta_star(
				start_xy=(float(start_xy[0]), float(start_xy[1])),
				goal_xy=(float(goal_xy[0]), float(goal_xy[1])),
				utctime=str(self._current_datetime),
				map_type=str(self._current_map_type),
				min_slope_deg=float(payload.get("min_slope_deg", 0.0)),
				max_slope_deg=float(payload.get("max_slope_deg", 20.0)),
				slope_weight=float(payload.get("slope_weight", 1.0)),
				sun_weight=float(payload.get("sun_weight", 0.5)),
			)
		except Exception as exc:
			logger.error(f"Autopath failed: {exc}")
			QMessageBox.critical(self, "Autopath", f"Autopath failed:\n{exc}")
			self._sidebar.set_autopath_waypoints(None)
			return

		if not points_xy or len(points_xy) < 2:
			QMessageBox.warning(self, "Autopath", "No path found.")
			self._view_container.set_autopath([])
			self._sidebar.set_autopath_waypoints(None)
			return

		self._view_container.set_autopath(points_xy)
		self._sidebar.set_autopath_waypoints(points_xy)
		self.statusBar().showMessage(f"Autopath complete: {len(points_xy)} nodes")

	def _on_start_simulation(self):
		"""
		Handles start simulation.

		:return: None
		"""
		self.statusBar().showMessage("Running simulation...")
		# Process events to ensure status bar updates
		QApplication.processEvents()

		points = self._view_container.get_waypoint_3d_points()
		if len(points) < 2:
			self._results_panel.set_error("Please add at least two waypoints.")
			self.statusBar().showMessage("Ready")
			return

		try:
			rover = self._sidebar.get_rover_settings()
		except ValueError as exc:
			self._results_panel.set_error(str(exc))
			self.statusBar().showMessage("Ready")
			return

		stats, points_array = calculate_simulation_stats(
			points,
			self._view_container.get_current_map_data(),
			rover=rover,
		)
		self._last_simulation_stats = stats
		self._last_simulation_points = points_array
		self._results_panel.set_stats(stats, rover=rover)

		if float(stats.get("traverse_feasible", 1.0)) < 0.5:
			req_mu = float(stats.get("required_wheel_friction_coeff", 0.0))
			QMessageBox.warning(
				self,
				"Traverse not feasible",
				f"Traversal failed under the dynamic rover model.\n\n"
				f"Current settings:\n"
				f"- μ: {rover.wheel_friction_coeff:.3f}\n"
				f"- power: {rover.power_hp:.3f} hp\n"
				f"- mass: {rover.mass_kg:.2f} kg\n\n"
				f"Minimum μ needed (with current power/mass): {req_mu:.3f}\n\n"
				"Try increasing friction, increasing horsepower, or decreasing weight.",
			)
			self.statusBar().showMessage("Simulation warning: traverse not feasible")
			return

		self.statusBar().showMessage("Simulation complete")

	def _export_simulation_data(self):
		"""
		Performs export simulation data.

		:return: The resulting value.
		"""
		if self._last_simulation_stats is None or self._last_simulation_points is None:
			QMessageBox.warning(
				self,
				"No Simulation Data",
				"Run a simulation before exporting simulation data.",
			)
			return

		default_name = "simulation_data.csv"
		if self._current_path:
			default_name = f"{self._current_path.split('/')[-1]}_simulation_data.csv"

		path, _ = QFileDialog.getSaveFileName(
			self,
			"Export Simulation Data",
			default_name,
			"CSV files (*.csv);;All files (*)",
		)
		if not path:
			return

		if not path.lower().endswith(".csv"):
			path = f"{path}.csv"

		metadata = {
			"site_path": self._current_path or "",
			"datetime": self._current_datetime,
			"map_type": self._current_map_type,
		}

		try:
			write_simulation_csv(
				path,
				metadata,
				self._last_simulation_stats,
				self._last_simulation_points,
			)
		except OSError as exc:
			logger.error(f"Failed to export simulation data: {exc}")
			QMessageBox.critical(
				self,
				"Export Failed",
				f"Failed to export simulation data:\n{exc}",
			)
			return

		self.statusBar().showMessage(f"Simulation data exported: {path}")

	def _open_file_dialog(self):
		"""
		Performs open file dialog.

		:return: The resulting value.
		"""
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
		"""
		Performs load site.

		:param path: Path to the file.
		:type path: str
		:return: The resulting value.
		"""
		self._load_site_with_datetime(
			path, self._current_datetime, self._current_map_type
		)

	def _normalize_path(self, path: str) -> str:
		"""Normalize paths so string comparisons are stable."""
		try:
			return str(Path(path).expanduser().resolve())
		except Exception:
			return str(Path(path).expanduser())

	def _normalize_datetime_str(self, datetime_str: str) -> str:
		"""Normalize datetime strings to YYYY-mm-ddTHH:MM:SS (no tz)."""
		try:
			dt = datetime.fromisoformat(datetime_str)
		except ValueError:
			return datetime_str
		if dt.tzinfo is not None:
			dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
		dt = dt.replace(microsecond=0)
		return dt.strftime("%Y-%m-%dT%H:%M:%S")

	def _load_site_with_datetime(
		self, path: str, datetime_str: str, map_type: str = "Elevation"
	):
		"""
		Performs load site with datetime.

		:param path: Path to the file.
		:type path: str
		:param datetime_str: Parameter value.
		:type datetime_str: str
		:param map_type: Map type identifier.
		:type map_type: str
		:return: The resulting value.
		"""
		path = self._normalize_path(path)
		datetime_str = self._normalize_datetime_str(datetime_str)

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
		self._sidebar.set_autopath_waypoints(None)
		self._view_container.load(path, map_type, datetime_str)
		self._current_path = path
		self._current_datetime = datetime_str
		self._current_map_type = map_type
		self.statusBar().showMessage(f"Loaded {map_type} map: {path} at {datetime_str}")

	def _on_refresh(self):
		"""
		Handles refresh.

		:return: None
		"""
		pass

	def get_view_container(self):
		"""
		Returns the view container.

		:return: The resulting value.
		"""
		return self._view_container
