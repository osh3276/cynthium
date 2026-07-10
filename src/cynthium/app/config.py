import os
from pathlib import Path

import pooch

DEBUG = True

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parents[3]

_DEV_DATA_ROOT = PROJECT_ROOT / "data"
_CACHE_DATA_ROOT = Path(pooch.os_cache("cynthium"))

_env_data_root = os.environ.get("CYNTHIUM_DATA_DIR")
if _env_data_root:
	DATA_ROOT = Path(_env_data_root).expanduser()
elif _DEV_DATA_ROOT.exists():
	DATA_ROOT = _DEV_DATA_ROOT
else:
	DATA_ROOT = _CACHE_DATA_ROOT

DATA_DIR = DATA_ROOT / "elevation"
SLOPE_DIR = DATA_ROOT / "slope"
ILLUMINATION_DIR = DATA_ROOT / "illum"
ILLUMINATION_ANGLES_DIR = ILLUMINATION_DIR / "angles"
TEMPERATURE_DIR = DATA_ROOT / "temperature"
METEOR_DIR = DATA_ROOT / "meteor"
METEOR_ANGLES_DIR = METEOR_DIR / "angles"


def resolve_data_file_path(path: Path) -> Path:
	"""Failsafe for expected `data/<subdir>/<file>` layouts.

	If the expected parent subdirectory does not exist, try `data/<file>`.
	"""
	if path.exists():
		return path
	try:
		parent = path.parent
	except Exception:
		return path

	if not parent.exists():
		fallback = DATA_ROOT / path.name
		if fallback.exists():
			return fallback

	return path


def ensure_data_file_path(path: Path) -> Path:
	"""Resolve then download (if needed) into the data cache.

	Only downloads if the filename is present in `cynthium.app.data.REGISTRY`.
	"""
	resolved = resolve_data_file_path(path)
	if resolved.exists():
		return resolved

	try:
		from cynthium.app import data as data_store
	except Exception:
		return resolved

	name = resolved.name
	registry = getattr(data_store, "REGISTRY", {})
	if name not in registry:
		return resolved

	try:
		fetched = data_store.fetch(name)
	except Exception:
		return resolved

	return Path(str(fetched))


ILLUMINATION_RASTER_PATH = resolve_data_file_path(
	DATA_ROOT / "illum.tif"
)
AVERAGE_TEMPERATURE_RASTER_PATH = resolve_data_file_path(
	TEMPERATURE_DIR / "polar_south_80_summer_avg-float.tif"
)
METEOR_FLUX_RASTER_PATH = resolve_data_file_path(
	DATA_ROOT / "meteor_energy.tif"
)
METEOR_NUMBER_RASTER_PATH = resolve_data_file_path(
	DATA_ROOT / "meteor_number.tif"
)
PSR_RASTER_PATH = resolve_data_file_path(
	DATA_ROOT / "psr.tif"
)

RASTER_LAYERS = {
	"realistic": resolve_data_file_path(DATA_DIR / "realistic.tif"),
	"elevation": resolve_data_file_path(DATA_DIR / "elevation.TIF"),
	"illumination": ILLUMINATION_RASTER_PATH,
	"average_temperature": AVERAGE_TEMPERATURE_RASTER_PATH,
	"meteor_flux": METEOR_FLUX_RASTER_PATH,
	"ldem": resolve_data_file_path(DATA_DIR / "LDEM_80S_40MPP_ADJ.tiff"),
	# add layers here as you acquire them
}

MAP_TYPES = [
	"Elevation",
	"Slope",
	"Hillshade",
	"Solar Illumination (mo. avg.)",
	"Solar Illumination (day avg.)",
	"Meteor Flux (mo. avg.)",
	"Meteor Flux (day avg.)",
	"Meteor Number (mo. avg.)",
	"Meteor Number (day avg.)",
	"Average Temperature",
	"Permanently Shaded Regions",
]

# --- Lunar CRS ---
# Lunar south pole stereographic (LOLA native projection)
# Not in EPSG registry; defined manually via proj string.
LUNAR_CRS_PROJ = "+proj=stere +lat_0=-90 +lon_0=0 +k=1 +R=1737400 +units=m +no_defs"
# Lunar geographic latitude/longitude on the Moon
FRONTEND_CRS = "+proj=longlat +R=1737400 +no_defs +type=crs"

# --- Rover parameters ---
ROVER_MAX_SLOPE_DEG = 20.0  # hard impassable threshold
ROVER_WARN_SLOPE_DEG = 15.0  # soft warning threshold
ROVER_MASS_KG = 150.0
LUNAR_GRAVITY = 1.625  # m/s^2
LUNAR_REGOLITH_FRICTION = (
	0.1  # rolling resistance coefficient on regolith, not used for now
)

# --- Site presets ---

# coordinates not finalized

SUF = "_20mpp_surf"
SITE_PRESET_PATHS = {
	"Haworth": resolve_data_file_path(DATA_DIR / f"Haworth{SUF}.tif"),
	"Shoemaker": resolve_data_file_path(DATA_DIR / f"Shoemaker{SUF}.tif"),
	"Amundsen rim": resolve_data_file_path(DATA_DIR / f"DM1{SUF}.tif"),
	"Nobile rim 2": resolve_data_file_path(DATA_DIR / f"DM2{SUF}.tif"),
	"Shackleton rim B": resolve_data_file_path(DATA_DIR / f"LM1{SUF}.tif"),
	"Shoemaker rim A": resolve_data_file_path(DATA_DIR / f"LM2{SUF}.tif"),
	"Shoemaker rim B": resolve_data_file_path(DATA_DIR / f"LM3{SUF}.tif"),
	"Shoemaker rim C": resolve_data_file_path(DATA_DIR / f"LM4{SUF}.tif"),
	"Shoemaker rim D": resolve_data_file_path(DATA_DIR / f"LM5{SUF}.tif"),
	"Shoemaker rim E": resolve_data_file_path(DATA_DIR / f"LM6{SUF}.tif"),
	"Faustini rim A": resolve_data_file_path(DATA_DIR / f"LM7{SUF}.tif"),
	"Shoemaker rim F": resolve_data_file_path(DATA_DIR / f"LM8{SUF}.tif"),
	"Cabeus exterior wall 1": resolve_data_file_path(DATA_DIR / f"NPA{SUF}.tif"),
	"Amundsen 1": resolve_data_file_path(DATA_DIR / f"NPB{SUF}.tif"),
	"Idel'son L crater 1": resolve_data_file_path(DATA_DIR / f"NPC{SUF}.tif"),
	"Malapert crater 1": resolve_data_file_path(DATA_DIR / f"NPD{SUF}.tif"),
	"Connecting ridge": resolve_data_file_path(DATA_DIR / f"Site01{SUF}.tif"),
	"Shackleton rim": resolve_data_file_path(DATA_DIR / f"Site04{SUF}.tif"),
	"Nobile rim 1": resolve_data_file_path(DATA_DIR / f"Site06{SUF}.tif"),
	"Peak near Shackleton": resolve_data_file_path(DATA_DIR / f"Site07{SUF}.tif"),
	"de Gerlache rim": resolve_data_file_path(DATA_DIR / f"Site11{SUF}.tif"),
	"de Gerlache rim 2": resolve_data_file_path(DATA_DIR / f"SL2{SUF}.tif"),
	"Leibnitz beta plateau": resolve_data_file_path(DATA_DIR / f"Site20{SUF}.tif"),
	"Leibnitz beta plateau, extended": resolve_data_file_path(DATA_DIR / f"Site20v2{SUF}.tif"),
	"Malapert massif": resolve_data_file_path(DATA_DIR / f"Site23{SUF}.tif"),
	"de Gerlache-Kocher massif": resolve_data_file_path(DATA_DIR / f"Site42{SUF}.tif"),
}


def get_slope_path(elevation_path: str | Path) -> Path:
	"""
	Given a path to an elevation map, return the corresponding slope map.

	The elevation files in this project use names like ``Haworth_5mpp_surf.tif`` while
	the matching slope files use names like ``Haworth_final_adj_5mpp_slp.tif``.  A few
	fallback candidates are checked as well so custom files can still work.
	"""
	p = Path(elevation_path)
	name = p.stem

	candidates: list[Path] = []
	if name.endswith("_5mpp_surf"):
		site_name = name.removesuffix("_5mpp_surf")
		candidates.append(SLOPE_DIR / f"{site_name}_final_adj_5mpp_slp.tif")
		candidates.append(SLOPE_DIR / f"{site_name}_5mpp_slp.tif")
	if name.endswith("_20mpp_surf"):
		site_name = name.removesuffix("_20mpp_surf")
		candidates.append(SLOPE_DIR / f"{site_name}_final_adj_20mpp_slp.tif")
		candidates.append(SLOPE_DIR / f"{site_name}_20mpp_slp.tif")
	if name.endswith("_surf"):
		candidates.append(SLOPE_DIR / f"{name.removesuffix('_surf')}_slp.tif")

	candidates.append(SLOPE_DIR / f"{name}_slp.tif")

	for candidate in candidates:
		resolved = resolve_data_file_path(candidate)
		if resolved.exists():
			return resolved

	return resolve_data_file_path(candidates[0])


# --- Pathfinding cost weights ---
ALPHA_SLOPE = 100.0  # weight for slope cost
BETA_SHADOW = 10.0  # weight for shadow/illumination cost
METEOR_FLUX_WEIGHT = 5.0  # weight for meteor flux cost (low flux preferred)
TEMPERATURE_WEIGHT = 5.0  # weight for temperature cost (high temp preferred)
