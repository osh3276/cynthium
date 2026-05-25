from PySide6.QtWidgets import (
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QVBoxLayout,
	QWidget,
)

from craterview.app.config import ROVER_MASS_KG


class RoverSettingsPanel(QWidget):
	def __init__(self):
		"""UI for rover parameters used by the simulation."""
		super().__init__()
		self._build()

	def _build(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(4)

		layout.addWidget(QLabel("Rover Settings"))

		mass_layout = QHBoxLayout()
		mass_layout.addWidget(QLabel("Rover mass (kg):"))
		self.mass_field = QLineEdit()
		self.mass_field.setPlaceholderText("kg")
		self.mass_field.setText(str(float(ROVER_MASS_KG)))
		mass_layout.addWidget(self.mass_field)
		layout.addLayout(mass_layout)

		power_layout = QHBoxLayout()
		power_layout.addWidget(QLabel("Rover power (hp):"))
		self.power_field = QLineEdit()
		self.power_field.setPlaceholderText("hp")
		self.power_field.setText("0.2")
		power_layout.addWidget(self.power_field)
		layout.addLayout(power_layout)

		friction_layout = QHBoxLayout()
		friction_layout.addWidget(QLabel("Wheel friction coeff (μ):"))
		self.friction_field = QLineEdit()
		self.friction_field.setPlaceholderText("mu")
		self.friction_field.setText("0.6")
		friction_layout.addWidget(self.friction_field)
		layout.addLayout(friction_layout)

	def get_values(self) -> tuple[str, str, str]:
		return (
			self.mass_field.text().strip(),
			self.power_field.text().strip(),
			self.friction_field.text().strip(),
		)
