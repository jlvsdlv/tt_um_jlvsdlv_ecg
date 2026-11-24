"""LVS reference (schematic) netlist for tt_um_ecg_v5 (TT sky130 2x2 analog tile).
Net naming: vdd = ua[5] (1.0 V core supply), VGND = 0, VDPWR = 1.8 V logic supply.
Generates tt_um_ecg_v5.spice; device values are the frozen v5 design (DESIGN_v5.md)."""
P, PL, N, NL = "sky130_fd_pr__pfet_01v8", "sky130_fd_pr__pfet_01v8_lvt", "sky130_fd_pr__nfet_01v8", "sky130_fd_pr__nfet_01v8_lvt"
MIM, VAR, RX = "sky130_fd_pr__cap_mim_m3_1", "sky130_fd_pr__cap_var_lvt", "sky130_fd_pr__res_xhigh_po_0p35"
L = []
def m(name, d, g, s, b, model, w, l, mult=1):
    L.append(f"X{name} {d} {g} {s} {b} {model} W={w} L={l} m={mult}")
def cap(name, a, b, w, l, mult=1):            # MIM: C ~ 2 fF/um2 * w*l
    L.append(f"X{name} {a} {b} {MIM} W={w} L={l} m={mult}")
def var(name, gate, well, w, l, mult):
    L.append(f"X{name} {gate} {well} VGND {VAR} W={w} L={l} m={mult}")
def res(name, a, b, l, mult=1):
    L.append(f"X{name} {a} {b} VGND {RX} L={l} m={mult}")
# side-specific nets
vi = {1: "vi1", 2: "vi2"}; vo = {1: "vo1", 2: "vo2"}
# ---------------- input pair (DTMOS, AC-coupled bodies) 16 x 50/8 each, as 4 quads of nf=4
m("M1", "vo2", "vi1", "tail", "nw1", PL, 25, 8, 32)      # 4 stacked pairs x 2 cells x nf4
m("M2", "vo1", "vi2", "tail", "nw2", PL, 25, 8, 32)
# coupling varactors gate = nw (higher), well = vi ; 60 x (10/8)
# Cbc = varactor (36 x 10/8, gate on nw) || MIM (5 x 30x30: 3 over the varactor, 2 over the input pair) -> 19.5-27 pF over corners
var("CBC1", "nw1", "vi1", 10, 8, 27); var("CBC2", "nw2", "vi2", 10, 8, 27)
cap("CBM1", "nw1", "vi1", 30, 30, 5); cap("CBM2", "nw2", "vi2", 30, 30, 5)
# well bias: replica-biased linear pseudo-R (4 series per side) + replica + IRB mirror
m("MREP", "vgr", "vgr", "tail", "tail", P, 10, 1, 48)
for sd in (1, 2):
    nodes = ["tail"] + [f"xr{sd}{i}" for i in range(3)] + [f"nw{sd}"]
    for i in range(4): m(f"MRB{sd}{i}", nodes[i + 1], "vgr", nodes[i], nodes[i], P, 2, 20)
m("IRBM", "vgr", "nd", "VGND", "VGND", NL, 0.42, 16)
# ---------------- loads: bulk-switched halves A/B in two isolated p-wells (DNW)
for side, (d, g) in {3: ("vo2", "g3"), 4: ("vo1", "g4")}.items():
    for h, w in (("A", "vbna"), ("B", "vbnb")):
        m(f"M{side}{h}", d, g, "VGND", w, NL, 2.5, 64, 2)
# feedback pseudo-R and gain caps
m("MR3", "g3", "vo2", "vo2", "vo2", P, 0.42, 4); m("MR4", "g4", "vo1", "vo1", "vo1", P, 0.42, 4)
cap("CF3", "vo2", "g3", 23.6, 23.6); cap("CF4", "vo1", "g4", 23.6, 23.6)            # 1.12 pF
cap("CGA", "g3", "g4", 30, 30, 4); cap("CGB", "g4", "g3", 30, 30, 4)               # 2 x 7.5 pF (common-centroid halves)
cap("CPF1", "vo1", "vi1", 20.5, 20.5); cap("CPF2", "vo2", "vi2", 20.5, 20.5)        # 0.84 pF (post-layout: covers extracted gate-drain fringe)
# tail mirror
m("MB1", "nb", "nb", "vdd", "vdd", PL, 2, 2, 10)
m("MB2", "tail", "nb", "vdd", "vdd", PL, 2, 2, 200)
# reset switches: pfet_lvt, n-well = low-impedance side, gate = rstb
for nm, a, b in (("SWF3", "g3", "vo2"), ("SWF4", "g4", "vo1"), ("SWB1", "nw1", "tail"), ("SWB2", "nw2", "tail")):
    m(nm, a, "rstb", b, b, PL, 0.42, 0.5)
# ---------------- input trim banks Ct (10 bits per side, common code): varactor gate = vi, well = ctX_k, nfet switch to VGND
# bits 0-5: varactor units (2 x 0.8 um, ~6-14 fF each, gate on vi); bits 6-9: MIM 0.3/0.6/1.2/2.4 pF (top plate vi)
# sub-binary across the type change but every bit <= sum of the lower bits + LSB at all corners -> no gaps
MIMBITS = {6: (12.2, 12.2, 1), 7: (17.3, 17.3, 1), 8: (24.5, 24.5, 1), 9: (24.5, 24.5, 2)}
for sd in (1, 2):
    for k in range(10):
        if k <= 3: var(f"CT{sd}_{k}", vi[sd], f"ct{sd}_{k}", 2, 0.8, 2 ** k)
        elif k <= 5: var(f"CT{sd}_{k}", vi[sd], f"ct{sd}_{k}", 8, 3.2, 2 ** (k - 4))
        else:
            w, l_, mm = MIMBITS[k]; cap(f"CT{sd}_{k}", vi[sd], f"ct{sd}_{k}", w, l_, mm)
        m(f"SCT{sd}_{k}", f"ct{sd}_{k}", f"b{k}", "VGND", "VGND", N, 1, 0.5)
# ---------------- bias-electrode loop
for i in range(7):
    a = "vdd" if i == 0 else f"r{i}"; b = "VGND" if i == 6 else f"r{i+1}"
    m(f"LD{i}", b, b, a, a, PL, 2, 2)
m("BP", "nd", "nb", "vdd", "vdd", PL, 2, 2); m("BN", "nd", "nd", "VGND", "VGND", NL, 2, 8)
m("S1", "s1", "nd", "VGND", "VGND", NL, 2, 8)
m("A1", "xa", "tail", "s1", "VGND", NL, 2, 4); m("A2", "x", "r1", "s1", "VGND", NL, 2, 4)
m("PA", "xa", "xa", "vdd", "vdd", PL, 4, 2); m("PB", "x", "xa", "vdd", "vdd", PL, 4, 2)
m("P2", "drl", "x", "vdd", "vdd", PL, 4, 2); m("S2", "drl", "nd", "VGND", "VGND", NL, 2, 8, 4)
cap("CCM", "x", "drl", 30, 30, 5)                                                     # ~9-10 pF Miller
# ---------------- bias reference (replaces external IB): beta multiplier + 2-bit R trim + start-up
m("RN1", "n1", "n1", "VGND", "VGND", NL, 2, 8); m("RN2", "n2", "n1", "rs", "VGND", NL, 2, 8, 8)
m("RP1", "n1", "n2", "vdd", "vdd", PL, 4, 8); m("RP2", "n2", "n2", "vdd", "vdd", PL, 4, 8)
m("RN3", "nb", "n1", "VGND", "VGND", NL, 2, 8, 5)
def rchain(nm, a, b, l, n):
    nodes = [a] + [f"{nm.lower()}_{k}" for k in range(n - 1)] + [b]
    for k in range(n): res(f"{nm}_{k}", nodes[k], nodes[k + 1], l)
rchain("RR0", "rs", "rt1", 70, 16); rchain("RR1", "rt1", "rt2", 65.5, 2); rchain("RR2", "rt2", "VGND", 65.5, 4)   # 0.85 / 0.10 / 0.20 x 7.5 MOhm
m("RS1", "rs", "it0", "rt1", "VGND", N, 1, 0.5); m("RS2", "rt1", "it1", "rt2", "VGND", N, 1, 0.5)   # wait: shorting switches below
m("RML", "st", "vdd", "vdd", "vdd", P, 0.42, 4); m("RMI", "st", "n1", "VGND", "VGND", NL, 0.42, 1)
m("RMK", "n2", "st", "VGND", "VGND", N, 0.42, 1); cap("CST", "vdd", "st", 7, 7)
# ---------------- 1.8 V logic: rst inverter, bulk-switch driver (2 phases), clamps
def inv(nm, o, i, wp=1, wn=0.5):
    m(nm + "P", o, i, "VDPWR", "VDPWR", P, wp, 0.5); m(nm + "N", o, i, "VGND", "VGND", N, wn, 0.5)
def nand(nm, o, a, b):
    m(nm + "P1", o, a, "VDPWR", "VDPWR", P, 1, 0.5); m(nm + "P2", o, b, "VDPWR", "VDPWR", P, 1, 0.5)
    m(nm + "N1", o, a, nm.lower() + "m", "VGND", N, 1, 0.5); m(nm + "N2", nm.lower() + "m", b, "VGND", "VGND", N, 1, 0.5)
inv("IRST", "rstb", "rst")
inv("IKC", "clkb", "clk")
for ph, ck in (("a", "clk"), ("b", "clkb")):
    nand(f"NDA{ph}", f"x1{ph}", ck, "en"); inv(f"I1{ph}", f"x2{ph}", f"x1{ph}", 2, 1); inv(f"I2{ph}", f"drv{ph}", f"x2{ph}", 4, 2)
    cap(f"CC{ph.upper()}", f"drv{ph}", f"vbn{ph}", 30, 30, 3)                      # ~5 pF
    m(f"MCL{ph}", "VGND", "VGND", "VGND", f"vbn{ph}", N, 2, 0.5)                    # n+/p-well clamp
L = [l for l in L if not l.startswith("XRS")]
# R trim: switch shorts segment when bit = 1   (it0 -> RR1 (0.1R), it1 -> RR2 (0.2R))
m("RS1", "rt1", "it0", "rt2", "VGND", N, 1, 0.5); m("RS2", "rt2", "it1", "VGND", "VGND", N, 1, 0.5)
PORTS = ("VDPWR VGND ua[0] ua[1] ua[2] ua[3] ua[4] ua[5] clk ui_in[0] ui_in[1] ui_in[2] ui_in[3] ui_in[4] ui_in[5] ui_in[6] ui_in[7] "
         "uio_in[0] uio_in[1] uio_in[2] uio_in[3] uio_in[4] uio_in[5]")
ALIAS = {"vi1": "ua[0]", "vi2": "ua[1]", "vo1": "ua[2]", "vo2": "ua[3]", "drl": "ua[4]", "vdd": "ua[5]",
         **{f"b{k}": f"ui_in[{k}]" for k in range(8)}, "b8": "uio_in[0]", "b9": "uio_in[1]", "en": "uio_in[2]", "rst": "uio_in[3]",
         "it0": "uio_in[4]", "it1": "uio_in[5]"}
import re
def sub(line):
    return " ".join(ALIAS.get(t, t) for t in line.split())
out = [f".subckt tt_um_ecg_v5 {PORTS}"] + [sub(l) for l in L] + [".ends tt_um_ecg_v5"]
open("tt_um_ecg_v5_ref.spice", "w").write("* tt_um_ecg_v5 LVS reference (schematic)\n" + "\n".join(out) + "\n")
nets = set(t for l in out[1:-1] for t in l.split()[1:5])
print(f"{len(out)-2} devices; nets {len(nets)}")
