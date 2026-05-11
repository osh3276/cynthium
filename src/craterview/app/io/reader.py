import rasterio
import numpy as np

def load_geotif(path):
	with rasterio.open(path) as src:
		data = src.read(1).astype(np.float32)
		meta = {
			"crs": src.crs,
			"transform": src.transform,
			"bounds": src.bounds,
			"resolution": src.res
		}
	return data, meta