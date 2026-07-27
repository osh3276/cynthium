# Cynthium

Scientific desktop app for **lunar rover traversal planning** and **terrain analysis** at the lunar south pole.
Loads 20 m/px LOLA/LRO GeoTIFFs, plans paths, and computes terrain statistics along them.

> **Beta.** If something doesn't work, open an issue at
> [github.com/osh3276/cynthium/issues](https://github.com/osh3276/cynthium/issues).

## Features

- **2D map + 3D terrain** views with cursor tooltip showing raster values
- **Layer manager** — elevation, slope, hillshade, illumination (monthly/daily avg), meteor flux, temperature, permanently shaded regions
- **Waypoint management** — editable table with per-waypoint pause durations, live on the map
- **Pathfinding** — A\*/Dijkstra over a 16-connected grid using slope, illumination, meteor flux, and temperature costs. Weighted or minimax strategy. Optional 4× bicubic upsampling for 5 m/px effective resolution
- **Rover simulation** — 4-wheel skid-steer with stop-pivot-go, PID speed control, resistive motor model, and battery drain. Configurable mass, power, friction, wheel geometry, motor torque, damping, and more
- **Illumination analysis** — sun position and shadow mapping via NASA SPICE
- **Data export** — paths, simulation stats, and full session settings as CSV/JSON
- **Custom GeoTIFF import** with CRS validation
- **Site rasters** auto-download via pooch on first use

## Install

```bash
git clone https://github.com/osh3276/cynthium.git
cd cynthium
pip install -e .
```

Requires Python ≥3.12 and a C/C++ compiler (for `rasterio`).

## Usage

```bash
cynthium
```

1. **Load a site** — pick a preset (Haworth, Shackleton rim, Nobile rim 1, ...)
2. **Choose a map layer** — elevation, slope, illumination, etc.
3. **Plan a path** — place waypoints on the map, click *Autopath*. A progress dialog keeps the UI responsive while the computation runs in a background thread
4. **Configure the rover** — select a preset or open **Tools → Rover Settings**
5. **Run a simulation** — click *Run Simulation*. Results in Path / Slope / Environment tabs with traverse time, battery stats, failure point, and more
6. **Inspect in 3D** — switch to the Terrain View tab
7. **Export** — paths, simulation data, or full session settings

## Troubleshooting

**No path found** — start or goal may be on an untraversable pixel. Try moving to a ridge or sunlit area.

**Rover gets stuck** — max climbable slope is the minimum of traction (μ − Crr), power, and torque limits. Increase μ, reduce mass, increase power, or increase motor torque.

**Data files not found** — Cynthium downloads them via pooch on first use. Needs internet.

## Related Work

[SEXTANT](https://dspace.mit.edu/handle/1721.1/59560) is a MATLAB tool with similar goals. Cynthium is an open-source Python alternative.
