from datetime import datetime, timezone

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QSplitter, QWidget

from craterview.app.io.reader import load_geotif
from craterview.app.services.site_rasters import (
	RasterPayload,
	load_context_rasters,
	load_slope_raster,
	select_display_raster,
)
from craterview.app.utils.logger import get_logger

from .map_view import MapView
from .terrain_view import TerrainView

logger = get_logger(__name__)


class ViewContainer(QWidget):
	def __init__(self, parent=None):
		"""
		Initializes the ViewContainer instance.

		:param parent: Parent widget.
		:return: None
		"""
		super().__init__(parent)

		self._current_path = None
		self._current_datetime = None
		self._current_data = None
		self._current_meta = None
		self._current_slope_data = None
		self._current_slope_meta = None
		self._current_illumination_data = None
		self._current_illumination_meta = None
		self._current_temperature_data = None
		self._current_temperature_meta = None

		self.terrain_view = TerrainView(parent=self)
		self.raster_view = MapView(parent=self)

		splitter = QSplitter(Qt.Orientation.Horizontal)
		splitter.addWidget(self.raster_view)
		splitter.addWidget(self.terrain_view)
		splitter.setSizes([500, 500])

		layout = QHBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.addWidget(splitter)

		self.setStyleSheet("border: 1px solid #cccccc;")

	def load(
		self,
		path: str,
		map_type: str = "Elevation",
		date: str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
	):
		"""
		Loads the data.

		:param path: Path to the file.
		:type path: str
		:param map_type: Map type identifier.
		:type map_type: str
		:param date: Parameter value.
		:type date: str
		:return: The resulting value.
		"""
		data, meta = load_geotif(path)
		self._current_path = path
		self._current_datetime = date
		self._current_data = data
		self._current_meta = meta

		self._current_slope_data, self._current_slope_meta = load_slope_raster(path)
		(
			(self._current_illumination_data, self._current_illumination_meta),
			(self._current_temperature_data, self._current_temperature_meta),
		) = load_context_rasters(path)

		self.display_map_type(map_type)
		self.terrain_view.load(path, date)

	def display_map_type(self, map_type: str) -> bool:
		"""
		Displays the map type.

		:param map_type: Map type identifier.
		:type map_type: str
		:return: The resulting value.
		"""
		if self._current_data is None or self._current_meta is None:
			logger.warning("Cannot display map type before a site has been loaded.")
			return False

		display_data, display_meta = select_display_raster(
			map_type,
			self._elevation_raster,
			self._slope_raster,
			self._illumination_raster,
			self._temperature_raster,
		)
		if display_data is None:
			logger.warning(f"No raster data available for map type: {map_type}")
			return False

		self.raster_view.load(
			display_data,
			display_meta,
			map_type,
			utctime=self._current_datetime,
		)
		return True

	@property
	def _elevation_raster(self) -> RasterPayload:
		"""
		Performs elevation raster.

		:return: The resulting value.
		"""
		return self._current_data, self._current_meta

	@property
	def _slope_raster(self) -> RasterPayload:
		"""
		Performs slope raster.

		:return: The resulting value.
		"""
		return self._current_slope_data, self._current_slope_meta

	@property
	def _illumination_raster(self) -> RasterPayload:
		"""
		Performs illumination raster.

		:return: The resulting value.
		"""
		return self._current_illumination_data, self._current_illumination_meta

	@property
	def _temperature_raster(self) -> RasterPayload:
		"""
		Performs temperature raster.

		:return: The resulting value.
		"""
		return self._current_temperature_data, self._current_temperature_meta

	def get_current_map_data(self):
		"""
		Returns the current map data.

		:return: The resulting value.
		"""
		return (
			self._current_data,
			self._current_meta,
			self._current_slope_data,
			self._current_temperature_data,
			self._current_temperature_meta,
			self._current_illumination_data,
			self._current_illumination_meta,
		)

	def add_waypoint(self, x: float, y: float):
		"""
		Adds the waypoint.

		:param x: X coordinate.
		:type x: float
		:param y: Y coordinate.
		:type y: float
		:return: None
		"""
		self.raster_view.add_waypoint(x, y)
		self.terrain_view.add_waypoint(x, y)

	def remove_waypoint(self, index: int):
		"""
		Removes the waypoint.

		:param index: Item index.
		:type index: int
		:return: None
		"""
		self.raster_view.remove_waypoint(index)
		self.terrain_view.remove_waypoint(index)

	def get_waypoint_3d_points(self):
		"""
		Returns the waypoint 3d points.

		:return: The resulting value.
		"""
		return self.terrain_view.get_waypoint_3d_points()
