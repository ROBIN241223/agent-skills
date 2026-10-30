# Stability analysis (control loops, regulators, op-amps)

Use this when the user asks whether a loop, regulator, filter or amplifier is
**stable**, how much margin it has, or how to compensate it.

## 1. Define the loop

- Identify the **loop gain** `T(s) = A(s)·β(s)`: forward path (amplifier, modulator,
  power stage) times feedback network.
- Find the **crossover frequency** `fc` where `|T| = 1` (0 dB) and the **phase margin**
  `PM = 180° + ∠T(fc)`.
- Rule of thumb targets: **PM ≥ 45° (aim 50–70°)**, **gain margin ≥ 6–10 dB**.

## 2. Where the poles/zeros come from

| Element | Contributes |
| --- | --- |
| Output cap + load | pole at `1/(2π·R_load·C_out)` |
| Cap ESR | zero at `1/(2π·ESR·C_out)` (helps phase) |
| Inductor + cap (buck) | double pole at `1/(2π√(LC))` |
| RC compensation | added pole/zero for shaping |
| Op-amp GBW | dominant pole; limits bandwidth |
| Input/output filters | extra poles that erode margin |

## 3. Methods (use the right tool)

- **Bode plot** — read PM/GM directly. Fastest for most cases.
- **Nyquist** — encirclements of −1 for tricky/multi-loop systems.
- **Routh–Hurwitz** — algebraic check that all closed-loop poles are in the LHP;
  good for hand analysis of simple characteristic polynomials.
- **Root locus** — how poles move as gain/frequency changes.
- **Transient step response** — measure overshoot `Mp` and ringing; relate to PM:
  `PM ≈ 100·ζ` for small ζ, and `Mp ≈ e^{−πζ/√(1−ζ²)}`.

## 4. Topology-specific notes

- **LDO / linear regulator**: stability set by output cap ESR and load; some require a
  capacitor within an ESR window — check the datasheet's stability region, not just ESR=0.
- **Buck/boost (current-mode)**: easier (single dominant pole); voltage-mode has the LC
  double pole needing Type III compensation.
- **Op-amp feedback**: watch input capacitance creating a pole at the summing node;
  add a feedback capacitor `Cf` to phase-lead when needed.
- **Multiple/stacked loops**: analyze one at a time; back off the others; verify with
  simulation.

## 5. Compensation types

- **Type I**: integrator (DC pole). For simple/current-mode.
- **Type II**: one pole at origin + one zero (and a high pole). Typical for current-mode
  converters and most LDO compensations.
- **Type III**: pole at origin + two zeros + two poles. For voltage-mode converters with
  an LC double pole.
- Design by placing the first zero at/below the LC or load pole and the second zero near
  it, then set the high-frequency poles above crossover to attenuate switching ripple.

## 6. Simulate and verify

LTspice is available on this machine. A practical loop-gain measurement:

1. Build the AC model (average switch model for converters, or the linearized circuit).
2. Break the loop; insert a small AC source `V_inject` in series.
3. Run `.ac dec 100 10 1Meg`, plot `V(out)/V(in)` in dB and phase.
4. Read PM/GM at 0 dB. Re-tune until `PM ≥ 50°`, `GM ≥ 8 dB`.
5. Cross-check with a transient (load step) — expect modest overshoot and settling.

Also confirm with measurement when possible: injection transformer + FRA, or a load-step
scope capture; compare measured PM to simulation.

## 7. Report

- Loop identified, topology, and the targeted `fc`, PM, GM.
- Pole/zero table with component values and their frequencies.
- Simulated/measured Bode summary and the margin achieved.
- Recommended component changes (with the resulting frequency shift), and residual risk.
