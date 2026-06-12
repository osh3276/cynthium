import numpy as np
import rasterio
from rasterio.transform import array_bounds
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds


def load_geotif(path):
	with rasterio.open(path) as src:
		data = src.read(1).astype(np.float32)
		meta = {
			"crs": src.crs,
			"transform": src.transform,
			"bounds": src.bounds,
			"resolution": src.res,
		}
	return data, meta


def load_geotif_cropped_to_reference(source_path, reference_path):
	with (
		rasterio.open(reference_path) as reference,
		rasterio.open(source_path) as source,
	):
		bounds = reference.bounds
		if reference.crs and source.crs and reference.crs != source.crs:
			bounds = transform_bounds(
				reference.crs,
				source.crs,
				*reference.bounds,
				densify_pts=21,
			)

		window = from_bounds(*bounds, transform=source.transform)
		window = window.round_offsets().round_lengths()
		if window.width <= 0 or window.height <= 0:
			raise ValueError(
				f"Crop bounds {bounds} do not overlap source raster {source_path}"
			)

		data = source.read(
			1,
			window=window,
			boundless=True,
			fill_value=source.nodata,
		).astype(np.float32)
		transform = source.window_transform(window)
		output_bounds = array_bounds(data.shape[0], data.shape[1], transform)
		meta = {
			"crs": source.crs,
			"transform": transform,
			"bounds": output_bounds,
			"resolution": source.res,
		}
	return data, meta
