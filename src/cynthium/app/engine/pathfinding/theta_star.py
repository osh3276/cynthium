import heapq
import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ThetaStarConfig:
	min_slope_deg: float = -90.0
	max_slope_deg: float = 20.0
	slope_weight: float = 1.0
	sun_weight: float = 0.5


@dataclass(frozen=True)
class ThetaStarResult:
	path_rc: list[tuple[int, int]]
	total_cost: float
	expanded: int


def _bresenham_line(r0: int, c0: int, r1: int, c1: int) -> list[tuple[int, int]]:
	"""Integer grid line (super basic Bresenham).

	Returns inclusive endpoints.
	"""
	x0, y0 = int(c0), int(r0)
	x1, y1 = int(c1), int(r1)

	dx = abs(x1 - x0)
	dy = abs(y1 - y0)
	sx = 1 if x1 >= x0 else -1
	sy = 1 if y1 >= y0 else -1

	x, y = x0, y0
	points: list[tuple[int, int]] = [(y, x)]

	if dx >= dy:
		err = dx // 2
		while x != x1:
			x += sx
			err -= dy
			if err < 0:
				y += sy
				err += dx
			points.append((y, x))
	else:
		err = dy // 2
		while y != y1:
			y += sy
			err -= dx
			if err < 0:
				x += sx
				err += dy
			points.append((y, x))

	return points


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
	"""Cost of the segment rc0→rc1.

	Base cost integrates cell_cost (sun, etc.) along the Bresenham line.
	Adds a grade penalty based on elevation difference between endpoints.
	grade_power=1 → linear (weighted cost).
	grade_power > 1 → minimax (punishes steep grades exponentially).
	"""
	line = _bresenham_line(rc0[0], rc0[1], rc1[0], rc1[1])
	if len(line) < 2:
		return 0.0

	max_slope = float(max_slope_deg)
	cost = 0.0
	prev_r, prev_c = line[0]
	prev_cc = float(cell_cost[prev_r, prev_c])
	prev_e = float(elev[prev_r, prev_c]) if max_slope > 0 else 0.0
	for r, c in line[1:]:
		cc = float(cell_cost[r, c])
		dr = abs(r - prev_r)
		dc = abs(c - prev_c)
		step = math.hypot(float(dc) * float(res_x), float(dr) * float(res_y))

		# Hard limit: no intermediate step may exceed max slope
		if max_slope > 0 and step > 1e-9:
			curr_e = float(elev[r, c])
			if math.isfinite(prev_e) and math.isfinite(curr_e):
				g = _grade_deg(prev_e, curr_e, step)
				if g > max_slope:
					return float("inf")
			prev_e = curr_e

		cost += step * 0.5 * (prev_cc + cc)
		prev_r, prev_c = r, c
		prev_cc = cc

	# Grade-based cost between endpoints.
	total_dr = abs(rc1[0] - rc0[0])
	total_dc = abs(rc1[1] - rc0[1])
	horiz = math.hypot(float(total_dc) * float(res_x), float(total_dr) * float(res_y))
	if horiz > 1e-9:
		e0 = float(elev[rc0[0], rc0[1]])
		e1 = float(elev[rc1[0], rc1[1]])
		if math.isfinite(e0) and math.isfinite(e1):
			g = _grade_deg(e0, e1, horiz)
			grade_norm = min(1.0, g / max_slope) if max_slope > 0 else 0.0
			cost += float(slope_weight) * (grade_norm ** float(grade_power)) * horiz

	return float(cost)


def _line_of_sight(
	*,
	rc0: tuple[int, int],
	rc1: tuple[int, int],
	traversable: np.ndarray,
) -> bool:
	"""True if rc0→rc1 is a valid shortcut.

	All intermediate cells must be traversable. Grade is handled
	by cost penalty, not hard rejection.
	"""
	for r, c in _bresenham_line(rc0[0], rc0[1], rc1[0], rc1[1]):
		if not bool(traversable[r, c]):
			return False

	return True


def _heuristic(
	*,
	rc: tuple[int, int],
	goal: tuple[int, int],
	res_x: float,
	res_y: float,
) -> float:
	dr = float(goal[0] - rc[0])
	dc = float(goal[1] - rc[1])
	return float(math.hypot(dc * float(res_x), dr * float(res_y)))


def theta_star(
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
) -> ThetaStarResult | None:
	"""Theta* over an 8-connected grid.

	- `traversable`: True where allowed (finite elevation, etc.).
	- `cell_cost`: per-cell coefficient for sun/shadow cost (>=1 recommended).
	- `elev`: elevation array used to compute grade on-the-fly.
	- Grade between two cells is computed from elevation difference; the
	  steepness penalty is added dynamically.
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
	heapq.heappush(
		open_heap,
		(
			_heuristic(rc=(sr, sc), goal=(gr, gc), res_x=res_x, res_y=res_y),
			sr,
			sc,
		),
	)

	# 8-connected + 8 knight-move directions (16-connected)
	neighbors = [
		(-1, -1),
		(-1, 0),
		(-1, 1),
		(0, -1),
		(0, 1),
		(1, -1),
		(1, 0),
		(1, 1),
		(-2, -1),
		(-2, 1),
		(2, -1),
		(2, 1),
		(-1, -2),
		(-1, 2),
		(1, -2),
		(1, 2),
	]

	expanded = 0
	while open_heap:
		_f, r, c = heapq.heappop(open_heap)
		if closed[r, c]:
			continue
		closed[r, c] = True
		expanded += 1
		if expanded > int(max_expanded):
			return None
		if r == gr and c == gc:
			break

		pr = int(parent_r[r, c])
		pc = int(parent_c[r, c])
		if pr < 0 or pc < 0:
			pr, pc = r, c

		for dr, dc in neighbors:
			nr = int(r + dr)
			nc = int(c + dc)
			if nr < 0 or nc < 0 or nr >= H or nc >= W:
				continue
			if closed[nr, nc]:
				continue
			if not bool(traversable[nr, nc]):
				continue

			best_parent = (r, c)
			best_g = g[r, c] + _segment_cost(
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

			if _line_of_sight(
				rc0=(pr, pc),
				rc1=(nr, nc),
				traversable=traversable,
			):
				cand_g = g[pr, pc] + _segment_cost(
					rc0=(pr, pc),
					rc1=(nr, nc),
					cell_cost=cell_cost,
					elev=elev,
					res_x=res_x,
					res_y=res_y,
					max_slope_deg=max_slope_deg,
					slope_weight=slope_weight,
					grade_power=grade_power,
				)
				if cand_g < best_g:
					best_g = cand_g
					best_parent = (pr, pc)

			if best_g < g[nr, nc]:
				g[nr, nc] = float(best_g)
				parent_r[nr, nc] = int(best_parent[0])
				parent_c[nr, nc] = int(best_parent[1])
				f = float(best_g) + _heuristic(
					rc=(nr, nc),
					goal=(gr, gc),
					res_x=res_x,
					res_y=res_y,
				)
				heapq.heappush(open_heap, (f, nr, nc))

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
	return ThetaStarResult(path_rc=path, total_cost=float(g[gr, gc]), expanded=int(expanded))
