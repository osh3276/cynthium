# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] — 2026-07-27

### Fixed

- **Progress dialog hang on completion.** The dialog could hang after simulation or
  autopath finished due to lambda closure issues in cross-thread signal connections.
  Replaced lambdas with bound methods and instance variables for thread/worker
  lifecycle management. (#31dca02)
- **File I/O in background threads causing timer warnings.** Raster loading (pooch
  downloads, GeoTIFF reads) now runs exclusively on the main thread before the
  worker starts — the worker only does pure computation. Created a standalone
  `compute_path_segment()` function that takes pre-loaded numpy arrays instead of
  calling `ViewContainer.compute_autopath()` from the background thread.
- **Missing `_info_label` in PlanningPanel.** Added the missing QLabel that displays
  lat/lon coordinates for each waypoint. (#3a94c7a)

## [1.1.0] — 2026-07-26

### Added

- **Progress dialogs for long operations.** A `ProgressPopup` (non-modal dialog with
  indeterminate progress bar) now appears when running a simulation or computing an
  autopath. The computation runs in a background `QThread` so the UI stays responsive
  and the progress bar animates correctly. (#073a253)
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
- **Autopath orchestration.** Pathfinding now uses a dedicated
  `autopath_service.compute_validated_path()` with a simulation-based validation retry
  loop. (#e23815e)
- **Illumination aggregation.** Daily illumination rasters are now used for both
  pathfinding costs and simulation accuracy. Fixed import issues with daily-averaged
  data. (#6ab9eaa)
- **UI layout refresh.** Sidebar, results panel, and map views reorganized for a
  cleaner workflow. (#581238b)
- **Simulation results formatting.** Better tooltips, formatted field labels, and
  per-tab grouping (Path / Slope / Environment). (#35a38c6)
- **Dead code removal.** Stripped unused modules and legacy code paths. (#ca7f976)

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

### Removed

- **Old changelog.** Replaced with this Keep a Changelog format file. (#a2fce87)

## [1.0.0] — 2026-06-26

### Added

- Initial release with terrain analysis, manual waypoint planning, A*/Dijkstra
  pathfinding, rover simulation, and multi-format export.

[1.1.1]: https://github.com/osh3276/cynthium/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/osh3276/cynthium/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/osh3276/cynthium/releases/tag/v1.0.0
