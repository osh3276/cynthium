import math
import re
from pathlib import Path

import numpy as np

from cynthium.app.config import (
	AVERAGE_TEMPERATURE_RASTER_PATH,
	ILLUMINATION_ANGLES_DIR,
	ILLUMINATION_RASTER_PATH,
	METEOR_ANGLES_DIR,
	METEOR_FLUX_RASTER_PATH,
	ensure_data_file_path,
	get_slope_path,
	resolve_data_file_path,
)
from cynthium.app.engine.illumination.sun_position import sun_position
from cynthium.app.engine.raster.point_conversion import xy_to_longlat
from cynthium.app.io.reader import load_geotif, load_geotif_cropped_to_reference
from cynthium.app.utils.logger import get_logger

logger = get_logger(__name__)

RasterPayload = tuple[np.ndarray | None, dict | None]


def load_slope_raster(elevation_path: str) -> RasterPayload:
	"""
	Loads the slope raster.

	:param elevation_path: Path to the elevation raster.
	:type elevation_path: str
	:return: The resulting value.
	"""
	slope_path = ensure_data_file_path(get_slope_path(elevation_path))
	if slope_path.exists():
		data, meta = load_geotif(str(slope_path))
		logger.info(f"Loaded slope map: {slope_path}")
		return data, meta

	logger.warning(f"No slope map found for {elevation_path}. Expected: {slope_path}")
	return None, None


def load_context_rasters(reference_path: str) -> tuple[RasterPayload, RasterPayload, RasterPayload]:
	"""
	Loads the context rasters: illumination, temperature, and meteor flux.

	:param reference_path: Path to the reference file.
	:type reference_path: str
	:return: Tuple of (illumination, temperature, meteor_flux) payloads.
	"""
	illumination = load_cropped_context_raster(
		ILLUMINATION_RASTER_PATH,
		reference_path,
		"illumination",
	)
	temperature = load_cropped_context_raster(
		AVERAGE_TEMPERATURE_RASTER_PATH,
		reference_path,
		"temperature",
	)
	meteor_flux = load_cropped_context_raster(
		METEOR_FLUX_RASTER_PATH,
		reference_path,
		"meteor_flux",
	)
	return illumination, temperature, meteor_flux


def _round_azimuth_deg_to_nearest_12(azimuth_deg: float) -> int:
	az = float(azimuth_deg) % 360.0
	angle = int(math.floor((az + 6.0) / 12.0)) * 12
	angle = angle % 360
	return 360 if angle == 0 else angle


def load_daily_avg_illumination_raster(
	*,
	reference_path: str,
	reference_meta: dict | None,
	reference_shape: tuple[int, int],
	utctime: str,
) -> RasterPayload:
	"""Load a daily-avg illumination map by snapping sun azimuth to 12° bins.

	- Computes sun azimuth for the *center* of the reference raster at `utctime`.
	- Rounds to the nearest multiple of 12 degrees.
	- Loads `data/illum/angles/illum_angle_{bin}.tif` cropped to the reference raster.
	"""
	if not reference_meta or "transform" not in reference_meta:
		logger.warning("Cannot compute daily illumination: reference raster has no transform")
		return None, None

	transform = reference_meta["transform"]
	rows, cols = int(reference_shape[0]), int(reference_shape[1])
	center_x = float(transform.c + (0.5 * cols * transform.a) + (0.5 * rows * transform.b))
	center_y = float(transform.f + (0.5 * cols * transform.d) + (0.5 * rows * transform.e))
	center_lon, center_lat = xy_to_longlat(center_x, center_y)

	time_for_az = utctime
	if "T" in utctime:
		time_for_az = f"{utctime.split('T', 1)[0]}T12:00:00"

	az_deg, _el_deg = sun_position(float(center_lat), float(center_lon), time_for_az)
	angle_deg = _round_azimuth_deg_to_nearest_12(float(az_deg))
	angle_path = ensure_data_file_path(
		resolve_data_file_path(ILLUMINATION_ANGLES_DIR / f"illum_angle_{angle_deg}.tif")
	)

	if not angle_path.exists():
		logger.warning(f"Missing daily illumination angle raster: {angle_path}")
		return None, None

	try:
		data, meta = load_geotif_cropped_to_reference(str(angle_path), reference_path)
	except ValueError as exc:
		logger.warning(f"Failed to crop daily illumination raster {angle_path}: {exc}")
		return None, None

	logger.info(
		f"Daily illumination: azimuth={float(az_deg):.2f}°, snapped={angle_deg}°, raster={angle_path.name}"
	)
	return data, meta


def load_daily_avg_meteor_raster(
	*,
	reference_path: str,
	reference_meta: dict | None,
	reference_shape: tuple[int, int],
	utctime: str,
) -> RasterPayload:
	"""Load a daily-avg meteor flux map by snapping sun azimuth to 12° bins.

	- Computes sun azimuth for the *center* of the reference raster at `utctime`.
	- Rounds to the nearest multiple of 12 degrees.
	- Loads `data/meteor/angles/meteor_angle_{bin}.tif` cropped to the reference raster.
	"""
	if not reference_meta or "transform" not in reference_meta:
		logger.warning("Cannot compute daily meteor flux: reference raster has no transform")
		return None, None

	transform = reference_meta["transform"]
	rows, cols = int(reference_shape[0]), int(reference_shape[1])
	center_x = float(transform.c + (0.5 * cols * transform.a) + (0.5 * rows * transform.b))
	center_y = float(transform.f + (0.5 * cols * transform.d) + (0.5 * rows * transform.e))
	center_lon, center_lat = xy_to_longlat(center_x, center_y)

	time_for_az = utctime
	if "T" in utctime:
		time_for_az = f"{utctime.split('T', 1)[0]}T12:00:00"

	az_deg, _el_deg = sun_position(float(center_lat), float(center_lon), time_for_az)
	angle_deg = _round_azimuth_deg_to_nearest_12(float(az_deg))
	angle_path = ensure_data_file_path(
		resolve_data_file_path(METEOR_ANGLES_DIR / f"meteor_angle_{angle_deg}.tif")
	)

	if not angle_path.exists():
		logger.warning(f"Missing daily meteor angle raster: {angle_path}")
		return None, None

	try:
		data, meta = load_geotif_cropped_to_reference(str(angle_path), reference_path)
	except ValueError as exc:
		logger.warning(f"Failed to crop daily meteor raster {angle_path}: {exc}")
		return None, None

	logger.info(
		f"Daily meteor flux: azimuth={float(az_deg):.2f}°, snapped={angle_deg}°, raster={angle_path.name}"
	)
	return data, meta


def load_cropped_context_raster(
	source_path: Path,
	reference_path: str,
	label: str,
) -> RasterPayload:
	"""
	Loads the cropped context raster.

	:param source_path: Path to the source file.
	:type source_path: Path
	:param reference_path: Path to the reference file.
	:type reference_path: str
	:param label: Label text.
	:type label: str
	:return: The resulting value.
	"""
	source_path = ensure_data_file_path(resolve_data_file_path(source_path))
	if not source_path.exists():
		logger.warning(f"Missing {label} raster: {source_path}")
		return None, None

	try:
		data, meta = load_geotif_cropped_to_reference(str(source_path), reference_path)
	except ValueError as exc:
		logger.warning(f"Failed to crop {label} raster: {exc}")
		return None, None

	logger.info(f"Loaded cropped {label} raster from {source_path}")
	return data, meta


def _normalize_map_key(map_type: str) -> str:
	key = map_type.strip().lower()
	key = re.sub(r"[^a-z0-9]+", "_", key)
	key = re.sub(r"_+", "_", key).strip("_")
	return key


def select_display_raster(
	map_type: str,
	elevation: RasterPayload,
	slope: RasterPayload,
	illumination: RasterPayload,
	temperature: RasterPayload,
	meteor_flux: RasterPayload = (None, None),
) -> RasterPayload:
	"""
	Selects the display raster.

	:param map_type: Map type identifier.
	:type map_type: str
	:param elevation: Parameter value.
	:type elevation: RasterPayload
	:param slope: Parameter value.
	:type slope: RasterPayload
	:param illumination: Parameter value.
	:type illumination: RasterPayload
	:param temperature: Parameter value.
	:type temperature: RasterPayload
	:return: The resulting value.
	"""
	map_key = _normalize_map_key(map_type)

	if map_key == "slope":
		return _fallback_if_missing(slope, elevation, "Slope")

	if map_key == "hillshade":
		return elevation

	if map_key == "solar_illumination" or map_key.startswith("solar_illumination_"):
		return _fallback_if_missing(illumination, elevation, "Illumination")

	if map_key == "average_temperature":
		return _fallback_if_missing(temperature, elevation, "Temperature")

	if map_key.startswith("meteor_flux"):
		return _fallback_if_missing(meteor_flux, elevation, "Meteor Flux")

	return elevation


def _fallback_if_missing(
	requested: RasterPayload,
	fallback: RasterPayload,
	label: str,
) -> RasterPayload:
	"""
	Performs fallback if missing.

	:param requested: Parameter value.
	:type requested: RasterPayload
	:param fallback: Parameter value.
	:type fallback: RasterPayload
	:param label: Label text.
	:type label: str
	:return: The resulting value.
	"""
	data, meta = requested
	if data is None:
		logger.warning(f"{label} map was requested, but it is unavailable.")
		return fallback

	return data, meta or fallback[1]
