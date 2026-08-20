Overview
########

Cynthium is a scientific desktop application for planning lunar rover traverses
and analyzing terrain data from the lunar south pole.

Features
********

* **Multi-dimensional Visualization**: 2D map views and 3D terrain
  visualisation using data from NASA's Lunar Reconnaissance Orbiter.
* **Advanced Pathfinding**: Optimal path routing using A\* or Dijkstra,
  considering distance, terrain slope, solar illumination, meteor flux, and
  temperature.
* **Rover Simulation**: Physics-based traversal simulation including energy
  consumption, velocity, and slope-based hazards.
* **Illumination Analysis**: Sun position calculation and shadow mapping for
  specific lunar dates and times.
* **Site Management**: Automated handling of lunar site rasters and data
  products.
* **Layer Manager**: Checkboxes and reordering for map layers, with automatic
  refresh when the visible layer or preset changes.
* **Waypoint Management**: Editable waypoint table with coordinate cells,
  per-waypoint pause durations, and live map updates.
* **Cursor Value Tooltip**: Displays the raster value and unit under the
  mouse cursor (with scientific notation for large numbers).
* **Battery Simulation**: Battery drain modelling including motor power
  consumption and constant idle drain, with remaining charge and total
  energy consumed in results.
* **Data Export**: Export waypoints, autopaths, simulation statistics, and
  full application settings for further analysis.
* **Custom Data Import**: Import GeoTIFF rasters with automatic CRS
  validation, and restore complete sessions from exported settings files.

Architecture
************

The application is organised into several subpackages under
``cynthium.app``:

.. list-table::
   :header-rows: 1

   * - Package
     - Responsibility
   * - :mod:`cynthium.app.engine`
     - Core algorithms: pathfinding (A\*, Dijkstra), illumination (sun
       position, shadows), rover simulation (4WD skid-steer, adaptive
       cruise for slow rovers, PID speed control, brake model, battery
       drain).
   * - :mod:`cynthium.app.services`
     - High-level orchestration: site raster management, autopath
       validation loop, simulation lifecycle.
   * - :mod:`cynthium.app.ui`
     - PySide6-based graphical interface: 2D map and 3D terrain views,
       sidebar panels, rover settings dialog, simulation results panel.
   * - :mod:`cynthium.app.io`
     - Data reading (GeoTIFF with CRS validation), CSV/JSON export.
   * - :mod:`cynthium.app.utils`
     - Logging and general utilities.
   * - :mod:`cynthium.app.config`
     - Application configuration, data paths, site presets.
   * - :mod:`cynthium.app.data`
     - Pooch-based file registry with SHA256 hashes for automatic
       download of data products from GitHub releases.
