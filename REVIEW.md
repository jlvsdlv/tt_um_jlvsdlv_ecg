# Design review guide — tt_um_jlvsdlv_ecg (TTSKY26e, 2×2 analog)

This guide is for reviewers. It covers what the design is, what was verified and how, what is known to be imperfect, and where to look. All numbers are simulations (ngspice 42, SKY130 BSIM4 models). Nothing has been measured yet.

## 1. Architecture (see `docs/schematic.png`)

The amplifier is a differential-difference amplifier (DDA) with capacitive feedback, running from a 1.0 V analog supply (`ua[5]`). Logic and the bulk-switching driver run from VDPWR = 1.8 V.

| Block | Implementation |
|---|---|
| Input pair M1/M2 | pfet_01v8_lvt, 800/8 µm each (32 × 25/8), cross-quad. **AC-coupled DTMOS:** body ↔ gate through C<sub>bc</sub> (cap_var_lvt ∥ MIM, ≈ 17–22 pF). Body DC-biased to the tail by a replica-biased pseudo-resistor (4 × pfet 2/20 in series, replica 10/1 ×48, I<sub>RB</sub> = 0.5 nA). |
| Loads M3/M4 | nfet_01v8_lvt 2.5/64, each split into halves A/B placed in two isolated p-wells inside one deep n-well. **Two-phase complementary bulk switching** at 2 kHz: the wells are driven in antiphase through C<sub>c</sub> = 5 pF from a 0–1.8 V driver, with an n+/p-well clamp. One half always conducts. |
| Gain / feedback | C<sub>g</sub>/C<sub>f</sub> (≈ 33.7 dB), pseudo-resistor feedback (high-pass ≈ 2 mHz). |
| Input-impedance boost | Fixed positive feedback C<sub>pf</sub> = 0.82 pF (deliberate over-neutralization) plus a 10-bit input-node trim C<sub>t</sub> to ground. |
| Common mode | Bias-electrode (DRL) driver on `ua[4]`: two-stage OTA that servos the tail to 6/7·V<sub>DD</sub>. |
| Bias | On-chip subthreshold beta-multiplier (xhigh_po R, 2-bit trim `IT`), ≈ 50 nA, ×20 to the tail (≈ 0.93 µA). |
| Reset | pfet_lvt 0.42/0.5 switches on the TΩ nodes, driven by `RST`. |

## 2. Verification status

| Check | Tool | Result | Evidence |
|---|---|---|---|
| DRC (flattened GDS, full deck) | magic 8.3.706 `drc(full)` | 0 errors | — |
| TT precheck (gds, precheck, viewer) | GitHub Actions @ttsky26e | green on `b218b05` | Actions tab |
| LVS (GDS-extracted vs reference) | netgen | unique match, 132 devices, no property errors | `verification/lvs/lvs_gds.out` |
| Antenna | magic `antennacheck` | 0 violations (3 diodes added: `ui_in[4]`, `ui_in[5]`, `uio_in[4]`) | `verification/lvs/antenna.log` |
| Post-layout AC/noise, 10 PVT corners | schematic + magic-extracted coupling/substrate C back-annotated | see §3 | `verification/sim/v5_post.py`, `results/v5_post_x1_cpf820.json` |
| **Extracted-netlist transient** (flat GDS extraction incl. parasitic C; power-up from 0 V → reset → switching + 4 mVpp + mains) | ngspice | tt 27 °C: gain 33.75 dB, start-up 0.1 ms, bias settled 3.1 ms | `verification/sim/v5_chip_tran.py`, `results/chip_final_tt27.json` |

## 3. Key simulated performance (post-layout)

| Parameter | Value |
|---|---|
| Gain | 32.9–34.0 dB |
| -3 dB bandwidth | ≈ 2 mHz (66 mHz at 60 °C) to 2.3–2.8 kHz |
| IRN, 0.5–150 Hz, switching on | 0.89–1.00 µVrms |
| IRN, full band | 3.1–3.3 µVrms (ENBW ≈ 3.3 kHz) |
| NEF, full band (whole chip at 1.0 V / tail only) | 2.11 / 2.02 (tt 27 °C) |
| NEF, 0.5–150 Hz (whole chip / tail only) | 2.85 / 2.73 |
| Z<sub>in</sub> after trim, 0.5–150 Hz | ≥ 2.30 GΩ (worst at 150 Hz); 20–108 GΩ at 50 Hz |
| Supply | ≈ 0.96–1.14 µA at 1.0 V + ≈ 12 nA at 1.8 V |

AC-coupled DTMOS vs. the alternatives was simulated on the same amplifier (`verification/sim/v5_dtmos_cmp.py`, tt 27 °C):

| | Standard pfet | Conventional DTMOS | AC-coupled DTMOS |
|---|---|---|---|
| Effective gm | 9.6 µS | 12.5 µS | 12.0 µS |
| DC input current | fA | 94 pA (540 pA at 60 °C) | fA |
| Resistive input impedance at 1 Hz | 2 TΩ | 0.65 GΩ | 610 GΩ |
| IRN (switching on) | 1.05 µVrms | 0.80 µVrms | 0.90 µVrms |

## 4. Known issues and limitations — please scrutinize

1. **The C<sub>t</sub> MIM bits are half their intended weight.** Bits 6–9 are ≈ 0.31 / 0.61 / 1.22 / 2.44 pF per side instead of 0.64 / 1.28 / 2.56 / 5.12 pF.
   - Range is 0–5.3 pF and the code is non-monotonic (code 64 < code 63), but there are no gaps (≈ 11 fF resolution).
   - C<sub>pf</sub> was lowered to 0.82 pF so the optimum (2.2–4.1 pF across corners) falls inside the range.
   - Firmware must do a full code search.
2. **Gate-drain fringe is not in the BSIM model** (cf = 0). Magic extracts ≈ 100 fF of vi–vo coupling, which is multiplied by the gain through the Miller effect. C<sub>pf</sub> is sized against magic's estimate, so if that estimate is off by more than ≈ ±25 fF, the trim range may not suffice.
3. **The p-well islands power up high** (+0.2–0.3 V), because the supply ramp kicks them up and they relax back only slowly through the forward clamp.
   - The schematic transients started them already settled at about 0 V; the extracted-netlist transient shows the real behaviour.
   - Effect: larger 2 kHz ripple, gain unchanged.
   - No reset switch is possible, because any switch from the island to ground conducts when the island swings to −1.4 V.
4. **2 kHz ripple:** ≈ 170 µV at the output (≈ 3.5 µV input-referred). It comes from the islands above plus a 1.2 fF routing coupling between `drvb` and `ua[1]`. It is out of band.
5. **Bias-electrode driver margin at cold/slow.** At ss 0 °C with the reference trim at default, the DRL loses control at the mains peaks. With `IT` = 11 it holds, with about 60 mVpp of common-mode swing. Firmware must set `IT` for I(VDD) ≥ 0.9 µA.
6. **Gate-oxide stress on the switched loads.** V<sub>gb</sub> reaches about 1.8 V in the accumulation phase, which is at the 1.8 V device rating.
7. **Not yet run on the final GDS:** extracted transients at ff 60 °C and ss 0 °C (ss 0 °C was run on the previous routing and passes with `IT` = 11), and Monte Carlo with the post-layout C plus the real C<sub>t</sub> weights.
8. **Modelling simplifications:**
   - Varactors are linearized per corner, because the ngspice charge model fails in operating-point analysis.
   - MIM/xhigh_po/diode use simple models (`verification/sim/passives_ext.spice`).
   - The trap/bulk-switching noise reduction uses a model calibrated to Han et al. (TCAS-II 2015) measurements (β = 0.049).
   - Magic names the substrate node after p-well island B (the parasitic C to substrate is remapped to ground), and lumps a node's junction area onto one device (replaced by per-device geometry in the extracted transient).

## 5. Where things are

- `gds/`, `lef/`, `mag/`: final layout (top `tt_um_jlvsdlv_ecg`, metal 1–4 only).
- `layout_gen/`: generator (`build5.py`), router (`route6.py`), reference netlist generator (`ref_netlist.py`), export / DRC / antenna / extraction scripts.
- `verification/lvs/`: reference netlist, GDS-extracted LVS netlist, parasitic-extracted netlist, netgen report, antenna log.
- `verification/sim/`: testbenches (`v5_core.py`, `v5_sim.py`, `v5_bias.py`, `v5_post.py`, `v5_chip_tran.py`, …) and `results/`.
