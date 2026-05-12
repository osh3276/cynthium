import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.colors import LightSource

from enum import Enum

class MapView(QWidget):
	def __init__(self, parent=None):
		super().__init__(parent)

		pg.setConfigOptions(antialias=False, useOpenGL=True)

		self._view = pg.GraphicsLayoutWidget()
		self._view.setBackground("w")
		self._plot = self._view.addPlot()
		self._plot.setAspectLocked(True)
		self._img = pg.ImageItem()
		self._plot.addItem(self._img)

		self._waypoints = pg.ScatterPlotItem(size=10, pen=pg.mkPen(None), brush=pg.mkBrush(255, 0, 0, 255))
		self._plot.addItem(self._waypoints)

		self._path_line = pg.PlotDataItem(pen=pg.mkPen('y', width=2))
		self._plot.addItem(self._path_line)
		self._waypoint_list = []

		self.setStyleSheet("border-right: 1px solid #cccccc;")

		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.addWidget(self._view)

	def load(self, data: np.ndarray, meta: dict = None, map_type: str = "elevation"):
		match map_type:
			case "hillshade":
				ls = LightSource(azdeg=315, altdeg=45)
				rendered = ls.hillshade(data, vert_exag=1.0)
				rendered = (rendered * 255).astype(np.uint8)
			case "elevation":
				lo, hi = data.min(), data.max()
				rendered = ((data - lo) / (hi - lo) * 255).astype(np.uint8)

		self._img.setImage(np.flipud(rendered).T)

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

	def add_waypoint(self, x: float, y: float):
		self._waypoint_list.append((x, y))
		self._update_graph()

	def remove_waypoint(self, index: int):
		if 0 <= index < len(self._waypoint_list):
			self._waypoint_list.pop(index)
			self._update_graph()

	def _update_graph(self):
		self._waypoints.setData(pos=np.array(self._waypoint_list) if self._waypoint_list else np.empty((0, 2)))
		
		if len(self._waypoint_list) > 1:
			xs = [p[0] for p in self._waypoint_list]
			ys = [p[1] for p in self._waypoint_list]
			self._path_line.setData(xs, ys)
		else:
			self._path_line.setData([], [])