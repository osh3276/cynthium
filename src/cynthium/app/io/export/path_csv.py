import csv
from pathlib import Path

import numpy as np


def write_path_csv(
	path: str | Path,
	points_3d: list[tuple[float, float, float]] | list[list[float]] | np.ndarray,
	*,
	metadata: dict[str, str] | None = None,
	pause_durations: list[float] | None = None,
):
	"""Write 3D waypoints / autopath points to a CSV file.

	Parameters
	----------
	path :
		Output file path.
	points_3d :
		Sequence of (x, y, z) tuples or an Nx3 array.
	metadata :
		Optional key/value pairs written at the top of the CSV.
	pause_durations :
		Optional list of pause durations (seconds) at each waypoint.
		Length should be len(points_3d) - 1 (pause at destination of each leg).
		The first waypoint (start) always gets 0.
	"""
	with open(path, "w", newline="") as f:
		writer = csv.writer(f)

		if metadata:
			writer.writerow(["metadata_key", "metadata_value"])
			for k, v in metadata.items():
				writer.writerow([k, v])
			writer.writerow([])

		writer.writerow(["index", "x", "y", "z", "pause_s"])
		for i, pt in enumerate(points_3d, start=1):
			pause = float(pause_durations[i - 2]) if pause_durations and i > 1 and (i - 2) < len(pause_durations) else 0.0
			writer.writerow([i, float(pt[0]), float(pt[1]), float(pt[2]), pause])
