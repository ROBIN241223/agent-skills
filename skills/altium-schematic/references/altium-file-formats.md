# Altium file formats & what we can extract

Verified against real Altium Designer 24 projects (FMUH750, Handle_Ultrasonic) and
component libraries. This is the ground truth the `scripts/` rely on.

## File kinds

| Extension | Kind | Container | How data is stored |
| --- | --- | --- | --- |
| `.SchDoc` | Schematic sheet | OLE2 compound | ASCII records in the `FileHeader` stream |
| `.SchLib` | Schematic library | OLE2 compound | ASCII records in `<LibName>/Data` + header in `FileHeader` |
| `.PcbDoc` | PCB layout | OLE2 compound | binary PCB streams (copper not parsed here) |
| `.PcbLib` | Footprint library | OLE2 compound | one storage per footprint (`<FP>/Data`, `Library/Data`) |
| `.IntLib` | Compiled integrated lib | OLE2 + zlib | `SchLib/0.schlib`, `PCBLib/0.pcblib` are zlib-wrapped nested OLE2; `LibCrossRef.Txt` is text |
| `.PrjPcb` | Project | text (UTF-8 BOM, INI) | `[Design]`, `[DocumentN]` with `DocumentPath=` |
| `.OutJob` | Output job | text (INI) | `[OutputJobFile]`, `[PublishSettings]` |
| `.BomDoc` | Live BOM document | text records | `\|RECORD=BOM\|`, `\|RECORD=CatalogItem\|`, `\|RECORD=GeneralOptions\|` |
| `.csv/.xls/.xlsx` | BOM/netlist exports | text / OLE2(BIFF) / ZIP | LCSC/DigiKey/JLCPCB quotes, Altium component exports |

OLE2 magic: `D0 CF 11 E0 A1 B1 1A E1`. Inside `.IntLib`, member bytes start with a
single length/version byte `0x02` then `78 9C` (zlib); decompress `data[1:]`.

## The record format

Schematic/symbol records are ASCII, pipe-delimited, NUL-terminated:
`|RECORD=<n>|<Key>=<Value>|<Key>=<Value>|...`

Common `RECORD` numbers:

| # | Meaning | Useful fields |
| --- | --- | --- |
| 1 | Component | `LibReference`, `ComponentDescription`, `PartCount`, `AllPinCount` |
| 2 | Pin (in `.SchDoc`) | `Name`, `Designator`, `Electrical`, `OwnerIndex` |
| 4 | Net label | `Text` |
| 6/7/8/12/13/14 | Graphic primitives | geometry (not needed for analysis) |
| 17 | Power port | `Text` (e.g. `GND`, `+3V3`) |
| 18 | Port / sheet entry | `Name` |
| 27/28/29 | Wire / bus / junction | connectivity |
| 31 | Sheet settings | fonts, size, `Display_Unit` |
| 34 | Designator | `Text`, `OwnerIndex` |
| 41 | Parameter | `Name`, `Text` (`Value`, `Comment`, `Footprint`, `Manufacturer Part Number`...) |
| 44 | Implementation list | `OwnerIndex` -> component |
| 45 | Implementation (model) | `ModelName`, `ModelType=PCBLIB` |
| 46/48 | Implementation map | pin/pad mapping |

### How objects link

`OwnerIndex` is the **0-based index of the owning record in the full record list**
(the record's position in stream order), not the designator or sheet index.

- Component children (Designator 34, Pin 2, Parameter 41) carry `OwnerIndex` =
  the RECORD=1 component's position.
- Footprint chain: `45.OwnerIndex` -> the RECORD=44 position -> `44.OwnerIndex` ->
  the component. `45.IsCurrent=T` marks the active footprint when several exist.

`scripts/altium_tool.py` resolves both chains for you.

## What is reliable vs. not

Reliable:
- Component list: designator, LibReference, Value/Comment, description, footprint,
  manufacturer, MPN, all parameters (from RECORD 1/34/41/45).
- Named nets: net labels (4), power ports (17), ports/sheet entries (18).
- Project structure: documents and libraries from `.PrjPcb`.
- Library symbol headers and footprint names from `.PcbLib`/`.IntLib`.
- BomDoc CatalogItem rows (supplier/part data) and BOM spreadsheet exports.

Limited / needs care:
- **Full netlist (pin -> net)** requires connectivity tracing through wires, buses,
  junctions and ports. This tool does not compute it; use Altium's netlist export or
  a `.NET` file if a real netlist is needed.
- **Symbol pin lists in `.SchLib`** are stored as a binary pin block, not RECORD=2, so
  `lib` shows `pins=0` for libraries. Pin names/counts are read reliably from
  `.SchDoc` sheets instead.
- **`.PcbDoc` copper/stack-up** is proprietary binary and out of scope.
- Coordinates in records are in Altium internal units (1/10000 inch) with `_Frac`
  parts; not needed for schematic-level analysis.

## Commands

```bash
python scripts/altium_tool.py info      FILE...          # kind, streams, record histogram
python scripts/altium_tool.py project   FILE.PrjPcb      # documents, libraries, settings
python scripts/altium_tool.py schematic FILE.SchDoc --nets [--json]
python scripts/altium_tool.py lib       FILE.SchLib|PcbLib|IntLib
python scripts/altium_tool.py bom       SHEET... --out bom.csv
python scripts/altium_tool.py bomdoc    FILE.BomDoc
python scripts/altium_tool.py records   FILE --type 41    # undocumented/debug

python scripts/table_tool.py read       BOM.xls [--sheet N] [--list-sheets]
python scripts/table_tool.py headers    BOM.xlsx
```
