from astropy.coordinates import get_body_barycentric, SkyCoord, MCMF
from astropy.time import Time
import astropy.units as u
import numpy as np


def sun_position_from_moon(lat, lon, time: Time):
	"""
	lat, lon: selenographic coordinates in degrees
	time: astropy Time object
	returns: azimuth, elevation in degrees
	"""
	# Get Sun position in MCMF (accounts for lunar libration)
	sun_gcrs = get_body_barycentric("sun", time) - get_body_barycentric("moon", time)

	sun_mcmf = SkyCoord(
		x=sun_gcrs.xyz[0],
		y=sun_gcrs.xyz[1],
		z=sun_gcrs.xyz[2],
		frame="gcrs",
		obstime=time
	).transform_to(MCMF(obstime=time))

	# Local horizontal frame at the surface point
	lat_rad = np.radians(lat)
	lon_rad = np.radians(lon)

	sv = np.array([
		sun_mcmf.cartesian.x.to(u.km).value,
		sun_mcmf.cartesian.y.to(u.km).value,
		sun_mcmf.cartesian.z.to(u.km).value,
	])
	sv /= np.linalg.norm(sv)

	# Local frame basis vectors
	up = np.array([np.cos(lat_rad) * np.cos(lon_rad),
	               np.cos(lat_rad) * np.sin(lon_rad),
	               np.sin(lat_rad)])
	east = np.cross(np.array([0, 0, 1]), up)
	east /= np.linalg.norm(east)
	north = np.cross(up, east)

	el = np.degrees(np.arcsin(np.dot(sv, up)))
	az = np.degrees(np.arctan2(np.dot(sv, east), np.dot(sv, north))) % 360

	return az, el