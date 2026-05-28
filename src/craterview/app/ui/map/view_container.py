import math
import re
from datetime import datetime, timezone

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QSplitter, QWidget

from craterview.app.engine.pathfinding.theta_star import theta_star
from craterview.app.io.reader import load_geotif
from craterview.app.services.site_rasters import (
	RasterPayload,
	load_context_rasters,
	load_daily_avg_illumination_raster,
	load_slope_raster,
	select_display_raster,
)
from craterview.app.utils.logger import get_logger

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
		Loads the data.

		:param path: Path to the file.
		:type path: str
		:param map_type: Map type identifier.
		:type map_type: str
		:param date: Parameter value.
		:type date: str
		:return: The resulting value.
		"""
		data, meta = load_geotif(path)
		self._current_path = path
		self._current_datetime = date
		self._current_data = data
		self._current_meta = meta

		self._current_slope_data, self._current_slope_meta = load_slope_raster(path)
		(
			(self._current_illumination_data, self._current_illumination_meta),
			(self._current_temperature_data, self._current_temperature_meta),
		) = load_context_rasters(path)

		self.set_autopath([])
		self.display_map_type(map_type)
		self.terrain_view.load(path, date)

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

		display_data, display_meta = select_display_raster(
			map_type,
			self._elevation_raster,
			self._slope_raster,
			illumination_raster,
			self._temperature_raster,
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
		self.raster_view.add_waypoint(x, y)
		self.terrain_view.add_waypoint(x, y)

	def remove_waypoint(self, index: int):
		"""
		Removes the waypoint.

		:param index: Item index.
		:type index: int
		:return: None
		"""
		self.raster_view.remove_waypoint(index)
		self.terrain_view.remove_waypoint(index)

	def get_waypoint_3d_points(self):
		"""
		Returns the waypoint 3d points.

		:return: The resulting value.
		"""
		return self.terrain_view.get_waypoint_3d_points()

	def set_autopath(self, points_xy: list[tuple[float, float]]):
		self._autopath_xy = list(points_xy)
		self.raster_view.set_autopath(self._autopath_xy)
		self.terrain_view.set_autopath(self._autopath_xy)

	def compute_autopath_theta_star(
		self,
		*,
		start_xy: tuple[float, float],
		goal_xy: tuple[float, float],
		utctime: str,
		map_type: str,
		min_slope_deg: float,
		max_slope_deg: float,
		slope_weight: float,
		sun_weight: float,
		pad_cells: int = 200,
		max_expanded: int = 500000,
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

		win_h = int(r1 - r0)
		win_w = int(c1 - c0)
		max_nodes = 250000
		area = int(win_h * win_w)
		stride = 1
		if area > max_nodes:
			stride = int(math.ceil(math.sqrt(float(area) / float(max_nodes))))
			stride = max(1, stride)
			logger.info(f"Autopath: downsampling grid by stride={stride} (area={area})")

		elev = self._current_data[r0:r1:stride, c0:c1:stride]
		if self._current_slope_data is not None and self._current_slope_data.shape == self._current_data.shape:
			slope = self._current_slope_data[r0:r1:stride, c0:c1:stride]
		else:
			slope = np.zeros_like(elev, dtype=np.float32)

		illum_data = self._current_illumination_data
		illum_meta = self._current_illumination_meta
		map_key = map_type.strip().lower()
		map_key = re.sub(r"[^a-z0-9]+", "_", map_key)
		map_key = re.sub(r"_+", "_", map_key).strip("_")
		if map_key in {"solar_illumination_day_avg", "solar_illumination_daily_avg"} and self._current_path:
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

		max_slope = float(max_slope_deg)
		if not (max_slope > 0.0):
			max_slope = 1.0
		slope_norm = np.clip((slope.astype(np.float32) / max_slope), 0.0, 1.0)

		cell_cost = (
			1.0
			+ (float(max(0.0, slope_weight)) * slope_norm)
			+ (float(max(0.0, sun_weight)) * (1.0 - illum_norm))
		).astype(np.float32)
		cell_cost = np.clip(cell_cost, 0.01, np.inf).astype(np.float32)

		traversable = np.isfinite(elev)
		traversable &= np.isfinite(slope)
		traversable &= slope >= float(min_slope_deg)
		traversable &= slope <= float(max_slope_deg)

		start_local = (int((sr - r0) // stride), int((sc - c0) // stride))
		goal_local = (int((gr - r0) // stride), int((gc - c0) // stride))

		# Always allow start/goal even if they violate slope limits.
		if 0 <= start_local[0] < traversable.shape[0] and 0 <= start_local[1] < traversable.shape[1]:
			traversable[start_local[0], start_local[1]] = True
			if not np.isfinite(cell_cost[start_local[0], start_local[1]]):
				cell_cost[start_local[0], start_local[1]] = 1.0
		if 0 <= goal_local[0] < traversable.shape[0] and 0 <= goal_local[1] < traversable.shape[1]:
			traversable[goal_local[0], goal_local[1]] = True
			if not np.isfinite(cell_cost[goal_local[0], goal_local[1]]):
				cell_cost[goal_local[0], goal_local[1]] = 1.0

		res_x = float(abs(transform.a)) * float(stride)
		res_y = float(abs(transform.e)) * float(stride)

		result = theta_star(
			start_rc=start_local,
			goal_rc=goal_local,
			traversable=traversable,
			cell_cost=cell_cost,
			res_x=res_x,
			res_y=res_y,
			max_expanded=int(max_expanded),
		)
		if result is None or not result.path_rc:
			return None

		a, b, c_ = float(transform.a), float(transform.b), float(transform.c)
		d, e, f_ = float(transform.d), float(transform.e), float(transform.f)
		xy: list[tuple[float, float]] = []
		for r, c in result.path_rc:
			grr = float(r0 + (int(r) * int(stride))) + (0.5 * float(stride))
			gcc = float(c0 + (int(c) * int(stride))) + (0.5 * float(stride))
			x = (a * gcc) + (b * grr) + c_
			y = (d * gcc) + (e * grr) + f_
			xy.append((float(x), float(y)))

		if xy:
			xy[0] = (float(start_xy[0]), float(start_xy[1]))
			xy[-1] = (float(goal_xy[0]), float(goal_xy[1]))

		logger.info(
			f"Autopath Theta*: nodes={len(result.path_rc)} expanded={result.expanded} cost={result.total_cost:.2f}"
		)
		return xy
