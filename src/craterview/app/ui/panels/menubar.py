from PySide6.QtWidgets import QToolButton, QMenuBar


class AppMenuBar(QMenuBar):
	def __init__(self, parent=None):
		super().__init__(parent)
		self._build()

	def _build(self):
		file_menu = self.addMenu("File")
		edit_menu = self.addMenu("Edit")
		view_menu = self.addMenu("View")
		help_menu = self.addMenu("Help")


		self.action_open = file_menu.addAction("Open")
		self.action_open.setShortcut("Ctrl+O")
		file_menu.addAction(self.action_open)

		self.addSeparator()

		self.action_exit = file_menu.addAction("Exit")
		self.action_exit.setShortcut("Ctrl+Q")
		file_menu.addAction(self.action_exit)