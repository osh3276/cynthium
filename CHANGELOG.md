# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.2.1]: https://github.com/osh3276/cynthium/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/osh3276/cynthium/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/osh3276/cynthium/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/osh3276/cynthium/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/osh3276/cynthium/releases/tag/v1.0.0
