import PySide6
from PySide6.QtWidgets import QToolButton, QPushButton, QLabel, QLineEdit
from PySide6.QtWidgets import QVBoxLayout


class AppSidebar(QVBoxLayout):
	def __init__(self):
		super().__init__()
		self._build()

	def _build(self):
		# a bunch of stuff
		label = QLabel("sidebar content")
		self.addWidget(label)

		coord_label = QLabel("Coordinate:")
		self.addWidget(coord_label)

		coord_field = QLineEdit()
		coord_field.setWindowTitle("hi")
		coord_field.setPlaceholderText("x,y")
		self.addWidget(coord_field)

		button = QPushButton("add nonexistent coordinate")
		self.addWidget(button)