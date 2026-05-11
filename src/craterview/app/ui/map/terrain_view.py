import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor

from craterview.app.io.reader import load_geotif

import vtk

class CustomInteractorStyle(vtk.vtkInteractorStyleTrackballCamera):
    def __init__(self):
        self.AddObserver("LeftButtonPressEvent", self.on_left_press)
        self.AddObserver("LeftButtonReleaseEvent", self.on_left_release)
        self.AddObserver("RightButtonPressEvent", self.on_right_press)
        self.AddObserver("RightButtonReleaseEvent", self.on_right_release)
        self.AddObserver("MiddleButtonPressEvent", lambda o, e: None)
        self.AddObserver("MiddleButtonReleaseEvent", lambda o, e: None)

    def on_left_press(self, obj, event):
        self.StartPan()

    def on_left_release(self, obj, event):
        self.EndPan()

    def on_right_press(self, obj, event):
        self.StartRotate()

    def on_right_release(self, obj, event):
        self.EndRotate()


class TerrainView(QtInteractor):
	def __init__(self, parent=None):
		super().__init__(parent=parent)
		self.interactor.SetInteractorStyle(CustomInteractorStyle())

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

		# TODO: Change to accommodate different resolutions
		grid.spacing = (5, 5, 1) # (mpp, mpp, 1)

		warped = grid.warp_by_scalar("Elevation")
		warped = warped.extract_surface()

		mesh = warped.compute_normals(cell_normals=False, point_normals=True)
		sun_dir = np.array([-1, -1, 2])  # adjust azimuth/elevation here
		sun_dir = sun_dir / np.linalg.norm(sun_dir)
		normals = mesh.point_data["Normals"]
		hillshade = np.clip(normals @ sun_dir, 0, 1)
		mesh.point_data["Hillshade"] = hillshade
		self.add_mesh(mesh, scalars="Hillshade", cmap="gray", lighting=False, show_scalar_bar=False)
		# self.add_scalar_bar(title="Elevation (m)", font_family="Times")
		self.add_bounding_box()

		axes = pv.CubeAxesActor(camera=self.camera)
		self.show_grid(
			n_xlabels=12,
			n_ylabels=12,
		)
		self.reset_camera()

		self.setStyleSheet("border: 1px solid #cccccc;")
