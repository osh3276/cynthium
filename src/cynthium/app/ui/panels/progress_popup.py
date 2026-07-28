from __future__ import annotations

import traceback

import numpy as np
from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout
from scipy.ndimage import zoom

from cynthium.app.engine.pathfinding.astar import a_star


class ProgressPopup(QDialog):
	"""Non-modal popup with an indeterminate progress bar."""

	def __init__(self, title: str = "Working...", text: str = "Please wait...", parent=None):
		super().__init__(parent)
		self.setWindowTitle(title)
		self.setModal(False)
		self.setFixedSize(300, 100)

		layout = QVBoxLayout(self)
		layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

		self._label = QLabel(text)
		self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		layout.addWidget(self._label)

		bar = QProgressBar()
		bar.setRange(0, 0)  # indeterminate / busy
		bar.setFixedWidth(250)
		layout.addWidget(bar)

	def set_text(self, text: str):
		self._label.setText(text)


class Worker(QObject):
	"""Runs a callable in a background QThread."""

	finished = Signal(object)
	failed = Signal(str)

	def __init__(self, fn, *args, **kwargs):
		super().__init__()
		self._fn = fn
		self._args = args
		self._kwargs = kwargs

	@Slot()
	def run(self):
		try:
			result = self._fn(*self._args, **self._kwargs)
			self.finished.emit(result)
		except Exception:
			self.failed.emit(traceback.format_exc())


# Standalone pathfinding

_SAMPLE_FIELDS = ("illumination", "meteor", "temperature", "meteor_number")


def _sample_raster_to_grid(
	raster_data: np.ndarray | None,
	raster_meta: dict | None,
	elev: np.ndarray,
	r0: int, r1: int,
	c0: int, c1: int,
	stride: int,
	transform,
	default_value: float = 0.5,
) -> np.ndarray:
	"""Sample a raster into the elevation tile's grid and min-max normalize."""
	sampled = np.full_like(elev, np.nan, dtype=np.float32)
	if raster_data is not None and raster_meta is not None and "transform" in raster_meta:
		it = raster_meta["transform"]
		inv_it = ~it
		for r in range(0, elev.shape[0], stride):
			for c in range(0, elev.shape[1], stride):
				gr = r0 + r
				gc = c0 + c
				cr, cc = inv_it * (gc + 0.5, gr + 0.5)
				sr = int(round(cr))
				sc = int(round(cc))
				if 0 <= sr < raster_data.shape[0] and 0 <= sc < raster_data.shape[1]:
					sampled[r, c] = raster_data[sr, sc]

	mask = np.isfinite(sampled)
	if np.any(mask):
		vmin, vmax = sampled[mask].min(), sampled[mask].max()
		if vmax > vmin:
			sampled = (sampled - vmin) / (vmax - vmin)
		else:
			sampled[mask] = 0.5
	sampled[~mask] = default_value
	return sampled.astype(np.float32)


def compute_path_segment(
	*,
	start_xy: tuple[float, float],
	goal_xy: tuple[float, float],
	elevation_data: np.ndarray,
	elevation_meta: dict,
	illumination_data: np.ndarray | None,
	illumination_meta: dict | None,
	meteor_data: np.ndarray | None,
	meteor_meta: dict | None,
	temperature_data: np.ndarray | None,
	temperature_meta: dict | None,
	max_slope_deg: float = 20.0,
	slope_weight: float = 1.0,
	sun_weight: float = 0.5,
	meteor_flux_weight: float = 0.2,
	temperature_weight: float = 0.2,
	cost_strategy: str = "Weighted cost",
	algorithm: str = "A*",
	pad_cells: int = 200,
	max_expanded: int = 500000,
	blocked_cells: set[tuple[int, int]] | None = None,
	use_bicubic: bool = False,
) -> list[tuple[float, float]] | None:
	"""Pure-computation pathfinding, no file I/O or Qt access."""
	if elevation_data is None or elevation_meta is None:
		return None
	if "transform" not in elevation_meta:
		return None

	transform = elevation_meta["transform"]
	inv = ~transform
	sc_f, sr_f = inv * (float(start_xy[0]), float(start_xy[1]))
	gc_f, gr_f = inv * (float(goal_xy[0]), float(goal_xy[1]))
	sr = int(round(float(sr_f)))
	sc = int(round(float(sc_f)))
	gr = int(round(float(gr_f)))
	gc = int(round(float(gc_f)))

	H = int(elevation_data.shape[0])
	W = int(elevation_data.shape[1])
	if not (0 <= sr < H and 0 <= sc < W and 0 <= gr < H and 0 <= gc < W):
		return None

	dr = abs(gr - sr)
	dc = abs(gc - sc)
	dist_cells = int(max(dr, dc))
	pad = int(max(50, min(int(pad_cells), int(dist_cells * 0.5) + 50)))

	r0 = max(0, min(sr, gr) - pad)
	r1 = min(H, max(sr, gr) + pad + 1)
	c0 = max(0, min(sc, gc) - pad)
	c1 = min(W, max(sc, gc) + pad + 1)

	stride = 1
	upsample = 1

	elev: np.ndarray = elevation_data[r0:r1, c0:c1]
	res_x = float(abs(transform.a)) * stride
	res_y = float(abs(transform.e)) * stride

	illum_norm = _sample_raster_to_grid(
		illumination_data, illumination_meta, elev, r0, r1, c0, c1, stride, transform,
	)
	meteor_norm = _sample_raster_to_grid(
		meteor_data, meteor_meta, elev, r0, r1, c0, c1, stride, transform,
	)
	temp_norm = _sample_raster_to_grid(
		temperature_data, temperature_meta, elev, r0, r1, c0, c1, stride, transform,
	)

	if cost_strategy.strip().lower() == "minimax":
		sun_power = 4.0
		grade_power = 4.0
	else:
		sun_power = 1.0
		grade_power = 1.0

	sun_penalty = (1.0 - illum_norm)
	if sun_power != 1.0:
		sun_penalty = sun_penalty ** sun_power

	cell_cost = (
		1.0
		+ (max(0.0, sun_weight) * sun_penalty)
		+ (max(0.0, meteor_flux_weight) * meteor_norm)
		+ (max(0.0, temperature_weight) * (1.0 - temp_norm))
	).astype(np.float32)
	cell_cost = np.clip(cell_cost, 0.01, np.inf).astype(np.float32)

	traversable = np.isfinite(elev)

	if use_bicubic:
		upsample = 4
		elev = np.asarray(zoom(elev, upsample, order=3, mode="nearest"))
		cell_cost = np.repeat(np.repeat(cell_cost, upsample, axis=0), upsample, axis=1)
		traversable = np.repeat(np.repeat(traversable, upsample, axis=0), upsample, axis=1)
		if blocked_cells:
			for rr, cc in blocked_cells:
				br0 = (rr - r0) * upsample
				bc0 = (cc - c0) * upsample
				traversable[br0:br0 + upsample, bc0:bc0 + upsample] = False
			blocked_cells = None
		sr_u = (sr - r0) * upsample
		sc_u = (sc - c0) * upsample
		gr_u = (gr - r0) * upsample
		gc_u = (gc - c0) * upsample
		start_local = (float(sr_u), float(sc_u))
		goal_local = (float(gr_u), float(gc_u))
		res_x = float(abs(transform.a)) / upsample
		res_y = float(abs(transform.e)) / upsample

	max_expanded = max(max_expanded, int(elev.size))

	if blocked_cells:
		for rr, cc in blocked_cells:
			rr_local = (rr - r0) // stride
			cc_local = (cc - c0) // stride
			if 0 <= rr_local < traversable.shape[0] and 0 <= cc_local < traversable.shape[1]:
				traversable[rr_local, cc_local] = False

	if not use_bicubic:
		start_local = (float((sr - r0) // stride), float((sc - c0) // stride))
		goal_local = (float((gr - r0) // stride), float((gc - c0) // stride))

	if start_local is not None:
		sl0, sl1 = int(start_local[0]), int(start_local[1])
		if 0 <= sl0 < traversable.shape[0] and 0 <= sl1 < traversable.shape[1]:
			traversable[sl0, sl1] = True
			if not np.isfinite(cell_cost[sl0, sl1]):
				cell_cost[sl0, sl1] = 1.0
	if goal_local is not None:
		gl0, gl1 = int(goal_local[0]), int(goal_local[1])
		if 0 <= gl0 < traversable.shape[0] and 0 <= gl1 < traversable.shape[1]:
			traversable[gl0, gl1] = True
			if not np.isfinite(cell_cost[gl0, gl1]):
				cell_cost[gl0, gl1] = 1.0

	use_dijkstra = algorithm.strip().lower() == "dijkstra"
	if start_local is None or goal_local is None:
		return None

	result = a_star(
		start_rc=(int(start_local[0]), int(start_local[1])),
		goal_rc=(int(goal_local[0]), int(goal_local[1])),
		traversable=traversable,
		cell_cost=cell_cost,
		elev=np.asarray(elev),
		res_x=res_x,
		res_y=res_y,
		min_slope_deg=0.0,
		max_slope_deg=float(max_slope_deg),
		slope_weight=max(0.0, slope_weight),
		grade_power=grade_power,
		max_expanded=int(max_expanded),
		dijkstra=use_dijkstra,
	)

	if result is None or not result.path_rc:
		return None

	a_, b, c_ = float(transform.a), float(transform.b), float(transform.c)
	d, e, f_ = float(transform.d), float(transform.e), float(transform.f)
	xy: list[tuple[float, float]] = []
	for r, c in result.path_rc:
		if use_bicubic:
			grr = r0 + (r + 0.5) / upsample
			gcc = c0 + (c + 0.5) / upsample
		else:
			grr = float(r0 + (int(r) * int(stride))) + (0.5 * stride)
			gcc = float(c0 + (int(c) * int(stride))) + (0.5 * stride)
		x = (a_ * gcc) + (b * grr) + c_
		y = (d * gcc) + (e * grr) + f_
		xy.append((float(x), float(y)))

	if xy:
		xy[0] = (float(start_xy[0]), float(start_xy[1]))
		xy[-1] = (float(goal_xy[0]), float(goal_xy[1]))

	return xy
