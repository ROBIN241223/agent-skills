"""Build the full sheet: gear + frame + Vietnamese technical-spec table.

Reads the geometry DXF (produced by `gear_80T.py` via cadgen) and adds the sheet
furniture: frame + title block, a specification table, centre lines and reference
circles. Writes the finished drawing.

Usage:
    python build_gear_sheet.py [src_geometry.dxf] [out_sheet.dxf]

Defaults: ./DXF/gear_80T.dxf  ->  ./DXF/BanhRang_80Rang.dxf  (relative to CWD)

Keep this file UTF-8: the spec table is Vietnamese with diacritics. Verify with a
UTF-8-aware read - the Windows console will misrender it and look like corruption.
"""

from pathlib import Path
import math
import sys

import ezdxf
from ezdxf.enums import TextEntityAlignment

DEFAULT_SRC = Path("DXF") / "gear_80T.dxf"
DEFAULT_OUT = Path("DXF") / "BanhRang_80Rang.dxf"

# --- Design parameters (mm) ---
Z = 80
M = 2.5
ALPHA = 20.0
R = M * Z / 2.0
RA = R + M
RF = R - 1.25 * M
RB = R * math.cos(math.radians(ALPHA))
P_CIRC = math.pi * M
S_PITCH = P_CIRC / 2.0
HA = M
HF = 1.25 * M
H = HA + HF
TIP_F = 0.6
ROOT_F = 0.9

# Technical-spec table (Vietnamese, full diacritics).
SPECS_VI = [
    ("BÁNH RĂNG TRỤ RĂNG THẲNG (SPUR GEAR)", ""),
    ("Số răng                 z", f"{Z}"),
    ("Module                  m", f"{M} mm"),
    ("Góc áp lực              α", f"{ALPHA:g}°"),
    ("Bán kính vòng chia     r", f"{R:g} mm  (= 10 cm)"),
    ("Đường kính vòng chia   d", f"{2*R:g} mm"),
    ("Bán kính vòng đỉnh     ra", f"{RA:g} mm"),
    ("Đường kính vòng đỉnh   da", f"{2*RA:g} mm"),
    ("Bán kính vòng chân     rf", f"{RF:g} mm"),
    ("Đường kính vòng chân   df", f"{2*RF:g} mm"),
    ("Bán kính vòng cơ sở    rb", f"{RB:.3f} mm"),
    ("Bước răng          p = π·m", f"{P_CIRC:.3f} mm"),
    ("Chiều dày răng     s = p/2", f"{S_PITCH:.3f} mm"),
    ("Chiều cao đỉnh răng    ha", f"{HA:g} mm"),
    ("Chiều cao chân răng    hf", f"{HF:g} mm"),
    ("Chiều cao răng          h", f"{H:g} mm"),
    ("Bo góc đỉnh răng", f"R{TIP_F:g} mm"),
    ("Bo góc chân răng", f"R{ROOT_F:g} mm"),
    ("Số góc được bo tròn", f"{Z*4} (mỗi răng 4 góc)"),
    ("Đơn vị bản vẽ", "mm (milimét)"),
]


def add_layers(doc):
    for name, color in [
        ("FRAME", 7), ("TITLE", 7), ("NOTE", 3), ("REF", 1), ("CENTER", 4),
    ]:
        if name not in doc.layers:
            doc.layers.add(name, color=color)
    if "DASHED" not in doc.linetypes:
        doc.linetypes.add("DASHED", pattern=[0.6, 0.3, -0.3])
    doc.layers.get("REF").dxf.linetype = "DASHED"


def add_ref_geometry(msp):
    msp.add_line((-RA - 15, 0), (RA + 15, 0), dxfattribs={"layer": "CENTER"})
    msp.add_line((0, -RA - 15), (0, RA + 15), dxfattribs={"layer": "CENTER"})
    msp.add_circle((0, 0), R, dxfattribs={"layer": "REF"})    # pitch circle
    msp.add_circle((0, 0), RB, dxfattribs={"layer": "REF"})   # base circle
    msp.add_text(
        "Vong chia r=100", height=3.0,
        dxfattribs={"layer": "REF", "rotation": 90},
    ).set_placement((2, 62), align=TextEntityAlignment.LEFT)


def add_frame_and_title(msp):
    x0, y0, x1, y1 = -135.0, -120.0, 345.0, 120.0
    msp.add_lwpolyline(
        [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
        close=True, dxfattribs={"layer": "FRAME"},
    )
    msp.add_lwpolyline(
        [(x0 + 5, y0 + 5), (x1 - 5, y0 + 5), (x1 - 5, y1 - 5), (x0 + 5, y1 - 5)],
        close=True, dxfattribs={"layer": "FRAME"},
    )
    tb_x0, tb_y0, tb_x1, tb_y1 = 150.0, -115.0, 340.0, -55.0
    msp.add_lwpolyline(
        [(tb_x0, tb_y0), (tb_x1, tb_y0), (tb_x1, tb_y1), (tb_x0, tb_y1)],
        close=True, dxfattribs={"layer": "TITLE"},
    )
    msp.add_line((tb_x0, tb_y1 - 14), (tb_x1, tb_y1 - 14), dxfattribs={"layer": "TITLE"})
    msp.add_line((tb_x0, tb_y1 - 28), (tb_x1, tb_y1 - 28), dxfattribs={"layer": "TITLE"})
    msp.add_line((tb_x0 + 95, tb_y0), (tb_x0 + 95, tb_y1), dxfattribs={"layer": "TITLE"})

    def t(txt, x, y, h=4.0, layer="TITLE"):
        msp.add_text(txt, height=h, dxfattribs={"layer": layer}).set_placement(
            (x, y), align=TextEntityAlignment.LEFT)

    t("BAN VE BANH RANG 80 RANG", tb_x0 + 3, tb_y1 - 11, h=4.5)
    t("So rang / Teeth: 80", tb_x0 + 3, tb_y1 - 24, h=3.2)
    t("Module: 2.5 mm", tb_x0 + 3, tb_y1 - 40, h=3.2)
    t("Goc ap luc: 20 deg", tb_x0 + 98, tb_y1 - 24, h=3.2)
    t("Ti le / Scale: 1:1", tb_x0 + 98, tb_y1 - 40, h=3.2)
    t("Ngay / Date: 2026-10-16", tb_x0 + 3, tb_y0 + 8, h=3.2)
    t("VinaCAD  |  DXF/DWG", tb_x0 + 98, tb_y0 + 8, h=3.2)


def add_spec_table(msp, rows):
    x0, y0 = 150.0, -50.0
    row_h = 6.2
    label_x = x0 + 3
    value_x = x0 + 118
    top = y0 + row_h * len(rows) + 4
    msp.add_lwpolyline(
        [(x0, y0 - 4), (340.0, y0 - 4), (340.0, top), (x0, top)],
        close=True, dxfattribs={"layer": "NOTE"},
    )
    for i, (label, value) in enumerate(rows):
        y = top - 6 - i * row_h
        h = 3.6 if i == 0 else 3.0
        layer = "TITLE" if i == 0 else "NOTE"
        msp.add_text(label, height=h, dxfattribs={"layer": layer}).set_placement(
            (label_x, y), align=TextEntityAlignment.LEFT)
        if value:
            msp.add_text(value, height=h, dxfattribs={"layer": layer}).set_placement(
                (value_x, y), align=TextEntityAlignment.LEFT)


def build(src_dxf, out_dxf):
    doc = ezdxf.readfile(src_dxf)
    if "VNA" not in doc.styles:            # TrueType style so diacritics render
        doc.styles.add("VNA", font="arial.ttf")
    doc.header["$INSUNITS"] = 4            # millimetres
    doc.header["$MEASUREMENT"] = 1

    add_layers(doc)
    msp = doc.modelspace()
    add_ref_geometry(msp)
    add_frame_and_title(msp)
    add_spec_table(msp, SPECS_VI)

    for e in msp.query("TEXT"):
        e.dxf.style = "VNA"

    doc.header["$EXTMIN"] = (-135.0, -120.0, 0.0)
    doc.header["$EXTMAX"] = (345.0, 120.0, 0.0)
    doc.saveas(out_dxf)
    print("wrote", out_dxf)


def main(argv):
    src = Path(argv[1]) if len(argv) > 1 else DEFAULT_SRC
    out = Path(argv[2]) if len(argv) > 2 else DEFAULT_OUT
    build(src, out)


if __name__ == "__main__":
    main(sys.argv)
