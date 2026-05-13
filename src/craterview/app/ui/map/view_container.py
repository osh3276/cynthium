from datetime import datetime, timezone

from PySide6.QtWidgets import QWidget, QHBoxLayout, QSplitter
from PySide6.QtCore import Qt

from .terrain_view import TerrainView
from .map_view import MapView
from craterview.app.io.reader import load_geotif

class ViewContainer(QWidget):
	def __init__(self, parent=None):
		super().__init__(parent)

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

	def load(self, path: str, map_type: str = "elevation",
			 date: str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")):
		data, meta = load_geotif(path)
		self._current_data = data
		self._current_meta = meta
		self.raster_view.load(data, meta, map_type)
		self.terrain_view.load(path, date)

	def get_current_map_data(self):
		return self._current_data, self._current_meta

	def add_waypoint(self, x: float, y: float):
		self.raster_view.add_waypoint(x, y)
		self.terrain_view.add_waypoint(x, y)

	def remove_waypoint(self, index: int):
		self.raster_view.remove_waypoint(index)
		self.terrain_view.remove_waypoint(index)

	def get_waypoint_3d_points(self):
		return self.terrain_view.get_waypoint_3d_points()