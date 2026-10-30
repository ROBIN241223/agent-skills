# Schematic analysis workflow

Goal: turn an Altium project into a trustworthy description of **what the circuit is,
what it powers, what it connects, and what is risky**, before datasheet-level detail.

## 0. Gather ground truth first

```bash
python scripts/altium_tool.py project  PROJECT.PrjPcb
python scripts/altium_tool.py schematic SHEET.SchDoc --nets
python scripts/altium_tool.py bom      *.SchDoc --out bom.csv
```
Read every sheet's component list and named nets. Only then reason about function.
Never invent a net or a value that is not in the extracted data.

## 1. Build the power tree

- Collect power ports (RECORD 17) and their rails: `GND`, `+3V3`, `+5V`, `VBAT`, `VIN`...
- For each regulator/converter (LDO, buck, boost, charge pump, module), record:
  input rail -> output rail, current capability, switching frequency, enable/UVLO.
- Draw a text tree: `USB 5V -> U? (LDO) -> +3V3 -> MCU/radio/sensors`.
- Check every rail has: a source, a return path, and at least one decoupling cap.

## 2. Decoupling & filtering

- Bulk cap (uF) + local 100nF per power pin, close to the pin.
- Check decoupling against the datasheet's recommended values, not just "100nF".
- Look for analog/digital splits, ferrites/inductors (e.g. part numbers starting
  `NFM`/`BLM`), and whether sensitive rails are isolated.

## 3. Interfaces & connectivity

- Enumerate ports/sheet entries (RECORD 18) and net labels (RECORD 4) per sheet:
  I2C, SPI, UART, USB, CAN, Ethernet, RF, GPIO, connectors.
- Verify: pull-ups on I2C, series/termination on fast lines, level shifting across
  voltage domains, ESD protection on every off-board connector, differential pairs.
- Note bus naming conventions and hierarchical sheet pins.

## 4. Configuration & bring-up

- Clocking: crystal/oscillator frequency vs MCU/PLL expectations; load caps.
- Reset/boot: BOOT straps, reset supervisor, SWD/JTAG header.
- Address/ID straps, mode-select resistors.
- Test points and programming headers.

## 5. Risk review checklist

| Area | Look for |
| --- | --- |
| Voltage | part ratings vs. rail voltage (derate >= 20%) |
| Current | trace/connector/regulator current vs. load, inrush |
| Thermal | power dissipation, copper area, thermal pads |
| Timing | crystal vs. PLL, propagation, setup/hold on buses |
| Protection | reverse polarity, over-voltage, ESD, fuse/PTC |
| Single point | single source rail, missing pull-up, floating enable |
| Consistency | designator/value vs. BOM, footprint vs. package |

## 6. Cross-check with the BOM and libraries

- Use `bom` output to confirm each designator's value/footprint/MPN.
- Use `lib` on the project `.IntLib` to confirm the symbol's pins and the footprint
  name actually referenced by each component.
- Flag components whose footprint is empty or `*` (unassigned) — a real assembly risk.

## 7. Report format

1. **One-paragraph function** of each sheet.
2. **Power tree** (text diagram) with ratings.
3. **Interface table**: signal, direction, voltage domain, protection.
4. **Findings**, each with: severity (info/warn/error), the designator, the evidence
   (record/value), and a concrete fix.
5. **Open questions** — anything the files don't determine.

Keep extracted facts and your inference visually separate. Mark inference explicitly.
