"""Tests for IO export functions — CSV and JSON writing."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from cynthium.app.io.export.path_csv import write_path_csv
from cynthium.app.io.export.settings_json import write_settings_json
from cynthium.app.io.export.simulation_csv import write_simulation_csv


class TestWritePathCSV:
	def test_basic_export(self):
		points = [(0.0, 0.0, 100.0), (10.0, 0.0, 105.0), (20.0, 5.0, 110.0)]
		with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=False) as f:
			path = f.name
		try:
			write_path_csv(path, points)
			content = Path(path).read_text()
			assert "index,x,y,z,pause_s" in content
			assert "1,0.0,0.0,100.0,0.0" in content
			assert "2,10.0,0.0,105.0,0.0" in content
			assert "3,20.0,5.0,110.0,0.0" in content
		finally:
			Path(path).unlink(missing_ok=True)

	def test_with_metadata(self):
		points = [(1.0, 2.0, 3.0)]
		metadata = {"site": "Haworth", "rover": "Artemis SR"}
		with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=False) as f:
			path = f.name
		try:
			write_path_csv(path, points, metadata=metadata)
			content = Path(path).read_text()
			assert "metadata_key,metadata_value" in content
			assert "site,Haworth" in content
			assert "rover,Artemis SR" in content
		finally:
			Path(path).unlink(missing_ok=True)

	def test_with_pause_durations(self):
		points = [(0.0, 0.0, 100.0), (10.0, 0.0, 105.0), (20.0, 0.0, 110.0)]
		pauses = [30.0, 60.0]
		with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=False) as f:
			path = f.name
		try:
			write_path_csv(path, points, pause_durations=pauses)
			content = Path(path).read_text()
			lines = content.strip().split("\n")
			# First waypoint: pause should be 0.0
			assert "1,0.0,0.0,100.0,0.0" in content
			# Second waypoint: first pause duration
			assert "2,10.0,0.0,105.0,30.0" in content
			# Third waypoint: second pause duration
			assert "3,20.0,0.0,110.0,60.0" in content
		finally:
			Path(path).unlink(missing_ok=True)

	def test_numpy_array_input(self):
		points = np.array([[0.0, 0.0, 100.0], [5.0, 5.0, 105.0]], dtype=np.float64)
		with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=False) as f:
			path = f.name
		try:
			write_path_csv(path, points)
			content = Path(path).read_text()
			assert "2,5.0,5.0,105.0,0.0" in content
		finally:
			Path(path).unlink(missing_ok=True)

	def test_empty_points(self):
		with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=False) as f:
			path = f.name
		try:
			write_path_csv(path, [])
			content = Path(path).read_text()
			assert "index,x,y,z,pause_s" in content
		finally:
			Path(path).unlink(missing_ok=True)


class TestWriteSimulationCSV:
	@pytest.fixture
	def sample_stats(self):
		return {
			"total_displacement": 1000.0,
			"total_distance_travelled": 1050.0,
			"total_elevation_gain": 50.0,
			"net_elevation_change": 30.0,
			"average_slope": 2.5,
			"max_slope": 10.0,
			"min_slope": 0.0,
			"surface_average_slope": 3.1,
			"surface_max_slope": 12.0,
			"surface_min_slope": 0.0,
			"average_meteor_flux": 0.5,
			"max_meteor_flux": 1.2,
			"min_meteor_flux": 0.0,
			"max_temperature": 280.0,
			"min_temperature": 250.0,
			"average_temperature": 265.0,
			"percent_illumination": 75.0,
			"average_velocity_mps": 1.5,
			"min_velocity_mps": 0.5,
			"max_velocity_mps": 2.5,
			"max_climbable_slope_deg": 25.0,
			"traversal_time_s": 700.0,
			"solar_energy_per_m2_j": 1500.0,
			"avg_solar_illumination_w_per_m2": 200.0,
			"traverse_feasible": 1.0,
			"required_wheel_friction_coeff": 0.35,
			"required_climb_slope_deg": 8.0,
		}

	def test_basic_export(self, sample_stats):
		metadata = {"site": "Nobile rim 1", "rover": "Perseverance"}
		points = np.array([[0.0, 0.0, 100.0], [1000.0, 0.0, 150.0]], dtype=np.float64)
		with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=False) as f:
			path = f.name
		try:
			write_simulation_csv(path, metadata, sample_stats, points)
			content = Path(path).read_text()
			assert "metadata_key,metadata_value" in content
			assert "total_displacement_m,1000.0" in content
			assert "traversal_time_s,700.0" in content
			assert "waypoint_index,x,y,z,pause_s" in content
			assert "1,0.0,0.0,100.0,0.0" in content
			assert "2,1000.0,0.0,150.0,0.0" in content
		finally:
			Path(path).unlink(missing_ok=True)

	def test_with_pause_durations(self, sample_stats):
		metadata = {"site": "Test"}
		points = np.array([[0.0, 0.0, 100.0], [10.0, 0.0, 105.0]], dtype=np.float64)
		with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=False) as f:
			path = f.name
		try:
			write_simulation_csv(path, metadata, sample_stats, points, pause_durations=[60.0])
			content = Path(path).read_text()
			assert "2,10.0,0.0,105.0,60.0" in content
		finally:
			Path(path).unlink(missing_ok=True)

	def test_none_points_no_crash(self, sample_stats):
		metadata = {"site": "Test"}
		with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=False) as f:
			path = f.name
		try:
			write_simulation_csv(path, metadata, sample_stats, None)
			content = Path(path).read_text()
			assert "waypoint_index" in content
		finally:
			Path(path).unlink(missing_ok=True)

	def test_missing_stats_key_defaults_zero(self, sample_stats):
		metadata = {"site": "Test"}
		# Remove one key to test default
		stats = dict(sample_stats)
		del stats["traversal_time_s"]
		with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=False) as f:
			path = f.name
		try:
			write_simulation_csv(path, metadata, stats, None)
			content = Path(path).read_text()
			assert "traversal_time_s,0.0" in content
		finally:
			Path(path).unlink(missing_ok=True)


class TestWriteSettingsJSON:
	def test_basic_export(self):
		settings = {
			"site": "Haworth",
			"rover": "Apollo LRV",
			"path_mode": "Start to finish",
			"max_slope": 20.0,
		}
		with tempfile.NamedTemporaryFile(mode="r", suffix=".json", delete=False) as f:
			path = f.name
		try:
			write_settings_json(path, settings)
			content = Path(path).read_text()
			data = json.loads(content)
			assert data["site"] == "Haworth"
			assert data["rover"] == "Apollo LRV"
			assert data["max_slope"] == 20.0
		finally:
			Path(path).unlink(missing_ok=True)

	def test_empty_dict(self):
		with tempfile.NamedTemporaryFile(mode="r", suffix=".json", delete=False) as f:
			path = f.name
		try:
			write_settings_json(path, {})
			content = Path(path).read_text()
			assert json.loads(content) == {}
		finally:
			Path(path).unlink(missing_ok=True)

	def test_nested_settings(self):
		settings = {
			"rover_params": {
				"mass_kg": 200.0,
				"power_hp": 0.5,
			},
			"cost_weights": {"slope": 100.0, "shadow": 10.0},
		}
		with tempfile.NamedTemporaryFile(mode="r", suffix=".json", delete=False) as f:
			path = f.name
		try:
			write_settings_json(path, settings)
			content = Path(path).read_text()
			data = json.loads(content)
			assert data["rover_params"]["mass_kg"] == 200.0
			assert data["cost_weights"]["shadow"] == 10.0
		finally:
			Path(path).unlink(missing_ok=True)
