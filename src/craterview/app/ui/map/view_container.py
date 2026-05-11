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

    def load(self, path: str):
        data, meta = load_geotif(path)
        self.raster_view.load(data)
        self.terrain_view.load(path)