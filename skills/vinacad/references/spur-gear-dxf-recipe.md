# Worked example: 80-tooth spur gear -> DXF sheet -> DWG

This is the end-to-end recipe that produced the drawing this skill was written from.
It combines `$dxf` (build123d geometry) with `ezdxf` (sheet furniture) and this
skill's VinaCAD step (DWG export). Use it as a template for "a gear/part with all
corners rounded, dimensioned sheet, delivered as DWG".

## Requirements this satisfied

- 80 evenly spaced teeth ("banh rang 80 rang deu nhau"), every corner rounded.
- Pitch radius 100 mm (10 cm) -> module `m = 2*r/z = 2.5 mm`.
- Full technical specification table on the sheet.
- Delivered as `.dwg` and `.dxf` (no `.step`).

## Gear parameters (metric, 20 deg pressure angle)

| Symbol | Meaning | Value |
| --- | --- | --- |
| `z` | teeth | 80 |
| `m` | module | 2.5 mm |
| `alpha` | pressure angle | 20 deg |
| `r = m*z/2` | pitch radius | 100 mm (10 cm) |
| `ra = r + 1.0*m` | tip radius | 102.5 mm |
| `rf = r - 1.25*m` | root radius | 96.875 mm |
| `rb = r*cos(alpha)` | base radius | 93.969 mm |
| `p = pi*m` | circular pitch | 7.854 mm |
| `s = p/2` | tooth thickness at pitch | 3.927 mm |
| `ha = m` | addendum | 2.5 mm |
| `hf = 1.25*m` | dedendum | 3.125 mm |

Interpretation: "radius 10 cm" was taken as the **pitch radius**. If the user meant
the **outer** radius, use `ra = 100` and derive `r = ra - m`, then `m = 2*r/z`.
Always state the choice and offer to switch.

## Geometry (involute tooth, sampled, all corners filleted)

Per tooth, going counter-clockwise: left involute flank -> tip arc -> right involute
flank -> root arc, repeated `z` times.

- involute flank angle at radius `rho`: `theta = s/(2r) + inv(alpha) - inv(a)`,
  with `a = acos(rb/rho)` and `inv(x) = tan(x) - x`; sample ~10 points per flank.
- tip arc spans `2*theta(ra)` at radius `ra`; root arc spans
  `pitch_angle - 2*theta(rf)` at radius `rf`, where `pitch_angle = 2*pi/z`.
- Round **every** corner with `build123d` fillets after building the wire:
  tip corners `R0.6`, root corners `R0.9`, selecting vertices by distance from
  centre (`> (ra+rf)/2` = tip).

The full source is `scripts/gear_80T.py` (this is a `cadgen` `@dxf` model — run it
with the project interpreter, e.g. `python gear_80T.py`, and it writes the `.dxf`).

Resulting DXF entity census (sanity check): **160 SPLINE, 480 ARC** — 80 tip arcs
(`ra`), 80 root arcs (`rf`), and 320 fillet arcs (160 x R0.6 + 160 x R0.9).

## Sheet furniture (ezdxf)

`scripts/build_gear_sheet.py` reads the geometry DXF and adds, in millimetres,
`$INSUNITS = 4` and `$MEASUREMENT = 1`:

- layers `FRAME / TITLE / NOTE / REF / CENTER` (REF dashed),
- centre lines and reference circles (pitch + base),
- an A-size frame with a title block,
- a Vietnamese specification table (UTF-8, drawn with a TrueType style `VNA` =
  `arial.ttf` so diacritics render).

**Keep the Vietnamese as real UTF-8, and check it properly.** The file is valid UTF-8;
the Windows console misrenders it (you will see `BANH RANG TR? RANG TH?NG` /
`G�c �p l?c`) and it is easy to mistake that for corruption. Verify with a UTF-8-aware
read (the file reader, a hexdump, or `[System.Text.Encoding]::UTF8.GetString(...)`), not
with the console. The spec table uses the TrueType style `VNA` = `arial.ttf` so the
diacritics render in the drawing.

## Export to DWG (this skill's part)

```powershell
# open in VinaCAD and save as DWG (see ../SKILL.md for the why)
pwsh -File scripts\vcad-saveas-dwg.ps1 -Drawing .\BanhRang_80Rang.dxf -Out .\BanhRang_80Rang.dwg
```

Verified result: a 52,877-byte file whose header is `AC1032` (**DWG 2018**), which
VinaCAD reopened with `CVinaCADApp::openFile [Finish reading file: BanhRang_80Rang]`.
Note it was recovered from `%APPDATA%\VinaCAD\BanhRang_80Rang.bak` — VinaCAD's
save/backup swap wrote the DWG there; check the `.bak` if the expected `.dwg` is
missing.

## Delivering

Report the gear parameters table, the two output paths with sizes, and the verified
DWG version. Mention the radius interpretation and offer to change the fillet radii
or the interpretation.
