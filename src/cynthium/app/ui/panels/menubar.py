from PySide6.QtWidgets import QMenuBar


class AppMenuBar(QMenuBar):
	def __init__(self, parent=None):
		super().__init__(parent)
		self._build()

	def _build(self):
		file_menu = self.addMenu("File")
		self.addMenu("Edit")
		self.addMenu("View")

		settings_menu = self.addMenu("Settings")
		self.action_rover_settings = settings_menu.addAction("Rover...")
		self.action_rover_settings.setShortcut("Ctrl+R")

		self.addMenu("Help")

		# --- Import ---
		self.action_import_tif = file_menu.addAction("Import GeoTIFF...")
		self.action_import_tif.setShortcut("Ctrl+I")
		self.action_import_settings = file_menu.addAction(
			"Import Settings..."
		)

		file_menu.addSeparator()

		# --- Open (load preset or existing site) ---
		self.action_open = file_menu.addAction("Open")
		self.action_open.setShortcut("Ctrl+O")

		file_menu.addSeparator()

		# --- Export ---
		self.action_export_manual_path = file_menu.addAction(
			"Export Manual Path"
		)
		self.action_export_autopath = file_menu.addAction(
			"Export Auto Path"
		)
		self.action_export_settings = file_menu.addAction(
			"Export Settings..."
		)
		self.action_export_simulation_data = file_menu.addAction(
			"Export Simulation Data"
		)
		self.action_export_simulation_data.setShortcut("Ctrl+E")

		file_menu.addSeparator()

		self.action_exit = file_menu.addAction("Exit")
		self.action_exit.setShortcut("Ctrl+Q")
