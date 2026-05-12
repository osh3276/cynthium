import PySide6
from PySide6.QtWidgets import QLabel, QComboBox, QWidget
from PySide6.QtWidgets import QVBoxLayout

from craterview.app.utils.logger import get_logger
from craterview.app.config import SITE_PRESET_PATHS, MAP_TYPES

logger = get_logger(__name__)


class MapSelectionPanel(QWidget):
	map_selected = PySide6.QtCore.Signal(str)

	def __init__(self):
		super().__init__()
		self._build()
		self.map_selected.emit(str(SITE_PRESET_PATHS["Haworth"]))

	def _build(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(4)

		self.setMinimumWidth(180)
		preset_label = QLabel("Map types:")
		layout.addWidget(preset_label)

		type_chooser = QComboBox()
		type_chooser.addItems(MAP_TYPES)
		type_chooser.currentTextChanged.connect(self._on_map_type_changed)
		layout.addWidget(type_chooser)

		preset_label = QLabel("Preset maps:")
		layout.addWidget(preset_label)

		preset_chooser = QComboBox()
		preset_chooser.addItems(SITE_PRESET_PATHS.keys())
		preset_chooser.currentTextChanged.connect(self._on_path_changed)
		layout.addWidget(preset_chooser)

		layout.addStretch(1)

	def _on_path_changed(self, site_name: str):
		logger.info(f"Site selected: {site_name}")
		site_path = SITE_PRESET_PATHS[site_name]
		self.map_selected.emit(str(site_path))

	def _on_map_type_changed(self, map_type: str):
		logger.info(f"Map type changed: {map_type}")
