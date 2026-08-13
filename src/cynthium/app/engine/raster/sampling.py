"""Resample context rasters onto an elevation tile's grid.

The pathfinding cost model needs per-cell illumination, temperature, and
meteor-flux values on the same grid as the elevation model.  These context
rasters are stored at coarser resolutions and with different origins than
the elevation tile, so this module converts each elevation-grid pixel
centre to world coordinates with the elevation affine and then to pixel
coordinates in the context raster.

Historically this logic lived (twice) in UI modules, where one copy
drifted out of sync with the other and silently sampled the wrong cells.
It lives here so every caller shares a single implementation.
"""

from __future__ import annotations

import numpy as np


def sample_raster_to_grid(
	raster_data: np.ndarray | None,
	raster_meta: dict | None,
	elev: np.ndarray,
	r0: int, r1: int,
	c0: int, c1: int,
	stride: int,
	transform,
	default_value: float = 0.5,
) -> np.ndarray:
	"""Sample a raster into the elevation tile's grid and min-max normalize.

	``elev`` is the local crop of the elevation tile (rows ``r0:r1``,
	cols ``c0:c1``) and ``transform`` is the elevation tile's affine.
	Each cell centre is mapped to world coordinates and then to
	``raster_data``'s pixel space; cells outside the raster keep
	``default_value``.  The result is normalised to [0, 1] over the
	finite sampled values.
	"""
	sampled = np.full_like(elev, np.nan, dtype=np.float32)
	if raster_data is not None and raster_meta is not None and "transform" in raster_meta:
		it = raster_meta["transform"]
		inv_it = ~it
		ia, ib, ic = float(inv_it.a), float(inv_it.b), float(inv_it.c)
		id_, ie, if_ = float(inv_it.d), float(inv_it.e), float(inv_it.f)
		a, b, c_ = float(transform.a), float(transform.b), float(transform.c)
		d, e, f_ = float(transform.d), float(transform.e), float(transform.f)

		cols = np.arange(int(c0), int(c1), int(stride), dtype=np.float64) + (0.5 * float(stride))
		for rr in range(int(r0), int(r1), int(stride)):
			rowc = float(rr) + (0.5 * float(stride))
			x = (a * cols) + (b * rowc) + c_
			y = (d * cols) + (e * rowc) + f_
			ci = np.rint((ia * x) + (ib * y) + ic).astype(np.int64)
			ri = np.rint((id_ * x) + (ie * y) + if_).astype(np.int64)

			local_r = int((rr - r0) // int(stride))
			valid = (
				(ri >= 0)
				& (ci >= 0)
				& (ri < int(raster_data.shape[0]))
				& (ci < int(raster_data.shape[1]))
			)
			if np.any(valid):
				sampled[local_r, valid] = raster_data[ri[valid], ci[valid]]

	normalized = np.full_like(sampled, default_value, dtype=np.float32)
	finite = sampled[np.isfinite(sampled)]
	if finite.size > 0:
		lo = float(np.min(finite))
		hi = float(np.max(finite))
		if hi > lo:
			normalized = ((sampled - lo) / (hi - lo)).astype(np.float32)
			normalized = np.clip(normalized, 0.0, 1.0)
			normalized[~np.isfinite(normalized)] = default_value

	return normalized
