import json
from pathlib import Path


def write_settings_json(path: str | Path, settings: dict):
	"""Write all current application settings to a JSON file.

	Parameters
	----------
	path :
		Output file path.
	settings :
		Arbitrary serialisable dict of all current settings.
	"""
	with open(path, "w") as f:
		json.dump(settings, f, indent=2, default=str)
