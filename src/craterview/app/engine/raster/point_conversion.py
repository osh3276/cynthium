from pyproj import Transformer

# # Initialize once at module level
# STERE_CRS = "+proj=stere +lat_0=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +a=1737400 +b=1737400 +units=m"
# LONGLAT_CRS = "+proj=longlat +a=1737400 +b=1737400"
#
# _to_longlat = Transformer.from_crs(STERE_CRS, LONGLAT_CRS, always_xy=True)
# _to_xy = Transformer.from_crs(LONGLAT_CRS, STERE_CRS, always_xy=True)
#

def xy_to_longlat(x, y):
	transformer = Transformer.from_crs(
		"+proj=stere +lat_0=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +a=1737400 +b=1737400 +units=m",
		"+proj=longlat +a=1737400 +b=1737400"
	)
	return transformer.transform(x, y)

def longlat_to_xy(lon, lat):
	transformer = Transformer.from_crs(
		"+proj=longlat +a=1737400 +b=1737400",
		"+proj=stere +lat_0=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +a=1737400 +b=1737400 +units=m"
	)
	return transformer.transform(lon, lat)
