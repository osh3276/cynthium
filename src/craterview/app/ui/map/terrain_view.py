import numpy as np
import pyvista as pv
from PySide6.QtWidgets import QWidget
from pyvistaqt import QtInteractor

from craterview.app.io.reader import load_geotif

import vtk

from craterview.app.rendering.terrain.render import TerrainRenderer

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

	# set the default to today
	def load(self, path: str, utctime: str):
		data, meta = load_geotif(path)
		self._build(data, utctime)

	def _build(self, data: np.ndarray, utctime: str):
		"""
		Renders a digital elevation model (DEM) from the input data.

		:param data: A 2D numpy array containing elevation values. Each value in the
			array represents the elevation of a specific point in the terrain.
		:type data: numpy.ndarray
		:return: None
		"""
		mesh = TerrainRenderer(data)
		mesh.compute_hillshade(utctime)
		self.add_mesh(mesh, scalars="Hillshade", cmap="gray", lighting=False, show_scalar_bar=False)
		self.add_bounding_box()

		self.show_grid(
			font_size=10,
			n_xlabels=12,
			n_ylabels=12,
		)

		self.reset_camera()

		self.setStyleSheet("border: 1px solid #cccccc;")
