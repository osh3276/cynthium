import pyvista
import numpy as np
from pyvista import PolyData

from craterview.app.engine.illumination.sun_position import sun_position


class TerrainRenderer(PolyData):
	def __init__(self, data: np.ndarray, origin: tuple = (0, 0, 0), spacing: tuple = (5, 5, 1)):
		grid = pyvista.ImageData()
		grid.dimensions = (data.shape[1], data.shape[0], 1)
		grid.origin = origin
		grid.spacing = spacing
		grid.point_data["Elevation"] = data.flatten(order="F").astype(np.float32)

		warped = grid.warp_by_scalar("Elevation").extract_surface(algorithm="dataset_surface")
		super().__init__(warped)
		self.compute_normals(
			cell_normals=False,
			point_normals=True,
			inplace=True
		)

	def compute_hillshade(self, utctime: str, center_longlat: tuple = (-89, 0)):
		az, el = sun_position(center_longlat[1], center_longlat[0], utctime)

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