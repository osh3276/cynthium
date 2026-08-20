Algorithms
##########

This page explains the core mathematics behind Cynthium's pathfinding,
rover simulation, and illumination analysis.

.. contents::
   :local:
   :depth: 2

Pathfinding
***********

Cynthium provides **A\*** (heuristic-guided) and **Dijkstra** (uniform-cost)
pathfinding over a 16-connected grid (8 cardinal + 8 knight-move directions).
There is no line-of-sight shortcutting — every step follows a concrete grid
edge so the grade limit is enforced on every individual transition.

.. code-block:: python

   a_star(start_rc, goal_rc, traversable, cell_cost, elev, res_x, res_y, ...)

A\* vs Dijkstra
===============

* **A\*** uses the Euclidean distance to the goal as a heuristic, which
  guides the search toward the goal and makes it faster on most terrain.
* **Dijkstra** (``dijkstra=True``) sets the heuristic to zero, exploring
  uniformly in all directions. It finds the true shortest path on the
  graph but is slower on large grids.

See :func:`cynthium.app.engine.pathfinding.astar.a_star`.

Cost function
=============

The total segment cost from cell :math:`a` to cell :math:`b` has two
components: a **base cost** that integrates a per-cell cost raster
:math:`C_{\text{cell}}` along the segment, and a **grade penalty** for
uphill steepness:

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
* :math:`w_{\text{sun}}` — sun weight (default 10.0).
* :math:`w_{\text{flux}}` — meteor flux weight (default 5.0).
* :math:`w_{\text{temp}}` — temperature weight (default 5.0).

Grade penalty
-------------

.. math::

   \theta = \arctan\left(\frac{z_b - z_a}{\Delta s_{\text{horiz}}}\right)

is the **signed** grade angle in degrees (+ uphill, − downhill).
Only uphill segments incur a grade penalty; downhill segments add
no grade cost (gravity assists the rover).

* :math:`\theta_{\max}` — maximum climbable slope (default 20°).
* :math:`w_{\text{slope}}` — slope weight (default 100.0).
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
goal.

Coordinate system
=================

All pathfinding operates in **pixel (row, col) space**. The
:func:`~cynthium.app.engine.raster.point_conversion` module converts
between geographic coordinates (latitude/longitude, projected easting/northing)
and pixel indices using the GeoTIFF's affine transform.

Simulation validation loop
==========================

The autopath workflow uses a simulation validation loop to ensure
paths are physically traversable:

.. code-block:: python

   for attempt in range(MAX_ATTEMPTS):
       path = pathfind(start, goal, ...)
       stats = simulate(path, rover, ...)
       if stats["traverse_feasible"]:
           break
       # Block failed cells and retry

If the first path fails the physics simulation, its cells are blocked
and the pathfinder finds the next-best route. This accounts for effects
the static cost model cannot capture (momentum carryover, power-limited
climbs, etc.).

Simulation
**********

Path Sampling
=============

Before simulation, waypoints are converted into a dense 3D polyline
sampled at approximately **one pixel per step**:

.. math::

   n_{\text{samples}} = \left\lceil \frac{\Delta s}{\text{resolution}} \right\rceil

where :math:`\Delta s` is the horizontal distance between consecutive
waypoints and *resolution* is the GeoTIFF pixel size (e.g. 20 m).

At each sample point, the elevation is read from the DEM via the affine
transform, producing an :math:`(x, y, z)` polyline that follows the
terrain surface pixel-by-pixel.

Bicubic interpolation
---------------------

When the *Use bicubic interpolation* checkbox is enabled in the UI,
two things change:

**Pathfinding grid upsampling.**  The elevation raster and all cost/
penalty rasters are upsampled 4× using
:func:`scipy.ndimage.zoom` with cubic spline interpolation (``order=3``):

.. math::

   \text{elev}_{\text{fine}}[i, j] = f_{\text{cubic}}(\text{elev}, i/4, j/4)

The search operates on a grid with an effective resolution of
**5 m/px** (instead of the native 20 m/px), so A\*/Dijkstra can
route around small terrain features that would fall between or
along the edges of coarser cells.  The 4× upsampling ratio was
chosen because 20 / 4 = 5 m matches the resolution of the legacy
5 m/px tiles, giving comparable granularity.

**Simulation elevation sampling.**  Path elevations are sampled at
an effective 5 m step size using
:func:`scipy.ndimage.map_coordinates` with bicubic interpolation
(``order=3``), instead of nearest-neighbour snapping:

.. math::

   z = \text{map\_coordinates}(\text{elev}, [r, c], \text{order}=3)

where :math:`(r, c)` are sub-pixel floating-point coordinates.  The
bicubic kernel produces a :math:`C^1`-continuous elevation profile,
which in turn yields smoother grade angles and avoids the
quantisation noise that nearest-neighbour sampling can introduce
on gentle slopes.

Both modes share the same steady-state physics; only the spatial
sampling changes.

See :func:`cynthium.app.engine.simulation.path_sampling.sample_path_elevations`.

---

Rover Dynamics & Physics
========================

The simulation models the rover as a **4-wheel skid-steer vehicle** with a
rigid rectangular chassis.  Steering is achieved by differential thrust
between left and right sides.  The rover follows a **stop-pivot-go**
navigation: it drives toward the next waypoint, stops, pivots in place
to face the next one, then drives again.

**Stop-Pivot-Go state machine:**

1. **DRIVE** — the target speed comes from the configured cruise speed,
   ramped down over the last few metres for a smooth approach.  Two
   control regimes are used (see `Adaptive cruise timestep`_ below):

   * Rovers cruising at **2 m/s or less** use *adaptive cruise*: a large
     timestep (up to 30 s, bounded so the rover advances at most 1 m per
     step) with a one-step deadbeat throttle and heading correction.
   * Faster rovers use the classic PID speed controller at the small
     control timestep (0.02–0.1 s).

2. **STOP** — once within 3 m of the waypoint, the target speed is set
   to zero and the rover brakes to a halt at its configured maximum brake
   deceleration (a single step for adaptive-cruise rovers).
3. **PAUSE** (optional) — waits for the configured per-waypoint pause
   duration before pivoting.  No dynamics are integrated during a pause,
   so it advances in chunks of up to 60 s of simulated time per step.
4. **PIVOT** — applies opposing left/right thrusts to rotate in place
   until the heading aligns with the next waypoint.

Adaptive cruise timestep
------------------------

A fixed 0.1 s control timestep makes slow rovers prohibitively slow to
simulate: a 100 m traverse at 0.04 m/s is 2,500 s of simulated time
(~25,000 steps at dt = 0.1 s), and simply raising the timestep uniformly
makes the PID speed and yaw controllers oscillate around the waypoints.
Rovers with a cruise speed at or below ``CRUISE_ADAPTIVE_SPEED_MPS``
(2 m/s) therefore switch to **adaptive cruise** on straight sections,
where the timestep is chosen from the current speed so the rover advances
at most ``CRUISE_STEP_DIST_M`` (1 m) per step:

.. math::

   \Delta t_{\text{cruise}} =
   \operatorname{clamp}\left(\frac{1\,\text{m}}{v},\; 0.02\,\text{s},\;
   30\,\text{s}\right)

**Deadbeat throttle.**  Instead of a PID loop, the throttle is solved so
the rover reaches the target speed :math:`v_t` in a single step.  The
required net force is

.. math::

   F_{\text{desired}} = F_{\text{roll}} + F_{\text{grade}} +
   m \cdot \frac{v_t - v}{\Delta t}

and the throttle is the ratio of that force to the power-limited drive
force available at the current speed,
:math:`F_{\text{power}} = P / \max(v, v_{\min})`:

.. math::

   \text{throttle} = \operatorname{clamp}\left(
   \frac{F_{\text{desired}}}{F_{\text{power}}},\; 0,\; 1\right)

This one-step deadbeat is stable at any timestep, whereas the PID speed
controller limit-cycles at low speeds (at 0.04 m/s it toggles the speed
between 0 and ~0.08 m/s — a ±100% error).  On descending grades
:math:`F_{\text{desired}}` can be negative; the throttle is then zeroed
and the rover brakes instead:

.. math::

   \text{brake\_decel} = \operatorname{clamp}\left(
   -\frac{F_{\text{desired}}}{m},\; 0,\; \text{max\_brake\_decel}\right)

Without this branch the rover would accelerate without bound on
downhill sections.  Acceleration from rest is timed exactly rather than
billed as a full cruise step, and the approach ramp is shortened to
:math:`\operatorname{clamp}(v \cdot 5\,\text{s},\; 3\,\text{m},\; 10\,\text{m})`
so slow rovers do not waste steps crawling to a stop.

**Heading.**  During cruise the yaw rate is set directly to the deadbeat
value :math:`\dot\psi = \operatorname{clamp}(\psi_{\text{err}} / \Delta t,\;
\pm \dot\psi_{\max})` (traction-limited) instead of integrating the
yaw-error controller, and any leftover pivot yaw rate is zeroed on
entering cruise so the power-limited wheel model sees both wheels at the
same speed.

**Terrain pitch.**  The pitch under the vehicle is sampled from the
nearest path segment; adaptive-cruise rovers search a small window around
the previously best segment instead of the whole path, keeping the
per-step cost roughly constant as the rover advances.

Each loop iteration now advances at most ``MAX_STEP_S`` (60 s) of
simulated time, and ``max_traversal_duration_s`` uses this bound when
deciding which sun-angle rasters a traversal can possibly need.
Convergence checks against smaller cruise steps show the discretisation
error stays well under 1% of the traversal time.

Drive model
-----------

Each wheel is driven by a DC motor (no freewheel).  The available drive
force per side is power-limited and capped by the motor torque and the
wheel traction:

* Power limit: :math:`F_{\text{power}} = P_{\text{side}} / v_{\text{side}}`
  (falls back to :math:`v_{\min}` near standstill to avoid a singularity)
* Torque limit: :math:`F_{\text{torque}} = T_{\text{peak}} / r`
* Traction limit: :math:`F_{\text{trac}} = \frac{1}{2} \mu \cdot m \cdot g \cdot |\cos\theta|`

Max wheel speed is determined by the motor's no-load RPM and wheel
radius:

.. math::

   v_{\text{max}} = \frac{\text{RPM} \cdot \pi}{30} \cdot r

Above :math:`v_{\text{max}}` the drive force is not applied, so the
rover cannot exceed this speed.  Braking is modelled as a direct
deceleration (m/s²) up to the configured ``max_brake_decel`` — there is
no motor back-EMF or Coulomb-friction model.  Per-side forces are
summed, a yaw differential from the heading error is added, then
integrated to update vehicle speed, position, and heading.

Battery drain
-------------

Battery energy is consumed by the drive motors and a constant idle
drain:

.. math::

   E_{\text{battery}} = \int (P_{\text{throttle}} + P_{\text{idle}}) \, dt

* When driving: :math:`P_{\text{throttle}} = P_{\text{max}} \cdot \text{throttle}`
* When pivoting: :math:`P_{\text{pivot}} = 0.3 \cdot P_{\text{max}}`
* Idle drain is always active (computers, sensors, avionics):
  :math:`P_{\text{idle}}`

Solar energy accumulation
-------------------------

At each timestep, the illumination raster is sampled at the rover's
current position:

.. math::

   E_{\text{solar}} = \sum I \cdot \Delta t \quad (\text{J/m}^2)

Key outputs
===========

.. list-table::
   :header-rows: 1

   * - Output
     - Meaning
   * - ``traverse_feasible``
     - 1 if rover reached the final waypoint, 0 otherwise
   * - ``traversal_time_s``
     - Total time including stops and pauses
   * - ``average_velocity_mps``
     - :math:`\text{distance} / \text{time}`
   * - ``failure_reason``
     - Text description of why the traverse failed (traction, divergence, timeout)
   * - ``battery_energy_used_j``
     - Total energy drawn from battery (J)
   * - ``battery_remaining_pct``
     - Remaining battery charge (%)
   * - ``simulation_steps``
     - Physics loop iterations used (adaptive cruise keeps slow rovers
       in the hundreds rather than tens of thousands)

Lunar parameters
================

.. list-table::
   :header-rows: 1

   * - Parameter
     - Value
     - Source
   * - Lunar gravity
     - 1.625\u2009m/s\u00b2
     - Standard value
   * - Max climbable slope
     - :math:`\arctan(\mu - C_{rr})`
     - Derived from rover friction & rolling resistance
   * - Max wheel speed
     - :math:`\text{RPM} \cdot \pi / 30 \cdot r`
     - From motor max RPM and wheel radius

See:

* :func:`cynthium.app.engine.simulation.sim_orchestrator.compute_traversal_dynamics`
* :func:`cynthium.app.engine.simulation.rover_4wd.simulate_rover_4wd`

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

Traversal slope (average, maximum, and minimum) is measured over a default
span of 40 m of path rather than between consecutive ~20 m samples. This
averages out single-step artifacts of the 16-connected search grid
(diagonal and knight moves), which could otherwise appear as unrealistic
50°+ grades in the max/min statistics. The span is controlled by
``TRAVERSAL_SLOPE_STEP_M`` in
:mod:`cynthium.app.engine.simulation.stats`; it affects only the reported
statistics, not pathfinding or the simulation physics.

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
