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

	# Get the position of the sun relative to the moon
	state, _ = spice.spkpos("SUN", et, "MOON_ME", "LT+S", "MOON")
	sun_pos = np.array(state)
	sun_pos /= np.linalg.norm(sun_pos)

	# Convert latitude and longitude to radians
	lat_rad = np.radians(lat)
	lon_rad = np.radians(lon)

	# Calculate the local up, east, and north vectors
	up = np.array([np.cos(lat_rad) * np.cos(lon_rad),
				   np.cos(lat_rad) * np.sin(lon_rad),
				   np.sin(lat_rad)])
	east = np.cross(np.array([0, 0, 1]), up)
	east /= np.linalg.norm(east)
	north = np.cross(up, east)

	# Calculate the local azimuth and elevation
	elevation = np.degrees(np.arcsin(np.dot(sun_pos, up)))
	azimuth = np.degrees(np.arctan2(np.dot(sun_pos, east), np.dot(sun_pos, north))) % 360

	return azimuth, elevation