import math

import numpy as np
import spiceypy as spice

from cynthium.app import data as data_store


def round_azimuth_to_nearest_12(azimuth_deg: float) -> int:
	"""Round sun azimuth to the nearest 12-degree bin (0, 12, 24, ... 348)."""
	az = float(azimuth_deg) % 360.0
	angle = int(math.floor((az + 6.0) / 12.0)) * 12
	angle = angle % 360
	return 0 if angle == 360 else angle


_kernels_loaded = False


def _ensure_kernels_loaded() -> None:
	"""Fetch SPICE kernels via pooch on first use and furnsh them once."""
	global _kernels_loaded
	if _kernels_loaded:
		return
	for name in data_store.SPICE_KERNELS:
		spice.furnsh(str(data_store.fetch(name)))
	_kernels_loaded = True


def sub_solar_latitude(utctime: str) -> float:
	"""Return the sub-solar point latitude (degrees) at the given UTC time.

	Negative = sun in southern hemisphere (summer at south pole).
	Positive = sun in northern hemisphere (winter at south pole).
	"""
	_ensure_kernels_loaded()
	et = spice.utc2et(utctime)
	state, _ = spice.spkpos("SUN", et, "MOON_ME", "LT+S", "MOON")
	pos = state[:3]
	_, lon, lat = spice.reclat(pos)
	return float(np.degrees(lat))


def sun_position(lat, lon, time):
	"""
	lat, lon: selenographic degrees
	et: SPICE ephemeris time (use spice.utc2et)
	"""
	_ensure_kernels_loaded()
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
