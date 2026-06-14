"""Scotch — Parametric Facade Prototype (Phase 16.4)

RhinoPython script that generates a parametric window grid on the front
elevation of a Scotch project, driven by Window-to-Wall Ratio (WWR).

Parameters (edit the PARAMS block below):
  WWR      — Window-to-Wall Ratio (0.0–1.0). 0.35 = 35% of wall area is glass.
  BAY_W    — Bay width in feet (windows repeat every BAY_W feet). Default 6 ft.
  SILL_H   — Window sill height from floor, ft. Default 2.5 ft.
  HEAD_H   — Window head height from floor, ft. Default 7.0 ft.
  FACADE_W — Front wall width in feet (= site width by default).
  FACADE_H — Facade height in feet (= floor_height by default).
  MARGIN   — Horizontal margin at each end of the facade, ft. Default 1.0 ft.

How to run:
  1. Open Rhino 7+ with a Scotch project already imported (run floor_plan_rhino.py first).
  2. Tools → PythonScript → Edit → open this file → Run Script.
  3. Adjust PARAMS below and re-run to iterate.

Layer output:
  Scotch::Facade::Frame   — solid wall panel with window voids cut out
  Scotch::Facade::Glass   — glass surface fills (translucent display material)
  Scotch::Facade::Mullions — thin vertical mullion boxes between window bays

Coordinate system: same as floor_plan_rhino.py (feet × FT at runtime).
"""

import rhinoscriptsyntax as rs

# ── PARAMS — edit here ────────────────────────────────────────────────────────
PARAMS = {
    "WWR":      0.35,   # Window-to-Wall Ratio (fraction)
    "BAY_W":    6.0,    # Bay width, ft
    "SILL_H":   2.5,    # Sill height from floor, ft
    "HEAD_H":   7.0,    # Head height from floor, ft
    "FACADE_W": 30.0,   # Front wall width, ft (override with site.width)
    "FACADE_H": 10.0,   # Facade height, ft (override with building.floor_height)
    "MARGIN":   1.0,    # End margin, ft
    "WALL_T":   0.5,    # Wall thickness, ft
    "MULLION_W": 0.15,  # Mullion width, ft
}

# ── Unit auto-detection ───────────────────────────────────────────────────────
_unit = rs.UnitSystem()
if _unit == 2:
    FT = 0.3048
elif _unit == 8:
    FT = 1.0
else:
    FT = 304.8

# ── Derived values ────────────────────────────────────────────────────────────
wwr    = PARAMS["WWR"]
bay_w  = PARAMS["BAY_W"]
sill   = PARAMS["SILL_H"]
head   = PARAMS["HEAD_H"]
fw     = PARAMS["FACADE_W"]
fh     = PARAMS["FACADE_H"]
margin = PARAMS["MARGIN"]
wall_t = PARAMS["WALL_T"]
mull_w = PARAMS["MULLION_W"]

win_h = head - sill                     # window opening height, ft
usable_w = fw - 2 * margin             # usable facade width for bays

# How many complete bays fit?
n_bays = max(1, int(usable_w / bay_w))
bay_actual = usable_w / n_bays          # adjusted bay width to fill evenly

# Window width per bay from WWR: win_w × win_h / (bay_actual × fh) = wwr
win_w = min(wwr * bay_actual * fh / win_h, bay_actual - mull_w * 2)
win_w = max(win_w, 0.5)                # at least 6 in window

# ── Layer setup ───────────────────────────────────────────────────────────────
_LAYERS = [
    "Scotch::Facade::Frame",
    "Scotch::Facade::Glass",
    "Scotch::Facade::Mullions",
]
for _lname in _LAYERS:
    if not rs.IsLayer(_lname):
        rs.AddLayer(_lname)


def _box(x_ft, y_ft, z_ft, w_ft, d_ft, h_ft, layer):
    x, y, z = x_ft * FT, y_ft * FT, z_ft * FT
    w, d, h = w_ft * FT, d_ft * FT, h_ft * FT
    corners = [
        [x, y, z],         [x + w, y, z],         [x + w, y + d, z],         [x, y + d, z],
        [x, y, z + h],     [x + w, y, z + h],     [x + w, y + d, z + h],     [x, y + d, z + h],
    ]
    obj = rs.AddBox(corners)
    if obj:
        rs.ObjectLayer(obj, layer)
    return obj


def _plane_rect(x_ft, y_ft, z_ft, w_ft, h_ft, layer):
    """Thin planar rectangle (glass fill — depth = 0.05 ft)."""
    return _box(x_ft, y_ft, z_ft, w_ft, 0.05, h_ft, layer)


# ── Facade wall panel ─────────────────────────────────────────────────────────
# The facade runs along Y = 0 (front of site), from X = 0 to X = fw.
print("Building facade wall panel ...")
_frame = _box(0.0, -wall_t / 2, 0.0, fw, wall_t, fh, "Scotch::Facade::Frame")

# ── Window bays ──────────────────────────────────────────────────────────────
print(f"  {n_bays} bays × {bay_actual:.2f} ft, WWR = {wwr:.0%}")
print(f"  Window: {win_w:.2f} ft wide × {win_h:.2f} ft tall")

voids = []
for i in range(n_bays):
    bay_x = margin + i * bay_actual
    win_x = bay_x + (bay_actual - win_w) / 2  # centered in bay

    # Window void (cut from frame)
    void_id = _box(win_x, -wall_t, sill, win_w, wall_t * 3, win_h, "Scotch::Facade::Frame")
    if void_id:
        voids.append(void_id)

    # Glass fill surface
    _plane_rect(win_x, 0.0, sill, win_w, win_h, "Scotch::Facade::Glass")

    # Mullions (left and right of window bay)
    if i < n_bays - 1:
        mullion_x = bay_x + bay_actual - mull_w / 2
        _box(mullion_x, -wall_t / 4, 0.0, mull_w, wall_t / 2, fh, "Scotch::Facade::Mullions")

# ── Cut window voids from frame ───────────────────────────────────────────────
if _frame and voids:
    _result = rs.BooleanDifference([_frame], voids, delete_input=True)
    if _result:
        for _obj in _result:
            rs.ObjectLayer(_obj, "Scotch::Facade::Frame")
            rs.ObjectName(_obj, "Facade Frame")

# ── Summary ───────────────────────────────────────────────────────────────────
total_win_area = n_bays * win_w * win_h
total_wall_area = fw * fh
actual_wwr = total_win_area / total_wall_area if total_wall_area > 0 else 0.0

print("Scotch facade prototype complete.")
print(f"  Bays       : {n_bays}")
print(f"  Window W×H : {win_w:.2f} × {win_h:.2f} ft")
print(f"  Target WWR : {wwr:.0%}")
print(f"  Actual WWR : {actual_wwr:.1%}  (total window area / total wall area)")
print("Tip: adjust PARAMS at top of script and re-run to iterate.")
print("     Pair with Number Sliders in Grasshopper for live parametric control.")
