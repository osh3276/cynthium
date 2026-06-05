Overview
========

Cynthium is a scientific desktop application for planning lunar rover traverses
and analyzing terrain data from the lunar south pole.

Features
--------

* **Multi-dimensional Visualization**: 2D map views and 3D terrain
  visualisation using GeoTIFF data (LOLA / LRO).
* **Advanced Pathfinding**: Optimal path routing using the Theta\* algorithm,
  considering distance *and* terrain slope.
* **Rover Simulation**: Physics-based traversal simulation including energy
  consumption, velocity, and slope-based hazards.
* **Illumination Analysis**: Sun position calculation and shadow mapping for
  specific lunar dates and times.
* **Site Management**: Automated handling of lunar site rasters and data
  products.
* **Data Export**: Export traversal statistics and simulation results for
  further scientific analysis.

Architecture
------------

The application is organised into several subpackages under
``cynthium.app``:

.. list-table::
   :header-rows: 1

   * - Package
     - Responsibility
   * - :mod:`cynthium.app.engine`
     - Core algorithms: pathfinding (Theta\*, Dijkstra), illumination (sun
       position, shadows), rover simulation (dynamics, physics).
   * - :mod:`cynthium.app.rendering`
     - 2D heightmap and 3D terrain rendering via ``pyqtgraph`` and ``PyVista``.
   * - :mod:`cynthium.app.services`
     - High-level orchestration: site raster management, simulation lifecycle.
   * - :mod:`cynthium.app.ui`
     - PySide6-based graphical interface: map views, sidebar panels, dialogs.
   * - :mod:`cynthium.app.io`
     - Data reading (GeoTIFF) and export (CSV).
   * - :mod:`cynthium.app.utils`
     - Logging and general utilities.

Related Work
------------

`SEXTANT <https://dspace.mit.edu/handle/1721.1/59560>`_ is a MATLAB-based tool
with similar capabilities. Cynthium aims to provide an open-source Python
alternative with a focus on extensibility, high performance (via Numba), and
modern GIS compatibility.
