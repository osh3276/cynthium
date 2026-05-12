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
		self._plot.invertY(True)
		self._img = pg.ImageItem()
		self._plot.addItem(self._img)

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

		self._img.setImage(rendered.T)

		if meta:
			transform = meta["transform"]
			# pyqtgraph ImageItem positioning:
			# setPos(x, y) sets the origin.
			# rasterio transform: c is x_origin, f is y_origin. a is x_res, e is y_res.
			# a is typically positive, e is typically negative.

			# We use a QTransform to handle both scale and position.
			# This is more robust than setPos + setScale if we have negative scaling.
			tr = pg.QtGui.QTransform()
			tr.translate(transform.c, transform.f)
			tr.scale(transform.a, transform.e)
			self._img.setTransform(tr)