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

from cynthium.app.engine.simulation.rover_settings import RoverSettings


@dataclass(frozen=True)
class _Field:
	label: str
	key: str
	fmt: str


_PATH_FIELDS = [
	_Field("Total distance", "total_distance_travelled", "{:.2f} m"),
	_Field("Total displacement", "total_displacement", "{:.2f} m"),
	_Field("Total elevation gain", "total_elevation_gain", "{:.2f} m"),
	_Field("Net elevation change", "net_elevation_change", "{:.2f} m"),
	_Field("Avg resolution", "average_resolution", "{:.2f} m/px"),
]

_SLOPE_FIELDS = [
	_Field("Traversal avg slope", "average_slope", "{:.2f}\u00b0"),
	_Field("Traversal max slope", "max_slope", "{:.2f}\u00b0"),
	_Field("Traversal min slope", "min_slope", "{:.2f}\u00b0"),
	_Field("Surface avg slope", "surface_average_slope", "{:.2f}\u00b0"),
	_Field("Surface max slope", "surface_max_slope", "{:.2f}\u00b0"),
	_Field("Surface min slope", "surface_min_slope", "{:.2f}\u00b0"),
]

_ENV_FIELDS = [
	_Field("Max temperature (avg)", "max_temperature", "{:.2f} K"),
	_Field("Min temperature (avg)", "min_temperature", "{:.2f} K"),
	_Field("Avg temperature (avg)", "average_temperature", "{:.2f} K"),
	_Field("Illumination (yearly avg)", "percent_illumination", "{:.2f}%"),
	_Field("Avg solar illum (time-weighted)", "avg_solar_illumination_w_per_m2", "{:.2f} W/m\u00b2"),
	_Field("Solar energy (per m\u00b2)", "solar_energy_per_m2_j", "{:.2f} J/m\u00b2"),
	_Field("Meteor flux (avg)", "average_meteor_flux", "{:.2f} J/yr*m\u00b2"),
	_Field("Meteor flux (max)", "max_meteor_flux", "{:.2f} J/yr*m\u00b2"),
	_Field("Meteor flux (min)", "min_meteor_flux", "{:.2f} J/yr*m\u00b2"),
]

_ROVER_FIELDS = [
	_Field("Average velocity", "average_velocity_mps", "{:.2f} m/s"),
	_Field("Min velocity", "min_velocity_mps", "{:.2f} m/s"),
	_Field("Max velocity", "max_velocity_mps", "{:.2f} m/s"),
	_Field("Traversal time", "traversal_time_s", "{}"),
	_Field("Max climbable slope", "max_climbable_slope_deg", "{:.2f}\u00b0"),
	_Field("Rover mass", "rover_mass_kg", "{:.2f} kg"),
	_Field("Rover power", "rover_power_hp", "{:.3f} hp"),
	_Field("Wheel friction coeff", "rover_mu", "{:.3f}"),
	_Field("Rolling resistance (Crr)", "rover_crr", "{:.3f}"),
	_Field("Traverse feasible", "traverse_feasible", "{}"),
	_Field("Required wheel friction (\u03bc) (dynamic)", "required_wheel_friction_coeff", "{:.3f}"),
	_Field("Equivalent traction angle", "required_climb_slope_deg", "{:.2f}\u00b0"),
]


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


def _build_tab_group(parent: QWidget, fields_list: list[list[_Field]], label_store: dict[str, QLabel]):
	"""Populate parent with a QTabWidget containing sub-tabs for each field group."""
	tabs = QTabWidget()
	tab_names = ["Path", "Slope", "Environment", "Rover"]
	for tab_name, fields in zip(tab_names, fields_list):
		tab = QWidget()
		form = QFormLayout(tab)
		for field in fields:
			value = QLabel("-")
			value.setTextInteractionFlags(value.textInteractionFlags())
			form.addRow(QLabel(field.label), value)
			label_store[field.key] = value
		tabs.addTab(tab, tab_name)

	parent_layout = QVBoxLayout(parent)
	parent_layout.setContentsMargins(0, 0, 0, 0)
	parent_layout.addWidget(tabs)


class SimulationResultsPanel(QWidget):
	def __init__(self, parent=None):
		super().__init__(parent=parent)
		self._manual_labels: dict[str, QLabel] = {}
		self._auto_labels: dict[str, QLabel] = {}
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

		outer_tabs = QTabWidget()
		layout.addWidget(outer_tabs)

		manual_tab = QWidget()
		auto_tab = QWidget()
		outer_tabs.addTab(manual_tab, "Manual Path")
		outer_tabs.addTab(auto_tab, "Auto Path")

		all_fields = [_PATH_FIELDS, _SLOPE_FIELDS, _ENV_FIELDS, _ROVER_FIELDS]
		_build_tab_group(manual_tab, all_fields, self._manual_labels)
		_build_tab_group(auto_tab, all_fields, self._auto_labels)

	def set_error(self, message: str):
		self._status.setText(message)

	def set_stats(
		self,
		manual_stats: dict[str, float],
		auto_stats: dict[str, float] | None = None,
		rover: RoverSettings | None = None,
	):
		auto_available = auto_stats is not None and bool(auto_stats)

		if not auto_available:
			status = "Simulation complete (manual path only)"
		else:
			status = "Simulation complete"

		if rover is not None:
			feasible_manual = float(manual_stats.get("traverse_feasible", 1.0))
			feasible_auto = float(auto_stats.get("traverse_feasible", 1.0)) if auto_available else 1.0
			if feasible_manual < 0.5 or feasible_auto < 0.5:
				req_mu_manual = float(manual_stats.get("required_wheel_friction_coeff", 0.0))
				status = (
					f"Traverse failed (dynamic model). "
					f"Manual path: required μ={req_mu_manual:.3f}. "
				)
				if auto_available:
					req_mu_auto = float(auto_stats.get("required_wheel_friction_coeff", 0.0))
					status += f"Auto path: required μ={req_mu_auto:.3f}. "
				status += "Please increase friction, horsepower, or decrease weight."

		self._status.setText(status)

		self._apply_stats(self._manual_labels, manual_stats, rover)
		self._apply_stats(self._auto_labels, auto_stats if auto_available else {}, rover)

	def _apply_stats(
		self,
		label_store: dict[str, QLabel],
		stats: dict[str, float],
		rover: RoverSettings | None,
	):
		merged = dict(stats)
		if rover is not None:
			merged["rover_mass_kg"] = float(rover.mass_kg)
			merged["rover_power_hp"] = float(rover.power_hp)
			merged["rover_mu"] = float(rover.wheel_friction_coeff)
			merged["rover_crr"] = float(rover.rolling_resistance_coeff)

		for key, label in label_store.items():
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
		"average_slope": "{:.2f}\u00b0",
		"max_slope": "{:.2f}\u00b0",
		"min_slope": "{:.2f}\u00b0",
		"surface_average_slope": "{:.2f}\u00b0",
		"surface_max_slope": "{:.2f}\u00b0",
		"surface_min_slope": "{:.2f}\u00b0",
		"average_meteor_flux": "{:.2f} J/yr*m\u00b2",
		"max_meteor_flux": "{:.2f} J/yr*m\u00b2",
		"min_meteor_flux": "{:.2f} J/yr*m\u00b2",
		"max_temperature": "{:.2f} K",
		"min_temperature": "{:.2f} K",
		"average_temperature": "{:.2f} K",
		"percent_illumination": "{:.2f}%",
		"avg_solar_illumination_w_per_m2": "{:.2f} W/m\u00b2",
		"solar_energy_per_m2_j": "{:.2f} J/m\u00b2",
		"average_velocity_mps": "{:.2f} m/s",
		"min_velocity_mps": "{:.2f} m/s",
		"max_velocity_mps": "{:.2f} m/s",
		"max_climbable_slope_deg": "{:.2f}\u00b0",
		"required_wheel_friction_coeff": "{:.3f}",
		"required_climb_slope_deg": "{:.2f}\u00b0",
		"rover_mass_kg": "{:.2f} kg",
		"rover_power_hp": "{:.3f} hp",
		"rover_mu": "{:.3f}",
		"rover_crr": "{:.3f}",
	}
	return fmts.get(key)
