# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.3] - 2026-08-20

### Added

- **Adaptive cruise timestep for slow rovers.** Rovers with a cruise
  speed at or below 2 m/s (`CRUISE_ADAPTIVE_SPEED_MPS`) no longer step
  the physics at the fixed 0.1 s control timestep. On straight cruise
  sections the timestep is chosen from the current speed so the rover
  advances at most 1 m per step (`CRUISE_STEP_DIST_M`, capped at 30 s),
  and a one-step **deadbeat throttle** replaces the PID speed
  controller, which limit-cycled with ±100% speed error at low speeds.
  A downhill braking branch prevents runaways on descending grades, the
  yaw rate is zeroed on entering cruise so a leftover pivot rate cannot
  halve the drive force, the approach ramp is shortened for slow rovers,
  and terrain-pitch sampling searches a window around the previous best
  segment instead of the whole path. Pauses advance in chunks of up to
  60 s of simulated time, and the simulation result now includes
  `simulation_steps`. A slow rover that previously needed ~25,000+ steps
  per 100 m now completes in a few hundred steps, so slow missions
  (e.g. Curiosity at 0.04 m/s) simulate in well under a second of wall
  time. Rovers faster than 2 m/s keep the original dt ≤ 0.1 s control
  loop with unchanged results. (#86ee3a2)

- **Cancellable autopath and simulation runs.** Both progress dialogs now
  have a **Cancel** button, and closing the dialog (X button or Esc) stops
  the running computation. The background worker shuts down cleanly, so
  closing the popup or the application mid-run no longer crashes with
  "QThread: Destroyed while thread is still running". (#33f98e6, #e19d590)

- **Full rover configuration in exported settings.** Export Settings now
  writes the complete rover model, including the advanced parameters from
  the rover settings dialog (wheel radius, motor torque, track width,
  wheelbase, battery capacity, motor speed, cruise speed, braking, idle
  drain), and Import Settings restores them, so a saved session round-trips
  completely. (#5dfc35c)

### Changed

- **Curiosity preset cruise speed set to 0.04 m/s.** The Curiosity rover
  preset now uses its real-world top speed instead of inheriting the
  2 m/s dataclass default. (#86ee3a2)

### Fixed

- **Rover settings dialog fields not applied to the simulation.** Edits to
  battery capacity, motor max RPM, target cruise speed, maximum brake
  deceleration, and idle power drain in the rover settings dialog were
  silently ignored, and the simulation always ran with the default values
  for these parameters. They now take effect. (#5dfc35c)

## [1.2.2] - 2026-08-17

### Added

- **Download-failure reporting.** When a managed data file cannot be
  downloaded, the failure is now logged with the file name and source URL,
  and in the GUI a dialog explains what failed and how to recover, instead
  of silently surfacing as a "missing raster" warning. Cancelling the
  download progress dialog is logged but does not raise an error dialog.
  The unused `fetch_all` helper was removed from `cynthium.app.data`.
  (#23a536b)

- **Documentation updates.** The usage guide now covers importing custom
  GeoTIFFs (with and without CRS validation), the simulation CSV export
  format (including battery and rover metadata), and the 40 m traversal
  slope statistic; the API docs add autodoc for the pathfinding planner
  and raster sampling modules. (#e6a4bb4)

### Fixed

- **Semantically equal projections no longer rejected when loading sites.**
  CRS validation now compares projections semantically instead of by exact
  string match, with a fallback check for the lunar south-pole
  stereographic family (stere, lat_0=-90, R=1737400), so valid tiles with
  equivalent-but-differently-written CRS definitions load without a
  "Wrong Projection" warning. (#b14cb18)

### Changed

- **Simulations download only the sun-angle maps they can use.** Angle-map
  pre-loading now takes the maximum possible traversal duration (bounded by
  the simulation step cap and rover battery) and downloads the start bin
  plus the forward arc swept by the sun, instead of all 30 bins for each of
  the illumination, meteor-energy, and meteor-number products. A typical
  rover now downloads ~4 bins (12 files) rather than 30 (90 files).
  (#b879164)

## [1.2.1] - 2026-08-13

### Added

- **Battery statistics and rover settings in simulation CSV exports.**
  `battery_energy_used_j`, `battery_remaining_pct`, `battery_capacity_wh`,
  and the failure reason are now written alongside the other simulation
  statistics, and the CSV metadata includes the full rover configuration
  (mass, power, friction, rolling resistance, wheel radius, track width,
  wheelbase, battery capacity, motor RPM, cruise speed, brake deceleration,
  idle drain). Exported runs are now self-contained enough to diagnose a
  failed traverse and to reproduce a session. (#19e1407)

### Fixed

- **Environmental cost layers in pathfinding.** Illumination, temperature,
  and meteor-flux rasters are now sampled at the correct terrain
  coordinates, so the path cost function no longer reacts to shifted data.
  Routes now respond correctly to shadow, temperature, and meteor-flux
  costs, and may differ from routes planned with earlier versions. (#19e1407)

### Changed

- **Traversal slope statistics measured over a 40 m span.** The reported
  average/maximum/minimum traversal slope now averages over 40 m of path
  instead of a single ~20 m step, removing single-step grid artifacts
  (diagonal and knight moves on the 16-connected search grid) that could
  appear as unrealistic 50°+ grades. The span is controlled by
  `TRAVERSAL_SLOPE_STEP_M` in `cynthium.app.engine.simulation.stats`;
  pathfinding and the simulation physics are unaffected. (#613d250)

## [1.2.0] — 2026-07-30

### Added

- **Sun-angle-driven illumination map switching during simulation.**
  The simulation now uses the correct illumination raster at each timestep
  based on the rover's current position and elapsed simulation time. When
  the sun azimuth crosses a 12-degree bin boundary, the illumination cost
  and solar energy accumulation switch to the corresponding angle-specific
  raster in real time. (#9a3a025)
- **Battery drain failure simulation.** The rover simulation now detects
  battery depletion during drive, pivot, and pause phases. A red marker
  appears at the exact location where the battery died, along with the
  reason text "Battery depleted". (#8b8e3f1)

### Fixed

- **Pause durations dropped in autopath pipeline.** Per-waypoint pause
  durations are now correctly propagated through the autopath validation
  loop so the simulation respects them. (#750d984)

## [1.1.1] — 2026-07-27

### Fixed

- **Progress dialog hang on completion.** The progress dialog could hang after a
  simulation or autopath finished; it now closes reliably. (#31dca02)
- **File I/O in background threads causing timer warnings.** Raster loading (pooch
  downloads, GeoTIFF reads) now runs on the main thread before the background
  worker starts, so long computations no longer trigger Qt timer warnings.
- **Missing waypoint coordinate display.** Waypoint latitude/longitude is now shown
  in the planning panel. (#3a94c7a)

## [1.1.0] — 2026-07-26

### Added

- **Progress dialogs for long operations.** A non-modal progress dialog with an
  indeterminate progress bar now appears while a simulation or autopath is computed,
  and the UI stays responsive during the calculation. (#073a253)
- **Waypoint pausing.** Each waypoint now has a configurable pause duration (seconds)
  in the planning table. The simulation respects these pauses during traversal. (#4f32df7)
- **Brake physics.** The rover simulation now models braking forces, making stopping
  behaviour more realistic. (#7d153d2)
- **4WD physics engine.** Replaced the single-wheel model with a four-wheel-drive
  physics simulation, improving traction and slope-handling accuracy. (#d76a571)
- **Wheel radius and peak torque settings.** Rover settings dialog now includes fields
  for wheel radius and motor peak torque. (#f037878)
- **Scientific notation formatting.** Simulation stats (meteor flux, etc.) now display
  in scientific notation for readability. (#3ec3d94)

### Changed

- **Rover settings overhaul.** Settings panel redesigned with new fields, presets, and
  a dedicated dialog override for fine-grained control. (#f9156a5)
- **Autopath validation.** Planned routes are now validated with the physics
  simulation before being presented, and the planner automatically re-routes around
  segments the rover cannot drive. (#e23815e)
- **Illumination aggregation.** Daily illumination rasters are now used for both
  pathfinding costs and simulation accuracy, and daily-averaged data now imports
  correctly. (#6ab9eaa)
- **UI layout refresh.** Sidebar, results panel, and map views reorganized for a
  cleaner workflow. (#581238b)
- **Simulation results formatting.** Better tooltips, formatted field labels, and
  per-tab grouping (Path / Slope / Environment). (#35a38c6)

### Fixed

- **UI freeze during simulation / autopath.** Previously the entire application would
  hang while the computation ran. Now the work is offloaded to a background thread.
- **Simulation failure reporting.** Failure points are now correctly shown on the map
  for both manual and auto paths. (#78fff1b)
- **Waypoint editing reliability.** Editing coordinates in the planning table now
  correctly updates the map views. (#4f32df7)
- **Meteor flux registration.** Added missing meteor flux entries to the raster
  registry. (#b677a55)
- **Daily illumination filtering.** Ensured daily rasters are used only when
  applicable, with fallback to yearly averages.

## [1.0.0] — 2026-06-26

### Added

- Initial release with terrain analysis, manual waypoint planning, A*/Dijkstra
  pathfinding, rover simulation, and multi-format export.

[1.2.3]: https://github.com/osh3276/cynthium/compare/v1.2.2...v1.2.3
[1.2.1]: https://github.com/osh3276/cynthium/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/osh3276/cynthium/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/osh3276/cynthium/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/osh3276/cynthium/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/osh3276/cynthium/releases/tag/v1.0.0
