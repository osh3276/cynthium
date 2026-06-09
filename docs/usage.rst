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
#. Configure rover parameters
#. Run pathfinding
#. Run physics simulation
#. Inspect the 3D terrain view
#. Export results to CSV

1. Load a Site
**************

#. In the sidebar, select a preset lunar site from the dropdown (e.g.
   *Haworth*, *Shackleton rim*, *Nobile rim 1*).
#. The elevation GeoTIFF loads automatically. A colour-mapped elevation
   image appears in the 2D map view.

Sites are stored under ``data/elevation/`` as 5 m/px GeoTIFFs in a lunar
south polar stereographic projection. See the :doc:`installation` page
for how data is fetched.

2. Select a Map Layer
*********************

The layer dropdown lets you switch between visualisations of the same
terrain:

* **Elevation**: raw LOLA DEM, colour-mapped from low (blue) to high (red).
* **Slope**: terrain steepness derived from the DEM.
* **Hillshade**: shaded relief for a synthetic sun angle.

  .. note::

     Hillshading is a **visual aid only**. It does not represent accurate
     shadows. The shading is based on a single synthetic light source and
     does not account for terrain occlusion, local horizon, or time of day.
     Only the azimuth of the light source is accurate to real conditions.

* **Solar Illumination**: annual or daily-average solar exposure.

  .. note::

     The **daily-average** variant is **not a true daily average**. It
     samples the sun azimuth at a single time of day, rounds to the
     nearest 12° bin (30 bins total), and loads the pre-computed raster
     for that bin. This discretisation roughly lines up with a month's
     worth of days but is only a snapshot, not a time-weighted mean.

* **Meteor Flux**: modelled meteorite impact flux.

  .. note::

     Same discretisation as the daily-average illumination: the sun
     azimuth is rounded to the nearest 12° bin and the corresponding
     angle-specific raster is used.
* **Average Temperature**: modelled surface temperature.

Each layer is a pre-computed raster stored alongside the elevation data.

3. Plan a Path
**************

#. Click on the 2D map to place a **start point** (green marker).
#. Click again to place a **goal point** (red marker).
#. Click *Autopath* to find the optimal route.
#. The optimal path is overlaid on the map as a coloured polyline.

**Pathfinding algorithm**: Theta\* (see :doc:`algorithms`), with a
Dijkstra fallback option. The algorithm minimises a weighted cost
function that blends four terrain factors:

* **Slope** — steep terrain costs more to traverse.
* **Solar illumination** — shadowed cells are penalised.
* **Meteor flux** — high-impact-flux areas are avoided.
* **Temperature** — cold areas are penalised.

The cost for each step combines a per-cell penalty from the raster
layers and a grade penalty from elevation change.  Each factor has
its own weight slider (see *Configure Pathfinding* below) — set a
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
     - ``1.0``
     - How strongly steep terrain is penalised.
       Higher values force the path to avoid slopes.
   * - ``Sun weight``
     - ``0.5``
     - How strongly shadowed cells are penalised.
       Higher values bias the path toward sunlit areas.
   * - ``Meteor flux weight``
     - ``0.2``
     - How strongly high meteor flux is penalised.
       Higher values bias the path toward low-flux areas.
   * - ``Temp weight``
     - ``0.2``
     - How strongly cold cells are penalised.
       Higher values bias the path toward warmer areas.
   * - ``Algorithm``
     - ``Theta*``
     - Which pathfinding algorithm to use:

       * **Theta*** — any-angle paths with line-of-sight
         shortcuts (shorter, more natural routes).
       * **Dijkstra** — 8-connected grid only (jagged
         paths, baseline comparison).
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

.. tip::

   **Minimax** is useful for mission-critical routes where
   exceeding a slope or shadow threshold is unacceptable.
   **Weighted cost** is better for everyday exploration where
   a reasonable trade-off is acceptable.

4. Configure the Rover
**********************

Open the rover settings panel in the sidebar and adjust:

+------------------------+----------+------------------------------------+
| Parameter              | Default  | Description                        |
+========================+==========+====================================+
| Mass                   | 150 kg   | Rover mass (affects normal force)  |
+------------------------+----------+------------------------------------+
| Power                  | 0.5 hp   | Motor power (max throttle)         |
+------------------------+----------+------------------------------------+
| Wheel Friction         | 0.5      | Traction coefficient :math:`\mu`   |
+------------------------+----------+------------------------------------+
| Rolling Resistance     | 0.1      | Regolith rolling resistance        |
+------------------------+----------+------------------------------------+

These map directly to the physics model described under :doc:`algorithms`.

5. Run a Simulation
*******************

Hit *Run Simulation* to execute the physics-based 1D rover traverse.

The simulation steps are:

#. Sample the 3D path at ~1-pixel intervals along each segment (see
   :func:`~cynthium.app.engine.simulation.path_sampling.sample_path_elevations`).
#. For each segment, compute net acceleration from thrust, gravity,
   and rolling resistance.
#. Integrate velocity and time-of-flight along the path.
#. Accumulate solar energy dose from the illumination raster.

**Results table** shows:

* Total distance travelled and straight-line displacement
* Elevation gain and net elevation change
* Average / max / min traversal slope
* Average / max / min velocity
* Traversal time
* Solar energy received (J/m²) and average illumination (W/m²)
* **Feasible?**: whether the rover could complete the traverse without
  stopping (i.e. kinetic energy never reached zero).

If the rover gets stuck, the simulation also reports the **required wheel
friction coefficient** that *would* make the traverse feasible (useful
for mission design).

6. Inspect in 3D
****************

Switch to the **3D Terrain View** tab to see the path draped over the
digital elevation model as a mesh. The view supports:

* Orbit / pan / zoom with mouse controls
* Toggling the path overlay
* Visual inspection of slopes and crater rims

The 3D renderer uses PyVista (VTK); see
:class:`cynthium.app.rendering.terrain.render.TerrainRenderer`.

7. Export Results
*****************

Use the *Export* menu item (or button) to save simulation statistics as CSV.
The CSV contains one row per simulation run with all the statistics listed
above, suitable for external analysis in Excel, MATLAB, or pandas.

Troubleshooting
***************

**No path found / path too short**
  The start or goal may be on an untraversable pixel (e.g. a shadowed
  crater interior). Try moving the points to a ridge or sunlit area.

**Rover gets stuck on a seemingly gentle slope**
  The friction coefficient :math:`\mu` determines max climbable slope via
  :math:`\theta_{\max} = \arctan(\mu)`. Increase :math:`\mu` or reduce
  the rover mass.

**Data files not found**
  Cynthium will attempt to download missing files via ``pooch`` on first
  use. Ensure you have an internet connection for the initial fetch.
