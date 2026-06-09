# Cynthium

Scientific desktop application for **lunar rover traversal planning** and
**terrain analysis**, focused on the lunar south pole.

Cynthium enables loading high-resolution lunar elevation data (LOLA/LRO
GeoTIFFs), defining rover traversal paths, and computing terrain statistics
along those paths. It is designed for scientific use cases where map resolution,
numerical accuracy, and reproducibility are critical.

## Features

- **Multi-dimensional Visualization**: 2D map views and 3D terrain
  visualisation using GeoTIFF data (LOLA / LRO).
- **Advanced Pathfinding**: Optimal path routing using the Theta\* algorithm,
  considering distance, terrain slope, solar illumination, meteor flux, and
  temperature.
- **Rover Simulation**: Physics-based traversal simulation including energy
  consumption, velocity, and slope-based hazards.
- **Illumination Analysis**: Sun position calculation and shadow mapping for
  specific lunar dates and times using NASA SPICE.
- **Site Management**: Automated handling of lunar site rasters and data
  products.
- **Data Export**: Export traversal statistics and simulation results for
  further scientific analysis.

## Architecture

The application is organised into several subpackages under `cynthium.app`:

| Package         | Responsibility                                                  |
|-----------------|-----------------------------------------------------------------|
| `engine`        | Core algorithms: pathfinding (Theta\*, Dijkstra), illumination (sun position, shadows), rover simulation (dynamics, physics). |
| `rendering`     | 2D heightmap and 3D terrain rendering via `pyqtgraph` and `PyVista`. |
| `services`      | High-level orchestration: site raster management, simulation lifecycle. |
| `ui`            | PySide6-based graphical interface: map views, sidebar panels, dialogs. |
| `io`            | Data reading (GeoTIFF) and export (CSV).                        |
| `utils`         | Logging and general utilities.                                  |

## Installation

### Prerequisites

- Python 3.12 or newer.

### pip Install (from PyPI)

```bash
pip install cynthium
```

### Editable Install (from source)

```bash
git clone https://github.com/osh3276/cynthium.git
cd cynthium
pip install -e .
```

Key dependencies include: `PySide6`, `numpy`, `numba`, `rasterio`, `pyqtgraph`,
`PyVista`, and `spiceypy`.

## Usage

Launch Cynthium from the terminal:

```bash
cynthium
```

Or equivalently:

```bash
python -m cynthium
```

The main window opens with a **sidebar** on the left, a **2D map view** in the
centre, and a **menu bar** at the top.

### Workflow

1. **Load a Site** — In the sidebar, select a preset lunar site (e.g. *Haworth*,
   *Shackleton rim*, *Nobile rim 1*). The elevation GeoTIFF loads automatically.
2. **Select a Map Layer** — Switch between visualisations: elevation, slope,
   hillshade, solar illumination, meteor flux, or temperature.
3. **Plan a Path** — Click on the 2D map to place start and goal points, then
   click *Autopath*. The optimal route is overlaid on the map. You can tune
   pathfinding with weights for slope, sun, meteor flux, and temperature, and
   choose between Theta\* and Dijkstra.
4. **Configure the Rover** — Adjust mass, power, wheel friction, and rolling
   resistance in the rover settings panel.
5. **Run a Simulation** — Hit *Run Simulation* to execute a physics-based 1D
   rover traverse. Results include distance, velocity, traversal time, solar
   energy received, and feasibility.
6. **Inspect in 3D** — Switch to the 3D Terrain View tab to see the path draped
   over the digital elevation model.
7. **Export Results** — Save simulation statistics as CSV for external analysis.

### Troubleshooting

**No path found / path too short**
  The start or goal may be on an untraversable pixel (e.g. a shadowed crater
  interior). Try moving the points to a ridge or sunlit area.

**Rover gets stuck on a seemingly gentle slope**
  The friction coefficient determines max climbable slope. Increase friction or
  reduce rover mass.

**Data files not found**
  Cynthium will attempt to download missing files via `pooch` on first use.
  Ensure you have an internet connection for the initial fetch.

## Related Work

[SEXTANT](https://dspace.mit.edu/handle/1721.1/59560) is a MATLAB-based tool
with similar capabilities. Cynthium aims to provide an open-source Python
alternative with a focus on extensibility, high performance (via Numba), and
modern GIS compatibility.
