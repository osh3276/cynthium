Usage
=====

Launching
---------

After installation, start Cynthium from the terminal:

.. code-block:: bash

   cynthium

Or equivalently:

.. code-block:: bash

   python -m cynthium

The main window opens with a **sidebar** on the left, a **2D map view** in
the centre, and a **menu bar** at the top.

---

Workflow Overview
-----------------

Simplified pipeline:

#. Load a site raster
#. Select a map overlay layer
#. Place start and goal points on the map
#. Configure rover parameters
#. Run pathfinding
#. Run physics simulation
#. Inspect the 3D terrain view
#. Export results to CSV

---

1. Load a Site
--------------

#. In the sidebar, select a preset lunar site from the dropdown (e.g.
   *Haworth*, *Shackleton rim*, *Nobile rim 1*).
#. The elevation GeoTIFF loads automatically. A colour-mapped elevation
   image appears in the 2D map view.

Sites are stored under ``data/elevation/`` as 5 m/px GeoTIFFs in a lunar
south polar stereographic projection. See the :doc:`installation` page
for how data is fetched.

2. Select a Map Layer
---------------------

The layer dropdown lets you switch between visualisations of the same
terrain:

* **Elevation**: raw LOLA DEM, colour-mapped from low (blue) to high (red).
* **Slope**: terrain steepness derived from the DEM.
* **Hillshade**: shaded relief for a synthetic sun angle.
* **Solar Illumination**: annual or daily-average solar exposure.
* **Meteor Flux**: modelled meteorite impact flux.
* **Average Temperature**: modelled surface temperature.

Each layer is a pre-computed raster stored alongside the elevation data.

3. Plan a Path
--------------

#. Click on the 2D map to place a **start point** (green marker).
#. Click again to place a **goal point** (red marker).
#. The pathfinding engine runs automatically (or click *Find Path*).
#. The optimal path is overlaid on the map as a coloured polyline.

**Pathfinding algorithm**: Theta\* (see :doc:`algorithms`). It balances
distance against terrain slope to find a route that is both short and
traversable. The cost function is:

.. math::

   \text{cost}(a \to b) = \int_{a}^{b} C_{\text{cell}} \; ds
   + w_{\text{slope}} \left( \frac{\theta}{\theta_{\max}} \right)^{p} \; \Delta s

where :math:`C_{\text{cell}}` encodes sun/shadow penalties, :math:`\theta` is
the grade angle, and :math:`\theta_{\max}` (default 20°) is the max climbable
slope.

4. Configure the Rover
----------------------

Open the rover settings panel in the sidebar and adjust:

+------------------------+----------+------------------------------------+
| Parameter              | Default  | Description                        |
+========================+==========+====================================+
| Mass                   | 150 kg   | Rover mass (affects normal force)  |
+------------------------+----------+------------------------------------+
| Power                  | 0.5 hp   | Motor power (max throttle)         |
+------------------------+----------+------------------------------------+
| Wheel Friction         | 0.5      | Traction coefficient :math:`\mu`   |
+------------------------+----------+------------------------------------+
| Rolling Resistance     | 0.1      | Regolith rolling resistance        |
+------------------------+----------+------------------------------------+

These map directly to the physics model described under :doc:`algorithms`.

5. Run a Simulation
-------------------

Hit *Run Simulation* to execute the physics-based 1D rover traverse.

The simulation steps are:

#. Sample the 3D path at ~1‑pixel intervals along each segment (see
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
----------------

Switch to the **3D Terrain View** tab to see the path draped over the
digital elevation model as a mesh. The view supports:

* Orbit / pan / zoom with mouse controls
* Toggling the path overlay
* Visual inspection of slopes and crater rims

The 3D renderer uses PyVista (VTK); see
:class:`cynthium.app.rendering.terrain.render.TerrainRenderer`.

7. Export Results
-----------------

Use the *Export* menu item (or button) to save simulation statistics as CSV.
The CSV contains one row per simulation run with all the statistics listed
above, suitable for external analysis in Excel, MATLAB, or pandas.

Troubleshooting
---------------

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
