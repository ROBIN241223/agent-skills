# Component selection for a schematic

Use this to pick a real, orderable part for a position (or a whole BOM), with the right
ratings, footprint and second source — and to find symbols/footprints when the library
is missing an entry.

## 1. Derive the requirement from the schematic

From `altium_tool.py schematic` / `bom`, for the target designator collect:

- **Value** (e.g. `100nF`, `4.7k`, `10uH`) and the parameter names (Voltage, Tolerance,
  Dielectric, Power, etc.).
- **Footprint** and **MPN** already assigned.
- Circuit context: rail voltage, expected current, signal type, environment.

Convert to hard limits:
- Voltage rating ≥ rail × **1.25–2×** (derate).
- Current rating ≥ load × **1.5–2×**.
- Tolerance/dielectric: X7R/X5R for decoupling, C0G/NP0 for timing/analog, 1%+ for
  dividers, low-ESR for regulators.
- Temperature range covers the product (`-40..85`/`-40..125 °C`).
- Package must match the **existing footprint** unless a layout change is allowed.

## 2. Search real supply

- **LCSC / JLCPCB** — best for assembly: stock, price breaks, "Basic vs Extended".
  The project already has LCSC quotations (`export_project_*.xls`) with
  `LCSC#, Mfr., Mfr#, Description, Package, Value, Quantity` — reuse that part number
  if the spec still matches.
- **DigiKey / Mouser** — broadest catalog, lifecycle/stock status, alternates.
- **SnapEDA / Ultra Librarian / manufacturer** — symbols & footprints. The FMUH library
  shows SnapEDA-sourced parts (`SnapEDA_Link`, `Purchase-URL` parameters) — reuse them.
- For **web research and datasheet retrieval**, use the `doc-research` skill (search /
  fetch) and this skill's `table_tool.py` for the quote spreadsheets.

## 3. Choose with a scorecard

| Criterion | Why it matters |
| --- | --- |
| Electrical spec margin | survive worst case, derating |
| Package & footprint match | no respin / library churn |
| Availability & MOQ | can actually be built |
| Lifecycle (active vs NRND/EOL) | longevity |
| Price at volume | BOM cost |
| Second source exists | supply resilience |
| Library support | symbol/footprint already available |

Prefer parts that are **In Stock**, **Active**, and **already in the design's library**
when the spec allows. Flag any `NRND`/`Not Recommended for New Designs`/`EOL`.

## 4. Validate before committing

1. Open the **datasheet**; confirm pinout, ratings, and the recommended application
   circuit (especially for regulators, crystals, references).
2. Match the symbol's pin count/naming to the datasheet (`altium_tool.py lib`).
3. Confirm the footprint name in the schematic equals the library footprint and the
   part's actual package (e.g. `QFN50P500X500X100-29N-D` vs the datasheet's QFN).
4. For regulators, check the stability requirements (cap type/ESR) — see
   `stability-analysis.md`.
5. Add the part to the BOM with supplier + MPN + alternates.

## 5. Output

Give a per-position table: designator, requirement, chosen MPN, supplier, key ratings,
footprint, qty, price, status, and a short justification plus at least one alternate.
Separate **"meets spec"** from **"cheapest"** choices when they differ.
