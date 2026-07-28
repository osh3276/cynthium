import pyvista
import numpy as np
from pyvista import PolyData

from cynthium.app.engine.illumination.sun_position import sun_position

def arrow_mesh(tip_point, length=100.0, shaft_radius=50, tip_radius=100):
	"""Create an arrow whose tip is at `tip_point` pointing downward (-z)."""
	direction = np.array([0, 0, -1])  # downward
	start_point = tip_point - direction * length  # start above the tip
	arrow = pyvista.Arrow(start=start_point, direction=direction,
						  scale=length, shaft_radius=shaft_radius,
						  tip_radius=tip_radius)
	return arrow


class TerrainRenderer(PolyData):
	def __init__(
		self, data: np.ndarray, origin: tuple = (0, 0, 0), spacing: tuple = (5, 5, 1)
	):
		"""Build a PyVista ImageData mesh from the elevation raster."""
		grid = pyvista.ImageData()
		grid.dimensions = (data.shape[1], data.shape[0], 1)
		grid.origin = origin
		grid.spacing = spacing
		grid.point_data["Elevation"] = np.flipud(data).flatten(order="C").astype(np.float32)

		warped = grid.warp_by_scalar("Elevation").extract_surface(algorithm="dataset_surface")
		super().__init__(warped)
		self.compute_normals(
			cell_normals=False,
			point_normals=True,
			inplace=True
		)

	def compute_hillshade(self, utctime: str, center_longlat: tuple = (-89, 0)):
		"""Compute hillshade from sun position at the given time and location."""
		az, _el = sun_position(center_longlat[1], center_longlat[0], utctime)

		az = np.radians(az)
		el = np.radians(20.0)

		sun_dir = np.array([
			np.cos(el) * np.sin(az),
			np.cos(el) * np.cos(az),
			np.sin(el)
		])
		sun_dir = sun_dir / np.linalg.norm(sun_dir)

		if "Normals" not in self.point_data:
			self.compute_normals(
				cell_normals=False,
				point_normals=True,
				inplace=True
			)

		normals = self.point_data["Normals"]
		self.point_data["Hillshade"] = np.clip(normals @ sun_dir, 0, 1)
