import math

import numpy as np
import pyvista
import vtk
from PySide6.QtCore import QTimer
from pyvistaqt import QtInteractor

from cynthium.app.engine.illumination.sun_position import sun_position
from cynthium.app.engine.raster.point_conversion import xy_to_longlat
from cynthium.app.rendering.terrain.render import TerrainRenderer
from cynthium.app.utils.logger import get_logger

logger = get_logger(__name__)

# Offset added to all path/waypoint Z values so they render cleanly above
# the terrain mesh.  Must be large enough to avoid z-fighting at any viewing
# angle.
PATH_ELEVATION_OFFSET_METERS = 5.0


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
		self._resize_timer = QTimer(self)
		self._resize_timer.setSingleShot(True)
		self._resize_timer.timeout.connect(self._render_after_resize)
		self._terrain_mesh = None
		self._loaded_path = None
		self._loaded_utctime = None
		self._waypoint_points = []
		self._waypoint_actors = []
		self._path_actor = None
		self._autopath_actor = None

	def resizeEvent(self, event):
		super().resizeEvent(event)
		self._resize_timer.start(50)

	def _render_after_resize(self):
		if not self.isVisible():
			return
		if self.width() < 2 or self.height() < 2:
			return
		self.render()

	# set the default to today
	def load(self, path: str, utctime: str, data: np.ndarray | None = None, meta: dict | None = None):
		"""
		Loads a terrain dataset and renders it in the view.

		:param path: Path to the GeoTIFF file (used for caching check).
		:param utctime: UTC time string for sun position calculation.
		:param data: Pre-loaded elevation array (if None, loads from path).
		:param meta: Pre-loaded raster metadata.
		:return: None
		"""
		if (
			self._terrain_mesh is not None
			and self._loaded_path == path
			and self._loaded_utctime == utctime
		):
			return

		if data is None:
			from cynthium.app.io.reader import load_geotif
			data, meta = load_geotif(path)
		self._build(data, utctime, meta)
		self._loaded_path = path
		self._loaded_utctime = utctime

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
		self.clear()
		self._autopath_actor = None

		stride = 1
		if meta:
			transform = meta["transform"]
			# Target ~10m/px for the 3D mesh
			source_res = float(abs(transform.a))
			target_res = 10.0
			stride = max(1, int(round(target_res / source_res)))
			if stride > 1:
				data = data[::stride, ::stride]
				logger.info(f"Terrain mesh: decimated by stride={stride} "
					f"({source_res:.1f}m/px → {source_res * stride:.1f}m/px)")

			# Set origin and spacing from the (possibly decimated) data
			# rasterio transform: (a, b, c, d, e, f)
			# x = a * col + b * row + c
			# y = d * col + e * row + f
			# For North-up: b=0, d=0. a=res_x, e=-res_y
			height = data.shape[0]
			self._origin = (transform.c, transform.f + (height * transform.e * stride), 0)
			self._spacing = (abs(transform.a) * stride, abs(transform.e) * stride, 1)
		else:
			self._origin = (0, 0, 0)
			self._spacing = (5 * stride, 5 * stride, 1)

		self._data = data

		mesh = TerrainRenderer(data, origin=self._origin, spacing=self._spacing)
		self._terrain_mesh = mesh

		center_x = self._origin[0] + (data.shape[1] * self._spacing[0]) / 2
		center_y = self._origin[1] + (data.shape[0] * self._spacing[1]) / 2
		center_longlat = xy_to_longlat(center_x, center_y)

		az_deg, _el_deg = sun_position(center_longlat[1], center_longlat[0], utctime)
		el_deg = 20.0

		display_mesh = mesh

		az = np.radians(float(az_deg))
		el = np.radians(float(el_deg))
		sun_dir = np.array(
			[
				np.cos(el) * np.sin(az),
				np.cos(el) * np.cos(az),
				np.sin(el),
			],
			dtype=np.float64,
		)
		sun_dir = sun_dir / np.linalg.norm(sun_dir)

		display_mesh.compute_normals(
			cell_normals=False,
			point_normals=True,
			inplace=True,
		)
		normals = display_mesh.point_data["Normals"]
		hillshade = np.clip(normals @ sun_dir, 0, 1).astype(np.float32)

		display_mesh.point_data["Hillshade"] = hillshade

		self.add_mesh(
			mesh,
			scalars="Hillshade",
			cmap="gray",
			lighting=False,
			show_scalar_bar=False,
		)
		self.show_bounds(
			bounds=mesh.bounds,
			grid="front",
			location="outer",
			all_edges=True,
			font_size=10,
			n_xlabels=12,
			n_ylabels=12,
			n_zlabels=0,
			show_zaxis=False,
			show_zlabels=False,
			color="black",
			render=True,
		)

		self.reset_camera()

		self.setStyleSheet("border: 1px solid #cccccc;")

	def add_waypoint(self, x: float, y: float):
		"""
		Renders a waypoint on the surface of the terrain mesh at (x, y).
		"""
		if self._terrain_mesh is None or self._data is None:
			return

		logger.info(f"add_waypoint called for ({x}, {y})")

		point = self._sample_surface_point(x, y, PATH_ELEVATION_OFFSET_METERS)
		if point is not None:
			sphere = vtk.vtkSphereSource()
			sphere.SetCenter(point)
			sphere.SetRadius(50)
			sphere.Update()

			actor = self.add_mesh(sphere.GetOutput(), color="red", label="Waypoint")
			logger.info(f"Added sphere: {actor}")

			self._waypoint_points.append(point)
			self._waypoint_actors.append(actor)
			self._update_path()
			logger.info(f"Added waypoint at {point}")
		else:
			logger.error("Failed to find waypoint on terrain mesh (out of bounds)")

	def remove_waypoint(self, index: int):
		"""
		Removes a waypoint from the terrain at the given index.
		"""
		if 0 <= index < len(self._waypoint_actors):
			actor = self._waypoint_actors.pop(index)
			self.remove_actor(actor)
			self._waypoint_points.pop(index)
			self._update_path()

	def get_waypoint_3d_points(self):
		"""
		Returns the list of 3D points for all waypoints.
		"""
		return self._waypoint_points

	def get_autopath_3d_points(self) -> list[list[float]]:
		"""
		Returns the 3D points of the autogenerated path.

		:return: List of 3D points.
		"""
		return list(self._autopath_points) if hasattr(self, "_autopath_points") else []

	def set_autopath(self, points_xy: list[tuple[float, float]]):
		if self._autopath_actor is not None:
			self.remove_actor(self._autopath_actor)
			self._autopath_actor = None
		self._autopath_points = []

		if not points_xy or len(points_xy) < 2:
			return

		# Sample along each segment at terrain resolution so the line follows
		# the terrain surface instead of cutting straight through ridges.
		if not hasattr(self, "_spacing"):
			self._spacing = (5.0, 5.0, 1.0)
		resolution = min(self._spacing[0], self._spacing[1])
		path_points: list[list[float]] = []
		for i in range(len(points_xy) - 1):
			x0, y0 = points_xy[i]
			x1, y1 = points_xy[i + 1]
			dx = float(x1 - x0)
			dy = float(y1 - y0)
			dist = math.hypot(dx, dy)
			samples = max(1, int(math.ceil(dist / resolution)))
			for j in range(samples + 1):
				if i > 0 and j == 0:
					continue  # skip duplicates at segment joins
				frac = j / samples
				x = float(x0 + dx * frac)
				y = float(y0 + dy * frac)
				pt = self._sample_surface_point(x, y, PATH_ELEVATION_OFFSET_METERS)
				if pt is not None:
					path_points.append(pt)

		if len(path_points) < 2:
			return

		self._autopath_points = list(path_points)

		path = pyvista.MultipleLines(points=np.array(path_points))
		self._autopath_actor = self.add_mesh(
			path,
			color="blue",
			line_width=4,
			label="Autopath",
		)

	def _update_path(self):
		"""
		Updates the 3D path connecting the waypoints.
		"""
		if self._path_actor is not None:
			self.remove_actor(self._path_actor)
			self._path_actor = None

		if len(self._waypoint_points) < 2:
			return

		path_points = self._sample_path_surface_points()
		if len(path_points) < 2:
			return

		path = pyvista.MultipleLines(points=np.array(path_points))
		self._path_actor = self.add_mesh(
			path, color="yellow", line_width=3, label="Path"
		)

	def _sample_path_surface_points(self) -> list[list[float]]:
		path_points = []
		resolution = min(self._spacing[0], self._spacing[1])

		for index in range(len(self._waypoint_points) - 1):
			start = np.array(self._waypoint_points[index][:2], dtype=float)
			end = np.array(self._waypoint_points[index + 1][:2], dtype=float)
			distance = float(np.linalg.norm(end - start))
			sample_count = max(1, int(np.ceil(distance / resolution)))

			for sample_index in range(sample_count + 1):
				if index > 0 and sample_index == 0:
					continue

				fraction = sample_index / sample_count
				x, y = start + fraction * (end - start)
				point = self._sample_surface_point(
					float(x),
					float(y),
					PATH_ELEVATION_OFFSET_METERS,
				)
				if point is not None:
					path_points.append(point)

		return path_points

	def _sample_surface_point(
		self,
		x: float,
		y: float,
		z_offset: float = 0.0,
	) -> list[float] | None:
		if self._data is None:
			return None

		col = (x - self._origin[0]) / self._spacing[0]
		row_from_bottom = (y - self._origin[1]) / self._spacing[1]
		data_row = (self._data.shape[0] - 1) - row_from_bottom

		if (
			col < 0
			or data_row < 0
			or col > self._data.shape[1] - 1
			or data_row > self._data.shape[0] - 1
		):
			return None

		z = self._sample_elevation_bilinear(data_row, col)
		if not np.isfinite(z):
			return None

		return [x, y, float(z + z_offset)]

	def _sample_elevation_bilinear(self, row: float, col: float) -> float:
		row0 = int(np.floor(row))
		col0 = int(np.floor(col))
		row1 = min(row0 + 1, self._data.shape[0] - 1)
		col1 = min(col0 + 1, self._data.shape[1] - 1)
		row_weight = row - row0
		col_weight = col - col0

		z00 = self._data[row0, col0]
		z01 = self._data[row0, col1]
		z10 = self._data[row1, col0]
		z11 = self._data[row1, col1]
		values = np.array([z00, z01, z10, z11], dtype=float)
		if not np.all(np.isfinite(values)):
			return float(np.nanmean(values))

		z0 = z00 * (1 - col_weight) + z01 * col_weight
		z1 = z10 * (1 - col_weight) + z11 * col_weight
		return float(z0 * (1 - row_weight) + z1 * row_weight)

	def mouseDoubleClickEvent(self, event):
		pass
