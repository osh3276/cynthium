"""Tests for config module — pure functions with local file/dir logic."""

from pathlib import Path

from cynthium.app.config import (
	DATA_ROOT,
	ensure_data_file_path,
	get_slope_path,
	resolve_data_file_path,
)


class TestGetSlopePath:
	"""Tests that the path generation logic is correct.
	Actual file existence is environment-dependent, so we test path pattern matching."""

	def test_5mpp_surf_pattern(self):
		path = get_slope_path("/some/dir/Haworth_5mpp_surf.tif")
		# The result should contain the SLOPE_DIR prefix and the expected filename
		assert str(DATA_ROOT / "slope") in str(path)
		assert "Haworth" in str(path)
		assert "slp" in str(path)

	def test_20mpp_surf_pattern(self):
		path = get_slope_path("/some/dir/Shoemaker_20mpp_surf.tif")
		# The candidate path includes the slope dir name in the filename pattern
		assert "Shoemaker" in str(path)
		assert "slp" in str(path)
		assert "20mpp" in str(path)

	def test_surf_without_mpp_pattern(self):
		path = get_slope_path("/some/dir/CustomSite_surf.tif")
		assert str(DATA_ROOT / "slope") in str(path)
		assert "CustomSite" in str(path)

	def test_generic_name(self):
		path = get_slope_path("/some/dir/map.tif")
		assert str(DATA_ROOT / "slope") in str(path)
		assert "map" in str(path)

	def test_pathlib_input(self):
		path = get_slope_path(Path("/data/Haworth_5mpp_surf.tif"))
		assert str(DATA_ROOT / "slope") in str(path)

	def test_unknown_pattern_still_returns_path(self):
		path = get_slope_path("/data/random_file.tif")
		assert str(DATA_ROOT / "slope") in str(path)


class TestResolveDataFilePath:
	def test_returns_same_path_if_exists(self, tmp_path):
		# Create a temp file
		f = tmp_path / "test.tif"
		f.write_text("dummy")
		result = resolve_data_file_path(f)
		assert result == f

	def test_returns_input_if_not_exists_and_parent_exists(self):
		p = DATA_ROOT / "nonexistent_file.tif"
		result = resolve_data_file_path(p)
		assert result == p


class TestEnsureDataFilePathDownloadFailure:
	"""A failed download must be reported (logged; popup only in the GUI) and
	must fall back to returning the unresolved path."""

	def test_failure_logged_and_path_returned(self, tmp_path, monkeypatch, caplog):
		from cynthium.app import data as data_store

		name = next(iter(data_store.REGISTRY))
		p = tmp_path / name  # exists as a registry filename, but not on disk

		def fake_fetch(filename):
			raise RuntimeError("simulated network failure")

		monkeypatch.setattr(data_store, "fetch", fake_fetch)
		with caplog.at_level("ERROR", logger="cynthium.app.data"):
			result = ensure_data_file_path(p)

		assert result == p
		assert "Failed to download" in caplog.text
		assert "simulated network failure" in caplog.text

	def test_cancelled_download_is_not_reported_as_failure(self, tmp_path, monkeypatch, caplog):
		from cynthium.app import data as data_store

		name = next(iter(data_store.REGISTRY))
		p = tmp_path / name

		def fake_fetch(filename):
			raise Exception("Download cancelled by user")

		monkeypatch.setattr(data_store, "fetch", fake_fetch)
		with caplog.at_level("INFO", logger="cynthium.app.data"):
			result = ensure_data_file_path(p)

		assert result == p
		assert "cancelled by user" in caplog.text
		assert "Failed to download" not in caplog.text
