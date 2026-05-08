import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.colors import LightSource


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

	def load(self, data: np.ndarray):
		ls = LightSource(azdeg=315, altdeg=45)
		hillshade = ls.hillshade(data, vert_exag=1.0)
		hillshade_uint8 = (hillshade * 255).astype(np.uint8)
		self._img.setImage(hillshade_uint8.T)