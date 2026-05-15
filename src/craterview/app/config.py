from pathlib import Path

DEBUG = True

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "elevation"
SLOPE_DIR = PROJECT_ROOT / "data" / "slope"
ILLUMINATION_DIR = PROJECT_ROOT / "data" / "illum"
TEMPERATURE_DIR = PROJECT_ROOT / "data" / "temperature"
ILLUMINATION_RASTER_PATH = ILLUMINATION_DIR / "Illumination_mask_80mpp_FULL_GEO.tif"
AVERAGE_TEMPERATURE_RASTER_PATH = (
	TEMPERATURE_DIR / "polar_south_80_summer_avg-float.tif"
)

RASTER_LAYERS = {
	"realistic": DATA_DIR / "realistic.tif",
	"elevation": DATA_DIR / "elevation.TIF",
	"illumination": ILLUMINATION_RASTER_PATH,
	"average_temperature": AVERAGE_TEMPERATURE_RASTER_PATH,
	"meteor_flux": DATA_DIR / "meteor_flux.tif",
	"ldem": DATA_DIR / "LDEM_80S_40MPP_ADJ.tiff",
	# add layers here as you acquire them
}

MAP_TYPES = [
	"Elevation",
	"Slope",
	"Hillshade",
	"Solar Illumination",
	"Meteor Flux",
	"Average Temperature",
]

# --- Lunar CRS ---
# Lunar south pole stereographic (LOLA native projection)
# Not in EPSG registry; defined manually via proj string.
# TODO: Verify this is the same as Jack's
LUNAR_CRS_PROJ = "+proj=stere +lat_0=-90 +lon_0=0 +k=1 +R=1737400 +units=m +no_defs"
# Lunar geographic latitude/longitude on the Moon
FRONTEND_CRS = "+proj=longlat +R=1737400 +no_defs +type=crs"

# --- Rover parameters ---
ROVER_MAX_SLOPE_DEG = 20.0  # hard impassable threshold
ROVER_WARN_SLOPE_DEG = 15.0  # soft warning threshold
ROVER_MASS_KG = 150.0
LUNAR_GRAVITY = 1.62  # m/s^2
LUNAR_REGOLITH_FRICTION = (
	0.1  # rolling resistance coefficient on regolith, not used for now
)

# --- Site presets ---

# coordinates not finalized

SUF = "_5mpp_surf"
SITE_PRESET_PATHS = {
	"Haworth": DATA_DIR / f"Haworth{SUF}.tif",
	"Shoemaker": DATA_DIR / f"Shoemaker{SUF}.tif",
	"Amundsen rim": DATA_DIR / f"DM1{SUF}.tif",
	"Nobile rim 2": DATA_DIR / f"DM2{SUF}.tif",
	"Shackleton Rim B": DATA_DIR / f"LM1{SUF}.tif",
	"Shoemaker Rim A": DATA_DIR / f"LM2{SUF}.tif",
	"Shoemaker Rim B": DATA_DIR / f"LM3{SUF}.tif",
	"Shoemaker Rim C": DATA_DIR / f"LM4{SUF}.tif",
	"Shoemaker Rim D": DATA_DIR / f"LM5{SUF}.tif",
	"Shoemaker Rim E": DATA_DIR / f"LM6{SUF}.tif",
	"Faustini Rim A": DATA_DIR / f"LM7{SUF}.tif",
	"Shoemaker Rim F": DATA_DIR / f"LM8{SUF}.tif",
	"Cabeus exterior wall 1": DATA_DIR / f"NPA{SUF}.tif",
	"Amundsen 1": DATA_DIR / f"NPB{SUF}.tif",
	"Idel'son L crater 1": DATA_DIR / f"NPC{SUF}.tif",
	"Malapert crater 1": DATA_DIR / f"NPD{SUF}.tif",
	"Connecting ridge": DATA_DIR / f"Site01{SUF}.tif",
	"Shackleton rim": DATA_DIR / f"Site04{SUF}.tif",
	"Nobile rim 1": DATA_DIR / f"Site06{SUF}.tif",
	"Peak near Shackleton": DATA_DIR / f"Site07{SUF}.tif",
	"de Gerlache rim": DATA_DIR / f"Site11{SUF}.tif",
	"de Gerlache rim 2": DATA_DIR / f"SL2{SUF}.tif",
	"Leibnitz beta plateau": DATA_DIR / f"Site20{SUF}.tif",
	"Leibnitz beta plateau, extended": DATA_DIR / f"Site20v2{SUF}.tif",
	"Malapert massif": DATA_DIR / f"Site23{SUF}.tif",
	"de Gerlache-Kocher massif": DATA_DIR / f"Site42{SUF}.tif",
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
	if name.endswith("_surf"):
		candidates.append(SLOPE_DIR / f"{name.removesuffix('_surf')}_slp.tif")

	candidates.append(SLOPE_DIR / f"{name}_slp.tif")

	for candidate in candidates:
		if candidate.exists():
			return candidate

	return candidates[0]


# --- Pathfinding cost weights ---
ALPHA_SLOPE = 1.0  # weight for slope cost
BETA_SHADOW = 0.5  # weight for shadow/illumination cost
