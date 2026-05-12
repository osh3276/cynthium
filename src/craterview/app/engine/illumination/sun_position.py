from pathlib import Path

import spiceypy as spice
import numpy as np

BASE_DIR = Path(__file__).resolve().parents[2] / "planetary" / "moon_spice_kernels"

for kernel in [
	"naif0012.tls",  # leap-second conversion
	"de430.bsp",  # planetary/lunar ephemeris
	"moon_pa_de440_200625.bpc",  # lunar orientation/dotation
	"moon_de440_250416.tf",  # lunar reference frame definitions
	"pck00011.tpc",  # planetary constants
]:
	spice.furnsh(str(BASE_DIR / kernel))

def sun_position(lat, lon, time):
	"""
    lat, lon: selenographic degrees
    et: SPICE ephemeris time (use spice.utc2et)
    """
	et = spice.utc2et(time)

	state, _ = spice.spkpos("SUN", et, "MOON_ME", "LT+S", "MOON")
	sv = np.array(state)
	sv /= np.linalg.norm(sv)

	lat_rad = np.radians(lat)
	lon_rad = np.radians(lon)

	up = np.array([np.cos(lat_rad) * np.cos(lon_rad),
	               np.cos(lat_rad) * np.sin(lon_rad),
	               np.sin(lat_rad)])
	east = np.cross(np.array([0, 0, 1]), up)
	east /= np.linalg.norm(east)
	north = np.cross(up, east)

	elevation = np.degrees(np.arcsin(np.dot(sv, up)))
	azimuth = np.degrees(np.arctan2(np.dot(sv, east), np.dot(sv, north))) % 360

	return azimuth, elevation