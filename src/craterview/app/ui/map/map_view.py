import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.colors import LightSource

from enum import Enum

class MapType(Enum):
    HILLSHADE = "hillshade"
    ELEVATION = "elevation"

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

		self.setStyleSheet("border: 1px solid #cccccc;")

		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.addWidget(self._view)

	def load(self, data: np.ndarray, map_type: MapType = MapType.ELEVATION):
		match map_type:
			case MapType.HILLSHADE:
				ls = LightSource(azdeg=315, altdeg=45)
				rendered = ls.hillshade(data, vert_exag=1.0)
				rendered = (rendered * 255).astype(np.uint8)
			case MapType.ELEVATION:
				lo, hi = data.min(), data.max()
				rendered = ((data - lo) / (hi - lo) * 255).astype(np.uint8)

		self._img.setImage(rendered.T)