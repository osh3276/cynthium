from pathlib import Path

import numpy as np

from craterview.app.config import (
	AVERAGE_TEMPERATURE_RASTER_PATH,
	ILLUMINATION_RASTER_PATH,
	get_slope_path,
)
from craterview.app.io.reader import load_geotif, load_geotif_cropped_to_reference
from craterview.app.utils.logger import get_logger

logger = get_logger(__name__)

RasterPayload = tuple[np.ndarray | None, dict | None]


def load_slope_raster(elevation_path: str) -> RasterPayload:
	"""
	Loads the slope raster.

	:param elevation_path: Path to the elevation raster.
	:type elevation_path: str
	:return: The resulting value.
	"""
	slope_path = get_slope_path(elevation_path)
	if slope_path.exists():
		data, meta = load_geotif(str(slope_path))
		logger.info(f"Loaded slope map: {slope_path}")
		return data, meta

	logger.warning(f"No slope map found for {elevation_path}. Expected: {slope_path}")
	return None, None


def load_context_rasters(reference_path: str) -> tuple[RasterPayload, RasterPayload]:
	"""
	Loads the context rasters.

	:param reference_path: Path to the reference file.
	:type reference_path: str
	:return: The resulting value.
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
	return illumination, temperature


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
	if not source_path.exists():
		logger.warning(f"Missing {label} raster: {source_path}")
		return None, None

	try:
		data, meta = load_geotif_cropped_to_reference(source_path, reference_path)
	except ValueError as exc:
		logger.warning(f"Failed to crop {label} raster: {exc}")
		return None, None

	logger.info(f"Loaded cropped {label} raster from {source_path}")
	return data, meta


def select_display_raster(
	map_type: str,
	elevation: RasterPayload,
	slope: RasterPayload,
	illumination: RasterPayload,
	temperature: RasterPayload,
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
	map_key = map_type.strip().lower().replace(" ", "_")

	if map_key == "slope":
		return _fallback_if_missing(slope, elevation, "Slope")

	if map_key == "hillshade":
		return elevation

	if map_key == "solar_illumination":
		return _fallback_if_missing(illumination, elevation, "Illumination")

	if map_key == "average_temperature":
		return _fallback_if_missing(temperature, elevation, "Temperature")

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
