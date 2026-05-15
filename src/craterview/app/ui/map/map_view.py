import numpy as np
import pyqtgraph as pg
from matplotlib.colors import LightSource
from PySide6.QtWidgets import QVBoxLayout, QWidget


class MapView(QWidget):
	def __init__(self, parent=None):
		super().__init__(parent)

		pg.setConfigOptions(antialias=False, useOpenGL=True)

		self._view = pg.GraphicsLayoutWidget()
		self._view.setBackground("w")
		self._plot = self._view.addPlot()  # type: ignore[attr-defined]
		self._plot.setAspectLocked(True)
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
			size=10, pen=pg.mkPen(None), brush=pg.mkBrush(0, 0, 0, 255)
		)
		self._waypoints.setZValue(20)
		self._plot.addItem(self._waypoints)
		self._waypoint_list = []

		self.setStyleSheet("border-right: 1px solid #cccccc;")

		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.addWidget(self._view)

	def load(
		self, data: np.ndarray, meta: dict | None = None, map_type: str = "elevation"
	):
		normalized_map_type = map_type.lower().replace(" ", "_")

		if normalized_map_type == "hillshade":
			ls = LightSource(azdeg=315, altdeg=45)
			rendered = (ls.hillshade(data, vert_exag=1.0) * 255).astype(np.uint8)
			self._img.setColorMap(self._gray_cmap)
			self._colorbar.setVisible(False)
		else:
			rendered = data.astype(np.float32)
			self._img.setColorMap(self._cmap)
			self._colorbar.setColorMap(self._cmap)
			self._set_colorbar_levels(rendered)
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

	def _set_colorbar_levels(self, data: np.ndarray):
		finite_values = data[np.isfinite(data)]
		if finite_values.size == 0:
			return

		lo = float(np.min(finite_values))
		hi = float(np.max(finite_values))
		if lo == hi:
			hi = lo + 1.0
		self._colorbar.setLevels(values=(lo, hi))

	def add_waypoint(self, x: float, y: float):
		self._waypoint_list.append((x, y))
		self._update_graph()

	def remove_waypoint(self, index: int):
		if 0 <= index < len(self._waypoint_list):
			self._waypoint_list.pop(index)
			self._update_graph()

	def _update_graph(self):
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
