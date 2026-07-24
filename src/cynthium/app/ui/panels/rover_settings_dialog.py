"""Dialog for configuring rover settings, accessible from the menu bar."""

from math import atan, degrees

from PySide6.QtWidgets import (
	QComboBox,
	QDialog,
	QDialogButtonBox,
	QFormLayout,
	QLabel,
	QLineEdit,
	QVBoxLayout,
)

from cynthium.app.engine.simulation.rover_settings import (
	ROVER_PRESETS,
	RoverSettings,
	rover_settings_from_strings,
)


class RoverSettingsDialog(QDialog):
	"""Modal dialog for editing rover parameters."""

	def __init__(self, current: RoverSettings | None = None, parent=None):
		super().__init__(parent)
		self.setWindowTitle("Rover Settings")
		self.setMinimumWidth(380)
		self._result: RoverSettings | None = current
		self._build(current)

	def _build(self, current: RoverSettings | None):
		layout = QVBoxLayout(self)

		form = QFormLayout()

		self._preset_combo = QComboBox()
		self._preset_combo.addItems(list(ROVER_PRESETS.keys()))
		self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
		form.addRow("Preset:", self._preset_combo)

		form.addRow(QLabel(""))  # spacer

		self._mass_field = QLineEdit()
		self._mass_field.setPlaceholderText("kg")
		self._mass_field.textChanged.connect(self._recompute_slope)
		form.addRow("Rover mass (kg):", self._mass_field)

		self._power_field = QLineEdit()
		self._power_field.setPlaceholderText("hp")
		self._power_field.textChanged.connect(self._recompute_slope)
		form.addRow("Rover power (hp):", self._power_field)

		self._friction_field = QLineEdit()
		self._friction_field.setPlaceholderText("\u03bc")
		self._friction_field.textChanged.connect(self._recompute_slope)
		form.addRow("Wheel friction (\u03bc):", self._friction_field)

		self._crr_field = QLineEdit()
		self._crr_field.setPlaceholderText("Crr")
		self._crr_field.textChanged.connect(self._recompute_slope)
		form.addRow("Rolling resistance (Crr):", self._crr_field)

		form.addRow(QLabel(""))  # spacer

		self._wheel_radius_field = QLineEdit()
		self._wheel_radius_field.setPlaceholderText("m")
		self._wheel_radius_field.textChanged.connect(self._recompute_slope)
		form.addRow("Wheel radius (m):", self._wheel_radius_field)

		self._torque_field = QLineEdit()
		self._torque_field.setPlaceholderText("Nm (leave blank for power-limited)")
		self._torque_field.textChanged.connect(self._recompute_slope)
		form.addRow("Motor peak torque (Nm):", self._torque_field)

		form.addRow(QLabel(""))  # spacer

		self._track_width_field = QLineEdit()
		self._track_width_field.setPlaceholderText("m")
		form.addRow("Track width (m):", self._track_width_field)

		self._wheelbase_field = QLineEdit()
		self._wheelbase_field.setPlaceholderText("m")
		form.addRow("Wheelbase (m):", self._wheelbase_field)

		form.addRow(QLabel(""))  # spacer

		self._battery_field = QLineEdit()
		self._battery_field.setPlaceholderText("Wh")
		form.addRow("Battery capacity (Wh):", self._battery_field)

		self._rpm_field = QLineEdit()
		self._rpm_field.setPlaceholderText("RPM")
		form.addRow("Motor max RPM:", self._rpm_field)

		self._cruise_field = QLineEdit()
		self._cruise_field.setPlaceholderText("m/s")
		form.addRow("Cruise speed (m/s):", self._cruise_field)

		self._inertia_field = QLineEdit()
		self._inertia_field.setPlaceholderText("kg\u00b7m\u00b2")
		form.addRow("Wheel inertia (kg\u00b7m\u00b2):", self._inertia_field)

		self._damping_field = QLineEdit()
		self._damping_field.setPlaceholderText("N\u00b7m\u00b7s")
		form.addRow("Motor damping (N\u00b7m\u00b7s):", self._damping_field)

		self._coulomb_field = QLineEdit()
		self._coulomb_field.setPlaceholderText("N\u00b7m")
		form.addRow("Coulomb friction (N\u00b7m):", self._coulomb_field)

		self._idle_drain_field = QLineEdit()
		self._idle_drain_field.setPlaceholderText("W")
		form.addRow("Idle power drain (W):", self._idle_drain_field)

		layout.addLayout(form)

		self._max_slope_label = QLabel()
		layout.addWidget(self._max_slope_label)

		buttons = QDialogButtonBox(
			QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
		)
		buttons.accepted.connect(self._on_accept)
		buttons.rejected.connect(self.reject)
		layout.addWidget(buttons)

		# Pre-fill from current settings or default preset
		if current is not None:
			self._mass_field.setText(str(current.mass_kg))
			self._power_field.setText(str(current.power_hp))
			self._friction_field.setText(str(current.wheel_friction_coeff))
			self._crr_field.setText(str(current.rolling_resistance_coeff))
			self._wheel_radius_field.setText(str(current.wheel_radius_m))
			if current.motor_peak_torque_nm is not None:
				self._torque_field.setText(str(current.motor_peak_torque_nm))
			self._track_width_field.setText(str(current.track_width_m))
			self._wheelbase_field.setText(str(current.wheelbase_m))
			self._battery_field.setText(str(current.battery_capacity_wh))
			self._rpm_field.setText(str(current.motor_max_rpm))
			self._cruise_field.setText(str(current.target_cruise_speed_mps))
			self._inertia_field.setText(str(current.wheel_inertia_kgm2))
			self._damping_field.setText(str(current.motor_damping))
			self._coulomb_field.setText(str(current.coulomb_friction_nm))
			self._idle_drain_field.setText(str(current.idle_drain_w))
			self._update_max_slope_direct(
				current.wheel_friction_coeff,
				current.rolling_resistance_coeff,
			)
		else:
			self._on_preset_changed("Curiosity")

	def _on_preset_changed(self, name: str):
		preset = ROVER_PRESETS.get(name)
		if preset is None:
			return
		self._mass_field.setText(str(preset.mass_kg))
		self._power_field.setText(str(preset.power_hp))
		self._friction_field.setText(str(preset.wheel_friction_coeff))
		self._crr_field.setText(str(preset.rolling_resistance_coeff))
		self._wheel_radius_field.setText(str(preset.wheel_radius_m))
		if preset.motor_peak_torque_nm is not None:
			self._torque_field.setText(str(preset.motor_peak_torque_nm))
		else:
			self._torque_field.clear()
		self._track_width_field.setText(str(preset.track_width_m))
		self._wheelbase_field.setText(str(preset.wheelbase_m))
		self._battery_field.setText(str(preset.battery_capacity_wh))
		self._rpm_field.setText(str(preset.motor_max_rpm))
		self._cruise_field.setText(str(preset.target_cruise_speed_mps))
		self._inertia_field.setText(str(preset.wheel_inertia_kgm2))
		self._damping_field.setText(str(preset.motor_damping))
		self._coulomb_field.setText(str(preset.coulomb_friction_nm))
		self._idle_drain_field.setText(str(preset.idle_drain_w))
		self._update_max_slope_direct(
			preset.wheel_friction_coeff,
			preset.rolling_resistance_coeff,
		)

	def _recompute_slope(self):
		"""Live update slope label from current field values."""
		try:
			tmp = rover_settings_from_strings(
				self._mass_field.text().strip() or "1000",
				self._power_field.text().strip() or "1",
				self._friction_field.text().strip() or "0.5",
				self._crr_field.text().strip() or "0",
				wheel_radius_m=self._wheel_radius_field.text().strip() or "0.5",
				motor_peak_torque_nm=self._torque_field.text().strip() or None,
				track_width_m=self._track_width_field.text().strip() or "1.0",
				wheelbase_m=self._wheelbase_field.text().strip() or "1.5",
			)
			self._max_slope_label.setText(
				f"Max climbable slope: {tmp.max_climbable_slope_deg:.1f}\u00b0"
			)
		except (ValueError, TypeError, ZeroDivisionError):
			self._max_slope_label.setText("Max climbable slope: \u2014")

	def _update_max_slope_direct(self, mu: float, crr: float):
		angle = degrees(atan(max(0.001, mu - crr)))
		self._max_slope_label.setText(
			f"Max climbable slope: {angle:.1f}\u00b0 (traction only)"
		)

	def _on_accept(self):
		try:
			torque_str = self._torque_field.text().strip()
			settings = rover_settings_from_strings(
				self._mass_field.text().strip(),
				self._power_field.text().strip(),
				self._friction_field.text().strip(),
				self._crr_field.text().strip(),
				wheel_radius_m=self._wheel_radius_field.text().strip() or "0.5",
				motor_peak_torque_nm=torque_str if torque_str else None,
				track_width_m=self._track_width_field.text().strip() or "1.0",
				wheelbase_m=self._wheelbase_field.text().strip() or "1.5",
				battery_capacity_wh=self._battery_field.text().strip() or "500.0",
				motor_max_rpm=self._rpm_field.text().strip() or "200.0",
				target_cruise_speed_mps=self._cruise_field.text().strip() or "2.0",
				wheel_inertia_kgm2=self._inertia_field.text().strip() or "0.1",
				motor_damping=self._damping_field.text().strip() or "5.0",
				coulomb_friction_nm=self._coulomb_field.text().strip() or "0.5",
				idle_drain_w=self._idle_drain_field.text().strip() or "10.0",
			)
			self._result = settings
			self.accept()
		except (ValueError, TypeError) as exc:
			from PySide6.QtWidgets import QMessageBox

			QMessageBox.warning(
				self,
				"Invalid Rover Settings",
				f"Could not parse rover parameters:\n{exc}",
			)

	def get_settings(self) -> RoverSettings | None:
		return self._result
