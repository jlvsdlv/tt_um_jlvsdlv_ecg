# ECG DDA v5: design freeze (schematic level)

SKY130, ngspice 42, BSIM4. Amplifier VDD 1.0 V, switching driver 1.8 V. All numbers are simulated. "Switched" noise uses the trap model calibrated to Han 2015 (β = 0.049).

## Headline: all 10 corners (tt/ss/ff/sf/fs at 27 °C, tt 0/37/60 °C, ss0, ff60)

| Spec | Result |
|---|---|
| Gain | 33.0–34.2 dB (MC σ 0.2 dB) |
| IRN 0.5–150 Hz, bulk switching on | 0.88–0.91 µVrms (0–37 °C); 0.96–0.99 at 60 °C |
| IRN, switching off | 2.05–2.29 µVrms (only one load half conducts at a time) |
| Input impedance at the pad, after trim | ≥ 2.6 GΩ over 0.5–150 Hz; 24–115 GΩ at 50 Hz (MC worst 2.4 / 21 GΩ) |
| Linearity (switched transient, tt27) | THD 0.29% at 4 mVpp, 2.2% at 10 mVpp differential (ss0 0.51%, ff60 0.24% at 4 mVpp) |
| Electrode offset (differential DC) | ±20 mV: no effect; ±50 mV: −1 dB gain; ±100 mV: −3 dB |
| Input CM | set on chip by the bias-electrode loop: tail at 0.842–0.855 V at every corner (MC σ 11 mV); body/inputs settle at 0.37–0.70 V |
| Mains (230 Vrms, 2 pF to body, dry 10 MΩ electrodes incl. bias electrode, 10% input-electrode mismatch) | input CM ripple 10–17 mVpp; 50 Hz at the output referred to input ≤ 12–28 µVpp |
| Power-up | with a 20 ms reset pulse: settled within 2–26 ms at tt27, ss0, sf27, fs27, ff60. Without reset: stuck (outputs at VDD) |
| Supply | 989–1181 nA at 1.0 V (tt27: 1038 nA, incl. bias-electrode driver) + 11.9 nA at 1.8 V (driver, all corners) |
| Power, tt27 | ≈ 1.06 µW (≤ 1 µW needs IB about 7% lower) |
| Output ripple at 2 kHz | 1–65 µV at the output |

## Change log from v4

| Block | v4 | v5 | Why |
|---|---|---|---|
| Input trim | 3-bit Cpf, LSB × (A−1) | Cpf fixed 0.68 pF (over-compensated) + 10-bit Ct (10 fF LSB) from each vi to ground | Trim LSB is no longer multiplied by the gain (Zheng & Liu, JSSC 2026) |
| Output roll-off | CL,ext 17.7 pF | 8.8 pF (fLP 2.5–3.1 kHz) | Trimmed Zin is set by negative conductance G ∝ f²/fLP |
| DTMOS well bias | Cbc 5 pF, ideal 10 TΩ | Cbc 20 pF + replica-biased linear pseudo-R (4 × pfet_01v8 2/20 per side, replica 48 × 10/1 on the tail, 0.5 nA mirrored from the driver bias) | The 10 TΩ well was set by fA leakage, so cold corners landed in a wrong DC state |
| Gain network | Cg 5 pF, Cf 0.125 pF (37 dB), Rf pfet 1/4 | Cg 15 pF, Cf 1.12 pF (33.8 dB), Rf pfet 0.42/4 | Rf is junction-leakage limited at high T. Loop gain was only ≈ 2 at 37 dB, so the output compressed (8% THD at 8 mVpp). The front end sets the IRN, so the lower gain costs nothing |
| Input CM | ideal source re-centred per corner | bias-electrode loop (below) | Nothing on chip defined it |
| Reset | none | nfet 0.42/0.5 switches across Rf (g3–vo2, g4–vo1) and Rb (nw–tail), body in an isolated p-well bootstrapped to the low-impedance side, gate from a ui_in pin (1.8 V) | TΩ nodes need 10³ s to settle otherwise; the circuit does not start without it |
| Switching driver logic | L = 0.15 µm | L = 0.5 µm | Min-L gates leaked 120 nA at ff60 (now 12 nA at all corners) |

## Bias-electrode loop

- **Sensing:** the input pair's tail node (VCM + Vsg(M1); differential signals cancel there), so there is no input loading.
- **Reference:** 6/7·VDD from 7 identical pfet_01v8_lvt 2/2 diodes, each in its own n-well. Ratio set by matching; current 1.6 pA–8.5 nA over corners.
- **Circuit:** two-stage OTA.
  - Stage 1: nfet_lvt 2/4 pair at 5.6 nA, pfet_lvt 4/2 mirror (low Vsg for headroom).
  - Stage 2: pfet_lvt 4/2 common source with a 20 nA sink.
  - Miller 10 pF. Output to pad ua[4] → bias electrode.
- **Loop:** DC gain 38–66 dB (sf27 lowest), UGB 0.7–1.1 kHz, PM 43–72°.
- **Fixed during verification:** stage 1 first saturated at sf27 (tail stuck at 0.90 V) until the mirror was widened.

## Corners (results/v5_final3.json)

| Corner | VCM | I(VDD) nA | Gain dB | fLP Hz | Ct fF | Zin min | Zin at 1 / 50 / 150 Hz (GΩ) | IRN static / switched µVrms |
|---|---|---|---|---|---|---|---|---|
| tt27 | 0.535 | 1038 | 33.9 | 2643 | 3930 | 2.65 G | 481 / 23.7 / 2.53 | 2.13 / 0.89 |
| ss27 | 0.432 | 1010 | 33.5 | 2643 | 2500 | 3.02 G | 456 / 27.3 / 2.88 | 2.19 / 0.91 |
| ff27 | 0.641 | 1083 | 34.1 | 2643 | 3260 | 2.77 G | 482 / 24.9 / 2.64 | 2.07 / 0.89 |
| sf27 | 0.372 | 1006 | 33.8 | 2494 | 3190 | 2.79 G | 542 / 24.9 / 2.67 | 2.05 / 0.90 |
| fs27 | 0.688 | 1131 | 33.0 | 3144 | 3100 | 3.25 G | 341 / 30.3 / 3.10 | 2.21 / 0.88 |
| tt0 | 0.474 | 1017 | 33.6 | 2643 | 4350 | 2.77 G | 740 / 24.6 / 2.64 | 2.10 / 0.90 |
| tt37 | 0.557 | 1046 | 33.9 | 2494 | 3710 | 2.64 G | 211 / 24.8 / 2.52 | 2.15 / 0.90 |
| tt60 | 0.605 | 1068 | 34.0 | 2494 | 3180 | 2.95 G | 24.5 / 115 / 2.80 | 2.29 / 0.99 |
| ss0 | 0.370 | 989 | 33.3 | 2643 | 3030 | 3.11 G | 755 / 27.7 / 2.97 | 2.16 / 0.91 |
| ff60 | 0.703 | 1181 | 34.2 | 2643 | 2250 | 3.32 G | 24.9 / 90.1 / 3.15 | 2.22 / 0.96 |

## Monte Carlo: 40 seeds, tt27, every device including pseudo-R/replica/ladder/OTA, plus 0.5% Cpf L/R mismatch (results/v5_mc2.json)

| Quantity | Mean ± σ | Range |
|---|---|---|
| tail | 855 ± 11 mV | 819–877 |
| VCM | 535 ± 12 mV | |
| output offset | σ 0.81 mV | max 1.6 |
| gain | 33.8 ± 0.2 dB | 32.9–34.1 |
| I(VDD) | 1040 ± 34 nA | |
| Ct code | 3.89 ± 0.56 pF | 1.6–4.7 |
| Zin min | 2.68 ± 0.24 GΩ | worst 2.38 |
| Zin at 50 Hz | 24 ± 2.4 GΩ | worst 21 |

## Switched transient with everything (bulk switching 2 kHz, bias loop, dry electrodes, mains, reset released at a signal zero crossing; results/v5_tranfinal2.log)

| Case | Gain | THD | 50 Hz in-ref | Output ripple | Input CM | Current |
|---|---|---|---|---|---|---|
| tt27, 4 mVpp + mains | 33.7 dB | 0.29% | 15 µVpp | 25 µV | 0.531 V (10 mVpp) | 1038 nA + 11.9 nA |
| tt27, 10 mVpp, no mains | 33.3 dB | 2.2% | (≤ 25, fit residual) | 65 µV | | |
| ss0, 4 mVpp + mains | 33.3 dB | 0.51% | 28 µVpp | 53 µV | 0.370 V (17 mVpp) | |
| ff60, 4 mVpp + mains | 34.0 dB | 0.24% | 12 µVpp | 1 µV | 0.699 V (14 mVpp) | 1181 nA + 12.0 nA |

## Usage notes (for the board / firmware)

- **Reset:** hold rst (ui_in) high ≥ 20 ms after power-up and after any saturation (lead-off, big artefact).
  - Release it on the ECG baseline (TP segment). The reset captures the instantaneous differential input as the new zero; the captured error then decays with the Rf·Cf time constant, which is very long (mHz HP corner at 27 °C).
  - The reset also captures the electrode DC offset, which is what lets ±50 mV through.
- **Electrodes:** three-electrode use is required (two inputs + bias electrode on ua[4]). A digital 50/60 Hz notch is needed.
- **Trim:** Ct is a 10-bit code (common to both sides), found once per board by maximising source-referred gain with a 500 MΩ‖22 pF source impedance (as Zheng & Liu do).

## Capacitors and pins

- **Capacitors:** Cbc 2×20, Ct 2×≤5, Cg 15, Cf 2×1.12, Cpf 2×0.68, driver Cc 10, bulk Cc 2×5 ≈ 89 pF.
  - Plan: MOS caps (≈ 8 fF/µm²) for Cbc, Cg, Ct and driver Cc; MIM for Cf, Cpf and bulk Cc. About 14,000 µm².
  - Ct can be 1.5 pF fixed + 9 bits.
- **Pins:** ua0/1 inputs, ua2/3 outputs (+ external 8.8 pF each), ua4 bias electrode, ua5 IB (50 nA reference).
  - Digital: clk (switching), en, rst, and a trim shift register (clk/data/latch).

## Open before layout

1. Layout plus extraction. TΩ nodes (vi, nw, g3/4, r1–r6, vgr) need guard rings; leakage paths matter at the fA level.
2. IB generation: currently an ideal 50 nA. A board resistor (≈ 15 MΩ from ua5) gives ±20% across corners. Decide whether that's acceptable or add an on-chip reference.
3. Power-up with switching on and with mismatch; the reset logic timing in the TT wrapper.
4. Rb noise and replica current are from the linear-equivalent model. Measuring the pseudo-R value on silicon (via Zin at 0.5 Hz) is part of the test plan.

## Layout prep (2x2 tile)

### On-chip bias reference (v5_iref.py), replacing the external 50 nA
- **Circuit:** subthreshold beta-multiplier (constant-gm). nfet_lvt 2/8 ×1 vs ×8 (K = 8); pfet_lvt 4/8 1:1 mirror; R = xhigh_po 0.35 µm, 7.5 MΩ.
  - Core branches 9 nA each; ×5 nfet mirror sinks about 50 nA from nb.
  - Extra current: about 18 nA.
- **Trim:** 2-bit on R, ×{0.85, 0.95, 1.05, 1.15}.
- **Start-up:** self-biased. A 0.1 pF cap from VDD kicks st high on the supply ramp, nfet Mk pulls n2 low, and Mi (gate n1) clears st once running; st ≈ 0 in steady state.
- **Performance:**
  - Untrimmed: 35–74 nA over MOS × R (±15%) × 0–60 °C.
  - Trimmed at 27 °C: 48.6 nA at both R extremes, ±7% over MOS corners.
  - PTAT: ×0.87 at 0 °C, ×1.17 at 60 °C. That keeps gm ∝ 1/R, so noise holds over temperature.
  - Supply: 48.0 / 50.0 / 52.0 nA at VDD 0.9 / 1.0 / 1.1 V.
- **Full amplifier power-up with the reference:** settles in 1–26 ms at tt27, ss0, ff60, sf27. I(VDD) 845–1428 nA untrimmed.

### Cbc as an accumulation varactor (saves about 40 pF of MIM)
- **Device:** sky130_fd_pr__cap_var_lvt, gate on nw (higher), n-well on vi; 240 units of 10×2.
- **Capacitance:** 17.5–29.8 pF over corners (bias Vgw 0.13–0.47 V). Plus 0.7 pF n-well bottom plate at each input, absorbed by Ct.
- **Results vs ideal 20 pF:** IRN 0.85–0.995 µVrms, Zin min 2.60–3.23 GΩ, Zin at 50 Hz 23–142 GΩ. Equal or better.
- **Area:** a longer-l unit (10/8) gives a better area ratio. MIM can be stacked on top, in parallel.
- **Ct bank:** varactors as well (gate on vi, well switched to ground), 3.9–8.8 fF/µm².

### Tail mirror shrunk 5× in W
MB1 2/2 ×10, MB2 2/2 ×200, DRL bias leg 2/2. Tail and loop are unchanged (I(VDD) 1012 vs 1038 nA).

### Pins
| Pin | Signal |
|---|---|
| ua0 / ua1 | VIN1 / VIN2 |
| ua2 / ua3 | VOUT1 / VOUT2 |
| ua4 | bias electrode |
| ua5 | VDD 1.0 V supply (freed by the on-chip reference) |
| ui_in[7:0], uio_in[1:0] | Ct[9:0] |
| uio_in[2] | en (switching) |
| uio_in[3] | rst |
| uio_in[5:4] | IREF trim |
| clk | 2 kHz switching clock |
| uio_oe, uo_out | tied to VGND |

6 analog pins: 2 × €40 + 4 × €100.

### Floorplan (lay5/floorplan_v5.png)
- Devices + varactors + logic: about 48,900 µm² (65% of 75,600).
- MIM overlays: about 30,000 µm² (40%), placed over devices.
- Bulk Cc and Miller Cc regions are about 15% short of area as drawn. Use the free pockets beside the I-ref block and at the right edge, or take the Miller Cc to 8 pF (PM is still above 40°).
