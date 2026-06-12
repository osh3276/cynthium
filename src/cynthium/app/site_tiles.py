"""
Pre-computed geographic bounds for every 5 m/px site tile.

Each entry gives ``(left, bottom, right, top)`` in the lunar south‑pole
stereographic projection (metres).  These are the raw values read from
the original ``*_5mpp_surf.tif`` files, so the LDEM crop can be done
without opening those files at all.

Generated 2026-06-12 by reading every ``*_5mpp_surf.tif`` in ``data/``.
"""

from __future__ import annotations

from typing import Final

# (left, bottom, right, top)  —  all in metres in stereographic projection
SITE_TILE_BOUNDS: Final[dict[str, tuple[float, float, float, float]]] = {
	"DM1_5mpp_surf":     ( 154000.0,   51500.0,  174000.0,   71500.0),
	"DM2_5mpp_surf":     ( 147000.0,   85000.0,  167000.0,  105000.0),
	"Haworth_5mpp_surf": ( -52900.0,   75600.0,  -23100.0,  105400.0),
	"LM1_5mpp_surf":     (   2000.0,   -2000.0,   22000.0,   18000.0),
	"LM2_5mpp_surf":     (   2000.0,   47000.0,   22000.0,   67000.0),
	"LM3_5mpp_surf":     (   4000.0,   37000.0,   24000.0,   57000.0),
	"LM4_5mpp_surf":     (   9000.0,   15000.0,   29000.0,   35000.0),
	"LM5_5mpp_surf":     (  30000.0,    1000.0,   50000.0,   21000.0),
	"LM6_5mpp_surf":     (  49000.0,   10000.0,   69000.0,   30000.0),
	"LM7_5mpp_surf":     (  54000.0,  -10000.0,   74000.0,   10000.0),
	"LM8_5mpp_surf":     (  60000.0,   30000.0,   80000.0,   50000.0),
	"NPA_5mpp_surf":     ( -98500.0,   19500.0,  -78500.0,   39500.0),
	"NPB_5mpp_surf":     ( 175000.0,   -8500.0,  195000.0,   11500.0),
	"NPC_5mpp_surf":     ( 122500.0, -109500.0,  142500.0,  -89500.0),
	"NPD_5mpp_surf":     (  13000.0,  146000.0,   33000.0,  166000.0),
	"SL2_5mpp_surf":     ( -58500.0,   13000.0,  -38500.0,   33000.0),
	"Shoemaker_5mpp_surf":( 66000.0,   29000.0,   86000.0,   49000.0),
	"Site01_5mpp_surf":  ( -19000.0,  -20000.0,   -3000.0,   -4000.0),
	"Site04_5mpp_surf":  (  -9000.0,  -15000.0,    7000.0,    1000.0),
	"Site06_5mpp_surf":  (  74000.0,  100000.0,   94000.0,  120000.0),
	"Site07_5mpp_surf":  (  22000.0,  -28000.0,   38000.0,  -12000.0),
	"Site11_5mpp_surf":  ( -45000.0,    7000.0,  -29000.0,   23000.0),
	"Site20_5mpp_surf":  (  65000.0,  110000.0,   81000.0,  126000.0),
	"Site20v2_5mpp_surf":(  60000.0,  105000.0,   86000.0,  131000.0),
	"Site23_5mpp_surf":  ( -11000.0,  111000.0,   10000.0,  132000.0),
	"Site42_5mpp_surf":  (-123400.0,  -66100.0, -103400.0,  -46100.0),
}
