from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QWidget, QFileDialog

from .ui.map.view_container import ViewContainer
from .ui.map.map_view import MapView
from .ui.map.terrain_view import TerrainView
from craterview.app.ui.panels.sidebar.container import AppSidebar
from .ui.panels.menubar import AppMenuBar

from craterview.app.utils.logger import get_logger

logger = get_logger(__name__)

class Window(QMainWindow):

	_menubar: AppMenuBar
	_terrain_view: TerrainView
	_raster_view: MapView

	def __init__(self):
		super().__init__()
		self.setWindowTitle("CraterView")
		self.setGeometry(100, 100, 1600, 900)
		self._resize_timer = QTimer()
		self._resize_timer.setSingleShot(True)
		self._resize_timer.timeout.connect(self._on_resize_done)

		# self.addToolBar(create_toolbar(self))

		self._menubar = AppMenuBar(self)
		self.setMenuBar(self._menubar)

		# Create central widget and layout
		content = QWidget()
		self.setCentralWidget(content)

		layout = QHBoxLayout()

		# Add widgets
		self._view_container = ViewContainer(self)
		layout.addWidget(self._view_container, stretch=1)

		self._sidebar = AppSidebar()
		layout.addWidget(self._sidebar, stretch=0)

		content.setLayout(layout)

		self.statusBar().showMessage("Ready")
		self._connect_signals()
		logger.info("Window initialized")

	def on_button_clicked(self):
		logger.info("Button clicked")

	def resizeEvent(self, event):
		super().resizeEvent(event)
		self._resize_timer.start(1500)  # ms delay

	def _on_resize_done(self):
		self._view_container.terrain_view.render()

	def _connect_signals(self):
		self._menubar.action_open.triggered.connect(self._open_file_dialog)
		self._menubar.action_exit.triggered.connect(self.close)
		self._sidebar.map_selected.connect(self._load_site)

	def _load_site(self, path: str):
		self._view_container.load(path, "elevation", "2025-01-01T00:00:00")
		self.statusBar().showMessage(f"Site loaded: {path}")

	def _open_file_dialog(self):
		path, _ = QFileDialog.getOpenFileName(
			self,
			"Open Raster",
			"",
			"GeoTIFF Files (*.tif *.tiff);;All Files (*)"
		)
		if path:
			self._load_site(path)

	def _on_refresh(self):
		pass

	def get_view_container(self):
		return self._view_container


