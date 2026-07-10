"""High-level autopath orchestration: pathfinding + simulation retry loop."""

from __future__ import annotations

from typing import Callable

import numpy as np

from cynthium.app.engine.simulation.rover_dynamics import compute_traversal_dynamics
from cynthium.app.engine.simulation.rover_settings import RoverSettings
from cynthium.app.engine.simulation.stats import calculate_path_stats


def _build_pairs(
	waypoints_xy: list[tuple[float, float]],
	path_mode: str,
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
	"""Build start-goal pairs from waypoints based on path mode."""
	if path_mode == "Start to finish":
		return [(waypoints_xy[0], waypoints_xy[-1])]
	return [(waypoints_xy[i], waypoints_xy[i + 1]) for i in range(len(waypoints_xy) - 1)]


def _validate_segment_with_simulation(
	path_xy: list[tuple[float, float]],
	map_data_bundle: tuple,
	rover: RoverSettings,
	use_bicubic: bool,
) -> tuple[bool, dict]:
	"""Run physics simulation on a path and return (feasible, stats)."""
	try:
		map_data, map_meta, slope_data, temp_data, temp_meta, illum_data, illum_meta, meteor_data, meteor_meta = map_data_bundle
		transform = map_meta.get("transform") if map_meta else None
		temp_transform = temp_meta.get("transform") if temp_meta else None
		illum_transform = illum_meta.get("transform") if illum_meta else None
		meteor_transform = meteor_meta.get("transform") if meteor_meta else None

		points_array = np.array(path_xy)
		stats = calculate_path_stats(
			points_array, map_data, transform, slope_data,
			temp_data, temp_transform, illum_data, illum_transform,
			meteor_data, meteor_transform,
		)
		stats.update(
			compute_traversal_dynamics(
				waypoints_xyz=points_array,
				elevation_map=map_data, transform=transform,
				illumination_map=illum_data, illumination_transform=illum_transform,
				rover=rover, use_bicubic=use_bicubic,
			)
		)
		feasible = float(stats.get("traverse_feasible", 0.0)) >= 0.5
		return feasible, stats
	except Exception:
		return False, {}


def compute_validated_path(
	*,
	waypoints_xy: list[tuple[float, float]],
	path_mode: str,
	rover: RoverSettings,
	map_data_bundle: tuple,
	pathfind_fn: Callable,
	use_bicubic: bool = False,
	max_attempts: int = 20,
) -> dict:
	"""Pathfind with simulation validation retry loop.

	Returns a dict with:
	  - ``path_xy``: the final path polyline (or last attempted path)
	  - ``feasible``: whether the path passed simulation
	  - ``all_blocked``: set of blocked pixel coords from failed attempts
	  - ``failure_xy``: (x, y) where rover got stuck, or None
	  - ``stats``: simulation stats dict from last attempt
	"""
	pairs = _build_pairs(waypoints_xy, path_mode)
	all_blocked: set[tuple[int, int]] = set()
	overall_path: list[tuple[float, float]] = []
	overall_feasible = False
	last_stats: dict = {}
	last_failure_xy = None

	for attempt in range(max_attempts):
		segments: list[list[tuple[float, float]]] = []
		pathfind_failed = False

		for start_xy, goal_xy in pairs:
			seg = pathfind_fn(start_xy, goal_xy, all_blocked if all_blocked else None)
			if not seg or len(seg) < 2:
				pathfind_failed = True
				break
			segments.append(seg)

		if pathfind_failed:
			break

		overall: list[tuple[float, float]] = []
		for i, seg in enumerate(segments):
			if i == 0:
				overall.extend(seg)
			else:
				overall.extend(seg[1:])
		overall_path = overall

		feasible, stats = _validate_segment_with_simulation(
			overall_path, map_data_bundle, rover, use_bicubic,
		)
		last_stats = stats
		last_failure_xy = (
			(float(stats["failure_x"]), float(stats["failure_y"]))
			if stats.get("failure_x") is not None and stats.get("failure_y") is not None
			else None
		)

		if feasible:
			overall_feasible = True
			break

		# Block cells from this failed path
		meta = dict(map_data_bundle[1]) if map_data_bundle[1] else {}
		tr = meta.get("transform")
		if tr is not None:
			inv = ~tr
			for x, y in overall_path:
				c, r = inv * (float(x), float(y))
				all_blocked.add((int(r), int(c)))

	return {
		"path_xy": overall_path,
		"feasible": overall_feasible,
		"all_blocked": all_blocked,
		"failure_xy": last_failure_xy,
		"stats": last_stats,
	}
