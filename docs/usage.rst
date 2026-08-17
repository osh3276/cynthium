Usage
#####

Launching
*********

After installation, start Cynthium from the terminal:

.. code-block:: bash

   cynthium

Or equivalently:

.. code-block:: bash

   python -m cynthium

The main window opens with a **sidebar** on the left, a **2D map view** in
the centre, and a **menu bar** at the top.

Workflow Overview
*****************

Simplified pipeline:

#. Load a site raster
#. Select a map overlay layer
#. Place start and goal points on the map
#. Configure rover parameters (preset or custom)
#. Run pathfinding
#. Run physics simulation
#. Inspect the 3D terrain view
#. Export results to CSV

1. Load a Site
**************

#. In the sidebar, select a preset lunar site from the dropdown (e.g.
   *Haworth*, *Shackleton rim*, *Nobile rim 1*).
#. A 20 m/px elevation tile loads automatically. A colour-mapped elevation
   image appears in the 2D map view.

2. Select a Map Layer
*********************

The layer manager lets you switch between visualisations of the same
terrain, hide layers with checkboxes, and reorder them in the list:

* **Elevation**: raw LOLA DEM, colour-mapped from low (blue) to high (red).
* **Slope**: terrain steepness derived from the DEM.
* **Hillshade**: shaded relief for a synthetic sun angle.

  .. note::

     Hillshading is a **visual aid only**. It does not represent accurate
     shadows. The shading is based on a single synthetic light source and
     does not account for terrain occlusion, local horizon, or time of day.
     Only the azimuth of the light source is accurate to real conditions.

* **Solar Illumination**: annual or daily-average solar exposure,
  retrieved from :cite:`lopeswiegert`.

  .. note::

     The **daily-average** variant is **not a true daily average**. It
     samples the sun azimuth at a single time of day, rounds to the
     nearest 12° bin (30 bins total), and loads the pre-computed raster
     for that bin. This discretisation roughly lines up with a month's
     worth of days but is only a snapshot, not a time-weighted mean.

     During simulation, the illumination raster is re-evaluated at each
     timestep based on the rover's current position and elapsed simulation
     time. When the sun azimuth crosses a 12° bin boundary, the
     illumination cost and solar energy accumulation switch to the
     corresponding angle-specific raster in real time.

* **Meteor Flux**: modelled meteorite impact flux, retrieved from
  :cite:`lopeswiegert`.

  .. note::

     Same discretisation as the daily-average illumination: the sun
     azimuth is rounded to the nearest 12° bin and the corresponding
     angle-specific raster is used.

* **Meteor Number**: modelled meteorite impact number flux, from the
  same source :cite:`lopeswiegert`.

  .. note::

     Also discretised by sun azimuth into 12° bins, like the meteor
     flux layer.
* **Average Temperature**: modelled surface temperature, retrieved
  from the seasonal polar temperature maps of Williams et al.
  :cite:`williams2019`, which are compiled from Diviner Lunar
  Radiometer Experiment (DLRE) data.

Each layer is a pre-computed raster stored alongside the elevation data.
Changing the active layer or selecting a preset map updates the display
automatically; the **Generate Map** button remains available as a manual
fallback.

3. Plan a Path
**************

#. Click on the 2D map to place a **start point** (green marker).
#. Click again to place a **goal point** (green marker).
#. Click *Autopath* to find the optimal route. A progress dialog appears while the path is computed.
#. The progress dialog has a **Cancel** button; closing it (or pressing Esc) stops the computation, and the background worker shuts down cleanly.
#. The optimal path is overlaid on the map as a blue polyline. If the path fails physics validation, the last attempted route is shown in blue with a **red marker** at the point where the rover got stuck.
#. Click *Clear path* at any time to remove all waypoints, autopath results, and failure markers from both the 2D map and 3D terrain view at once.

**Pathfinding algorithm**: A\* (default) or Dijkstra (see :doc:`algorithms`).
The algorithm minimises a weighted cost function that blends four terrain
factors:

* **Slope** — steep uphill terrain costs more to traverse.
* **Solar illumination** — shadowed cells are penalised.
* **Meteor flux** — high-impact-flux areas are avoided.
* **Temperature** — cold areas are penalised.

The cost for each step combines a per-cell penalty from the raster
layers and a grade penalty from elevation change.  Each factor has
its own weight slider (see *Configure Pathfinding* below). set a
weight to zero to ignore that factor entirely.

For the exact mathematical formulation see :doc:`algorithms`.

Configure Pathfinding
=====================

The **Planning** panel in the sidebar exposes several pathfinding
settings:

.. list-table::
   :header-rows: 1

   * - Setting
     - Default
     - Description
   * - ``Slope weight``
     - ``100.0``
     - How strongly steep uphill terrain is penalised.
       Higher values force the path to avoid climbs.
   * - ``Sun weight``
     - ``10.0``
     - How strongly shadowed cells are penalised.
       Higher values bias the path toward sunlit areas.
   * - ``Meteor flux weight``
     - ``5.0``
     - How strongly high meteor flux is penalised.
       Higher values bias the path toward low-flux areas.
   * - ``Temp weight``
     - ``5.0``
     - How strongly cold cells are penalised.
       Higher values bias the path toward warmer areas.
   * - ``Algorithm``
     - ``A*``
     - Which pathfinding algorithm to use:

       * **A\*** — heuristic-guided search (faster).
       * **Dijkstra** — uniform-cost search (explores more widely).
   * - ``Strategy``
     - ``Weighted cost``
     - How penalties are aggregated along the path:

       * **Weighted cost** — linear combination.  A single
         bad cell adds its penalty proportionally; the path
         may cut through a short bad patch if the detour is
         much longer.
       * **Minimax** — extreme penalties are amplified, so
         even one very steep or very dark cell dominates the
         cost.  The path will go far out of its way to avoid
         any extreme value.

   * - ``Path mode``
     - ``Waypoint to waypoint``
     - How multiple waypoints are routed:

       * **Waypoint to waypoint** — a separate path is planned
         between each consecutive pair of waypoints.
       * **Start to finish** — a single path is planned from the
         first waypoint to the last, ignoring intermediate
         waypoints as routing constraints.

   * - ``Bicubic interp.``
     - ``Off``
     - When enabled, the pathfinding search grid and
       simulation elevation sampling both operate at an
       effective **5 m/px resolution** using bicubic
       interpolation (smooth cubic spline), rather than the
       native 20 m/px nearest-neighbour lookup.

       **Pathfinding**: the elevation and cost rasters are
       upsampled 4× via ``scipy.ndimage.zoom``, so A*/
       Dijkstra can navigate around small terrain features
       that would be missed at native resolution.

       **Simulation**: path elevations are sampled at 5 m
       spacing using ``map_coordinates(order=3)``, giving
       smoother grade profiles and more accurate physics.

       Ticked via the checkbox below the pathfinding config.
       Enabling it makes both autopath and simulation slower
       but more accurate.

4. Configure the Rover
**********************

Select a rover preset from the dropdown (Curiosity, Perseverance,
Apollo LRV, or Artemis SR), or customise the parameters manually via
**Tools > Rover Settings** (accessible from the toolbar or the
**Rover Settings** button in the sidebar).

The configurable parameters are:

.. list-table::
   :header-rows: 1

   * - Parameter
     - Description
   * - ``Mass``
     - Rover mass (kg). Affects normal force, traction, and grade resistance.
   * - ``Power``
     - Motor power (hp). Limits max drive force.
   * - ``Wheel Friction``
     - Traction coefficient :math:`\mu`. Determines max tractive force before slipping.
   * - ``Rolling Resistance``
     - Regolith rolling resistance :math:`C_{rr}`.
   * - ``Wheel Radius``
     - Radius per wheel (m). Affects max speed and mechanical torque leverage.
   * - ``Motor Peak Torque``
     - Max torque per motor (N\,m). Leave empty for no torque limit.
   * - ``Track Width``
     - Lateral distance between wheel centres (m). Affects yaw stability.
   * - ``Wheelbase``
     - Longitudinal distance between wheel centres (m). Affects pitch behaviour.
   * - ``Battery Capacity``
     - Total battery energy (Wh).
   * - ``Motor Max RPM``
     - No-load max wheel speed (RPM). Determines :math:`v_{\text{max}}` via wheel radius.
   * - ``Cruise Speed``
     - Target driving speed (m/s).
   * - ``Wheel Inertia``
     - Rotational inertia per wheel (kg\,m\ :sup:`2`). Affects acceleration/deceleration.
   * - ``Motor Damping``
     - Back-EMF damping coefficient (N\,m\,s). Resistive torque proportional to \ :math:`\omega`.
   * - ``Coulomb Friction``
     - Constant friction torque per wheel (N\,m). Resistive torque independent of \ :math:`\omega`.
   * - ``Idle Drain``
     - Constant power draw (W) for computers, sensors, and avionics.

These map directly to the physics model described under :doc:`algorithms`.
Access the full settings dialog from **Tools > Rover Settings** or click
the **Rover Settings** button in the sidebar's planning panel.

5. Run a Simulation
*******************

Click *Run Simulation* to execute the physics-based 4-wheel skid-steer
rover traverse. A progress dialog appears and the UI stays responsive.
The dialog can be cancelled with the **Cancel** button, the close (X)
button, or Esc; the simulation stops at the next physics step.

The simulation steps are:

#. Sample the 3D path at ~1-pixel intervals along each segment (see
	 :func:`~cynthium.app.engine.simulation.path_sampling.sample_path_elevations`).
#. For each waypoint segment, drive toward the waypoint using a
   **stop-pivot-go** state machine:

   * **DRIVE** — target speed set by the configured cruise speed
     (ramped over the last 10 m). A PID controller outputs throttle 0–1.
   * **STOP** — once within 3 m of the waypoint, the rover brakes and stops.
   * **PAUSE** (optional) — waits for the configured per-waypoint pause
     duration before continuing.
   * **PIVOT** — applies opposing left/right thrusts to rotate in place
     until the heading aligns with the next waypoint.

#. At each timestep, compute wheel torques from the motor (drive) split per side, then
   integrate to update vehicle speed, position, and heading.
#. Accumulate solar energy, meteor energy, temperature by sampling the corresponding raster
   at the rover's current position.
#. Consume battery energy (motor power × throttle + idle drain).

**Results table** (organised into **Path**, **Slope**, and
**Environment** tabs, matching the results panel):

**Path tab**

* Total distance travelled and straight-line displacement
* Elevation gain and net elevation change
* Average resolution of the sampled path (m/px)
* Average / max velocity and traversal time (including pauses)
* **Max climbable slope** derived from traction, power-to-mass, and
  torque limits
* **Traverse feasible?**: whether the rover could complete the
  traverse
* **Battery stats**: remaining charge (%), energy consumed (kJ),
  battery capacity (Wh), and whether the battery was depleted mid-run

**Slope tab**

* Traversal slope (avg / max / min), derived from elevation change
  over 40 m spans along the path (averages out single-step grid
  artifacts; configurable via ``TRAVERSAL_SLOPE_STEP_M``)
* Surface slope (avg / max / min), sampled from the slope raster

**Environment tab**

* Temperature (avg / max / min) in K
* Illumination — percent of the path in sunlight (yearly avg),
  time-weighted average solar illumination (W/m²), and total solar
  energy received (J/m²)
* Meteor flux (avg / max / min) in J/yr·m² and meteor number
  (avg / max / min)

If the rover gets stuck or its battery is depleted, a **red marker**
appears on both the 2D map and 3D terrain view at the exact location
where it stalled, along with a text reason (e.g. "Insufficient traction
— rover cannot make progress" or "Battery depleted").  The manual path
and autopath each have their own marker.

6. Inspect in 3D
****************

Switch to the **3D Terrain View** tab to see the path draped over the
digital elevation model as a mesh. The view supports:

* Orbit / pan / zoom with mouse controls
* Toggling the path overlay
* Visual inspection of slopes and crater rims

The 3D view is built with PyVista (VTK); see
:class:`cynthium.app.ui.map.terrain_view.TerrainView`.

7. Export Results
*****************

Use **File > Export Manual Path** to save the current waypoints (x, y, z)
as a CSV file, or **File > Export Auto Path** to save the computed autopath
coordinates.

Use **File > Export Simulation Data** (Ctrl+E) to save the full simulation
statistics and path waypoints as CSV. The CSV contains one row per
simulation run with all the statistics listed above — including battery
consumption, remaining charge, and the failure reason if the traverse
failed — plus the full rover configuration in the metadata section,
suitable for external analysis in Excel, MATLAB, or pandas.

Use **File > Export Settings...** to save all current configuration — rover
preset and the full rover model (including the advanced parameters from the
rover settings dialog: wheel radius, motor torque, track width, wheelbase,
battery capacity, motor speed, cruise speed, braking, and idle drain),
autopath weights/algorithm/strategy/path mode, bicubic flag, waypoints, and
session info (site path, datetime, map type) — as a JSON file. This lets you
restore a complete working session later.

8. Import Custom Data
*********************

Cynthium can load custom elevation data in addition to the bundled site
presets. A custom GeoTIFF is treated exactly like a preset tile: it becomes
the elevation model used for display, pathfinding, and simulation, and the
bundled illumination, temperature, and meteor-flux rasters are cropped to
its bounds where they overlap.

Two ways to load a file:

* **File > Import GeoTIFF...** (Ctrl+I) validates the file against the
  requirements below and warns if they are not met.
* **File > Open** (Ctrl+O) loads any GeoTIFF without checking the CRS.
  Use this only for files you already know are in the required projection:
  all downstream processing (coordinate display, sun position, path
  conversion, simulation) assumes the lunar south-pole stereographic
  projection.

Required GeoTIFF specifications
===============================

The import check enforces the CRS; the remaining properties are assumed by
the pipeline, so a file that meets all of the following works best:

.. list-table::
   :header-rows: 1

   * - Property
     - Requirement
   * - Coordinate reference system
     - Lunar south-polar stereographic (Moon 2015 sphere, radius
       1,737,400 m, units in metres). The file must carry the projection
       embedded in its metadata:

       .. code-block:: text

          +proj=stere +lat_0=-90 +lon_0=0 +k=1 +R=1737400 +units=m +no_defs

       The comparison is semantic: files whose projection describes the same
       lunar south-polar stereographic (e.g. written with
       ``+a=1737400 +b=1737400`` instead of ``+R=1737400``, or carrying the
       ``+type=crs`` suffix) are accepted. Only a genuinely different CRS
       (different projection or sphere radius) is rejected.
   * - Data type / values
     - Any rasterio-readable band type is accepted; values are converted
       to float32 and used as-is. Provide float32 files with absolute
       elevation in metres above the Moon 2015 reference sphere. Integer
       files with an embedded scale/offset are not rescaled: the raw
       stored values are used.
   * - Bands
     - Single-band. If the file has multiple bands, only band 1 is read.
   * - Pixel size
     - Any pixel size is supported (e.g. 5, 20, or 40 m/px). The path is
       sampled at one pixel per step of the file's own resolution, and the
       bicubic interpolation option upsamples the search grid by 4×.
   * - Orientation
     - Axis-aligned and north-up (standard GeoTIFF layout: positive pixel
       width, negative pixel height). Rotated rasters are not supported.
   * - No-data cells
     - Use NaN for cells without data. Non-finite elevation is treated as
       untraversable and is excluded from statistics. Other no-data
       sentinels (e.g. -9999) are read as real elevation and produce
       artifacts such as extreme slope spikes.
   * - Geographic coverage
     - The tile should fall within the region covered by the bundled
       illumination, temperature, and meteor-flux rasters (roughly the
       area within 80°S of the lunar south pole) for those layers to
       contribute to path costs and statistics. Tiles elsewhere still
       load and can be used for elevation display, pathfinding, and
       simulation, but the environmental cost layers remain at their
       neutral values.
   * - Slope layer (optional)
     - The slope map and surface-slope statistics come from a separate
       slope GeoTIFF, looked up by filename in ``data/slope/``. For a
       custom file ``my_tile.tif``, place the matching slope raster at
       ``data/slope/my_tile_slp.tif`` (see
       :func:`cynthium.app.config.get_slope_path` for the naming rules).
       If no slope raster is found, the slope layer is unavailable and
       surface-slope statistics are skipped; hillshade and traversal-slope
       statistics still work.

**File > Import Settings...** reads a previously exported JSON settings file
and restores the rover parameters, autopath configuration, and waypoints. If
the settings include a site path that still exists on disk, the site is
loaded automatically.

Troubleshooting
***************

**No path found / path too short**
  The start or goal may be on an untraversable pixel (e.g. a shadowed
  crater interior). Try moving the points to a ridge or sunlit area.

**Rover gets stuck on a seemingly gentle slope**
  The max climbable slope considers **three limits**:

  * **Traction**: :math:`\theta_{\text{trac}} = \arctan(\mu - C_{rr})`
  * **Power**: :math:`P / (v \cdot m \cdot g) \geq \sin\theta + C_{rr}\cos\theta`
  * **Torque**: :math:`T / (r \cdot m \cdot g) \geq \sin\theta + C_{rr}\cos\theta`

  The effective limit is the **minimum** of these three.  Increase
  :math:`\mu`, reduce mass, increase power, or increase motor torque.
  A red marker on the map shows exactly where the rover stalled,
  with the failure reason displayed in the results panel.

**Autopath finds a path but it fails validation**
  The autopath retries with blocked cells up to 3 times, re-routing
  around the failed segments.  If all attempts fail, the last attempted
  route is shown in blue with a red failure marker.

**Data files not found**
  If loading a map or running a simulation for the first time, Cynthium will attempt to download missing files via ``pooch`` on first
  use. Ensure you have an internet connection for the initial fetch.
