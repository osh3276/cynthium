import pyvista
import numpy as np
from pyvista import PolyData

from craterview.app.rendering.terrain.sun_position import sun_position_from_moon


class TerrainRenderer(PolyData):
	def __init__(self, data: np.ndarray, spacing: tuple = (5, 5, 1)):
		grid = pyvista.ImageData()
		grid.dimensions = (data.shape[1], data.shape[0], 1)
		grid.point_data["Elevation"] = data.flatten(order="F").astype(np.float32)
		grid.spacing = (5, 5, 1)

		warped = grid.warp_by_scalar("Elevation").extract_surface()
		super().__init__(warped)
		self.compute_normals(
			cell_normals=False,
			point_normals=True,
			inplace=True
		)

	def compute_hillshade(self, utctime: str):
		az, el = sun_position_from_moon(-89, 0, utctime)

		az = np.radians(az)
		el = np.radians(el)

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