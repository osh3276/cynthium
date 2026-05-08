import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor

from craterview.app.io.raster.reader import load_geotif

class TerrainView(QtInteractor):
	def __init__(self, parent=None):
		super().__init__(parent=parent)

	def load(self, path: str):
		data, meta = load_geotif(path)
		self._render_dem(data)

	def _render_dem(self, data: np.ndarray):
		"""
		Renders a digital elevation model (DEM) from the input data.

		This method processes the given numpy array, which represents the elevation
		data, to create a digital elevation model. The DEM is used to represent
		terrain information in a grid format.

		:param data: A 2D numpy array containing elevation values. Each value in the
			array represents the elevation of a specific point in the terrain.
		:type data: numpy.ndarray
		:return: None
		"""

		rows, cols = data.shape
		grid = pv.ImageData()
		grid.dimensions = (cols, rows, 1)
		grid.point_data["Elevation"] = data.flatten(order="F").astype(np.float32)

		warped = grid.warp_by_scalar("Elevation")
		self.clear()
		self.add_mesh(warped, cmap="gray", lighting=True, scalar_bar_args={"title": "Elevation (m)"})
		self.add_bounding_box()
		self.add_axes_at_origin()
		self.add_axes(
			xlabel="X",
			ylabel="Y",
			zlabel="Elevation",
			line_width=2,
		)
		self.add_scalar_bar(title="Elevation (m)")
		self.reset_camera()

		self.setStyleSheet("border: 1px solid #cccccc;")
