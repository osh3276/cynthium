# Changelog

## v1.2.1b (2026-06-16)

### Bug fixes
- **Slope map not loading** — site tile suffix was ``_5mpp_surf`` but all
  elevation tiles were renamed to ``_20mpp_surf`` in v1.2.0b.  ``SUF`` updated
  to match, fixing slope raster lookup.

### Other
- Change in versioning format; beta versions will no longer be numbered, and will just be tagged "b".
  Displayed as "b0" in PyPI.

## v1.2.0b1 (2026-06-15)

### Major changes

- **Default rover: Curiosity** — renamed the default rover preset from "Custom"
  to "Curiosity" with mass=899 kg, wheel friction μ=0.5, power=0.13 hp, and
  rolling resistance Crr=0.02.
- **Autopath retry loop re-enabled** — ``MAX_ATTEMPTS`` raised from 1 to 3,
  restoring the validate-and-retry loop that blocks infeasible path cells and
  re-routes around them.
- **Perseverance rover preset** — added with mass=1025 kg, power=0.14 hp,
  wheel friction μ=0.5, rolling resistance Crr=0.02.

### Bug fixes

- **Path blocking cell misalignment** — fixed a banker's-rounding bug
  (``int(round(r))`` → ``int(r)``) that caused half the blocked cells to land
  one cell off from the actual path, making the retry loop ineffective.

### UI / UX

- **Failure point markers** — when autopath or simulation validation fails, a
  red dot is placed on both the 2D map and 3D terrain view at the exact
  location where the rover stalled. Autopath and simulation failures use
  separate markers so both remain visible simultaneously.
- **Waypoint color** — changed from white (2D) / red (3D) to bright lime green
  on both views.
- **Failed autopath path shown** — the last attempted autopath route (blue
  line) is now rendered on the map even when validation fails, so the
  failure point appears in context on the path.

## v1.1.0b1 (2026-06-12)

### Major changes

- **20 m/px elevation tiles** — replaced 5 m/px site tiles with 20 m/px tiles
  split from the LDEM mosaic. All pathfinding, simulation, and 3D rendering
  now operate at 20 m/px native resolution.
- **Pre-split tile workflow** — added ``scripts/split_ldem_tiles.py`` to crop
  the LDEM mosaic into per-site tiles. Removed the runtime cropping from the
  big LDEM TIF.
- **Removed Theta\* pathfinding** — deleted ``theta_star.py``. Replaced with
  A\* (heuristic-guided) and Dijkstra (uniform-cost) over a 16-connected grid.
  No line-of-sight shortcutting.
- **Signed grade penalty** — grade is now signed (+ uphill, − downhill).
  Only uphill segments incur a grade penalty or hard limit. Downhill
  segments are always traversable (gravity assists).
- **No hard grade cutoff** — ``_segment_cost`` no longer returns ``inf`` for
  steep uphill edges. The grade penalty smoothly increases with steepness;
  the simulation retry loop validates true physical feasibility.
- **Native-resolution pathfinding** — removed stride-based downsampling.
  ``compute_autopath`` always searches at full 20 m/px resolution so slope
  checks match the actual terrain. ``max_expanded`` scales to the search
  window size automatically.
- **Reduced retry attempts** — simulation validation loop changed from 10
  to 1 attempt.

### Bug fixes

- **Min slope no longer capped at 0** — traversal min/max slope now filters
  out near-zero grid-artifact segments (``abs(slope) < 0.05°``) so the
  reported min/max reflect the true incline of the terrain.
- **Pathfinding no longer silently fails on large grids** — ``max_expanded``
  is now set to at least the search window cell count, preventing A\*/Dijkstra
  from being cut off mid-search on large tiles like Site20v2.
- **Slope check accuracy** — removed ``_block_mean`` downsampling that
  smoothed terrain and hid steep 20 m segments from the pathfinder.

### UI / UX

- **"Running autopath..." indicator** — the autopath text box now shows
  "Running autopath..." immediately and flushes pending events before the
  synchronous search starts.
- **Removed rover specs tab** — the "Rover" tab in simulation results was
  redundant (rover inputs are already shown in the sidebar). Simulation
  outputs (velocity, traversal time, feasibility) moved to the "Path" tab.
- **Lowered path elevation offset** — 3D terrain path height reduced from
  50 m to 5 m above surface.
- **Algorithm dropdown** — sidebar now offers "A\*" and "Dijkstra" instead
  of the defunct "Theta\*".

### Data & scripts

- **``scripts/split_ldem_tiles.py``** — new script to pre-crop the 20 m/px
  LDEM mosaic into individual site tiles.
- **``scripts/remove_5mpp_tiles.py``** — new script to delete 5 m/px tiles
  (dry-run by default, pass ``--run`` to execute).
- **``cynthium/app/site_tiles.py``** — pre-computed geographic bounds for
  every site tile, decoupling tile positioning from the 5 m/px files.

### Code organisation

- **Renamed ``dijkstra.py`` → ``astar.py``** — the module contains both A\*
  and Dijkstra (``dijkstra=True`` flag). ``theta_star.py`` removed.
- **Removed ``LDEM_20MPP_PATH``** — the big LDEM TIF is no longer cropped
  at runtime. Tiles are pre-split and loaded directly via
  ``load_geotif(path_20)``.
- **Slope path lookup** — ``get_slope_path()`` now handles ``_20mpp_surf``
  naming, looking for ``*_final_adj_20mpp_slp.tif`` and ``*_20mpp_slp.tif``.

### Documentation

- README, overview, usage, and algorithms docs updated to reflect A\*/Dijkstra,
  20 m/px resolution, signed grade, no hard cutoff, and simulation validation
  loop.
- Removed references to Theta\*, Bresenham LoS, Numba.
