import re

import numpy as np
import pyqtgraph as pg
from matplotlib.colors import LightSource
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from cynthium.app.engine.illumination.sun_position import sun_position
from cynthium.app.engine.raster.point_conversion import xy_to_longlat


def _unit_for_map_type(map_type_label: str) -> str:
	"""Return a short unit string for the displayed map type."""
	key = map_type_label.strip().lower()
	if "elevation" in key:
		return "m"
	if "slope" in key:
		return "deg"
	if "hillshade" in key:
		return ""
	if "illumination" in key:
		return "W/m\u00b2"
	if "meteor flux" in key or "meteor_flux" in key:
		return "J/yr\u00b7m\u00b2"
	if "meteor number" in key or "meteor_number" in key:
		return "#/yr"
	if "temperature" in key:
		return "K"
	if "psr" in key or "permanently" in key:
		return ""
	return ""


class MapView(QWidget):
	waypoint_added = Signal(float, float)

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
		self._plot.scene().sigMouseClicked.connect(self._on_click)
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

		self._autopath_line = pg.PlotDataItem(pen=pg.mkPen("b", width=2))
		self._autopath_line.setZValue(15)
		self._plot.addItem(self._autopath_line)

		self._waypoints = pg.ScatterPlotItem(
			size=10,
			pen=pg.mkPen("k", width=1),
			brush=pg.mkBrush(100, 255, 0, 255),
		)
		self._waypoints.setZValue(20)
		self._plot.addItem(self._waypoints)
		self._waypoint_list = []
		self._waypoint_labels: list[pg.TextItem] = []

		self._failure_point = pg.ScatterPlotItem(
			size=14,
			pen=pg.mkPen("k", width=1),
			brush=pg.mkBrush(255, 0, 0, 255),
		)
		self._failure_point.setZValue(25)
		self._plot.addItem(self._failure_point)

		self._sim_failure_point = pg.ScatterPlotItem(
			size=14,
			pen=pg.mkPen("k", width=1),
			brush=pg.mkBrush(255, 0, 0, 255),
		)
		self._sim_failure_point.setZValue(25)
		self._plot.addItem(self._sim_failure_point)

		self._raw_data: np.ndarray | None = None
		self._raster_transform = None
		self._map_type_label = ""
		self._cursor_label = pg.TextItem(
			text="", color=(255, 255, 255),
			fill=pg.mkBrush(0, 0, 0, 180), anchor=(-0.1, 1.1),
		)
		self._cursor_label.setZValue(50)
		self._cursor_label.setVisible(False)
		self._plot.addItem(self._cursor_label)
		self._plot.scene().sigMouseMoved.connect(self._on_mouse_moved)

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

		self._raw_data = data
		self._raster_transform = meta.get("transform") if meta else None
		self._map_type_label = map_type
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
			"meteor_number": "Meteor Number",
			"average_temperature": "Average Temperature (K)",
			"permanently_shaded_regions": "PSR",
		}
		map_key = map_type.strip().lower()
		map_key = re.sub(r"[^a-z0-9]+", "_", map_key)
		map_key = re.sub(r"_+", "_", map_key).strip("_")

		label = labels.get(map_key, None)
		if label is None and map_key.startswith("solar_illumination"):
			label = labels["solar_illumination"]
		if label is None and map_key.startswith("meteor_flux"):
			label = labels["meteor_flux"]
		if label is None and map_key.startswith("meteor_number"):
			label = labels["meteor_number"]
		if label is None and map_key in {"permanently_shaded_regions", "psr"}:
			label = labels["permanently_shaded_regions"]

		self._colorbar.setLabel("right", label or map_type)

	def _on_mouse_moved(self, pos):
		"""Show raster value under the cursor."""
		if self._raw_data is None or self._raster_transform is None:
			self._cursor_label.setVisible(False)
			return
		mouse_point = self._plot.vb.mapSceneToView(pos)
		mx, my = mouse_point.x(), mouse_point.y()
		tr = self._raster_transform
		# Check if cursor is within the image geographic bounds
		x0, y0 = tr.c, tr.f + self._raw_data.shape[0] * tr.e
		x1, y1 = tr.c + self._raw_data.shape[1] * tr.a, tr.f
		if not (min(x0, x1) <= mx <= max(x0, x1) and min(y0, y1) <= my <= max(y0, y1)):
			self._cursor_label.setVisible(False)
			return
		col = (mx - tr.c) / tr.a
		row = (my - tr.f) / tr.e
		ci, ri = int(round(col)), int(round(row))
		if 0 <= ri < self._raw_data.shape[0] and 0 <= ci < self._raw_data.shape[1]:
			val = float(self._raw_data[ri, ci])
			if np.isfinite(val):
				unit = _unit_for_map_type(self._map_type_label)
				if abs(val) >= 10000 or (abs(val) > 0 and abs(val) < 0.001):
					text = f"{val:.2e} {unit}"
				else:
					text = f"{val:.4f} {unit}"
				self._cursor_label.setText(text)
				self._cursor_label.setPos(mx, my)
				self._cursor_label.setVisible(True)
				return
		self._cursor_label.setVisible(False)

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

	def edit_waypoint(self, index: int, x: float, y: float):
		"""Replace the waypoint at index with new coordinates."""
		if 0 <= index < len(self._waypoint_list):
			self._waypoint_list[index] = (x, y)
			self._update_graph()

	def clear_all_waypoints(self):
		self._waypoint_list.clear()
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

		# Update waypoint number labels
		for label in self._waypoint_labels:
			self._plot.removeItem(label)
		self._waypoint_labels.clear()
		for i, (x, y) in enumerate(self._waypoint_list):
			label = pg.TextItem(
				text=str(i + 1),
				color=(255, 255, 255),
				fill=pg.mkBrush(0, 0, 0, 180),
				anchor=(1, 0.0),
			)
			label.setPos(x, y)
			label.setZValue(21)
			self._plot.addItem(label)
			self._waypoint_labels.append(label)

		if len(self._waypoint_list) > 1:
			xs = [p[0] for p in self._waypoint_list]
			ys = [p[1] for p in self._waypoint_list]
			self._path_line.setData(xs, ys)
		else:
			self._path_line.setData([], [])

	def clear_failure_point(self):
		self._failure_point.setData([])

	def set_failure_point(self, x: float, y: float):
		self._failure_point.setData(pos=np.array([[x, y]]))

	def set_sim_failure_point(self, x: float, y: float):
		self._sim_failure_point.setData(pos=np.array([[x, y]]))

	def clear_sim_failure_point(self):
		self._sim_failure_point.setData([])

	def set_autopath(self, points_xy: list[tuple[float, float]]):
		if not points_xy or len(points_xy) < 2:
			self._autopath_line.setData([], [])
			return

		xs = [p[0] for p in points_xy]
		ys = [p[1] for p in points_xy]
		self._autopath_line.setData(xs, ys)

	def _on_click(self, event):
		# Ignore clicks already handled by scene items (e.g. auto-range button)
		if event.isAccepted():
			return
		if event.button() != Qt.MouseButton.LeftButton:
			return
		pos = event.scenePos()
		mouse_point = self._plot.vb.mapSceneToView(pos)
		x, y = mouse_point.x(), mouse_point.y()
		print(f"clicked at {x:.2f}, {y:.2f}")
		self.waypoint_added.emit(x, y)
