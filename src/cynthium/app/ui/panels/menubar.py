from PySide6.QtWidgets import QMenuBar


class AppMenuBar(QMenuBar):
	def __init__(self, parent=None):
		super().__init__(parent)
		self._build()

	def _build(self):
		file_menu = self.addMenu("File")
		self.addMenu("Edit")
		self.addMenu("View")
		self.addMenu("Help")

		self.action_open = file_menu.addAction("Open")
		self.action_open.setShortcut("Ctrl+O")

		self.action_export_simulation_data = file_menu.addAction(
			"Export Simulation Data"
		)
		self.action_export_simulation_data.setShortcut("Ctrl+E")

		file_menu.addSeparator()

		self.action_exit = file_menu.addAction("Exit")
		self.action_exit.setShortcut("Ctrl+Q")
