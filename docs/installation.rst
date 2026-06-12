Installation
############

Prerequisites
*************

* Python 3.12 or newer.
* A working C/C++ compiler toolchain (required by ``rasterio``).

pip Install (from PyPI)
***********************

.. code-block:: bash

   pip install cynthium

Alternatively, install from pipx:

.. code-block:: bash

   pipx install cynthium

Editable Install (from source)
******************************

.. code-block:: bash

   git clone https://github.com/osh3276/cynthium.git
   cd cynthium
   pip install -e .

Key Dependencies
****************

+------------------+----------------------------------------------+
| Package          | Role                                         |
+==================+==============================================+
| ``PySide6``      | Qt GUI framework                             |
+------------------+----------------------------------------------+
| ``numpy``        | Array / numerical computation                |
+------------------+----------------------------------------------+
| ``rasterio``     | GeoTIFF raster I/O                           |
+------------------+----------------------------------------------+
| ``pyqtgraph``    | Fast 2D image / plot widgets                 |
+------------------+----------------------------------------------+
| ``PyVista``      | 3D terrain meshing and rendering             |
+------------------+----------------------------------------------+
| ``pyproj``       | Coordinate system transformations            |
+------------------+----------------------------------------------+
| ``spiceypy``     | NASA SPICE toolkit (ephemeris, frames)       |
+------------------+----------------------------------------------+
| ``matplotlib``   | Colormaps and supplementary plotting         |
+------------------+----------------------------------------------+

Building Documentation
**********************

.. code-block:: bash

   cd docs
   pip install sphinx
   make html

The built HTML documentation will be available at ``docs/_build/html/index.html``.
