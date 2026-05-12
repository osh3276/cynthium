from pyproj import Transformer

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
