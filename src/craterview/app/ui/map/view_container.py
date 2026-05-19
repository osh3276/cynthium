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
		super().__init__(parent)

		self._current_path = None
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
		data, meta = load_geotif(path)
		self._current_path = path
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

		self.raster_view.load(display_data, display_meta, map_type)
		return True

	@property
	def _elevation_raster(self) -> RasterPayload:
		return self._current_data, self._current_meta

	@property
	def _slope_raster(self) -> RasterPayload:
		return self._current_slope_data, self._current_slope_meta

	@property
	def _illumination_raster(self) -> RasterPayload:
		return self._current_illumination_data, self._current_illumination_meta

	@property
	def _temperature_raster(self) -> RasterPayload:
		return self._current_temperature_data, self._current_temperature_meta

	def get_current_map_data(self):
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
		self.raster_view.add_waypoint(x, y)
		self.terrain_view.add_waypoint(x, y)

	def remove_waypoint(self, index: int):
		self.raster_view.remove_waypoint(index)
		self.terrain_view.remove_waypoint(index)

	def get_waypoint_3d_points(self):
		return self.terrain_view.get_waypoint_3d_points()
