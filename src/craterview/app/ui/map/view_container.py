from datetime import datetime, timezone

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QSplitter, QWidget

from craterview.app.config import (
	AVERAGE_TEMPERATURE_RASTER_PATH,
	ILLUMINATION_RASTER_PATH,
	get_slope_path,
)
from craterview.app.io.reader import load_geotif, load_geotif_cropped_to_reference
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

		self._load_slope_map(path)
		self._load_context_maps(path)

		self.display_map_type(map_type)
		self.terrain_view.load(path, date)

	def display_map_type(self, map_type: str) -> bool:
		if self._current_data is None or self._current_meta is None:
			logger.warning("Cannot display map type before a site has been loaded.")
			return False

		display_data, display_meta = self._get_display_raster(
			self._current_path,
			map_type,
			self._current_data,
			self._current_meta,
		)
		self.raster_view.load(display_data, display_meta, map_type)
		return True

	def _get_display_raster(self, path: str | None, map_type: str, data, meta):
		normalized_map_type = self._normalize_map_type(map_type)

		if normalized_map_type == "slope":
			if self._current_slope_data is None:
				logger.warning(
					"Slope map was requested, but no matching slope file was found."
				)
				return data, meta
			return self._current_slope_data, self._current_slope_meta or meta

		if normalized_map_type == "solar_illumination":
			if self._current_illumination_data is None:
				logger.warning("Illumination map was requested, but it is unavailable.")
				return data, meta
			return (
				self._current_illumination_data,
				self._current_illumination_meta or meta,
			)

		if normalized_map_type == "average_temperature":
			if self._current_temperature_data is None:
				logger.warning("Temperature map was requested, but it is unavailable.")
				return data, meta
			return (
				self._current_temperature_data,
				self._current_temperature_meta or meta,
			)

		return data, meta

	def _load_context_maps(self, reference_path: str):
		self._current_illumination_data, self._current_illumination_meta = (
			self._load_cropped_context_raster(
				ILLUMINATION_RASTER_PATH,
				reference_path,
				"illumination",
			)
		)
		self._current_temperature_data, self._current_temperature_meta = (
			self._load_cropped_context_raster(
				AVERAGE_TEMPERATURE_RASTER_PATH,
				reference_path,
				"temperature",
			)
		)

	def _load_cropped_context_raster(
		self, source_path, reference_path: str, label: str
	):
		if not source_path.exists():
			logger.warning(f"Missing {label} raster: {source_path}")
			return None, None

		try:
			data, meta = load_geotif_cropped_to_reference(source_path, reference_path)
		except ValueError as exc:
			logger.warning(f"Failed to crop {label} raster: {exc}")
			return None, None

		logger.info(f"Loaded cropped {label} raster from {source_path}")
		return data, meta

	def _load_slope_map(self, elevation_path: str):
		slope_path = get_slope_path(elevation_path)
		if slope_path.exists():
			self._current_slope_data, self._current_slope_meta = load_geotif(
				str(slope_path)
			)
			logger.info(f"Loaded slope map: {slope_path}")
		else:
			self._current_slope_data = None
			self._current_slope_meta = None
			logger.warning(
				f"No slope map found for {elevation_path}. Expected: {slope_path}"
			)

	def _normalize_map_type(self, map_type: str) -> str:
		return map_type.strip().lower().replace(" ", "_")

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
