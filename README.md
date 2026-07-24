# Cynthium

Scientific desktop application for **lunar rover traversal planning** and
**terrain analysis**, focused on the lunar south pole.

Cynthium enables loading lunar elevation data (20 m/px LOLA/LRO GeoTIFFs),
defining rover traversal paths, and computing terrain statistics along those
paths. It is designed for scientific use cases where map resolution, numerical
accuracy, and reproducibility are critical.

> **Note**: Cynthium is in beta. Things may break, change, or be
> missing. If something doesn't work or you have an idea, open an issue at
> [github.com/osh3276/cynthium/issues](https://github.com/osh3276/cynthium/issues).

## Features

- **Multi-dimensional Visualization**: 2D map views and 3D terrain
  visualisation using GeoTIFF data (LOLA / LRO). Cursor tooltip shows raster
  values under the mouse.
- **Layer Manager**: Checkable, reorderable map layers — elevation, slope,
  hillshade, solar illumination (monthly/daily avg), meteor flux/number
  (monthly/daily avg), temperature (summer/winter seasonal), and permanently
  shaded regions. Automatic refresh on preset change.
- **Waypoint Management**: Editable waypoint table with coordinate cells and
  per-waypoint pause durations. Waypoints update live on the map.
- **Advanced Pathfinding**: A\* or Dijkstra over a 16-connected grid,
  considering terrain slope, solar illumination, meteor flux, and temperature.
  Weighted cost or minimax strategy. Optional 4× bicubic upsampling for 5 m/px
  effective resolution.
- **Rover Simulation**: 4-wheel skid-steer model with stop-pivot-go
  navigation, PID speed controller, resistive motor model (back-EMF + Coulomb
  friction), and battery drain (motor power + idle draw). Configurable mass,
  power, friction, wheel geometry, motor torque, damping, and more.
- **Battery Simulation**: Motor power consumption and constant idle drain
  modelled over the full traverse, with remaining charge and total energy
  consumed in results.
- **Illumination Analysis**: Sun position calculation and shadow mapping for
  specific lunar dates and times using NASA SPICE.
- **Site Management**: Automated handling of lunar site rasters and data
  products. Data auto-downloads via pooch on first use.
- **Data Export**: Export manual paths, autopaths, simulation statistics, and
  full session settings for external analysis.
- **Custom Data Import**: Import GeoTIFF rasters with CRS validation, or load
  custom sites directly through the file picker.

## Architecture

The application is organised into subpackages under `cynthium.app`:

| Package    | Responsibility |
|------------|----------------|
| `engine`   | Core algorithms: pathfinding (A\*, Dijkstra), illumination (sun position, shadows), rover simulation (4WD skid-steer, PID control, resistive motor model, battery drain). |
| `services` | High-level orchestration: site raster management, autopath validation loop, simulation lifecycle. |
| `ui`       | PySide6 GUI: 2D map and 3D terrain views, sidebar panels, rover settings dialog, simulation results panel. |
| `io`       | GeoTIFF reading, CSV/JSON export. |
| `config`   | Application configuration, data paths, site presets. |
| `data`     | Pooch-based file registry with SHA256 hashes for auto-download from GitHub releases. |
| `utils`    | Logging and general utilities. |

## Installation

### Prerequisites

- Python 3.12 or newer.
- A working C/C++ compiler toolchain (required by `rasterio`).

### Install from source

```bash
git clone https://github.com/osh3276/cynthium.git
cd cynthium
pip install -e .
```

Key dependencies: `PySide6`, `numpy`, `rasterio`, `pyqtgraph`,
`PyVista`, `spiceypy`, `scipy`, `pooch`, `pyproj`.

## Usage

Launch Cynthium:

```bash
cynthium
```

Or:

```bash
python -m cynthium
```

The main window opens with a **sidebar** on the left, a **2D map view** in the
centre, and a **menu bar** at the top.

### Workflow

1. **Load a Site** — Select a preset lunar site (e.g. *Haworth*,
   *Shackleton rim*, *Nobile rim 1*). A 20 m/px elevation tile loads with
   colour-mapped display.
2. **Select a Map Layer** — Use the layer manager to toggle layers and
   switch between elevation, slope, illumination, temperature, meteor maps.
3. **Plan a Path** — Place waypoints on the map. Click *Autopath* to find the
   optimal route (A\*/Dijkstra). Tune pathfinding weights for slope, sun,
   meteor flux, and temperature. Editable waypoint table with per-waypoint
   pause durations.
4. **Configure the Rover** — Select a preset (Curiosity, Perseverance,
   Apollo LRV, or Artemis SR) or open **Tools → Rover Settings** to adjust
   all parameters: mass, power, friction, rolling resistance, wheel radius,
   motor torque, track width, wheelbase, battery capacity, motor RPM, cruise
   speed, wheel inertia, motor damping, Coulomb friction, and idle drain.
5. **Run a Simulation** — Hit *Run Simulation* to execute a 4-wheel
   skid-steer traverse with stop-pivot-go navigation, PID speed control,
   resistive motor model, and battery drain. Results (Path/Slope/Environment
   tabs) include distance, velocity, traversal time (including pauses),
   solar energy, battery stats, max climbable slope, and failure point.
6. **Inspect in 3D** — Switch to the 3D Terrain View tab to see the path
   draped over the digital elevation model.
7. **Export Results** — Save paths, simulation stats, or full session
   settings as CSV/JSON.

### Troubleshooting

**No path found / path too short**
  The start or goal may be on an untraversable pixel (e.g. a shadowed crater
  interior). Try moving the points to a ridge or sunlit area.

**Rover gets stuck on a seemingly gentle slope**
  Max climbable slope considers three limits: traction (μ − Crr), power
  (P/(v·m·g)), and torque (T/(r·m·g)). Increase μ, reduce mass, increase
  power, or increase motor torque.

**Data files not found**
  Cynthium will attempt to download missing files via `pooch` on first use.
  Ensure you have an internet connection for the initial fetch.

## Related Work

[SEXTANT](https://dspace.mit.edu/handle/1721.1/59560) is a MATLAB-based tool
with similar capabilities. Cynthium aims to provide an open-source Python
alternative with a focus on extensibility, high performance, and modern GIS
compatibility.
