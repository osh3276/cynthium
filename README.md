# CraterView

A scientific desktop application for lunar rover traversal planning and terrain analysis, focused on the lunar south pole.

## Overview

CraterView lets you load high-resolution lunar elevation and data maps, define rover traversal paths, and compute terrain statistics along those paths. It is designed for scientific use cases where map resolution, numerical accuracy, and reproducibility matter.

The tool is currently in early development.

## Features (current)

- 2D and 3D terrain visualization from GeoTIFF input

## Planned Features

- A* optimal path routing (by distance, time, or energy cost)
- Full rover traversal simulation (energy consumption, velocity, slope hazard)
- Time-dependent illumination (sun angle, permanently shadowed regions)
- Crater and rock hazard detection
- Export of traversal statistics and simulation results

## Data Sources

The app is designed for use with LOLA (Lunar Orbiter Laser Altimeter) data and other products from LRO.

## Architecture

```text
craterview/
├── src/
│   └── craterview/
│       └── app/
│           ├── main.py              # Qt application entry point
│           ├── window.py            # Main application window
│           ├── config.py            # Application configuration
│           ├── constants.py         # Shared constants
│           ├── assets/              # UI/static assets
│           ├── controllers/         # UI orchestration
│           ├── models/              # Application state and domain models
│           │   ├── layers/
│           │   ├── metadata/
│           │   ├── project.py
│           ├── ui/                  # UI components
│           │   ├── dialogs/
│           │   ├── map/
│           │   ├── panels/
│           │   └── shared/
│           ├── engine/              # Numerical backend
│           │   ├── terrain/
│           │   ├── illumination/
│           │   ├── routing/
│           │   ├── pathfinding/
│           │   ├── hazard/
│           │   ├── simulation/
│           │   ├── raster/
│           │   ├── terrain.py
│           ├── rendering/           # Visualization pipeline
│           │   ├── flat/
│           │   ├── terrain/
│           ├── processing/          # Reproducible processing pipelines
│           ├── io/                  # File I/O
│           │   ├── cache/
│           │   ├── project/
│           │   ├── raster/
│           │   └── vector/
│           ├── planetary/           # Lunar/planetary constants and CRS definitions
│           ├── services/            # Business logic
│           └── utils/               # Shared utilities
├── data/                            # Local raster datasets
└── tests/
```

## Installation

Requires Python 3.12+.

```bash
git clone https://github.com/your-username/craterview.git
cd craterview
pip install -r requirements.txt
python -m craterview.app.main
```

Key dependencies: PyQt, pyqtgraph, rasterio, numpy, PyVista.

## Usage

WIP

## Related Work

[SEXTANT](https://dspace.mit.edu/handle/1721.1/59560) is a MATLAB-based tool with similar capabilities, including 3D/2D lunar elevation maps, shadowing, heat flux, rover energy consumption, and path optimization. CraterView aims to provide an open-source Python alternative with a focus on extensibility and compatibility with large offline datasets.