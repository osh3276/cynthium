Algorithms
==========

This page explains the core mathematics behind Cynthium's pathfinding,
rover simulation, and illumination analysis.

.. contents::
   :local:
   :depth: 2

---

Pathfinding: Theta\*
--------------------

Cynthium uses **Theta\***, an *any-angle* pathfinding algorithm similar to A\* that
produces shorter and more realistic paths grid-based terrain.
The algorithm is as follows:

#. Initialise the open set with the start node.
#. Pop the node with the lowest :math:`f = g + h` (same as A\*).
#. For each neighbour :math:`n` of the current node :math:`s`:

   a. Compute cost via :math:`s \to n` as candidate #0.
   b. If there is a **line-of-sight** from :math:`s`'s parent
      :math:`p(s)` to :math:`n`, compute cost via :math:`p(s) \to n`
      as candidate #1 (this is the shortcut).
   c. Use whichever candidate has lower cost.

#. The line-of-sight test uses `Bresenham's algorithm`_ to check every
   grid cell between two points. If any cell is untraversable (e.g.
   a shadowed crater interior), the shortcut is rejected.

.. _Bresenham's algorithm: https://en.wikipedia.org/wiki/Bresenham%27s_line_algorithm

Why not A\*?
^^^^^^^^^^^^

A\* restricts path headings to 8 or 16 discrete directions (the grid
neighbourhood), producing jagged paths. Theta\* relaxes this by allowing
a node to inherit its grandparent's parent when a **line-of-sight**
(LoS) check succeeds, creating straight shortcuts across open terrain.


Cost function
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The segment cost from cell :math:`a` to cell :math:`b` has two terms:

**Base cost**: integrates the :math:`C_{\text{cell}}` raster (sun/shadow
penalty) along the Bresenham line between :math:`a` and :math:`b`:

.. math::

   \text{cost}_{\text{base}} = \int_{a}^{b} C_{\text{cell}} \; ds

**Grade penalty**: adds a cost proportional to the steepness of the
segment:

.. math::

   \text{cost}_{\text{grade}} =
   w_{\text{slope}}
   \left( \frac{\theta}{\theta_{\max}} \right)^{p}
   \; \Delta s

where:

* :math:`\theta = \arctan\left(\frac{|z_b - z_a|}{\Delta s_{\text{horiz}}}\right)`
  : the absolute grade angle in degrees.
* :math:`\theta_{\max}`: the maximum climbable slope (default 20°).
* :math:`w_{\text{slope}}`: weight controlling how strongly steep terrain
  is penalised (default 1.0).
* :math:`p`: grade power exponent:

  * :math:`p = 1`: linear penalty (weighted average behaviour).
  * :math:`p > 1`: steep slopes are penalised exponentially (minimax
    behaviour, avoids extreme grades).

The heuristic :math:`h` is the straight-line Euclidean distance to the
goal (admissible, so Theta\* remains optimal).

Coordinate system
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All pathfinding operates in **pixel (row, col) space**. The
:func:`~cynthium.app.engine.raster.point_conversion` module converts
between geographic coordinates (latitude/longitude, projected easting/northing)
and pixel indices using the GeoTIFF's affine transform.

Reference
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   theta_star(start_rc, goal_rc, traversable, cell_cost, elev, res_x, res_y, ...)

See :func:`cynthium.app.engine.pathfinding.theta_star.theta_star`.

---

Fallback: Dijkstra
------------------

For comparison or constrained scenarios, Cynthium also provides a
standard **Dijkstra** implementation (no heuristic, no line-of-sight).
It produces the same shortest path as Theta\* but only along 8-connected
grid edges; paths are jagged and typically longer. It serves as a
baseline when evaluating Theta\* improvements.

See :func:`cynthium.app.engine.pathfinding.dijkstra.dijkstra`.

---

Path Sampling
-------------

Before simulation, waypoints are converted into a dense 3D polyline
sampled at approximately **one pixel per step**:

.. math::

   n_{\text{samples}} = \left\lceil \frac{\Delta s}{\text{resolution}} \right\rceil

where :math:`\Delta s` is the horizontal distance between consecutive
waypoints and *resolution* is the GeoTIFF pixel size (e.g. 5 m).

At each sample point, the elevation is read from the DEM via the affine
transform, producing an :math:`(x, y, z)` polyline that follows the
terrain surface pixel-by-pixel.

See :func:`cynthium.app.engine.simulation.path_sampling.sample_path_elevations`.

---

Rover Dynamics & Physics
------------------------

The simulation models the rover as a **1D point mass** moving along the
sampled path. It is always at **maximum throttle** (no PID, no steering).

Forces
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For each segment of the path:

.. math::

   F_{\text{net}} = F_{\text{drive}} - F_{\text{grade}} - F_{\text{roll}}

where:

* **Tractive force** (power-limited, capped by traction):

  .. math::

     F_{\text{drive}} = \min\left(
         \frac{P}{v_{\text{eff}}},\;
         \mu \, m \, g \, |\cos\theta|
     \right)

  with :math:`v_{\text{eff}} = \max(v, v_{\text{min}})` to avoid the
  :math:`P/v` singularity at zero velocity.

* **Gravity component** (uphill positive / downhill negative):

  .. math::

     F_{\text{grade}} = m \, g \, \sin\theta

* **Rolling resistance**:

  .. math::

     F_{\text{roll}} = C_{rr} \, m \, g \, |\cos\theta|

Velocity integration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Given :math:`F_{\text{net}}`, the acceleration is :math:`a = F_{\text{net}} / m`.
Velocity is integrated via the kinematic equation:

.. math::

   v_{\text{next}}^2 = v^2 + 2 a \Delta s

If :math:`v_{\text{next}}^2 \leq 0`, the rover stops mid-segment; the
traverse is **infeasible** (the rover got stuck).

The time for each segment is:

.. math::

   \Delta t = \frac{2 \Delta s}{v + v_{\text{next}}}

Solar energy accumulation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

At each segment midpoint, the illumination raster is sampled. The solar
energy received is:

.. math::

   E_{\text{solar}} = \int I(t) \, dt \quad (\text{J/m}^2)

where :math:`I(t)` is the local solar irradiance (W/m²) from the
illumination map, assumed constant over the short segment duration.

Key outputs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Output
     - Meaning
   * - ``traverse_feasible``
     - 1 if rover never stopped, 0 otherwise
   * - ``traversal_time_s``
     - Total time from start to goal
   * - ``average_velocity_mps``
     - :math:`\text{distance} / \text{time}`
   * - ``solar_energy_per_m2_j``
     - Total solar dose received
   * - ``required_friction``
     - Min :math:`\mu` needed to complete traverse

Lunar parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Parameter
     - Value
     - Source
   * - Lunar gravity
     - 1.625 m/s²
     - Standard value
   * - Max climbable slope
     - 20°
     - :math:`\arctan(\mu_{\text{max}})`

See:

* :func:`cynthium.app.engine.simulation.rover_dynamics.compute_traversal_dynamics`
* :func:`cynthium.app.engine.simulation.rover_physics.simulate_rover_over_path`

---

Path Statistics
---------------

The :func:`~cynthium.app.engine.simulation.stats.calculate_path_stats`
function computes a comprehensive set of path and terrain statistics.

Geometric stats
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Statistic
     - Formula
   * - Total distance travelled
     - :math:`\sum \|p_{i+1} - p_i\|`
   * - Total displacement
     - :math:`\|p_n - p_0\|`
   * - Total elevation gain
     - :math:`\sum \max(0, \Delta z_i)`
   * - Net elevation change
     - :math:`z_n - z_0`
   * - Average traversal slope
     - :math:`\text{mean}(\arctan(\Delta z / \Delta s_{\text{horiz}}))`

Raster-sampled stats
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When auxiliary rasters are available, the function samples their values
at each point along the path:

* **Surface slope**: from the pre-computed slope raster (terrain
  steepness, not traversal grade).
* **Temperature**: sampled from the average temperature raster.
* **Illumination**: percent of path points with non-zero solar exposure.
* **Meteor flux**: sampled from the meteor impact flux raster.

Sun Position & Illumination
----------------------------

Cynthium uses **NASA SPICE** (via ``spiceypy``) to compute the Sun's
position as seen from any lunar latitude/longitude at any UTC time.

Workflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Load SPICE kernels (fetched on first use via ``pooch``):

   .. list-table::
      :header-rows: 1

      * - File
        - Role
      * - ``naif0012.tls``
        - Leapseconds kernel (UTC → ET conversion)
      * - ``de430.bsp``
        - Planetary ephemeris (Sun, Moon, Earth positions)
      * - ``moon_pa_de440_200625.bpc``
        - Lunar orientation / binary PCK (principal axis)
      * - ``moon_de440_250416.tf``
        - Lunar frame definition (MOON_ME frame)
      * - ``pck00011.tpc``
        - Planetary constants kernel (Moon radii, etc.)
#. Convert the UTC time string to SPICE ephemeris time (ET) with
   :func:`spice.utc2et`.
#. Compute the Sun-to-Moon vector using
   :func:`spice.spkpos("SUN", et, "MOON_ME", "LT+S", "MOON")`.
#. Normalise to a unit vector.
#. Convert the observer's selenographic latitude/longitude to a local
   **up**, **east**, and **north** basis:
   :math:`\text{up} = [\cos\phi\cos\lambda,\; \cos\phi\sin\lambda,\; \sin\phi]`
#. Project the Sun vector onto this basis:

   .. math::

      \text{elevation} = \arcsin(\text{sun} \cdot \text{up})
      \qquad
      \text{azimuth} = \arctan2(\text{sun} \cdot \text{east},\; \text{sun} \cdot \text{noon})

What it's used for
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* **Shadow mapping**: at a given date/time, cells where the Sun is below
  the local horizon are flagged as shadowed.
* **Illumination rasters**: pre-computed annual or daily solar exposure
  maps that feed :math:`C_{\text{cell}}` in pathfinding and the solar
  energy calculation in the simulation.

See :func:`cynthium.app.engine.illumination.sun_position.sun_position`.

---

Coordinate Systems
------------------

Cynthium juggles three coordinate spaces:

.. list-table::
   :header-rows: 1

   * - Space
     - Description
   * - **Pixel (r, c)**
     - Row/column indices into the NumPy raster arrays. Used by
       pathfinding and sampling.
   * - **Projected (m)**
     - Easting/northing in metres, lunar south polar stereographic
       (:math:`+proj=stere +lat_0=-90 +R=1737400`). The native CRS
       of the LOLA DEMs.
   * - **Geographic**
     - Selenographic latitude/longitude in degrees on the Moon
       (:math:`+proj=longlat +R=1737400`). Used for sun position
       and display.

Conversions between pixel and projected space use the GeoTIFF's affine
transform matrix. The
:mod:`cynthium.app.engine.raster.point_conversion` module provides
these helpers.
