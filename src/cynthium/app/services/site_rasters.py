import re
from pathlib import Path

import numpy as np

from cynthium.app.config import (
	AVERAGE_TEMPERATURE_RASTER_PATH,
	DATA_ROOT,
	ILLUMINATION_ANGLES_DIR,
	ILLUMINATION_RASTER_PATH,
	METEOR_ANGLES_DIR,
	METEOR_FLUX_RASTER_PATH,
	METEOR_NUMBER_RASTER_PATH,
	NUM_ANGLE_BINS,
	PSR_RASTER_PATH,
	ANGLE_BIN_DEG,
	ensure_data_file_path,
	get_slope_path,
	resolve_data_file_path,
)
from cynthium.app.engine.illumination.sun_position import (
	round_azimuth_to_nearest_12,
	sun_position,
)
from cynthium.app.engine.raster.point_conversion import xy_to_longlat
from cynthium.app.io.reader import load_geotif, load_geotif_cropped_to_reference
from cynthium.app.utils.logger import get_logger

logger = get_logger(__name__)

RasterPayload = tuple[np.ndarray | None, dict | None]


def load_slope_raster(elevation_path: str) -> RasterPayload:
	"""Load slope raster for an elevation path."""
	slope_path = ensure_data_file_path(get_slope_path(elevation_path))
	if slope_path.exists():
		data, meta = load_geotif(str(slope_path))
		logger.info(f"Loaded slope map: {slope_path}")
		return data, meta

	logger.warning(f"No slope map found for {elevation_path}. Expected: {slope_path}")
	return None, None


def _select_temperature_raster(utctime: str | None = None) -> Path:
	"""Select summer or winter temperature raster based on lunar season."""
	from cynthium.app.config import WINTER_TEMPERATURE_RASTER_PATH

	if utctime is None:
		return AVERAGE_TEMPERATURE_RASTER_PATH

	try:
		from cynthium.app.engine.illumination.sun_position import sub_solar_latitude
		sub_lat = sub_solar_latitude(utctime)
		is_summer = sub_lat < 0.0  # sun in southern hemisphere
		logger.info(
			f"Lunar sub-solar latitude: {sub_lat:.2f}° → "
			f"{'summer' if is_summer else 'winter'} at south pole"
		)
		return AVERAGE_TEMPERATURE_RASTER_PATH if is_summer else WINTER_TEMPERATURE_RASTER_PATH
	except Exception as exc:
		logger.warning(f"Could not determine lunar season, defaulting to summer: {exc}")
		return AVERAGE_TEMPERATURE_RASTER_PATH


def load_context_rasters(
	reference_path: str,
	utctime: str | None = None,
) -> tuple[RasterPayload, RasterPayload, RasterPayload]:
	"""Load illumination, temperature, and meteor flux rasters, cropped to reference."""
	illumination = load_cropped_context_raster(
		ILLUMINATION_RASTER_PATH,
		reference_path,
		"illumination",
	)
	temperature_path = _select_temperature_raster(utctime)
	temperature = load_cropped_context_raster(
		temperature_path,
		reference_path,
		"temperature",
	)
	meteor_flux = load_cropped_context_raster(
		METEOR_FLUX_RASTER_PATH,
		reference_path,
		"meteor_flux",
	)
	return illumination, temperature, meteor_flux





def load_daily_avg_illumination_raster(
	*,
	reference_path: str,
	reference_meta: dict | None,
	reference_shape: tuple[int, int],
	utctime: str,
) -> RasterPayload:
	"""Load daily-avg illumination raster by snapping sun azimuth to 12 deg bins."""
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
	angle_deg = round_azimuth_to_nearest_12(float(az_deg))
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


def _load_daily_avg_angle_raster(
	*,
	reference_path: str,
	reference_meta: dict | None,
	reference_shape: tuple[int, int],
	utctime: str,
	angle_dir: Path,
	angle_prefix: str,
	label: str,
) -> RasterPayload:
	"""Load a daily-avg raster by snapping sun azimuth to 12 deg bins."""
	if not reference_meta or "transform" not in reference_meta:
		logger.warning(f"Cannot compute daily {label}: reference raster has no transform")
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
	angle_deg = round_azimuth_to_nearest_12(float(az_deg))
	angle_path = ensure_data_file_path(
		resolve_data_file_path(angle_dir / f"{angle_prefix}_{angle_deg}.tif")
	)

	if not angle_path.exists():
		logger.warning(f"Missing daily {label} angle raster: {angle_path}")
		return None, None

	try:
		data, meta = load_geotif_cropped_to_reference(str(angle_path), reference_path)
	except ValueError as exc:
		logger.warning(f"Failed to crop daily {label} raster {angle_path}: {exc}")
		return None, None

	logger.info(
		f"Daily {label}: azimuth={float(az_deg):.2f}°, snapped={angle_deg}°, raster={angle_path.name}"
	)
	return data, meta


def load_daily_avg_meteor_raster(
	*,
	reference_path: str,
	reference_meta: dict | None,
	reference_shape: tuple[int, int],
	utctime: str,
) -> RasterPayload:
	"""Load a daily-avg meteor flux map by snapping sun azimuth to 12 deg bins."""
	return _load_daily_avg_angle_raster(
		reference_path=reference_path,
		reference_meta=reference_meta,
		reference_shape=reference_shape,
		utctime=utctime,
		angle_dir=METEOR_ANGLES_DIR,
		angle_prefix="meteor_energy_angle",
		label="meteor flux",
	)


def load_daily_avg_meteor_number_raster(
	*,
	reference_path: str,
	reference_meta: dict | None,
	reference_shape: tuple[int, int],
	utctime: str,
) -> RasterPayload:
	"""Load a daily-avg meteor number map by snapping sun azimuth to 12 deg bins."""
	return _load_daily_avg_angle_raster(
		reference_path=reference_path,
		reference_meta=reference_meta,
		reference_shape=reference_shape,
		utctime=utctime,
		angle_dir=DATA_ROOT,
		angle_prefix="meteor_number_angle",
		label="meteor number",
	)


def load_angle_maps(
	*,
	reference_path: str,
	reference_meta: dict | None,
	reference_shape: tuple[int, int],
	utctime: str,
) -> tuple[
	dict[int, RasterPayload] | None,
	dict[int, RasterPayload] | None,
	dict[int, RasterPayload] | None,
	int,
	float | None,
	float | None,
	float | None,
]:
	"""Load all 30 angle maps for illumination, meteor energy, and meteor number."""
	import spiceypy as spice

	if not reference_meta or "transform" not in reference_meta:
		return None, None, None, 0, None, None, None

	transform = reference_meta["transform"]
	rows, cols = int(reference_shape[0]), int(reference_shape[1])
	center_x = float(transform.c + (0.5 * cols * transform.a) + (0.5 * rows * transform.b))
	center_y = float(transform.f + (0.5 * cols * transform.d) + (0.5 * rows * transform.e))
	center_lon, center_lat = xy_to_longlat(center_x, center_y)

	time_for_az = utctime
	if "T" in utctime:
		time_for_az = f"{utctime.split('T', 1)[0]}T12:00:00"

	az_deg, _el_deg = sun_position(float(center_lat), float(center_lon), time_for_az)
	start_angle_deg = round_azimuth_to_nearest_12(float(az_deg))

	# SPICE ephemeris time at sim start
	from cynthium.app.engine.illumination.sun_position import _ensure_kernels_loaded
	_ensure_kernels_loaded()
	start_et = spice.utc2et(utctime)

	logger.info(
		f"Loading angle maps: start azimuth={float(az_deg):.2f}°, "
		f"start bin={start_angle_deg}°"
	)

	illum_maps: dict[int, RasterPayload] = {}
	meteor_energy_maps: dict[int, RasterPayload] = {}
	meteor_number_maps: dict[int, RasterPayload] = {}

	for bin_angle in range(0, 360, ANGLE_BIN_DEG):
		# Illumination
		il_path = ensure_data_file_path(
			resolve_data_file_path(ILLUMINATION_ANGLES_DIR / f"illum_angle_{bin_angle}.tif")
		)
		if il_path.exists():
			try:
				data, meta = load_geotif_cropped_to_reference(str(il_path), reference_path)
				illum_maps[bin_angle] = (data, meta)
			except ValueError as exc:
				logger.warning(f"Failed to crop illum angle {bin_angle}: {exc}")

		me_path = ensure_data_file_path(
			resolve_data_file_path(METEOR_ANGLES_DIR / f"meteor_energy_angle_{bin_angle}.tif")
		)
		if me_path.exists():
			try:
				data, meta = load_geotif_cropped_to_reference(str(me_path), reference_path)
				meteor_energy_maps[bin_angle] = (data, meta)
			except ValueError as exc:
				logger.warning(f"Failed to crop meteor energy angle {bin_angle}: {exc}")

		mn_path = ensure_data_file_path(
			resolve_data_file_path(DATA_ROOT / f"meteor_number_angle_{bin_angle}.tif")
		)
		if mn_path.exists():
			try:
				data, meta = load_geotif_cropped_to_reference(str(mn_path), reference_path)
				meteor_number_maps[bin_angle] = (data, meta)
			except ValueError as exc:
				logger.warning(f"Failed to crop meteor number angle {bin_angle}: {exc}")

	illum_out = illum_maps if illum_maps else None
	meteor_e_out = meteor_energy_maps if meteor_energy_maps else None
	meteor_n_out = meteor_number_maps if meteor_number_maps else None

	logger.info(
		f"Loaded {len(illum_maps)} illum, {len(meteor_energy_maps)} meteor energy, "
		f"{len(meteor_number_maps)} meteor number angle maps"
	)
	return illum_out, meteor_e_out, meteor_n_out, start_angle_deg, center_lat, center_lon, start_et



def load_psr_raster(reference_path: str) -> RasterPayload:
	"""Load the permanently shaded regions raster, cropped to the reference."""
	return load_cropped_context_raster(
		PSR_RASTER_PATH, reference_path, "psr"
	)


def load_cropped_context_raster(
	source_path: Path,
	reference_path: str,
	label: str,
) -> RasterPayload:
	"""Load a raster cropped to match a reference raster's bounds."""
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
	meteor_number: RasterPayload = (None, None),
	psr: RasterPayload = (None, None),
) -> RasterPayload:
	"""Select the correct raster for display based on map type, with fallbacks."""
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

	if map_key.startswith("meteor_number"):
		return _fallback_if_missing(meteor_number, elevation, "Meteor Number")

	if map_key in {"permanently_shaded_regions", "psr"}:
		return _fallback_if_missing(psr, elevation, "PSR")

	return elevation


def _fallback_if_missing(
	requested: RasterPayload,
	fallback: RasterPayload,
	label: str,
) -> RasterPayload:
	"""Return the requested raster or fall back if unavailable."""
	data, meta = requested
	if data is None:
		logger.warning(f"{label} map was requested, but it is unavailable.")
		return fallback

	return data, meta or fallback[1]
