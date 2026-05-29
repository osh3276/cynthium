# Cynthium

A scientific desktop application for lunar rover traversal planning and terrain analysis, focused on the lunar south pole.

## Overview

Cynthium enables loading high-resolution lunar elevation data, defining rover traversal paths, and computing terrain statistics along those paths. It is designed for scientific use cases where map resolution, numerical accuracy, and reproducibility are critical.

## Features

- **Multi-dimensional Visualization**: 2D map views and 3D terrain visualization using GeoTIFF data (LOLA/LRO).
- **Advanced Pathfinding**: Optimal path routing using the Theta* algorithm, considering distance and terrain slope.
- **Rover Simulation**: Physics-based traversal simulation including energy consumption, velocity, and slope-based hazards.
- **Illumination Analysis**: Sun position calculation and shadow mapping for specific lunar dates and times.
- **Site Management**: Automated handling of lunar site rasters and data products.
- **Data Export**: Export of traversal statistics and simulation results for further scientific analysis.

## Project Structure

- `src/cynthium/app/engine`: Core logic for pathfinding (Theta*), illumination (sun position, shadows), and simulation (rover dynamics).
- `src/cynthium/app/ui`: PySide6-based graphical user interface, including map viewers and control panels.
- `src/cynthium/app/rendering`: Map and terrain rendering engines using `pyqtgraph` and `PyVista`.
- `src/cynthium/app/services`: High-level services for site data and simulation management.

## Installation

### Prerequisites

- Python 3.12 or newer.

### pip Installation
Run the following command to install Cynthium from PyPI:
```bash
pip install cynthium
```

### Setup

Clone the repository:

```bash
git clone https://github.com/osh3276/cynthium.git
cd cynthium
pip install -e .
```

Key dependencies include: `PySide6`, `numpy`, `numba`, `rasterio`, `pyqtgraph`, `PyVista`, and `spiceypy`.

## Usage

You can launch Cynthium using the provided entry point:

```bash
cynthium
```

Or via Python:

```bash
python -m cynthium
```

### Quick Start

1. **Load a Site**: Use the Sidebar to select a lunar site GeoTIFF.
2. **Plan a Path**: Use the planning panel to define start and end points for traversal.
3. **Run Simulation**: Configure rover settings and run a simulation to analyze energy and hazards.
4. **View 3D**: Switch to the 3D terrain view to inspect the topography in detail.

## Related Work

[SEXTANT](https://dspace.mit.edu/handle/1721.1/59560) is a MATLAB-based tool with similar capabilities. Cynthium aims to provide an open-source Python alternative with a focus on extensibility, high performance (via Numba), and modern GIS compatibility.
