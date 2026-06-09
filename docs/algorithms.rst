Algorithms
##########

This page explains the core mathematics behind Cynthium's pathfinding,
rover simulation, and illumination analysis.

.. contents::
   :local:
   :depth: 2

Pathfinding
***********

Cynthium uses **Theta\***, an *any-angle* pathfinding algorithm similar to A\* that
produces shorter and more realistic paths grid-based terrain.
The algorithm is as follows:

#. Initialise the open set with the start node.
#. Pop the node with the lowest :math:`f = g + h` (same as A\*),
   where :math:`g` is the accumulated cost from the start node
   and :math:`h` is the heuristic (straight-line distance to the goal).
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

.. code-block:: python

   theta_star(start_rc, goal_rc, traversable, cell_cost, elev, res_x, res_y, ...)

See :func:`cynthium.app.engine.pathfinding.theta_star.theta_star`.

Why not A\*?
============

A\* restricts path headings to 8 or 16 discrete directions (the grid
neighbourhood), producing jagged paths. Theta\* relaxes this by allowing
a node to inherit its grandparent's parent when a **line-of-sight**
(LoS) check succeeds, creating straight shortcuts across open terrain.


Cost function
=============

The total segment cost from cell :math:`a` to cell :math:`b` has two
components: a **base cost** that integrates a per-cell cost raster
:math:`C_{\text{cell}}` along the segment, and a **grade penalty** for
steepness:

.. math::

   \text{cost}(a \to b) =
   \int_{a}^{b} C_{\text{cell}} \; ds
   + w_{\text{slope}}
   \left( \frac{\theta}{\theta_{\max}} \right)^{p}
   \; \Delta s

The per-cell cost raster :math:`C_{\text{cell}}` bundles penalties from
multiple terrain layers:

.. math::

   C_{\text{cell}} = 1.0
   + w_{\text{sun}} \cdot (1.0 - I_{\text{norm}})
   + w_{\text{flux}} \cdot F_{\text{norm}}
   + w_{\text{temp}} \cdot (1.0 - T_{\text{norm}})

where:

* :math:`I_{\text{norm}}` — normalised solar illumination
  (0 = dark, 1 = full sun).
* :math:`F_{\text{norm}}` — normalised meteor flux
  (0 = low flux, 1 = high flux).
* :math:`T_{\text{norm}}` — normalised temperature
  (0 = cold, 1 = hot).
* :math:`w_{\text{sun}}` — sun weight (default 0.5).
* :math:`w_{\text{flux}}` — meteor flux weight (default 0.2).
* :math:`w_{\text{temp}}` — temperature weight (default 0.2).

Grade penalty
-------------

.. math::

   \theta = \arctan\left(\frac{|z_b - z_a|}{\Delta s_{\text{horiz}}}\right)

is the absolute grade angle in degrees, and:

* :math:`\theta_{\max}` — maximum climbable slope (default 20°).
* :math:`w_{\text{slope}}` — slope weight (default 1.0).
* :math:`p` — grade power exponent.

Cost strategy (minimax vs weighted cost)
----------------------------------------

The exponent :math:`p` controls how extreme values are treated.
It applies independently to the grade penalty and to each raster
layer (via the :math:`C_{\text{cell}}` components when ``minimax``
is selected).

* :math:`p = 1` (**Weighted cost**):
  Penalties accumulate linearly. A short stretch of bad terrain
  adds a proportional cost — the path may cut through it if the
  detour is long enough.
* :math:`p = 4` (**Minimax**):
  Penalties are raised to the 4th power. A single very steep,
  very dark, very high-flux, or very cold cell dominates the
  cost, forcing the path to avoid any extreme cell even at the
  cost of a long detour.

The heuristic :math:`h` is the straight-line Euclidean distance to the
goal (admissible, so Theta\* remains optimal).

Coordinate system
=================

All pathfinding operates in **pixel (row, col) space**. The
:func:`~cynthium.app.engine.raster.point_conversion` module converts
between geographic coordinates (latitude/longitude, projected easting/northing)
and pixel indices using the GeoTIFF's affine transform.

Dijkstra
========

Cynthium also provides a
standard **Dijkstra** implementation (no heuristic, no line-of-sight).
It attempts to produce the same shortest path as Theta\* but only along 8-connected
grid edges. As a result, paths are jagged and typically longer. It may serve as a
baseline when evaluating Theta\* improvements.

See :func:`cynthium.app.engine.pathfinding.dijkstra.dijkstra`.

Simulation
**********

Path Sampling
=============

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
========================

The simulation models the rover as a **1D point mass** moving along the
sampled path. It is always at **maximum throttle** (no PID, no steering).

Forces
------

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
--------------------

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
-------------------------

At each segment midpoint, the illumination raster is sampled. The solar
energy received is:

.. math::

   E_{\text{solar}} = \int I(t) \, dt \quad (\text{J/m}^2)

where :math:`I(t)` is the local solar irradiance (W/m²) from the
illumination map, assumed constant over the short segment duration.

Key outputs
===========

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
================

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

Path Statistics
===============

The :func:`~cynthium.app.engine.simulation.stats.calculate_path_stats`
function computes a comprehensive set of path and terrain statistics.

Geometric stats
---------------

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
--------------------

When auxiliary rasters are available, the function samples their values
at each point along the path:

* **Surface slope**: from the pre-computed slope raster (terrain
  steepness, not traversal grade).
* **Temperature**: sampled from the average temperature raster.
* **Illumination**: percent of path points with non-zero solar exposure.
* **Meteor flux**: sampled from the meteor impact flux raster.

Sun Position & Illumination
===========================

Cynthium uses **NASA SPICE** (via ``spiceypy``) to compute the Sun's
position as seen from any lunar latitude/longitude at any UTC time.

Workflow
--------

#. Load SPICE kernels (fetched on first use via ``pooch``):

   .. list-table::
      :header-rows: 1

      * - File
        - Role
      * - ``naif0012.tls``
        - Leapseconds kernel file. Used to compute the increment to be applied to UTC to give ET. [naif0012.tls]_
      * - ``de430.bsp``
        - Planet and Lunar ephemeris. Contains ephemeris data for the planet barycenters -- Mercury through Pluto (NAIF ID codes 1 through 9), plus the Sun (10), the earth mass center (399) and the moon (301). Valid from 1550 Jan 01 to 2650 Jan 22. [de430.bsp]_
      * - ``moon_pa_de440_200625.bpc``
        - Contains high-accuracy lunar orientation data from the JPL Solar System Dynamics Group's planetary ephemeris DE440. Valid from December 31, 1549 to January 25, 2650. [moon_pa_de440_200625_bpc]_
      * - ``moon_de440_250416.tf``
        - Specifies lunar body-fixed reference frames. [moon_de440_250416.tf]_
      * - ``pck00011.tpc``
        - Planetary constants kernel (Moon radii, etc.) [pck00011.tpc]_

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
------------------

* **Shadow mapping**: at a given date/time, cells where the Sun is below
  the local horizon are flagged as shadowed.
* **Illumination rasters**: pre-computed annual or daily solar exposure
  maps that feed :math:`C_{\text{cell}}` in pathfinding and the solar
  energy calculation in the simulation.

  .. note::

     The **daily-average** illumination and meteor flux rasters are
     **not true daily averages**. The sun azimuth is computed at a single
     epoch (12:00 UTC) for the raster centre, rounded to the nearest 12°
     bin (30 bins total), and the matching pre-computed angle slice is
     loaded. This gives a coarse approximation, where each bin corresponds
     to roughly one day of the lunar month, but the result is a single
     *time slice*, not a temporally averaged product.

See :func:`cynthium.app.engine.illumination.sun_position.sun_position`.

Coordinate Systems
==================

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

References
**********

.. [de430.bsp] Folkner, W. M., Williams, J. G., Boggs, D. H., Park, R. S., & Kuchynka, P. (2014). The Planetary and Lunar Ephemerides DE430 and DE431. Interplanetary Network Progress Report, 42–196, 1–81.

.. [moon_de440_250416.tf] Park, R. S., Folkner, W. M., Williams, J. G., & Boggs, D. H. (2021). The JPL Planetary and Lunar Ephemerides DE440 and DE441. The Astronomical Journal, 161(3), 105. https://doi.org/10.3847/1538-3881/abd414

.. [moon_pa_de440_200625_bpc] Bachman, Nat. NASA Navigation and Ancillary Information Facility (NAIF). (2021). SPICE Binary Lunar PCK [moon_pa_de440_200625.bpc]. Retrieved from https://naif.jpl.nasa.gov/pub/naif/generic_kernels/

.. [naif0012.tls] NASA Navigation and Ancillary Information Facility (NAIF). (2016). Leapseconds Kernel File [naif0012.tls]. Retrieved from https://naif.jpl.nasa.gov/pub/naif/generic_kernels/

.. [pck00011.tpc] Bachman, Nat. NASA Navigation and Ancillary Information Facility (NAIF). (2022). P_constants (PCK) SPICE kernel file [pck00011.tpc]. Retrieved from https://naif.jpl.nasa.gov/pub/naif/generic_kernels/
