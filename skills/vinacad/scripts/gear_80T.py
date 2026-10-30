"""Spur gear (banh rang tru rang thang) - 80 teeth, every corner filleted.

2D model: returns the cross-section (XY plane) of the gear.
Metric module, 20 deg pressure angle.

Runs as a cadgen @dxf drawing: `python gear_80T.py` writes the sibling .dxf.
Adjust `out=` for your project; paths in the decorator are relative to this file.
"""

import math

from cadgen import build123d as bd
from cadgen import dxf

# ---------------------------------------------------------------------------
# Design parameters (mm)
# ---------------------------------------------------------------------------
TEETH = 80                     # z - number of teeth
MODULE = 2.5                   # m - module (mm)
PRESSURE_ANGLE = 20.0          # alpha - pressure angle (deg)
ADDENDUM_COEF = 1.0            # addendum coefficient
DEDENDUM_COEF = 1.25           # dedendum coefficient

PITCH_R = MODULE * TEETH / 2.0                 # pitch radius
TIP_R = PITCH_R + ADDENDUM_COEF * MODULE       # tip radius
ROOT_R = PITCH_R - DEDENDUM_COEF * MODULE      # root radius
BASE_R = PITCH_R * math.cos(math.radians(PRESSURE_ANGLE))  # base radius

TIP_FILLET = 0.6               # tip corner fillet radius
ROOT_FILLET = 0.9              # root corner fillet radius

ANG_PITCH = 2.0 * math.pi / TEETH
HALF_T = math.pi / (2.0 * TEETH)          # half tooth thickness angle at pitch circle
ALPHA = math.radians(PRESSURE_ANGLE)


def _inv(a: float) -> float:
    """Involute function inv(a) = tan(a) - a."""
    return math.tan(a) - a


def _flank_angle(rho: float) -> float:
    """Polar angle of the involute flank at radius rho (>= BASE_R)."""
    a = math.acos(BASE_R / rho)
    return HALF_T + _inv(ALPHA) - _inv(a)


def _involute(sign: float, n: int = 10):
    """Involute flank points from root circle to tip circle."""
    pts = []
    for i in range(n + 1):
        rho = ROOT_R + (TIP_R - ROOT_R) * i / n
        th = sign * _flank_angle(rho)
        pts.append((rho * math.cos(th), rho * math.sin(th)))
    return pts


def _rot(pts, ang):
    c, s = math.cos(ang), math.sin(ang)
    return [(x * c - y * s, x * s + y * c) for (x, y) in pts]


def build_outline():
    """Gear outer outline, every corner rounded."""
    ta = _flank_angle(TIP_R)
    tr = _flank_angle(ROOT_R)

    with bd.BuildLine() as bl:
        for i in range(TEETH):
            base = i * ANG_PITCH
            # left flank (root -> tip)
            bd.Spline(_rot(_involute(-1.0), base))
            # tip arc
            bd.CenterArc(
                (0, 0), TIP_R,
                math.degrees(base - ta), math.degrees(2.0 * ta),
            )
            # right flank (tip -> root)
            bd.Spline(list(reversed(_rot(_involute(+1.0), base))))
            # root arc (to the next tooth)
            bd.CenterArc(
                (0, 0), ROOT_R,
                math.degrees(base + tr), math.degrees(ANG_PITCH - 2.0 * tr),
            )
    return bl.wires()[0]


def build_gear():
    outline = build_outline()
    with bd.BuildSketch() as sk:
        bd.add(bd.Face(outline))
        verts = sk.vertices()
        mid = (TIP_R + ROOT_R) / 2.0
        tip_verts = [v for v in verts if abs(v.center().length) > mid]
        root_verts = [v for v in verts if abs(v.center().length) <= mid]
        bd.fillet(tip_verts, radius=TIP_FILLET)
        bd.fillet(root_verts, radius=ROOT_FILLET)
    return sk.sketch


@dxf(out="gear_80T.dxf")
def gear_80T():
    return build_gear()


if __name__ == "__main__":
    g = build_gear()
    bb = g.bounding_box()
    print("area", round(g.area, 3))
    print("bbox", bb.min, bb.max)
    print("radius_x", round(bb.max.X, 4))
    print("TIP_R", round(TIP_R, 4), "ROOT_R", round(ROOT_R, 4), "BASE_R", round(BASE_R, 4))
    print("teeth", TEETH, "module", MODULE)
    gear_80T()
