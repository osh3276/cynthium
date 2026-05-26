from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
	QFormLayout,
	QFrame,
	QHBoxLayout,
	QLabel,
	QTabWidget,
	QVBoxLayout,
	QWidget,
)

from craterview.app.engine.simulation.rover_settings import RoverSettings


@dataclass(frozen=True)
class _Field:
	label: str
	key: str
	fmt: str


def _fmt_seconds(seconds: float) -> str:
	if seconds != seconds:
		return "NaN"
	if seconds == float("inf"):
		return "inf"
	seconds_i = int(round(float(seconds)))
	h = seconds_i // 3600
	m = (seconds_i % 3600) // 60
	s = seconds_i % 60
	if h > 0:
		return f"{h}h {m:02d}m {s:02d}s"
	if m > 0:
		return f"{m}m {s:02d}s"
	return f"{s}s"


class SimulationResultsPanel(QWidget):
	def __init__(self, parent=None):
		super().__init__(parent=parent)
		self._value_labels: dict[str, QLabel] = {}
		self._build()

	def _build(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(8, 8, 8, 8)
		layout.setSpacing(6)

		header = QHBoxLayout()
		header.addWidget(QLabel("Simulation Results"))
		header.addStretch(1)
		layout.addLayout(header)

		self._status = QLabel("No simulation run yet")
		self._status.setFrameShape(QFrame.Shape.NoFrame)
		layout.addWidget(self._status)

		tabs = QTabWidget()
		layout.addWidget(tabs)

		self._path_tab = QWidget()
		self._slope_tab = QWidget()
		self._env_tab = QWidget()
		self._rover_tab = QWidget()

		tabs.addTab(self._path_tab, "Path")
		tabs.addTab(self._slope_tab, "Slope")
		tabs.addTab(self._env_tab, "Environment")
		tabs.addTab(self._rover_tab, "Rover")

		self._build_path_tab()
		self._build_slope_tab()
		self._build_env_tab()
		self._build_rover_tab()

	def _add_fields(self, parent: QWidget, fields: list[_Field]):
		form = QFormLayout(parent)
		for field in fields:
			value = QLabel("-")
			value.setTextInteractionFlags(value.textInteractionFlags())
			form.addRow(QLabel(field.label), value)
			self._value_labels[field.key] = value

	def _build_path_tab(self):
		fields = [
			_Field("Total distance", "total_distance_travelled", "{:.2f} m"),
			_Field("Total displacement", "total_displacement", "{:.2f} m"),
			_Field("Total elevation gain", "total_elevation_gain", "{:.2f} m"),
			_Field("Net elevation change", "net_elevation_change", "{:.2f} m"),
			_Field("Avg resolution", "average_resolution", "{:.2f} m/px"),
		]
		self._add_fields(self._path_tab, fields)

	def _build_slope_tab(self):
		fields = [
			_Field("Average slope", "average_slope", "{:.2f}°"),
			_Field("Max slope", "max_slope", "{:.2f}°"),
			_Field("Min slope", "min_slope", "{:.2f}°"),
		]
		self._add_fields(self._slope_tab, fields)

	def _build_env_tab(self):
		fields = [
			_Field("Max temperature (avg)", "max_temperature", "{:.2f} K"),
			_Field("Min temperature (avg)", "min_temperature", "{:.2f} K"),
			_Field("Avg temperature (avg)", "average_temperature", "{:.2f} K"),
			_Field("Illumination (yearly avg)", "percent_illumination", "{:.2f}%"),
			_Field("Avg solar illum (time-weighted)", "avg_solar_illumination_w_per_m2", "{:.2f} W/m²"),
			_Field("Solar energy (per m²)", "solar_energy_per_m2_j", "{:.2f} J/m²"),
		]
		self._add_fields(self._env_tab, fields)

	def _build_rover_tab(self):
		fields = [
			_Field("Average velocity", "average_velocity_mps", "{:.2f} m/s"),
			_Field("Min velocity", "min_velocity_mps", "{:.2f} m/s"),
			_Field("Max velocity", "max_velocity_mps", "{:.2f} m/s"),
			_Field("Traversal time", "traversal_time_s", "{}"),
			_Field("Max climbable slope", "max_climbable_slope_deg", "{:.2f}°"),
			_Field("Rover mass", "rover_mass_kg", "{:.2f} kg"),
			_Field("Rover power", "rover_power_hp", "{:.3f} hp"),
			_Field("Wheel friction coeff", "rover_mu", "{:.3f}"),
			_Field("Rolling resistance (Crr)", "rover_crr", "{:.3f}"),
			_Field("Traverse feasible", "traverse_feasible", "{}"),
			_Field("Required wheel friction (μ) (dynamic)", "required_wheel_friction_coeff", "{:.3f}"),
			_Field("Equivalent traction angle", "required_climb_slope_deg", "{:.2f}°"),
		]
		self._add_fields(self._rover_tab, fields)

	def set_error(self, message: str):
		self._status.setText(message)

	def set_stats(self, stats: dict[str, float], rover: RoverSettings | None = None):
		status = "Simulation complete"
		if float(stats.get("traverse_feasible", 1.0)) < 0.5 and rover is not None:
			req_mu = float(stats.get("required_wheel_friction_coeff", 0.0))
			status = (
				f"Traverse failed (dynamic model). Current μ={rover.wheel_friction_coeff:.3f}, "
				f"required μ={req_mu:.3f}. Please increase friction, horsepower, or decrease weight."
			)
		self._status.setText(status)

		merged = dict(stats)
		if rover is not None:
			merged["rover_mass_kg"] = float(rover.mass_kg)
			merged["rover_power_hp"] = float(rover.power_hp)
			merged["rover_mu"] = float(rover.wheel_friction_coeff)
			merged["rover_crr"] = float(rover.rolling_resistance_coeff)

		for key, label in self._value_labels.items():
			value = merged.get(key, None)
			if value is None:
				label.setText("-")
				continue

			if key == "traversal_time_s":
				label.setText(_fmt_seconds(float(value)))
				continue

			if key == "traverse_feasible":
				label.setText("Yes" if float(value) >= 0.5 else "No")
				continue

			fmt = _find_fmt_for_key(key)
			if fmt is None:
				label.setText(str(value))
				continue
			label.setText(fmt.format(float(value)))


def _find_fmt_for_key(key: str) -> str | None:
	fmts = {
		"total_distance_travelled": "{:.2f} m",
		"total_displacement": "{:.2f} m",
		"total_elevation_gain": "{:.2f} m",
		"net_elevation_change": "{:.2f} m",
		"average_resolution": "{:.2f} m/px",
		"average_slope": "{:.2f}°",
		"max_slope": "{:.2f}°",
		"min_slope": "{:.2f}°",
		"max_temperature": "{:.2f} K",
		"min_temperature": "{:.2f} K",
		"average_temperature": "{:.2f} K",
		"percent_illumination": "{:.2f}%",
		"avg_solar_illumination_w_per_m2": "{:.2f} W/m²",
		"solar_energy_per_m2_j": "{:.2f} J/m²",
		"average_velocity_mps": "{:.2f} m/s",
		"min_velocity_mps": "{:.2f} m/s",
		"max_velocity_mps": "{:.2f} m/s",
		"max_climbable_slope_deg": "{:.2f}°",
		"required_wheel_friction_coeff": "{:.3f}",
		"required_climb_slope_deg": "{:.2f}°",
		"rover_mass_kg": "{:.2f} kg",
		"rover_power_hp": "{:.3f} hp",
		"rover_mu": "{:.3f}",
		"rover_crr": "{:.3f}",
	}
	return fmts.get(key)
