# Statement of Need & Audience

## What is Cynthium?

Cynthium is a scientific desktop application for **lunar rover traversal planning** and **terrain analysis** at the lunar south pole. It loads high-resolution LOLA/LRO GeoTIFF data (20 m/px native, with optional 5 m/px effective resolution via bicubic upsampling), plans optimal paths across the surface, runs physics-based rover simulations, and computes terrain statistics along traverses.

## Problem

Planning a rover traverse on the Moon requires integrating multiple physical datasets — elevation, slope, solar illumination, temperature, meteor flux, permanently shadowed regions — into a single cost model. Researchers and mission planners currently have few options:

- **General GIS tools** (QGIS, ArcGIS) lack lunar-specific physics models (illumination via SPICE, skid-steer rover dynamics, south-pole-specific shadow mapping).
- **Ad-hoc scripts** are not reproducible, lack a UI, and don't scale to multi-layer weighted pathfinding with physics validation.

There is no open-source, desktop-grade tool that lets a scientist load lunar rasters, plan a path, simulate a rover traversing it, and export the results — all from a single GUI.

## Audience

Cynthium is built for:

| Audience | How they use it |
|---|---|
| **Planetary scientists** | Analyse terrain accessibility at candidate landing sites. Compute slope statistics, illumination exposure, and traverse feasibility across a region of interest. |
| **Mission planners** | Evaluate rover traverse routes against mission constraints (max slope, energy budget, illumination windows). Compare multiple path strategies (weighted vs. minimax). |
| **Rover engineers** | Test rover configuration parameters (mass, wheel geometry, motor torque, friction) against real terrain data before hardware decisions are made. Simulate battery drain and traversal time for specific paths. |
| **Students & educators** | Learn about pathfinding on planetary surfaces, SPICE-based illumination modelling, and physics-based rover simulation with a visual, interactive tool. |

## Why Cynthium?

- **Open source (GPL-3.0).** Anyone can inspect, modify, and redistribute the code. No license fees, no vendor lock-in.
- **Python-based.** Usable as both a GUI application and a library. The engine modules (`cynthium.app.engine`) can be imported and called programmatically.
- **Lunar-specific.** Built from the ground up for lunar south pole data: SPICE-driven illumination, slope cost models tuned for lunar regolith, permanently shadowed region detection.
- **Reproducible.** Sessions can be exported as JSON and re-loaded. Pathfinding and simulation parameters are fully configurable and recorded in output files.
- **Extensible.** Custom GeoTIFF import with CRS validation, plugin-ready architecture, well-defined subpackage boundaries.

## Use Cases

1. **Site feasibility study** — Load a south pole site (e.g. Shackleton rim, Haworth), compute illumination over a month, identify sunlit traversable corridors.
2. **Traverse optimisation** — Place waypoints, run A* with slope + illumination cost weighting, validate the resulting path via simulation.
3. **Rover configuration trade-off** — Vary mass, wheel radius, motor torque, or friction and re-simulate the same path to compare energy consumption and traversal time.
4. **Educational demonstration** — Load a preset site, place waypoints, autopath, and run the simulation step-by-step in the 3D terrain view.
