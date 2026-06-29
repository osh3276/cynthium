from PySide6.QtWidgets import (
	QComboBox,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QVBoxLayout,
	QWidget,
)

from cynthium.app.engine.simulation.rover_settings import ROVER_PRESETS


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

		preset_layout = QHBoxLayout()
		preset_layout.addWidget(QLabel("Preset:"))
		self.preset_combo = QComboBox()
		self.preset_combo.addItems(list(ROVER_PRESETS.keys()))
		self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
		preset_layout.addWidget(self.preset_combo)
		layout.addLayout(preset_layout)

		mass_layout = QHBoxLayout()
		mass_layout.addWidget(QLabel("Rover mass (kg):"))
		self.mass_field = QLineEdit()
		self.mass_field.setPlaceholderText("kg")
		mass_layout.addWidget(self.mass_field)
		layout.addLayout(mass_layout)

		power_layout = QHBoxLayout()
		power_layout.addWidget(QLabel("Rover power (hp):"))
		self.power_field = QLineEdit()
		self.power_field.setPlaceholderText("hp")
		power_layout.addWidget(self.power_field)
		layout.addLayout(power_layout)

		friction_layout = QHBoxLayout()
		friction_layout.addWidget(QLabel("Wheel friction coeff (μ):"))
		self.friction_field = QLineEdit()
		self.friction_field.setPlaceholderText("mu")
		friction_layout.addWidget(self.friction_field)
		layout.addLayout(friction_layout)

		rr_layout = QHBoxLayout()
		rr_layout.addWidget(QLabel("Rolling resistance (Crr):"))
		self.rolling_resistance_field = QLineEdit()
		self.rolling_resistance_field.setPlaceholderText("crr")
		rr_layout.addWidget(self.rolling_resistance_field)
		layout.addLayout(rr_layout)

		# Apply default preset
		self._on_preset_changed("Curiosity")

	def _on_preset_changed(self, name: str):
		preset = ROVER_PRESETS.get(name)
		if preset is None:
			return
		self.mass_field.setText(str(preset.mass_kg))
		self.power_field.setText(str(preset.power_hp))
		self.friction_field.setText(str(preset.wheel_friction_coeff))
		self.rolling_resistance_field.setText(str(preset.rolling_resistance_coeff))

	def set_preset(self, name: str):
		"""Set the rover preset combo, triggering field updates."""
		if name in ROVER_PRESETS:
			idx = self.preset_combo.findText(name)
			if idx >= 0:
				self.preset_combo.setCurrentIndex(idx)
				return
		# Fallback: preset name not found, fill raw fields if they exist
		logger = __import__("cynthium.app.utils.logger", fromlist=["get_logger"]).get_logger(__name__)
		logger.warning(f"Rover preset '{name}' not found, using raw values if provided")

	def set_values(self, mass_kg: str, power_hp: str, mu: str, crr: str):
		"""Set rover field values directly (bypasses preset lookup)."""
		if mass_kg:
			self.mass_field.setText(str(mass_kg))
		if power_hp:
			self.power_field.setText(str(power_hp))
		if mu:
			self.friction_field.setText(str(mu))
		if crr:
			self.rolling_resistance_field.setText(str(crr))

	def get_preset_name(self) -> str:
		return self.preset_combo.currentText()

	def get_values(self) -> tuple[str, str, str, str]:
		return (
			self.mass_field.text().strip(),
			self.power_field.text().strip(),
			self.friction_field.text().strip(),
			self.rolling_resistance_field.text().strip(),
		)
