
class AppStatBar():
	def __init__(self, parent=None):
		super().__init__("Main Toolbar", parent)
		self._build()

	def _build(self):
		self.setMovable(False)

		self.home_button = QToolButton()
		self.home_button.setText("Home")
		self.addWidget(self.home_button)

		self.refresh_button = QToolButton()
	    self.refresh_button.setText("Refresh")
        self.addWidget(self.refresh_button)

        self.addSeparator()

        self.exit_button = QToolButton()
        self.exit_button.setText("Exit")
        self.exit_button.clicked.connect(self.parent().close if self.parent() is not None else lambda: None)
        self.addWidget(self.exit_button)
