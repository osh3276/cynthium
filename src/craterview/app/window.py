from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QMainWindow, QWidget, QFileDialog

from .ui.map.view_container import ViewContainer
from .ui.map.map_view import MapView
from .ui.map.terrain_view import TerrainView
from .ui.panels.sidebar import AppSidebar
from .ui.panels.menubar import AppMenuBar

class Window(QMainWindow):

	_menubar: AppMenuBar
	_terrain_view: TerrainView
	_raster_view: MapView

	def __init__(self):
		super().__init__()
		self.setWindowTitle("CraterView")
		self.setGeometry(99, 100, 600, 400)
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

		layout.addLayout(AppSidebar())

		content.setLayout(layout)

		self.statusBar().showMessage("Ready")
		self._connect_signals()

	def on_button_clicked(self):
		print("Button clicked")

	def resizeEvent(self, event):
		super().resizeEvent(event)
		self._resize_timer.start(1500)  # ms delay

	def _on_resize_done(self):
		self._view_container.terrain_view.render()

	def _connect_signals(self):
		self._menubar.action_open.triggered.connect(self._open_file_dialog)
		self._menubar.action_exit.triggered.connect(self.close)

	def _open_file_dialog(self):
		path, _ = QFileDialog.getOpenFileName(
			self,
			"Open Raster",
			"",
			"GeoTIFF Files (*.tif *.tiff);;All Files (*)"
		)
		if path:
			self._view_container.load(path)

	def _on_refresh(self):
		pass


