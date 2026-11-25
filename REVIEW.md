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
| Common mode | Bias-electrode (DRL) driver on `ua[4]`: two-stage OTA that servos the tail to 6/7·V<sub>DD</sub>. Class-A stage-2 sink of 40 nA (2 × 4-unit cells). Phase margin 61–74° over corners, ≥ 64° with the reference 25 % low. |
| Bias | On-chip subthreshold beta-multiplier (xhigh_po R, 2-bit trim `IT`), ≈ 50 nA, ×20 to the tail (≈ 0.93 µA). |
| Reset | pfet_lvt 0.42/0.5 switches on the TΩ nodes, driven by `RST`. |

## 2. Verification status

| Check | Tool | Result | Evidence |
|---|---|---|---|
| DRC (flattened GDS, full deck) | magic 8.3.706 `drc(full)` | 0 errors | — |
| TT precheck (gds, precheck, viewer) | GitHub Actions @ttsky26e | green on `b218b05` | Actions tab |
| LVS (GDS-extracted vs reference) | netgen | unique match, 133 devices, no property errors | `verification/lvs/lvs_gds.out` |
| Antenna | magic `antennacheck` | 0 violations (4 diodes added: `ui_in[4]`, `ui_in[5]`, `uio_in[1]`, `uio_in[4]`) | `verification/lvs/antenna.log` |
| Post-layout AC/noise, 10 PVT corners | schematic + magic-extracted coupling/substrate C back-annotated | see §3 | `verification/sim/v5_post.py`, `results/v5_post_x1_cpf820.json` |
| **Extracted-netlist transient** (flat GDS extraction incl. parasitic C; power-up from 0 V → reset → switching + 4 mVpp + mains) | ngspice | tt 27 °C (previous routing): gain 33.75 dB, start-up 0.1 ms, bias settled 3.1 ms. **ss 0 °C, final GDS, default `IT`:** gain 33.46 dB, THD 0.70 %, 50 Hz 41 µVpp, tail 0.839–0.859 V | `verification/sim/v5_chip_tran.py`, `results/chip_final_*.json` |
| Monte Carlo, 40 seeds, tt 27 °C, post-layout C + real C<sub>t</sub> weights | ngspice | C<sub>t</sub> optimum 1.02–4.52 pF (never at a limit); Z<sub>in</sub> ≥ 2.04 GΩ; gain σ 0.2 dB; tail 854 ± 11 mV | `verification/sim/v5_mc3.py`, `results/v5_mc3.json` |

## 3. Key simulated performance (post-layout)

| Parameter | Value |
|---|---|
| Gain | 32.9–34.0 dB |
| -3 dB bandwidth | ≈ 2 mHz (66 mHz at 60 °C) to 2.3–2.8 kHz |
| IRN, 0.5–150 Hz, switching on | 0.89–1.00 µVrms |
| IRN, full band | 3.1–3.3 µVrms (ENBW ≈ 3.3 kHz) |
| NEF, full band (whole chip at 1.0 V / tail only) | 2.11 / 2.02 (tt 27 °C) |
| NEF, 0.5–150 Hz (whole chip / tail only) | 2.85 / 2.73 |
| Z<sub>in</sub> after trim, 0.5–150 Hz | ≥ 2.24 GΩ (worst at 150 Hz); 20–104 GΩ at 50 Hz (MC worst 2.04 GΩ) |
| Supply | ≈ 0.98–1.16 µA at 1.0 V + ≈ 12 nA at 1.8 V |

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
   - C<sub>pf</sub> = 0.82 pF puts the optimum at 2.6–4.5 pF over corners and 1.0–4.5 pF in MC, so it never hits a limit.
   - Firmware must do a full code search.
   - Not fixable in the remaining time: doubling the bits needs about 2400 µm² more MIM per side.
2. **Gate-drain fringe is not in the BSIM model** (cf = 0 by design in SKY130; the PDK expects it from extraction). Magic extracts ≈ 85–95 fF of vi–vo coupling, which the Miller effect multiplies by the gain. C<sub>pf</sub> is sized on that extraction, and the trim tolerates roughly −45 / +15 fF of error.
3. **The p-well islands power up high** (+0.2–0.3 V), because the supply ramp kicks them and they relax only slowly through the forward clamp.
   - Effect: larger 2 kHz ripple, gain unchanged.
   - No island reset switch is possible: any switch to ground conducts when the island swings to −1.4 V.
4. **2 kHz ripple:** up to ≈ 350 µV at the output at ss 0 °C (≈ 7 µV input-referred), out of band. Sources: the islands above, plus a residual one-sided 0.5 fF coupling between `drva` and `nw1` (input-pair body) after the noisy/quiet router keep-out.
5. **Bias-electrode driver margin: fixed.** The stage-2 sink was doubled to 40 nA (+20 nA). On the extracted ss 0 °C run with default `IT`, the common mode now holds (tail 0.839–0.859 V, body ±11 mV). Previously it lost control at the mains peaks.
6. **Gate-oxide stress on the switched loads:** peak V<sub>gb</sub> = 1.69 V in the extracted ss 0 °C run, below the 1.95 V maximum for 1.8 V devices.
7. **Remaining open items:**
   - Extracted transient at ff 60 °C on the final GDS (running).
   - tt 27 °C on the final routing (done on the previous routing, which differs only in routing and the sink cell).
8. **Modelling simplifications:**
   - Varactors are linearized per corner, because the ngspice charge model fails in operating-point analysis.
   - MIM/xhigh_po/diode use simple models (`verification/sim/passives_ext.spice`).
   - The bulk-switching noise reduction uses a trap model calibrated to Han et al. (TCAS-II 2015) measurements (β = 0.049).
   - Magic names the substrate node after p-well island B (the parasitic C to substrate is remapped to ground), and lumps a node's junction area onto one device (replaced by per-device geometry in the extracted transient).
   - Noise and Z<sub>in</sub> use schematic + back-annotated C, not the full extracted netlist.

## 5. Where things are

- `gds/`, `lef/`, `mag/`: final layout (top `tt_um_jlvsdlv_ecg`, metal 1–4 only).
- `layout_gen/`: generator (`build5.py`), router (`route6.py`), reference netlist generator (`ref_netlist.py`), export / DRC / antenna / extraction scripts.
- `verification/lvs/`: reference netlist, GDS-extracted LVS netlist, parasitic-extracted netlist, netgen report, antenna log.
- `verification/sim/`: testbenches (`v5_core.py`, `v5_sim.py`, `v5_bias.py`, `v5_post.py`, `v5_chip_tran.py`, …) and `results/`.
