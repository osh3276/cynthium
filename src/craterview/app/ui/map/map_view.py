import re

import numpy as np
import pyqtgraph as pg
from matplotlib.colors import LightSource
from PySide6.QtWidgets import QVBoxLayout, QWidget

from craterview.app.engine.illumination.sun_position import sun_position
from craterview.app.engine.raster.point_conversion import xy_to_longlat


class MapView(QWidget):
	def __init__(self, parent=None):
		"""
		Initializes the MapView instance.

		:param parent: Parent widget.
		:return: None
		"""
		super().__init__(parent)

		pg.setConfigOptions(antialias=False, useOpenGL=False)

		self._view = pg.GraphicsLayoutWidget()
		self._view.setBackground("w")
		self._plot = self._view.addPlot()  # type: ignore[attr-defined]
		self._plot.setAspectLocked(True)
		self._plot.setLabel("bottom", "X", units="m")
		self._plot.setLabel("left", "Y", units="m")
		self._img = pg.ImageItem()
		self._plot.addItem(self._img)

		self._cmap = "turbo"
		self._gray_cmap = "CET-L1"
		self._img.setColorMap(self._cmap)

		self._colorbar = pg.ColorBarItem(
			colorMap=self._cmap,
			width=15,
			interactive=False,
		)
		self._colorbar.setImageItem(self._img, insert_in=self._plot)
		self._view.addItem(self._colorbar)

		self._path_line = pg.PlotDataItem(pen=pg.mkPen("y", width=2))
		self._path_line.setZValue(10)
		self._plot.addItem(self._path_line)

		self._waypoints = pg.ScatterPlotItem(
			size=10,
			pen=pg.mkPen("k", width=1),
			brush=pg.mkBrush(255, 255, 255, 255),
		)
		self._waypoints.setZValue(20)
		self._plot.addItem(self._waypoints)
		self._waypoint_list = []

		self.setStyleSheet("border-right: 1px solid #cccccc;")

		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.addWidget(self._view)

	def load(
		self,
		data: np.ndarray,
		meta: dict | None = None,
		map_type: str = "elevation",
		utctime: str | None = None,
	):
		"""
		Loads the data.

		:param data: Input data.
		:type data: np.ndarray
		:param meta: Raster metadata.
		:type meta: dict | None
		:param map_type: Map type identifier.
		:type map_type: str
		:return: The resulting value.
		"""
		normalized_map_type = map_type.strip().lower()
		normalized_map_type = re.sub(r"[^a-z0-9]+", "_", normalized_map_type)
		normalized_map_type = re.sub(r"_+", "_", normalized_map_type).strip("_")

		if normalized_map_type == "hillshade":
			dx = 1.0
			dy = 1.0
			azdeg = 315.0
			altdeg = 45.0

			if meta and "transform" in meta:
				transform = meta["transform"]
				dx = float(abs(transform.a))
				dy = float(abs(transform.e))

				if utctime:
					w = int(data.shape[1])
					h = int(data.shape[0])
					center_x = float(
						transform.c + (0.5 * w * transform.a) + (0.5 * h * transform.b)
					)
					center_y = float(
						transform.f + (0.5 * w * transform.d) + (0.5 * h * transform.e)
					)
					center_longlat = xy_to_longlat(center_x, center_y)
					az_deg, _el_deg = sun_position(
						center_longlat[1],
						center_longlat[0],
						utctime,
					)
					azdeg = float(az_deg)

			ls = LightSource(azdeg=azdeg, altdeg=altdeg)
			hs = ls.hillshade(data, vert_exag=1.0, dx=dx, dy=dy).astype(np.float32)
			hs = np.clip(hs, 0.0, 1.0)

			# Keep hillshade subdued (avoid blown-out highlights).
			rendered = (hs * 100.0).astype(np.uint8)
			self._img.setColorMap(self._gray_cmap)
			self._img.setLevels((0, 100))
			self._set_colorbar_label(map_type)
			self._colorbar.setVisible(False)
		else:
			rendered = data.astype(np.float32)
			self._img.setColorMap(self._cmap)
			self._colorbar.setColorMap(self._cmap)
			self._set_colorbar_levels(rendered)
			self._set_colorbar_label(map_type)
			self._colorbar.setVisible(True)

		self._img.setImage(np.flipud(rendered).T, autoLevels=False)

		if meta:
			transform = meta["transform"]
			# pyqtgraph ImageItem positioning:
			# setPos(x, y) sets the origin.
			# rasterio transform: c is x_origin, f is y_origin. a is x_res, e is y_res.
			# a is typically positive, e is typically negative.

			# We use a QTransform to handle both scale and position.
			# This is more robust than setPos + setScale if we have negative scaling.
			tr = pg.QtGui.QTransform()
			tr.translate(transform.c, transform.f + (data.shape[0] * transform.e))
			tr.scale(transform.a, abs(transform.e))
			self._img.setTransform(tr)

	def _set_colorbar_label(self, map_type: str):
		"""
		Sets the colorbar label.

		:param map_type: Map type identifier.
		:type map_type: str
		:return: None
		"""
		labels = {
			"elevation": "Elevation (m)",
			"hillshade": "Hillshade (unitless)",
			"slope": "Slope (deg)",
			"solar_illumination": "Solar Illumination (W/m²)",
			"meteor_flux": "Meteor Flux (J/yr*m²)",
			"average_temperature": "Average Temperature (K)",
		}
		map_key = map_type.strip().lower()
		map_key = re.sub(r"[^a-z0-9]+", "_", map_key)
		map_key = re.sub(r"_+", "_", map_key).strip("_")

		label = labels.get(map_key, None)
		if label is None and map_key.startswith("solar_illumination"):
			label = labels["solar_illumination"]

		self._colorbar.setLabel("right", label or map_type)

	def _set_colorbar_levels(self, data: np.ndarray):
		"""
		Sets the colorbar levels.

		:param data: Input data.
		:type data: np.ndarray
		:return: None
		"""
		finite_values = data[np.isfinite(data)]
		if finite_values.size == 0:
			return

		lo = float(np.min(finite_values))
		hi = float(np.max(finite_values))
		if lo == hi:
			hi = lo + 1.0
		self._colorbar.setLevels(values=(lo, hi))

	def add_waypoint(self, x: float, y: float):
		"""
		Adds the waypoint.

		:param x: X coordinate.
		:type x: float
		:param y: Y coordinate.
		:type y: float
		:return: None
		"""
		self._waypoint_list.append((x, y))
		self._update_graph()

	def remove_waypoint(self, index: int):
		"""
		Removes the waypoint.

		:param index: Item index.
		:type index: int
		:return: None
		"""
		if 0 <= index < len(self._waypoint_list):
			self._waypoint_list.pop(index)
			self._update_graph()

	def _update_graph(self):
		"""
		Performs update graph.

		:return: The resulting value.
		"""
		self._waypoints.setData(
			pos=np.array(self._waypoint_list)
			if self._waypoint_list
			else np.empty((0, 2))
		)

		if len(self._waypoint_list) > 1:
			xs = [p[0] for p in self._waypoint_list]
			ys = [p[1] for p in self._waypoint_list]
			self._path_line.setData(xs, ys)
		else:
			self._path_line.setData([], [])
