from datetime import datetime, timezone
from pathlib import Path

import rasterio
from PySide6.QtCore import QThread, Qt
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
from cynthium.app.services.autopath_service import compute_validated_path
from cynthium.app.services.simulation_service import calculate_simulation_stats
from cynthium.app.services.site_rasters import (
			load_angle_maps,
			load_daily_avg_illumination_raster,
			load_daily_avg_meteor_number_raster,
			load_daily_avg_meteor_raster,
)
from cynthium.app.ui.panels.sidebar.container import AppSidebar
from cynthium.app.utils.logger import get_logger

from .ui.map.map_view import MapView
from .ui.map.terrain_view import TerrainView
from .ui.map.view_container import ViewContainer
from .ui.panels.menubar import AppMenuBar
from .ui.panels.progress_popup import ProgressPopup, Worker, compute_path_segment
from .ui.panels.simulation_results_panel import SimulationResultsPanel

logger = get_logger(__name__)



def _run_autopath(
		user_wps, path_mode, rover, map_data_bundle,
		use_bicubic, max_slope_deg,
		slope_weight, sun_weight, meteor_flux_weight,
		temperature_weight, cost_strategy, algorithm,
		elevation_data, elevation_meta,
		illumination_data, illumination_meta,
		meteor_data, meteor_meta,
		temperature_data, temperature_meta,
		illumination_maps=None,
		meteor_energy_maps=None,
		meteor_number_maps=None,
		start_angle_deg=0,
		center_lat=None,
		center_lon=None,
		start_et=None,
		pause_durations=None,
):
	"""Run autopath computation in a background thread (no file I/O, no Qt)."""
	def _pathfind_segment(start_xy, goal_xy, blocked):
		return compute_path_segment(
			start_xy=start_xy,
			goal_xy=goal_xy,
			elevation_data=elevation_data,
			elevation_meta=elevation_meta,
			illumination_data=illumination_data,
			illumination_meta=illumination_meta,
			meteor_data=meteor_data,
			meteor_meta=meteor_meta,
			temperature_data=temperature_data,
			temperature_meta=temperature_meta,
			max_slope_deg=float(max_slope_deg),
			slope_weight=slope_weight,
			sun_weight=sun_weight,
			meteor_flux_weight=meteor_flux_weight,
			temperature_weight=temperature_weight,
			cost_strategy=cost_strategy,
			algorithm=algorithm,
			blocked_cells=blocked,
			use_bicubic=use_bicubic,
		)

	return compute_validated_path(
		waypoints_xy=user_wps,
		path_mode=path_mode,
		rover=rover,
		map_data_bundle=map_data_bundle,
		pathfind_fn=_pathfind_segment,
		use_bicubic=use_bicubic,
		illumination_maps=illumination_maps,
		meteor_energy_maps=meteor_energy_maps,
		meteor_number_maps=meteor_number_maps,
		start_angle_deg=start_angle_deg,
		center_lat=center_lat,
		center_lon=center_lon,
		start_et=start_et,
		pause_durations=pause_durations,
	)


def _run_simulation(manual_points, auto_points, mdb, rover,
					use_bicubic, pause_durs,
					illumination_maps=None,
					meteor_energy_maps=None,
					meteor_number_maps=None,
					start_angle_deg=0,
					center_lat=None,
					center_lon=None,
					start_et=None):
	"""Run simulation in background thread with pre-loaded meteor rasters."""
	manual_stats, manual_points_array = calculate_simulation_stats(
		manual_points,
		mdb,
		rover=rover,
		use_bicubic=use_bicubic,
		pause_durations=pause_durs,
		illumination_maps=illumination_maps,
		meteor_energy_maps=meteor_energy_maps,
		meteor_number_maps=meteor_number_maps,
		start_angle_deg=start_angle_deg,
		center_lat=center_lat,
		center_lon=center_lon,
		start_et=start_et,
	)

	auto_stats = None
	auto_points_array = None
	if len(auto_points) >= 2:
		auto_stats, auto_points_array = calculate_simulation_stats(
			auto_points,
			mdb,
			rover=rover,
			use_bicubic=use_bicubic,
			pause_durations=pause_durs,
			illumination_maps=illumination_maps,
			meteor_energy_maps=meteor_energy_maps,
			meteor_number_maps=meteor_number_maps,
			start_angle_deg=start_angle_deg,
			center_lat=center_lat,
			center_lon=center_lon,
			start_et=start_et,
		)

	return {
		"manual_stats": manual_stats,
		"manual_points_array": manual_points_array,
		"auto_stats": auto_stats,
		"auto_points_array": auto_points_array,
	}


class Window(QMainWindow):
	_menubar: AppMenuBar
	_terrain_view: TerrainView
	_raster_view: MapView

	def __init__(self):
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
		self._rover_settings_override = None

		self._menubar = AppMenuBar(self)
		self.setMenuBar(self._menubar)

		content = QWidget()
		self.setCentralWidget(content)

		root = QVBoxLayout(content)
		root.setContentsMargins(0, 0, 0, 0)

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
		logger.info("Button clicked")



	    def _connect_signals(self):
		        """Connect menu bar actions and UI signals."""
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
		self._menubar.action_rover_settings.triggered.connect(
			self._on_open_rover_settings
		)
		self._sidebar.map_generation_requested.connect(self._load_site_with_datetime)
		self._sidebar.waypoint_added.connect(self._view_container.add_waypoint)
		self._view_container.raster_view.waypoint_added.connect(
			self._sidebar.add_waypoint_direct
		)
		self._sidebar.waypoint_removed.connect(self._view_container.remove_waypoint)
		self._sidebar.waypoint_edited.connect(self._view_container.edit_waypoint)
		self._sidebar.waypoints_cleared.connect(self._on_clear_waypoints)
		self._sidebar.autopath_requested.connect(self._on_autopath_requested)
		self._sidebar.rover_settings_requested.connect(
			self._on_open_rover_settings
		)
		self._results_panel.simulation_started.connect(self._on_start_simulation)

	def _on_clear_waypoints(self):
		self._view_container.clear_all_waypoints()
		self._view_container.set_autopath([])
		self._sidebar.set_autopath_waypoints(None)
		self._view_container.clear_failure_point()
		self._view_container.clear_sim_failure_point()

	def _get_rover_settings(self):
		"""Return RoverSettings, merging sidebar panel values with dialog override."""
		base = self._sidebar.get_rover_settings()
		override = self._rover_settings_override
		if override is not None:
			from cynthium.app.engine.simulation.rover_settings import RoverSettings
			base = RoverSettings(
				mass_kg=base.mass_kg,
				power_hp=base.power_hp,
				wheel_friction_coeff=base.wheel_friction_coeff,
				rolling_resistance_coeff=base.rolling_resistance_coeff,
				wheel_radius_m=override.wheel_radius_m,
				motor_peak_torque_nm=override.motor_peak_torque_nm,
				track_width_m=override.track_width_m,
				wheelbase_m=override.wheelbase_m,
			)
		return base

	def _on_open_rover_settings(self):
		from cynthium.app.ui.panels.rover_settings_dialog import RoverSettingsDialog

		try:
			current = self._sidebar.get_rover_settings()
		except Exception:
			current = None
		if current is not None and self._rover_settings_override is not None:
			current = self._rover_settings_override

		dlg = RoverSettingsDialog(current=current, parent=self)
		if dlg.exec():
			updated = dlg.get_settings()
			if updated is not None:
				self._rover_settings_override = updated
				self._sidebar._rover_settings_panel.set_values(
					str(updated.mass_kg),
					str(updated.power_hp),
					str(updated.wheel_friction_coeff),
					str(updated.rolling_resistance_coeff),
				)

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

		user_wps: list[tuple[float, float]] = []
		for wp in waypoints_xy:
			if not (isinstance(wp, (list, tuple)) and len(wp) == 2):
				QMessageBox.warning(self, "Autopath", "Invalid waypoint format.")
				self._sidebar.set_autopath_waypoints(None)
				return
			user_wps.append((float(wp[0]), float(wp[1])))

		try:
			rover = self._get_rover_settings()
		except (ValueError, KeyError, TypeError) as exc:
			QMessageBox.warning(
				self, "Autopath",
				f"Rover settings are incomplete or invalid:\n{exc}\n\nFill in all rover fields or select a preset."
			)
			self._sidebar.set_autopath_waypoints(None)
			return

		vc = self._view_container
		map_data_bundle = vc.get_current_map_data()
		path_mode = str(payload.get("path_mode", "Waypoint to waypoint"))
		use_bicubic = bool(payload.get("use_bicubic", False))
		max_slope_deg = rover.max_climbable_slope_deg
		slope_weight = float(payload.get("slope_weight", 1.0))
		sun_weight = float(payload.get("sun_weight", 0.5))
		meteor_flux_weight = float(payload.get("meteor_flux_weight", 0.2))
		temperature_weight = float(payload.get("temperature_weight", 0.2))
		cost_strategy = str(payload.get("cost_strategy", "Weighted cost"))
		algorithm = str(payload.get("algorithm", "A*"))

		elevation_data = map_data_bundle[0]
		elevation_meta = map_data_bundle[1]
		# Use UI datetime - not stale cached value
		current_datetime = self._sidebar.get_datetime() or str(self._current_datetime)
		illum_data, illum_meta = map_data_bundle[5], map_data_bundle[6]
		meteor_data, meteor_meta = map_data_bundle[7], map_data_bundle[8]
		temp_data, temp_meta = map_data_bundle[3], map_data_bundle[4]

		if vc._current_path and elevation_meta is not None:
			H, W = int(elevation_data.shape[0]), int(elevation_data.shape[1])
			daily_illum = load_daily_avg_illumination_raster(
				reference_path=vc._current_path,
				reference_meta=elevation_meta,
				reference_shape=(H, W),
				utctime=current_datetime,
			)
			if daily_illum[0] is not None:
				illum_data, illum_meta = daily_illum

			daily_meteor = load_daily_avg_meteor_raster(
				reference_path=vc._current_path,
				reference_meta=elevation_meta,
				reference_shape=(H, W),
				utctime=current_datetime,
			)
			if daily_meteor[0] is not None:
				meteor_data, meteor_meta = daily_meteor

		illumination_maps = None
		meteor_energy_maps = None
		meteor_number_maps = None
		start_angle_deg = 0
		if vc._current_path and elevation_meta is not None:
			H, W = int(elevation_data.shape[0]), int(elevation_data.shape[1])
			result = load_angle_maps(
				reference_path=vc._current_path,
				reference_meta=elevation_meta,
				reference_shape=(H, W),
				utctime=current_datetime,
			)
			illumination_maps = result[0]
			meteor_energy_maps = result[1]
			meteor_number_maps = result[2]
			start_angle_deg = result[3]
			center_lat = result[4]
			center_lon = result[5]
			start_et = result[6]

		pause_durs = self._sidebar.get_pause_durations() if hasattr(self, "_sidebar") else []

		self._path_popup = ProgressPopup("Autopath", "Computing autopath...", self)
		self._path_worker = Worker(
			_run_autopath,
			user_wps, path_mode, rover, map_data_bundle,
			use_bicubic, max_slope_deg,
			slope_weight, sun_weight, meteor_flux_weight,
			temperature_weight, cost_strategy, algorithm,
			elevation_data, elevation_meta,
			illum_data, illum_meta,
			meteor_data, meteor_meta,
			temp_data, temp_meta,
			illumination_maps, meteor_energy_maps,
			meteor_number_maps, start_angle_deg,
			center_lat, center_lon, start_et,
			pause_durs,
		)
		self._path_thread = QThread()
		self._path_worker.moveToThread(self._path_thread)
		self._path_thread.started.connect(self._path_worker.run)
		self._path_worker.finished.connect(self._on_autopath_done)
		self._path_worker.failed.connect(self._on_autopath_error)
		self._path_thread.start()
		self._path_popup.show()

	def _on_autopath_done(self, result: dict):
		"""Handle autopath completion on the main thread."""
		self._path_popup.close()
		self._path_thread.quit()
		self._path_thread.deleteLater()
		self._path_popup = None
		self._path_thread = None
		self._path_worker = None

		self._view_container.clear_failure_point()

		if result["failure_xy"]:
			fx, fy = result["failure_xy"]
			self._view_container.set_failure_point(fx, fy)

		site_path_xy = result["path_xy"]

		if not result["feasible"]:
			if site_path_xy and len(site_path_xy) >= 2:
				self._view_container.set_autopath(site_path_xy)
				self._sidebar.set_autopath_waypoints(site_path_xy)
			self._sidebar.set_autopath_waypoints(None)
			max_slope = float(result.get("stats", {}).get("max_climbable_slope_deg", 0.0))
			mu = float(result.get("stats", {}).get("rover_mu", 0.0))
			QMessageBox.warning(
				self, "Autopath",
				"No traversable path found after multiple attempts.\n"
				f"Max climbable slope: {max_slope:.1f}° (μ={mu:.2f}).\n"
				"The rover cannot handle this terrain with the current settings.\n"
				"Try a different route or adjust the rover's friction coefficient."
			)
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
		manual_points = self._view_container.get_waypoint_3d_points()
		auto_points = self._view_container.get_autopath_3d_points()

		if len(manual_points) < 2:
			self._results_panel.set_error("Please add at least two waypoints.")
			self.statusBar().showMessage("Ready")
			return

		try:
			rover = self._get_rover_settings()
		except ValueError as exc:
			self._results_panel.set_error(str(exc))
			self.statusBar().showMessage("Ready")
			return

		vc = self._view_container
		mdb = list(vc.get_current_map_data())
		current_path = vc._current_path
		current_meta = vc._current_meta
		if current_path is not None and current_meta is not None:
			current_data = vc._current_data
			data_shape = (
				int(current_data.shape[0]),
				int(current_data.shape[1]),
			) if current_data is not None else None
			# Use UI datetime - not stale cached value
			current_datetime = self._sidebar.get_datetime() or str(self._current_datetime)
			daily_meteor = load_daily_avg_meteor_raster(
				reference_path=current_path, reference_meta=current_meta,
				reference_shape=data_shape, utctime=current_datetime,
			)
			if daily_meteor[0] is not None:
				mdb[7] = daily_meteor[0]
				mdb[8] = daily_meteor[1]
			daily_meteor_number = load_daily_avg_meteor_number_raster(
				reference_path=current_path, reference_meta=current_meta,
				reference_shape=data_shape, utctime=current_datetime,
			)
			if daily_meteor_number[0] is not None:
				mdb[9] = daily_meteor_number[0]
				mdb[10] = daily_meteor_number[1]

		# Pre-load angle maps for multi-day traversal support
		illumination_maps = None
		meteor_energy_maps = None
		meteor_number_maps = None
		start_angle_deg = 0
		if current_path is not None and current_meta is not None and current_data is not None:
			data_shape = (int(current_data.shape[0]), int(current_data.shape[1]))
			result = load_angle_maps(
				reference_path=current_path,
				reference_meta=current_meta,
				reference_shape=data_shape,
				utctime=current_datetime,
			)
			illumination_maps = result[0]
			meteor_energy_maps = result[1]
			meteor_number_maps = result[2]
			start_angle_deg = result[3]
			center_lat = result[4]
			center_lon = result[5]
			start_et = result[6]

		use_bicubic = self._sidebar.get_bicubic_enabled()
		pause_durs = self._sidebar.get_pause_durations()

		self._sim_popup = ProgressPopup("Simulation", "Running simulation...", self)
		self._sim_worker = Worker(
			_run_simulation,
			manual_points, auto_points, tuple(mdb), rover,
			use_bicubic, pause_durs,
			illumination_maps, meteor_energy_maps,
			meteor_number_maps, start_angle_deg,
			center_lat, center_lon, start_et,
		)
		self._sim_thread = QThread()
		self._sim_worker.moveToThread(self._sim_thread)
		self._sim_thread.started.connect(self._sim_worker.run)
		self._sim_worker.finished.connect(self._on_simulation_done)
		self._sim_worker.failed.connect(self._on_simulation_error)
		self._sim_thread.start()
		self._sim_popup.show()

	def _on_simulation_done(self, result: dict):
		"""Handle simulation completion on the main thread."""
		self._sim_popup.close()
		self._sim_thread.quit()
		self._sim_thread.deleteLater()
		self._sim_popup = None
		self._sim_thread = None
		self._sim_worker = None

		manual_stats = result["manual_stats"]
		manual_points_array = result["manual_points_array"]
		auto_stats = result["auto_stats"]
		auto_points_array = result["auto_points_array"]

		self._last_simulation_stats = manual_stats
		self._last_simulation_points = manual_points_array
		self._last_autopath_stats = auto_stats
		self._last_autopath_points = auto_points_array

		self._results_panel.set_stats(manual_stats, auto_stats)

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
				reason = stats.get("failure_reason", "Unknown error")
				return f"{label} traversal failed.\n{reason}"
			return None

		manual_warning = _feasible_warning(manual_stats, "Manual path")
		auto_warning = _feasible_warning(auto_stats, "Auto path")

		warnings = [w for w in [manual_warning, auto_warning] if w is not None]
		if warnings:
			QMessageBox.warning(
				self,
				"Traverse not feasible",
				"\n\n".join(warnings),
			)

		feasible = float(manual_stats.get("traverse_feasible", 1.0)) >= 0.5
		t_sec = float(manual_stats.get("traversal_time_s", 0.0))
		if t_sec >= 3600:
			time_str = f"{t_sec/3600:.1f}h"
		elif t_sec >= 60:
			time_str = f"{t_sec/60:.1f}m"
		else:
			time_str = f"{t_sec:.0f}s"
		dist = float(manual_stats.get("total_distance_travelled", 0.0))
		batt = float(manual_stats.get("battery_remaining_pct", 100.0))
		msg = f"Simulation completed: {time_str}, {dist:.0f}m, battery {batt:.0f}%"
		if not feasible:
			msg += " (failed)"
		self.statusBar().showMessage(msg)
		QMessageBox.information(self, "Simulation Complete", msg)

	def _on_autopath_error(self, error_msg: str):
		"""Handle autopath background worker failure."""
		self._path_popup.close()
		self._path_thread.quit()
		self._path_thread.deleteLater()
		self._path_popup = None
		self._path_thread = None
		self._path_worker = None
		logger.error(f"Autopath failed: {error_msg}")
		QMessageBox.critical(self, "Autopath", f"Autopath failed.\n\n{error_msg}")

	def _on_simulation_error(self, error_msg: str):
		"""Handle simulation background worker failure."""
		self._sim_popup.close()
		self._sim_thread.quit()
		self._sim_thread.deleteLater()
		self._sim_popup = None
		self._sim_thread = None
		self._sim_worker = None
		logger.error(f"Simulation failed: {error_msg}")
		QMessageBox.critical(self, "Simulation", f"Simulation failed.\n\n{error_msg}")

	def _export_simulation_data(self):
		"""Export the last simulation results to CSV files."""
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

		pause_durations = self._sidebar.get_pause_durations() if hasattr(self, "_sidebar") else []
		try:
			write_simulation_csv(
				f"{base}_manual.csv",
				{**metadata, "path_type": "manual"},
				self._last_simulation_stats,
				self._last_simulation_points,
				pause_durations=pause_durations,
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
			pause_durations = self._sidebar.get_pause_durations() if hasattr(self, "_sidebar") else []
			try:
				write_simulation_csv(
					f"{base}_auto.csv",
					{**metadata, "path_type": "auto"},
					self._last_autopath_stats,
					self._last_autopath_points,
					pause_durations=pause_durations,
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
		"""Open a file dialog to load a GeoTIFF."""
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
		pause_durations = self._sidebar.get_pause_durations() if hasattr(self, "_sidebar") else []
		try:
			write_path_csv(path, points, label="manual", metadata=metadata, pause_durations=pause_durations)
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
		pause_durations = self._sidebar.get_pause_durations() if hasattr(self, "_sidebar") else []
		try:
			write_path_csv(path, points, label="auto", metadata=metadata, pause_durations=pause_durations)
		except OSError as exc:
			logger.error(f"Failed to export autopath: {exc}")
			QMessageBox.critical(self, "Export Failed", f"Failed to export autopath:\n{exc}")
			return

		self.statusBar().showMessage(f"Auto path exported to {path}")

	def _export_settings(self):
		"""Export all current settings (rover, autopath, waypoints, etc.) as JSON."""
		settings = self._sidebar.export_settings()

		settings["session"] = {
			"site_path": self._current_path or "",
			"datetime": self._current_datetime,
			"map_type": self._current_map_type,
		}

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

		# import_settings auto-syncs view container via waypoint signals
		self._sidebar.import_settings(settings)

		session = settings.get("session", {})
		site_path = session.get("site_path", "")
		if site_path and Path(site_path).exists():
			dt = session.get("datetime", self._current_datetime)
			mt = session.get("map_type", self._current_map_type)
			self._load_site_with_datetime(site_path, dt, mt)

		self.statusBar().showMessage(f"Settings imported from {path}")

	def _import_custom_tif(self):
		"""Import a custom GeoTIFF, validating it matches the lunar stereographic CRS."""
		path, _ = QFileDialog.getOpenFileName(
			self,
			"Import Custom GeoTIFF",
			"",
			"GeoTIFF files (*.tif *.tiff);;All files (*)",
		)
		if not path:
			return

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

			self._load_site_with_datetime(
			path, self._current_datetime, self._current_map_type
		)


	def _load_site(self, path: str):
		"""Load a site raster by path."""
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
		"""Load a site with a specific datetime and map type."""
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
		"""Handle refresh (placeholder)."""
		pass

	def get_view_container(self):
		"""Return the view container widget."""
		return self._view_container
