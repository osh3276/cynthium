import numpy as np
import vtk
from pyvistaqt import QtInteractor

from craterview.app.engine.raster.point_conversion import xy_to_longlat
from craterview.app.io.reader import load_geotif
from craterview.app.rendering.terrain.render import TerrainRenderer


class CustomInteractorStyle(vtk.vtkInteractorStyleTrackballCamera):
	def __init__(self):
		self.AddObserver("LeftButtonDoubleClickEvent", self.on_left_double_click)
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

	def on_left_double_click(self, obj, event):
		pass


class TerrainView(QtInteractor):
	def __init__(self, parent=None):
		super().__init__(parent=parent)
		self.interactor.SetInteractorStyle(CustomInteractorStyle())

	# set the default to today
	def load(self, path: str, utctime: str):
		data, meta = load_geotif(path)
		self._build(data, utctime, meta)

	def _build(self, data: np.ndarray, utctime: str, meta: dict = None):
		"""
		Renders a digital elevation model (DEM) from the input data.

		:param data: A 2D numpy array containing elevation values. Each value in the
			array represents the elevation of a specific point in the terrain.
		:type data: numpy.ndarray
		:param utctime: UTC time string for sun position calculation.
		:param meta: Metadata from GeoTIFF including transform and resolution.
		:return: None
		"""
		origin = (0, 0, 0)
		spacing = (5, 5, 1)

		if meta:
			# rasterio transform: (a, b, c, d, e, f)
			# x = a * col + b * row + c
			# y = d * col + e * row + f
			# For North-up: b=0, d=0. a=res_x, e=-res_y (usually)
			transform = meta["transform"]
			origin = (transform.c, transform.f, 0)
			spacing = (abs(transform.a), abs(transform.e), 1)

		mesh = TerrainRenderer(data, origin=origin, spacing=spacing)

		center_x = origin[0] + (data.shape[1] * spacing[0]) / 2
		center_y = origin[1] + (data.shape[0] * spacing[1]) / 2
		center_longlat = xy_to_longlat(center_x, center_y)

		mesh.compute_hillshade(utctime, center_longlat=center_longlat)
		self.add_mesh(mesh, scalars="Hillshade", cmap="gray", lighting=False, show_scalar_bar=False)
		self.add_bounding_box()

		self.show_grid(
			font_size=10,
			n_xlabels=12,
			n_ylabels=12,
		)

		self.reset_camera()

		self.setStyleSheet("border: 1px solid #cccccc;")

	def mouseDoubleClickEvent(self, event):
		pass
