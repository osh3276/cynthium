import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QSplitter, QWidget
from scipy.ndimage import zoom

from cynthium.app.config import ensure_data_file_path
from cynthium.app.engine.pathfinding.astar import a_star
from cynthium.app.io.reader import load_geotif
from cynthium.app.services.site_rasters import (
	RasterPayload,
	load_context_rasters,
	load_daily_avg_illumination_raster,
	load_daily_avg_meteor_raster,
	load_slope_raster,
	select_display_raster,
)
from cynthium.app.utils.logger import get_logger

from .map_view import MapView
from .terrain_view import TerrainView

logger = get_logger(__name__)


class ViewContainer(QWidget):
	def __init__(self, parent=None):
		"""
		Initializes the ViewContainer instance.

		:param parent: Parent widget.
		:return: None
		"""
		super().__init__(parent)

		self._current_path = None
		self._current_datetime = None
		self._current_data = None
		self._current_meta = None
		self._current_slope_data = None
		self._current_slope_meta = None
		self._current_illumination_data = None
		self._current_illumination_meta = None
		self._current_temperature_data = None
		self._current_temperature_meta = None
		self._current_meteor_data = None
		self._current_meteor_meta = None

		self._autopath_xy = []

		self.terrain_view = TerrainView(parent=self)
		self.raster_view = MapView(parent=self)

		splitter = QSplitter(Qt.Orientation.Horizontal)
		splitter.addWidget(self.raster_view)
		splitter.addWidget(self.terrain_view)
		splitter.setSizes([500, 500])

		layout = QHBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.addWidget(splitter)

		self.setStyleSheet("border: 1px solid #cccccc;")

	def load(
		self,
		path: str,
		map_type: str = "Elevation",
		date: str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
	):
		"""
		Loads a site from a pre-split 20 m/px tile.

		Given a 5 m/px preset path (e.g. ``Haworth_5mpp_surf.tif``), derives
		the matching 20 m/px tile (``Haworth_20mpp_surf.tif``) in the same
		directory and loads that as the elevation data.

		:param path: Path to the 5 m/px site file.
		:type path: str
		:param map_type: Map type identifier.
		:type map_type: str
		:param date: Parameter value.
		:type date: str
		:return: The resulting value.
		"""
		path = str(ensure_data_file_path(Path(path)))

		# The preset path already points to the 20 m/px tile.
		path_20 = path

		data, meta = load_geotif(path_20)

		self._current_path = path_20
		self._current_datetime = date
		self._current_data = data
		self._current_meta = meta

		self._current_slope_data, self._current_slope_meta = load_slope_raster(path_20)
		(
			(self._current_illumination_data, self._current_illumination_meta),
			(self._current_temperature_data, self._current_temperature_meta),
			(self._current_meteor_data, self._current_meteor_meta),
		) = load_context_rasters(path_20)

		self.set_autopath([])
		self.display_map_type(map_type)
		self.terrain_view.load(path_20, date, data=data, meta=meta)

	def display_map_type(self, map_type: str) -> bool:
		"""
		Displays the map type.

		:param map_type: Map type identifier.
		:type map_type: str
		:return: The resulting value.
		"""
		if self._current_data is None or self._current_meta is None:
			logger.warning("Cannot display map type before a site has been loaded.")
			return False

		map_key = map_type.strip().lower()
		map_key = re.sub(r"[^a-z0-9]+", "_", map_key)
		map_key = re.sub(r"_+", "_", map_key).strip("_")

		illumination_raster = self._illumination_raster
		if map_key in {"solar_illumination_day_avg", "solar_illumination_daily_avg"} and self._current_path:
			daily = load_daily_avg_illumination_raster(
				reference_path=str(self._current_path),
				reference_meta=self._current_meta,
				reference_shape=(
					int(self._current_data.shape[0]),
					int(self._current_data.shape[1]),
				),
				utctime=str(self._current_datetime),
			)
			if daily[0] is not None:
				illumination_raster = daily

		meteor_raster = self._meteor_raster
		if map_key in {"meteor_flux_day_avg", "meteor_flux_daily_avg"} and self._current_path:
			daily_meteor = load_daily_avg_meteor_raster(
				reference_path=str(self._current_path),
				reference_meta=self._current_meta,
				reference_shape=(
					int(self._current_data.shape[0]),
					int(self._current_data.shape[1]),
				),
				utctime=str(self._current_datetime),
			)
			if daily_meteor[0] is not None:
				meteor_raster = daily_meteor

		display_data, display_meta = select_display_raster(
			map_type,
			self._elevation_raster,
			self._slope_raster,
			illumination_raster,
			self._temperature_raster,
			meteor_raster,
		)
		if display_data is None:
			logger.warning(f"No raster data available for map type: {map_type}")
			return False

		self.raster_view.load(
			display_data,
			display_meta,
			map_type,
			utctime=self._current_datetime,
		)
		return True

	@property
	def _elevation_raster(self) -> RasterPayload:
		"""
		Performs elevation raster.

		:return: The resulting value.
		"""
		return self._current_data, self._current_meta

	@property
	def _slope_raster(self) -> RasterPayload:
		"""
		Performs slope raster.

		:return: The resulting value.
		"""
		return self._current_slope_data, self._current_slope_meta

	@property
	def _illumination_raster(self) -> RasterPayload:
		"""
		Performs illumination raster.

		:return: The resulting value.
		"""
		return self._current_illumination_data, self._current_illumination_meta

	@property
	def _temperature_raster(self) -> RasterPayload:
		"""
		Performs temperature raster.

		:return: The resulting value.
		"""
		return self._current_temperature_data, self._current_temperature_meta

	@property
	def _meteor_raster(self) -> RasterPayload:
		"""
		Performs meteor flux raster.

		:return: The resulting value.
		"""
		return self._current_meteor_data, self._current_meteor_meta

	def get_current_map_data(self):
		"""
		Returns the current map data.

		:return: The resulting value.
		"""
		return (
			self._current_data,
			self._current_meta,
			self._current_slope_data,
			self._current_temperature_data,
			self._current_temperature_meta,
			self._current_illumination_data,
			self._current_illumination_meta,
			self._current_meteor_data,
			self._current_meteor_meta,
		)

	def add_waypoint(self, x: float, y: float):
		"""
		Adds the waypoint.

		:param x: X coordinate.
		:type x: float
		:param y: Y coordinate.
		:type y: float
		:return: None
		"""
		self.clear_failure_point()
		self.clear_sim_failure_point()
		self.raster_view.add_waypoint(x, y)
		self.terrain_view.add_waypoint(x, y)

	def remove_waypoint(self, index: int):
		"""
		Removes the waypoint.

		:param index: Item index.
		:type index: int
		:return: None
		"""
		self.clear_failure_point()
		self.clear_sim_failure_point()
		self.raster_view.remove_waypoint(index)
		self.terrain_view.remove_waypoint(index)

	def clear_all_waypoints(self):
		self.raster_view.clear_all_waypoints()
		self.terrain_view.clear_all_waypoints()

	def get_waypoint_3d_points(self):
		"""
		Returns the waypoint 3d points.

		:return: The resulting value.
		"""
		return self.terrain_view.get_waypoint_3d_points()

	def get_autopath_3d_points(self) -> list[list[float]]:
		"""
		Returns the 3D points of the autogenerated path.

		:return: List of 3D points.
		"""
		return self.terrain_view.get_autopath_3d_points()

	def set_autopath(self, points_xy: list[tuple[float, float]]):
		self._autopath_xy = list(points_xy)
		self.raster_view.set_autopath(self._autopath_xy)
		self.terrain_view.set_autopath(self._autopath_xy)

	def set_failure_point(self, x: float, y: float):
		self.raster_view.set_failure_point(x, y)
		self.terrain_view.set_failure_point(x, y)

	def clear_failure_point(self):
		self.raster_view.clear_failure_point()
		self.terrain_view.clear_failure_point()

	def set_sim_failure_point(self, x: float, y: float):
		self.raster_view.set_sim_failure_point(x, y)
		self.terrain_view.set_sim_failure_point(x, y)

	def clear_sim_failure_point(self):
		self.raster_view.clear_sim_failure_point()
		self.terrain_view.clear_sim_failure_point()

	def compute_autopath(
		self,
		*,
		start_xy: tuple[float, float],
		goal_xy: tuple[float, float],
		utctime: str,
		map_type: str,
		min_slope_deg: float = 0.0,
		max_slope_deg: float = 20.0,
		slope_weight: float = 1.0,
		sun_weight: float,
		meteor_flux_weight: float = 0.2,
		temperature_weight: float = 0.2,
		cost_strategy: str = "Weighted cost",
		algorithm: str = "Theta*",
		pad_cells: int = 200,
		max_expanded: int = 500000,
		blocked_cells: set[tuple[int, int]] | None = None,
		use_bicubic: bool = False,
	) -> list[tuple[float, float]] | None:
		if self._current_data is None or self._current_meta is None:
			return None
		if "transform" not in self._current_meta:
			return None

		transform = self._current_meta["transform"]
		inv = ~transform
		sc_f, sr_f = inv * (float(start_xy[0]), float(start_xy[1]))
		gc_f, gr_f = inv * (float(goal_xy[0]), float(goal_xy[1]))
		sr = int(round(float(sr_f)))
		sc = int(round(float(sc_f)))
		gr = int(round(float(gr_f)))
		gc = int(round(float(gc_f)))

		H = int(self._current_data.shape[0])
		W = int(self._current_data.shape[1])
		if not (0 <= sr < H and 0 <= sc < W and 0 <= gr < H and 0 <= gc < W):
			return None

		dr = abs(gr - sr)
		dc = abs(gc - sc)
		dist_cells = int(max(dr, dc))
		pad = int(max(50, min(int(pad_cells), int(dist_cells * 0.5) + 50)))

		r0 = max(0, min(sr, gr) - pad)
		r1 = min(H, max(sr, gr) + pad + 1)
		c0 = max(0, min(sc, gc) - pad)
		c1 = min(W, max(sc, gc) + pad + 1)

		# Pathfind at native resolution so slope checks are accurate.
		stride = 1
		upsample = 1

		elev: np.ndarray = self._current_data[r0:r1, c0:c1]
		start_local: tuple[float, float] | None = None
		goal_local: tuple[float, float] | None = None
		res_x: float = float(abs(transform.a)) * float(stride)
		res_y: float = float(abs(transform.e)) * float(stride)

		# Always try daily illumination for path cost (more accurate)
		illum_data = self._current_illumination_data
		illum_meta = self._current_illumination_meta
		if self._current_path:
			daily = load_daily_avg_illumination_raster(
				reference_path=self._current_path,
				reference_meta=self._current_meta,
				reference_shape=(H, W),
				utctime=str(utctime),
			)
			if daily[0] is not None:
				illum_data, illum_meta = daily

		illum_sampled = np.full_like(elev, np.nan, dtype=np.float32)
		if illum_data is not None and illum_meta is not None and "transform" in illum_meta:
			it = illum_meta["transform"]
			inv_it = ~it
			ia, ib, ic = float(inv_it.a), float(inv_it.b), float(inv_it.c)
			id_, ie, if_ = float(inv_it.d), float(inv_it.e), float(inv_it.f)
			a, b, c_ = float(transform.a), float(transform.b), float(transform.c)
			d, e, f_ = float(transform.d), float(transform.e), float(transform.f)

			cols = np.arange(int(c0), int(c1), int(stride), dtype=np.float64) + (0.5 * float(stride))
			for rr in range(int(r0), int(r1), int(stride)):
				rowc = float(rr) + (0.5 * float(stride))
				x = (a * cols) + (b * rowc) + c_
				y = (d * cols) + (e * rowc) + f_
				ci = np.rint((ia * x) + (ib * y) + ic).astype(np.int64)
				ri = np.rint((id_ * x) + (ie * y) + if_).astype(np.int64)

				local_r = int((rr - r0) // int(stride))
				valid = (
					(ri >= 0)
					& (ci >= 0)
					& (ri < int(illum_data.shape[0]))
					& (ci < int(illum_data.shape[1]))
				)
				if np.any(valid):
					illum_sampled[local_r, valid] = illum_data[ri[valid], ci[valid]]

		illum_norm = np.full_like(illum_sampled, 0.5, dtype=np.float32)
		finite_illum = illum_sampled[np.isfinite(illum_sampled)]
		if finite_illum.size > 0:
			lo = float(np.min(finite_illum))
			hi = float(np.max(finite_illum))
			if hi > lo:
				illum_norm = ((illum_sampled - lo) / (hi - lo)).astype(np.float32)
				illum_norm = np.clip(illum_norm, 0.0, 1.0)
				illum_norm[~np.isfinite(illum_norm)] = 0.5

		# --- meteor flux sampling ---
		meteor_data = self._current_meteor_data
		meteor_meta = self._current_meteor_meta
		if self._current_path:
			daily_meteor = load_daily_avg_meteor_raster(
				reference_path=self._current_path,
				reference_meta=self._current_meta,
				reference_shape=(H, W),
				utctime=str(utctime),
			)
			if daily_meteor[0] is not None:
				meteor_data, meteor_meta = daily_meteor
		meteor_sampled = np.full_like(elev, np.nan, dtype=np.float32)
		if meteor_data is not None and meteor_meta is not None and "transform" in meteor_meta:
			it = meteor_meta["transform"]
			inv_it = ~it
			ia, ib, ic = float(inv_it.a), float(inv_it.b), float(inv_it.c)
			id_, ie, if_ = float(inv_it.d), float(inv_it.e), float(inv_it.f)
			a, b, c_ = float(transform.a), float(transform.b), float(transform.c)
			d, e, f_ = float(transform.d), float(transform.e), float(transform.f)

			cols = np.arange(int(c0), int(c1), int(stride), dtype=np.float64) + (0.5 * float(stride))
			for rr in range(int(r0), int(r1), int(stride)):
				rowc = float(rr) + (0.5 * float(stride))
				x = (a * cols) + (b * rowc) + c_
				y = (d * cols) + (e * rowc) + f_
				ci = np.rint((ia * x) + (ib * y) + ic).astype(np.int64)
				ri = np.rint((id_ * x) + (ie * y) + if_).astype(np.int64)

				local_r = int((rr - r0) // int(stride))
				valid = (
					(ri >= 0)
					& (ci >= 0)
					& (ri < int(meteor_data.shape[0]))
					& (ci < int(meteor_data.shape[1]))
				)
				if np.any(valid):
					meteor_sampled[local_r, valid] = meteor_data[ri[valid], ci[valid]]

		meteor_norm = np.full_like(meteor_sampled, 0.5, dtype=np.float32)
		finite_meteor = meteor_sampled[np.isfinite(meteor_sampled)]
		if finite_meteor.size > 0:
			lo = float(np.min(finite_meteor))
			hi = float(np.max(finite_meteor))
			if hi > lo:
				meteor_norm = ((meteor_sampled - lo) / (hi - lo)).astype(np.float32)
				meteor_norm = np.clip(meteor_norm, 0.0, 1.0)
				meteor_norm[~np.isfinite(meteor_norm)] = 0.5

		# --- temperature sampling ---
		temp_data = self._current_temperature_data
		temp_meta = self._current_temperature_meta
		temp_sampled = np.full_like(elev, np.nan, dtype=np.float32)
		if temp_data is not None and temp_meta is not None and "transform" in temp_meta:
			it = temp_meta["transform"]
			inv_it = ~it
			ia, ib, ic = float(inv_it.a), float(inv_it.b), float(inv_it.c)
			id_, ie, if_ = float(inv_it.d), float(inv_it.e), float(inv_it.f)
			a, b, c_ = float(transform.a), float(transform.b), float(transform.c)
			d, e, f_ = float(transform.d), float(transform.e), float(transform.f)

			cols = np.arange(int(c0), int(c1), int(stride), dtype=np.float64) + (0.5 * float(stride))
			for rr in range(int(r0), int(r1), int(stride)):
				rowc = float(rr) + (0.5 * float(stride))
				x = (a * cols) + (b * rowc) + c_
				y = (d * cols) + (e * rowc) + f_
				ci = np.rint((ia * x) + (ib * y) + ic).astype(np.int64)
				ri = np.rint((id_ * x) + (ie * y) + if_).astype(np.int64)

				local_r = int((rr - r0) // int(stride))
				valid = (
					(ri >= 0)
					& (ci >= 0)
					& (ri < int(temp_data.shape[0]))
					& (ci < int(temp_data.shape[1]))
				)
				if np.any(valid):
					temp_sampled[local_r, valid] = temp_data[ri[valid], ci[valid]]

		temp_norm = np.full_like(temp_sampled, 0.5, dtype=np.float32)
		finite_temp = temp_sampled[np.isfinite(temp_sampled)]
		if finite_temp.size > 0:
			lo = float(np.min(finite_temp))
			hi = float(np.max(finite_temp))
			if hi > lo:
				temp_norm = ((temp_sampled - lo) / (hi - lo)).astype(np.float32)
				temp_norm = np.clip(temp_norm, 0.0, 1.0)
				temp_norm[~np.isfinite(temp_norm)] = 0.5

		# Cost-strategy powers.  Weighted cost = linear (1.0),
		# Minimax = 4th power so a single bad cell dominates.
		if str(cost_strategy).strip().lower() == "minimax":
			sun_power = 4.0
			grade_power = 4.0
		else:
			sun_power = 1.0
			grade_power = 1.0

		sun_penalty = (1.0 - illum_norm)
		if float(sun_power) != 1.0:
			sun_penalty = sun_penalty ** float(sun_power)

		cell_cost = (
			1.0
			+ (float(max(0.0, sun_weight)) * sun_penalty)
			+ (float(max(0.0, meteor_flux_weight)) * meteor_norm)
			+ (float(max(0.0, temperature_weight)) * (1.0 - temp_norm))
		).astype(np.float32)
		cell_cost = np.clip(cell_cost, 0.01, np.inf).astype(np.float32)

		traversable = np.isfinite(elev)

		# --- Bicubic upsampling for A* grid ---
		if use_bicubic:
			upsample = 4
			elev = np.asarray(zoom(elev, upsample, order=3, mode="nearest"))
			cell_cost = np.repeat(np.repeat(cell_cost, upsample, axis=0), upsample, axis=1)
			traversable = np.repeat(np.repeat(traversable, upsample, axis=0), upsample, axis=1)
			# Scale blocked cells to upsampled grid and apply directly
			if blocked_cells:
				for rr, cc in blocked_cells:
					br0 = (rr - r0) * upsample
					bc0 = (cc - c0) * upsample
					traversable[br0:br0 + upsample, bc0:bc0 + upsample] = False
				blocked_cells = None
			# Adjust start/goal to upsampled local coords
			sr_u = (sr - r0) * upsample
			sc_u = (sc - c0) * upsample
			gr_u = (gr - r0) * upsample
			gc_u = (gc - c0) * upsample
			start_local = (float(sr_u), float(sc_u))
			goal_local = (float(gr_u), float(gc_u))
			res_x = float(abs(transform.a)) / upsample
			res_y = float(abs(transform.e)) / upsample

		# Scale expansion limit to the (possibly upsampled) grid size
		max_expanded = max(int(max_expanded), int(elev.size))

		# Block cells from previous failed simulation attempts
		if blocked_cells:
			for rr, cc in blocked_cells:
				rr_local = (rr - r0) // stride
				cc_local = (cc - c0) // stride
				if 0 <= rr_local < traversable.shape[0] and 0 <= cc_local < traversable.shape[1]:
					traversable[rr_local, cc_local] = False

		if not use_bicubic:
			start_local = (float((sr - r0) // stride), float((sc - c0) // stride))
			goal_local = (float((gr - r0) // stride), float((gc - c0) // stride))

		# Always allow start/goal cells.
		if start_local is not None:
			sl0, sl1 = int(start_local[0]), int(start_local[1])
			if 0 <= sl0 < traversable.shape[0] and 0 <= sl1 < traversable.shape[1]:
				traversable[sl0, sl1] = True
				if not np.isfinite(cell_cost[sl0, sl1]):
					cell_cost[sl0, sl1] = 1.0
		if goal_local is not None:
			gl0, gl1 = int(goal_local[0]), int(goal_local[1])
			if 0 <= gl0 < traversable.shape[0] and 0 <= gl1 < traversable.shape[1]:
				traversable[gl0, gl1] = True
				if not np.isfinite(cell_cost[gl0, gl1]):
					cell_cost[gl0, gl1] = 1.0

		use_dijkstra = str(algorithm).strip().lower() == "dijkstra"
		if start_local is None or goal_local is None:
			return None

		result = a_star(
			start_rc=(int(start_local[0]), int(start_local[1])),
			goal_rc=(int(goal_local[0]), int(goal_local[1])),
			traversable=traversable,
			cell_cost=cell_cost,
			elev=np.asarray(elev),
			res_x=res_x,
			res_y=res_y,
			min_slope_deg=float(min_slope_deg),
			max_slope_deg=float(max_slope_deg),
			slope_weight=float(max(0.0, slope_weight)),
			grade_power=float(grade_power),
			max_expanded=int(max_expanded),
			dijkstra=use_dijkstra,
		)
		alg_name = "Dijkstra" if use_dijkstra else "A*"
		if result is None or not result.path_rc:
			return None

		a, b, c_ = float(transform.a), float(transform.b), float(transform.c)
		d, e, f_ = float(transform.d), float(transform.e), float(transform.f)
		xy: list[tuple[float, float]] = []
		for r, c in result.path_rc:
			if use_bicubic:
				grr = r0 + (r + 0.5) / upsample
				gcc = c0 + (c + 0.5) / upsample
			else:
				grr = float(r0 + (int(r) * int(stride))) + (0.5 * float(stride))
				gcc = float(c0 + (int(c) * int(stride))) + (0.5 * float(stride))
			x = (a * gcc) + (b * grr) + c_
			y = (d * gcc) + (e * grr) + f_
			xy.append((float(x), float(y)))

		if xy:
			xy[0] = (float(start_xy[0]), float(start_xy[1]))
			xy[-1] = (float(goal_xy[0]), float(goal_xy[1]))

		if use_bicubic and xy:
			logger.info(
				f"Bicubic path: first=({xy[0][0]:.1f}, {xy[0][1]:.1f}), "
				f"last=({xy[-1][0]:.1f}, {xy[-1][1]:.1f}), "
				f"len={len(xy)}"
			)

		logger.info(
			f"Autopath {alg_name}: nodes={len(result.path_rc)} expanded={result.expanded} cost={result.total_cost:.2f}"
		)
		return xy
