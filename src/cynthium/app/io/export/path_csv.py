import csv
from pathlib import Path

import numpy as np


def write_path_csv(
	path: str | Path,
	points_3d: list[tuple[float, float, float]] | list[list[float]] | np.ndarray,
	*,
	label: str = "path",
	metadata: dict[str, str] | None = None,
):
	"""Write 3D waypoints / autopath points to a CSV file.

	Parameters
	----------
	path :
		Output file path.
	points_3d :
		Sequence of (x, y, z) tuples or an Nx3 array.
	label :
		Descriptive label written in the header (e.g. "manual" or "auto").
	metadata :
		Optional key/value pairs written at the top of the CSV.
	"""
	with open(path, "w", newline="") as f:
		writer = csv.writer(f)

		if metadata:
			writer.writerow(["metadata_key", "metadata_value"])
			for k, v in metadata.items():
				writer.writerow([k, v])
			writer.writerow([])

		writer.writerow(["index", "x", "y", "z"])
		for i, pt in enumerate(points_3d, start=1):
			writer.writerow([i, float(pt[0]), float(pt[1]), float(pt[2])])
