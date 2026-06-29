from datetime import datetime, timezone
from pathlib import Path

import rasterio
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
from rasterio.crs import CRS

from cynthium.app.config import LUNAR_CRS_PROJ
from cynthium.app.io.export.path_csv import write_path_csv
from cynthium.app.io.export.settings_json import write_settings_json
from cynthium.app.io.export.simulation_csv import write_simulation_csv
from cynthium.app.services.simulation_service import calculate_simulation_stats
from cynthium.app.services.site_rasters import load_daily_avg_meteor_raster
from cynthium.app.ui.panels.sidebar.container import AppSidebar
from cynthium.app.utils.logger import get_logger

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
		self.setWindowTitle("Cynthium")
		self.setGeometry(100, 100, 1600, 900)

		self._current_path = None
		self._current_datetime = datetime.now(timezone.utc).strftime(
			"%Y-%m-%dT%H:%M:%S"
		)
		self._current_map_type = "Elevation"
		self._last_simulation_stats = None
		self._last_simulation_points = None
		self._last_autopath_stats = None
		self._last_autopath_points = None

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
		self._menubar.action_import_tif.triggered.connect(self._import_custom_tif)
		self._menubar.action_import_settings.triggered.connect(
			self._import_settings
		)
		self._menubar.action_open.triggered.connect(self._open_file_dialog)
		self._menubar.action_export_manual_path.triggered.connect(
			self._export_manual_path
		)
		self._menubar.action_export_autopath.triggered.connect(
			self._export_autopath
		)
		self._menubar.action_export_settings.triggered.connect(
			self._export_settings
		)
		self._menubar.action_export_simulation_data.triggered.connect(
			self._export_simulation_data
		)
		self._menubar.action_exit.triggered.connect(self.close)
		self._sidebar.map_generation_requested.connect(self._load_site_with_datetime)
		self._sidebar.waypoint_added.connect(self._view_container.add_waypoint)
		self._view_container.raster_view.waypoint_added.connect(
			self._sidebar.add_waypoint_direct
		)
		self._sidebar.waypoint_removed.connect(self._view_container.remove_waypoint)
		self._sidebar.waypoints_cleared.connect(self._on_clear_waypoints)
		self._sidebar.autopath_requested.connect(self._on_autopath_requested)
		self._results_panel.simulation_started.connect(self._on_start_simulation)

	def _on_clear_waypoints(self):
		self._view_container.clear_all_waypoints()
		self._view_container.set_autopath([])
		self._sidebar.set_autopath_waypoints(None)
		self._view_container.clear_failure_point()
		self._view_container.clear_sim_failure_point()

	def _on_autopath_requested(self, payload: dict):
		if self._current_path is None:
			QMessageBox.warning(self, "Autopath", "Load a site map first.")
			self._sidebar.set_autopath_waypoints(None)
			return

		waypoints_xy = payload.get("waypoints_xy")
		if not (isinstance(waypoints_xy, (list, tuple)) and len(waypoints_xy) >= 2):
			QMessageBox.warning(self, "Autopath", "Need at least 2 waypoints.")
			self._sidebar.set_autopath_waypoints(None)
			return

		try:
			user_wps: list[tuple[float, float]] = []
			for wp in waypoints_xy:
				if not (isinstance(wp, (list, tuple)) and len(wp) == 2):
					raise ValueError("Invalid waypoint format")
				user_wps.append((float(wp[0]), float(wp[1])))

			# Read rover settings
			try:
				rover = self._sidebar.get_rover_settings()
			except (ValueError, KeyError, TypeError) as exc:
				QMessageBox.warning(
					self, "Autopath",
					f"Rover settings are incomplete or invalid:\n{exc}\n\nFill in all rover fields or select a preset."
				)
				self._sidebar.set_autopath_waypoints(None)
				return
			max_slope_deg = rover.max_climbable_slope_deg

			path_mode = str(payload.get("path_mode", "Waypoint to waypoint"))
			if path_mode == "Start to finish":
				pairs = [(user_wps[0], user_wps[-1])]
			else:
				pairs = [(user_wps[i], user_wps[i + 1]) for i in range(len(user_wps) - 1)]

			map_data_bundle = self._view_container.get_current_map_data()

			# Validate-and-retry loop: pathfind, simulate, block failures, repeat
			MAX_ATTEMPTS = 20
			site_path_xy: list[tuple[float, float]] = []
			all_blocked: set[tuple[int, int]] = set()
			overall_feasible = False
			self._view_container.clear_failure_point()

			for attempt in range(MAX_ATTEMPTS):
				# --- Pathfind all segments ---
				segments: list[list[tuple[float, float]]] = []
				pathfind_failed = False
				for start_xy, goal_xy in pairs:
					seg = self._view_container.compute_autopath(
						start_xy=start_xy,
						goal_xy=goal_xy,
						utctime=str(self._current_datetime),
						map_type=str(self._current_map_type),
						slope_weight=float(payload.get("slope_weight", 1.0)),
						sun_weight=float(payload.get("sun_weight", 0.5)),
						meteor_flux_weight=float(payload.get("meteor_flux_weight", 0.2)),
						temperature_weight=float(payload.get("temperature_weight", 0.2)),
						cost_strategy=str(payload.get("cost_strategy", "Weighted cost")),
						algorithm=str(payload.get("algorithm", "A*")),
						max_slope_deg=float(max_slope_deg),
						blocked_cells=all_blocked if all_blocked else None,
						use_bicubic=bool(payload.get("use_bicubic", False)),
					)
					if not seg or len(seg) < 2:
						pathfind_failed = True
						break
					segments.append(seg)

				if pathfind_failed:
					# Pathfinding itself failed — blocked cells made start/goal disconnected
					if attempt == 0:
						QMessageBox.warning(
							self, "Autopath",
							"No path exists between these waypoints with the current rover.\n"
							f"Max climbable slope: {max_slope_deg:.1f}°."
						)
						self._sidebar.set_autopath_waypoints(None)
						return
					# On retry attempts, pathfind failed because start/goal got blocked.
					# No point retrying further.
					break

				overall: list[tuple[float, float]] = []
				for i, seg in enumerate(segments):
					if i == 0:
						overall.extend(seg)
					else:
						overall.extend(seg[1:])
				site_path_xy = overall

				# --- Validate with simulation ---
				stats: dict[str, float] = {}
				try:
					stats, _ = calculate_simulation_stats(
						site_path_xy,
						map_data_bundle,
						rover=rover,
						use_bicubic=bool(payload.get("use_bicubic", False)),
					)
					feasible = float(stats.get("traverse_feasible", 0.0)) >= 0.5
				except Exception:
					feasible = False

				if feasible:
					overall_feasible = True
					logger.info(f"Autopath: path validated (attempt {attempt + 1})")
					self._view_container.clear_failure_point()
					break

				# --- Block cells on this path and retry ---
				fx = stats.get("failure_x")
				fy = stats.get("failure_y")
				if fx is not None and fy is not None:
					self._view_container.set_failure_point(float(fx), float(fy))
				meta = self._view_container._current_meta
				if meta and "transform" in meta:
					inv = ~meta["transform"]
					for x, y in site_path_xy:
						c, r = inv * (float(x), float(y))
						all_blocked.add((int(r), int(c)))
				logger.info(f"Autopath: attempt {attempt + 1} infeasible, retrying with {len(all_blocked)} cells blocked")

			if not overall_feasible:
				# Show the last attempted path so the failure point is visible
				logger.info(f"Rendering failed path: {len(site_path_xy)} nodes")
				self._view_container.set_autopath(site_path_xy)
				QMessageBox.warning(
					self, "Autopath",
					"No traversable path found after multiple attempts.\n"
					f"Max climbable slope: {max_slope_deg:.1f}° (μ={rover.wheel_friction_coeff:.2f}).\n"
					"The rover cannot handle this terrain with the current settings.\n"
					"Try a different route or adjust the rover's friction coefficient."
				)
				self._sidebar.set_autopath_waypoints(site_path_xy)
				return

		except Exception as exc:
			logger.error(f"Autopath failed: {exc}")
			QMessageBox.critical(self, "Autopath", f"Autopath failed:\n{exc}")
			self._sidebar.set_autopath_waypoints(None)
			return

		if not site_path_xy or len(site_path_xy) < 2:
			QMessageBox.warning(self, "Autopath", "No path found.")
			self._view_container.set_autopath([])
			self._sidebar.set_autopath_waypoints(None)
			return

		self._view_container.set_autopath(site_path_xy)
		self._sidebar.set_autopath_waypoints(site_path_xy)
		self.statusBar().showMessage(f"Autopath complete: {len(site_path_xy)} nodes (validated via simulation)")

	def _on_start_simulation(self):
		"""
		Handles start simulation.

		:return: None
		"""
		self.statusBar().showMessage("Running simulation...")
		# Process events to ensure status bar updates
		QApplication.processEvents()

		manual_points = self._view_container.get_waypoint_3d_points()
		auto_points = self._view_container.get_autopath_3d_points()

		if len(manual_points) < 2:
			self._results_panel.set_error("Please add at least two waypoints.")
			self.statusBar().showMessage("Ready")
			return

		try:
			rover = self._sidebar.get_rover_settings()
		except ValueError as exc:
			self._results_panel.set_error(str(exc))
			self.statusBar().showMessage("Ready")
			return

		map_data_bundle = list(self._view_container.get_current_map_data())
		# Use daily-angle meteor raster for simulation if available.
		vc = self._view_container
		current_data = vc._current_data
		current_meta = vc._current_meta
		current_path = vc._current_path
		if current_data is not None and current_meta is not None and current_path is not None:
			daily_meteor = load_daily_avg_meteor_raster(
				reference_path=str(current_path),
				reference_meta=current_meta,
				reference_shape=(
					int(current_data.shape[0]),
					int(current_data.shape[1]),
				),
				utctime=str(self._current_datetime),
			)
			if daily_meteor[0] is not None:
				map_data_bundle[7] = daily_meteor[0]
				map_data_bundle[8] = daily_meteor[1]

		manual_stats, manual_points_array = calculate_simulation_stats(
			manual_points,
			tuple(map_data_bundle),
			rover=rover,
			use_bicubic=self._sidebar.get_bicubic_enabled(),
		)
		self._last_simulation_stats = manual_stats
		self._last_simulation_points = manual_points_array

		if len(auto_points) >= 2:
			auto_stats, auto_points_array = calculate_simulation_stats(
				auto_points,
				tuple(map_data_bundle),
				rover=rover,
				use_bicubic=self._sidebar.get_bicubic_enabled(),
			)
			self._last_autopath_stats = auto_stats
			self._last_autopath_points = auto_points_array
		else:
			auto_stats = None
			self._last_autopath_stats = None
			self._last_autopath_points = None

		self._results_panel.set_stats(manual_stats, auto_stats)

		# Mark failure point on the manual path if traversal failed
		manual_feasible = float(manual_stats.get("traverse_feasible", 1.0)) >= 0.5
		if not manual_feasible:
			fx = manual_stats.get("failure_x")
			fy = manual_stats.get("failure_y")
			if fx is not None and fy is not None:
				self._view_container.set_sim_failure_point(float(fx), float(fy))
		else:
			self._view_container.clear_sim_failure_point()

		def _feasible_warning(stats: dict[str, float] | None, label: str) -> str | None:
			if stats is None:
				return None
			if float(stats.get("traverse_feasible", 1.0)) < 0.5:
				req_mu = float(stats.get("required_wheel_friction_coeff", 0.0))
				# req_angle = float(stats.get("required_climb_slope_deg", 0.0))
				return (
					f"{label} traversal failed.\n"
					f"Required \u03bc: {req_mu:.3f}"
				)
			return None

		manual_warning = _feasible_warning(manual_stats, "Manual path")
		auto_warning = _feasible_warning(auto_stats, "Auto path")

		warnings = [w for w in [manual_warning, auto_warning] if w is not None]
		if warnings:
			QMessageBox.warning(
				self,
				"Traverse not feasible",
				"Some paths failed under the dynamic rover model.\n\n"
				+ "\n".join(warnings),
			)

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

		default_stem = "simulation_data"
		if self._current_path:
			default_stem = f"{self._current_path.split('/')[-1]}_simulation_data"

		path, _ = QFileDialog.getSaveFileName(
			self,
			"Export Simulation Data",
			f"{default_stem}.csv",
			"CSV files (*.csv);;All files (*)",
		)
		if not path:
			return

		base = path
		if base.lower().endswith(".csv"):
			base = base[:-4]

		metadata = {
			"site_path": self._current_path or "",
			"datetime": self._current_datetime,
			"map_type": self._current_map_type,
		}

		try:
			write_simulation_csv(
				f"{base}_manual.csv",
				{**metadata, "path_type": "manual"},
				self._last_simulation_stats,
				self._last_simulation_points,
			)
		except OSError as exc:
			logger.error(f"Failed to export manual path data: {exc}")
			QMessageBox.critical(
				self,
				"Export Failed",
				f"Failed to export manual path data:\n{exc}",
			)
			return

		if self._last_autopath_stats is not None and self._last_autopath_points is not None:
			try:
				write_simulation_csv(
					f"{base}_auto.csv",
					{**metadata, "path_type": "auto"},
					self._last_autopath_stats,
					self._last_autopath_points,
				)
			except OSError as exc:
				logger.error(f"Failed to export autopath data: {exc}")
				QMessageBox.critical(
					self,
					"Export Failed",
					f"Failed to export autopath data:\n{exc}",
				)
				return

		self.statusBar().showMessage(f"Simulation data exported to {base}_manual.csv and {base}_auto.csv")

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

	def _export_manual_path(self):
		"""Export the user's manual waypoints as a CSV file."""
		points = self._view_container.get_waypoint_3d_points()
		if not points or len(points) < 2:
			QMessageBox.warning(
				self,
				"No Manual Path",
				"Place at least two waypoints before exporting the manual path.",
			)
			return

		default_stem = "manual_path"
		if self._current_path:
			default_stem = f"{Path(self._current_path).stem}_manual_path"

		path, _ = QFileDialog.getSaveFileName(
			self,
			"Export Manual Path",
			f"{default_stem}.csv",
			"CSV files (*.csv);;All files (*)",
		)
		if not path:
			return

		metadata = {
			"site_path": self._current_path or "",
			"datetime": self._current_datetime,
			"map_type": self._current_map_type,
			"path_type": "manual",
		}
		try:
			write_path_csv(path, points, label="manual", metadata=metadata)
		except OSError as exc:
			logger.error(f"Failed to export manual path: {exc}")
			QMessageBox.critical(self, "Export Failed", f"Failed to export manual path:\n{exc}")
			return

		self.statusBar().showMessage(f"Manual path exported to {path}")

	def _export_autopath(self):
		"""Export the computed autopath as a CSV file."""
		points = self._view_container.get_autopath_3d_points()
		if not points or len(points) < 2:
			QMessageBox.warning(
				self,
				"No Auto Path",
				"Compute an autopath before exporting it.",
			)
			return

		default_stem = "auto_path"
		if self._current_path:
			default_stem = f"{Path(self._current_path).stem}_auto_path"

		path, _ = QFileDialog.getSaveFileName(
			self,
			"Export Auto Path",
			f"{default_stem}.csv",
			"CSV files (*.csv);;All files (*)",
		)
		if not path:
			return

		metadata = {
			"site_path": self._current_path or "",
			"datetime": self._current_datetime,
			"map_type": self._current_map_type,
			"path_type": "auto",
		}
		try:
			write_path_csv(path, points, label="auto", metadata=metadata)
		except OSError as exc:
			logger.error(f"Failed to export auto path: {exc}")
			QMessageBox.critical(self, "Export Failed", f"Failed to export auto path:\n{exc}")
			return

		self.statusBar().showMessage(f"Auto path exported to {path}")

	def _export_settings(self):
		"""Export all current settings (rover, autopath, waypoints, etc.) as JSON."""
		settings = self._sidebar.export_settings()

		# Add session-level info
		settings["session"] = {
			"site_path": self._current_path or "",
			"datetime": self._current_datetime,
			"map_type": self._current_map_type,
		}

		# Add autopath result if available
		auto_points = self._view_container.get_autopath_3d_points()
		if auto_points and len(auto_points) >= 2:
			settings["autopath_result"] = [
				[float(p[0]), float(p[1]), float(p[2])] for p in auto_points
			]

		default_stem = "settings"
		if self._current_path:
			default_stem = f"{Path(self._current_path).stem}_settings"

		path, _ = QFileDialog.getSaveFileName(
			self,
			"Export Settings",
			f"{default_stem}.json",
			"JSON files (*.json);;All files (*)",
		)
		if not path:
			return

		try:
			write_settings_json(path, settings)
		except OSError as exc:
			logger.error(f"Failed to export settings: {exc}")
			QMessageBox.critical(self, "Export Failed", f"Failed to export settings:\n{exc}")
			return

	def _import_settings(self):
		"""Import settings from a JSON file and apply them to the UI."""
		path, _ = QFileDialog.getOpenFileName(
			self,
			"Import Settings",
			"",
			"JSON files (*.json);;All files (*)",
		)
		if not path:
			return

		import json
		try:
			with open(path) as f:
				settings = json.load(f)
		except (OSError, json.JSONDecodeError) as exc:
			QMessageBox.critical(
				self, "Import Failed", f"Could not read settings file:\n{exc}"
			)
			return

		if not isinstance(settings, dict):
			QMessageBox.critical(
				self, "Import Failed", "Settings file must contain a JSON object."
			)
			return

		# Apply settings to sidebar panels.
		# import_settings emits waypoints_cleared then waypoint_added per waypoint,
		# which auto-syncs the view container — no extra sync needed.
		self._sidebar.import_settings(settings)

		# If the settings include a session with a site path, load it
		session = settings.get("session", {})
		site_path = session.get("site_path", "")
		if site_path and Path(site_path).exists():
			dt = session.get("datetime", self._current_datetime)
			mt = session.get("map_type", self._current_map_type)
			self._load_site_with_datetime(site_path, dt, mt)

		self.statusBar().showMessage(f"Settings imported from {path}")

	def _import_custom_tif(self):
		"""Import a custom GeoTIFF with CRS validation.

		The imported TIF must be in the lunar south-pole stereographic projection
		(LUNAR_CRS_PROJ), matching the preset site rasters.
		"""
		path, _ = QFileDialog.getOpenFileName(
			self,
			"Import Custom GeoTIFF",
			"",
			"GeoTIFF files (*.tif *.tiff);;All files (*)",
		)
		if not path:
			return

		# Validate projection against the lunar stereographic CRS
		try:
			with rasterio.open(path) as src:
				src_crs = src.crs
		except Exception as exc:
			QMessageBox.critical(
				self,
				"Import Failed",
				f"Could not read the GeoTIFF file:\n{exc}",
			)
			return

		expected_crs = CRS.from_string(LUNAR_CRS_PROJ)

		if src_crs is None:
			QMessageBox.warning(
				self,
				"Missing CRS",
				"The selected GeoTIFF has no embedded CRS.\n\n"
				"Only GeoTIFFs in the lunar south-pole stereographic projection\n"
				"(+proj=stere +lat_0=-90 +lon_0=0 +k=1 +R=1737400 +units=m)\n"
				"are supported. Load via File → Open to bypass CRS checks.",
			)
			return

		try:
			if not src_crs.is_exact_same(expected_crs):
				src_str = src_crs.to_string()
				expected_str = expected_crs.to_string()
				if src_str != expected_str:
					QMessageBox.warning(
						self,
						"Wrong Projection",
						f"The selected GeoTIFF uses an unsupported CRS.\n\n"
						f"Expected:\n{expected_str}\n\n"
						f"Got:\n{src_str}\n\n"
						"Only GeoTIFFs in the lunar south-pole stereographic projection\n"
						"are supported. Load via File → Open to bypass CRS checks.",
					)
					return
		except Exception:
			src_str = str(src_crs).lower()
			if "stere" not in src_str or "lat_0=-90" not in src_str:
				QMessageBox.warning(
					self,
					"Wrong Projection",
					"The selected GeoTIFF does not appear to be in the required\n"
					"lunar south-pole stereographic projection.\n\n"
					"Load via File → Open to bypass CRS checks.",
				)
				return

		# Projection is valid — load the site
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
