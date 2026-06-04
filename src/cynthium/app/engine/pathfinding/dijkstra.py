import heapq
import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DijkstraResult:
	path_rc: list[tuple[int, int]]
	total_cost: float
	expanded: int


def _grade_deg(
	e0: float,
	e1: float,
	horiz: float,
) -> float:
	"""Grade in degrees between two points (absolute, always >= 0)."""
	if horiz < 1e-9:
		return 0.0
	dz = abs(e1 - e0)
	if not (math.isfinite(dz)):
		return 0.0
	return float(math.degrees(math.atan2(dz, horiz)))


def _segment_cost(
	*,
	rc0: tuple[int, int],
	rc1: tuple[int, int],
	cell_cost: np.ndarray,
	elev: np.ndarray,
	res_x: float,
	res_y: float,
	max_slope_deg: float,
	slope_weight: float,
	grade_power: float = 1.0,
) -> float:
	"""Cost of moving between two adjacent cells (8-connected).

	Base cost from cell_cost (sun, etc.), plus grade penalty from
	elevation difference.
	grade_power=1 → linear (weighted cost).
	grade_power > 1 → minimax (punishes steep grades exponentially).
	"""
	cc0 = float(cell_cost[rc0[0], rc0[1]])
	cc1 = float(cell_cost[rc1[0], rc1[1]])
	dr = abs(rc1[0] - rc0[0])
	dc = abs(rc1[1] - rc0[1])
	step = math.hypot(float(dc) * float(res_x), float(dr) * float(res_y))
	cost = step * 0.5 * (cc0 + cc1)

	if step > 1e-9:
		e0 = float(elev[rc0[0], rc0[1]])
		e1 = float(elev[rc1[0], rc1[1]])
		if math.isfinite(e0) and math.isfinite(e1):
			g = _grade_deg(e0, e1, step)
			max_slope = float(max_slope_deg)
			grade_norm = min(1.0, g / max_slope) if max_slope > 0 else 0.0
			cost += float(slope_weight) * (grade_norm ** float(grade_power)) * step

	return float(cost)


def dijkstra(
	*,
	start_rc: tuple[int, int],
	goal_rc: tuple[int, int],
	traversable: np.ndarray,
	cell_cost: np.ndarray,
	elev: np.ndarray,
	res_x: float,
	res_y: float,
	min_slope_deg: float = 0.0,
	max_slope_deg: float = 20.0,
	slope_weight: float = 1.0,
	grade_power: float = 1.0,
	max_expanded: int = 500000,
) -> DijkstraResult | None:
	"""Dijkstra over an 8-connected grid (no heuristic, no line-of-sight).

	- `traversable`: True where allowed (finite elevation, etc.).
	- `cell_cost`: per-cell coefficient for sun/shadow cost (>=1 recommended).
	- `elev`: elevation array used to compute grade on-the-fly.
	- `grade_power`: exponent applied to grade_norm.  1 = linear cost,
	  higher values amplify steepness penalty (minimax behavior).
	"""
	H, W = traversable.shape
	sr, sc = int(start_rc[0]), int(start_rc[1])
	gr, gc = int(goal_rc[0]), int(goal_rc[1])
	if not (0 <= sr < H and 0 <= sc < W and 0 <= gr < H and 0 <= gc < W):
		return None
	if not bool(traversable[sr, sc]) or not bool(traversable[gr, gc]):
		return None

	N = int(H * W)
	INF = float("inf")

	g = np.full((H, W), INF, dtype=np.float64)
	closed = np.zeros((H, W), dtype=bool)
	parent_r = np.full((H, W), -1, dtype=np.int32)
	parent_c = np.full((H, W), -1, dtype=np.int32)

	g[sr, sc] = 0.0
	parent_r[sr, sc] = sr
	parent_c[sr, sc] = sc

	open_heap: list[tuple[float, int, int]] = []
	heapq.heappush(open_heap, (0.0, sr, sc))

	neighbors = [
		(-1, -1),
		(-1, 0),
		(-1, 1),
		(0, -1),
		(0, 1),
		(1, -1),
		(1, 0),
		(1, 1),
	]

	expanded = 0
	while open_heap:
		cost, r, c = heapq.heappop(open_heap)
		if closed[r, c]:
			continue
		closed[r, c] = True
		expanded += 1
		if expanded > int(max_expanded):
			return None
		if r == gr and c == gc:
			break

		for dr, dc in neighbors:
			nr = int(r + dr)
			nc = int(c + dc)
			if nr < 0 or nc < 0 or nr >= H or nc >= W:
				continue
			if closed[nr, nc]:
				continue
			if not bool(traversable[nr, nc]):
				continue

			new_g = g[r, c] + _segment_cost(
				rc0=(r, c),
				rc1=(nr, nc),
				cell_cost=cell_cost,
				elev=elev,
				res_x=res_x,
				res_y=res_y,
				max_slope_deg=max_slope_deg,
				slope_weight=slope_weight,
				grade_power=grade_power,
			)
			if new_g < g[nr, nc]:
				g[nr, nc] = float(new_g)
				parent_r[nr, nc] = r
				parent_c[nr, nc] = c
				heapq.heappush(open_heap, (float(new_g), nr, nc))

	if not closed[gr, gc]:
		return None

	path: list[tuple[int, int]] = []
	r, c = gr, gc
	for _ in range(N):
		path.append((int(r), int(c)))
		pr = int(parent_r[r, c])
		pc = int(parent_c[r, c])
		if pr == r and pc == c:
			break
		if pr < 0 or pc < 0:
			break
		r, c = pr, pc
	else:
		return None

	path.reverse()
	return DijkstraResult(path_rc=path, total_cost=float(g[gr, gc]), expanded=int(expanded))
