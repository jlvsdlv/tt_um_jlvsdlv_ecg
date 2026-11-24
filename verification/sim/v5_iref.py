"""On-chip bias reference replacing the external 50 nA IB sink.
Subthreshold beta-multiplier (constant-gm): MN1 (diode) / MN2 (K=8 x) with R in MN2's source, pfet 1:1 mirror.
I_core = n*Ut*ln(K)/R ~ 10 nA per branch; output nfet mirror x5 sinks ~50 nA from nb (gate of MB1/MB2).
R = xhigh_po 0.35 um (2 kOhm/sq), 2-bit trim {0.85, 0.95, 1.05, 1.15} x Rnom via nfet shorting switches.
Start-up: rst (1.8 V, already needed for the amplifier) pulls n2 low.
R modelled as Rsheet*L/W*(1+var)*(1+tc1*dT+tc2*dT^2) with var = -/0/+15 % (PDK res corners), tc1 -1.47e-3, tc2 2.7e-6 (xhigh_po model)."""
import numpy as np, re, sys, json
from concurrent.futures import ProcessPoolExecutor
from lv import run
from amp import dev, PDK, load_wrdata
NL, PL = "sky130_fd_pr__nfet_01v8_lvt", "sky130_fd_pr__pfet_01v8_lvt"
K, RNOM = 8, 7.5e6
GEO = dict(MN1=(2, 8, 1), MN2=(2, 8, K), MP=(4, 8, 1), MN3=(2, 8, 5), MS=(0.42, 0.5, 1))
def rval(var, temp, code=1):
    f = [0.85, 0.95, 1.05, 1.15][code]
    dT = temp - 30
    return RNOM * f * (1 + var) * (1 - 1.47e-3 * dT + 2.7e-6 * dT * dT)
def ref(p, var=0.0, code=1, temp=27, out="nb"):
    s = dev("RMN1", "n1", "n1", "vss", "vss", NL, GEO["MN1"], p)
    s += dev("RMN2", "n2x", "n1", "rs", "vss", NL, GEO["MN2"], p)
    s += dev("RMP1", "n1", "n2x", "vdd", "vdd", PL, GEO["MP"], p)
    s += dev("RMP2", "n2x", "n2x", "vdd", "vdd", PL, GEO["MP"], p)
    s += f"RREF rs vss {rval(var, temp, code):.6g}\n"
    s += dev("RMN3", out, "n1", "vss", "vss", NL, GEO["MN3"], p)
    # self-biased start-up: st is pulled up only by Ml's off-leakage; Mi (gate n1) holds st at 0 once the core runs; Mk kicks n2x low otherwise
    s += dev("RML", "st", "vdd", "vdd", "vdd", "sky130_fd_pr__pfet_01v8", (0.42, 4, 1), p)
    s += dev("RMI", "st", "n1", "vss", "vss", NL, (0.42, 1, 1), p)
    s += dev("RMK", "n2x", "st", "vss", "vss", "sky130_fd_pr__nfet_01v8", (0.42, 1, 1), p)
    s += "CST vdd st 0.1p\n"        # supply ramp couples st high -> kick (leakage alone is too slow at 0 C)
    return s
def hdr(corner, temp):
    return (f"* iref\n.include {PDK}/lib_{corner}.spice\n.temp {temp}\n.option gmin=1e-15 abstol=1e-18 reltol=1e-6 noacct\n")
def bench(a):
    corner, temp, var, code, vdd = a
    p = {}
    net = (hdr(corner, temp) + ref(p, var, code, temp, out="nbm") + "Vm nb nbm 0\n" + dev("MB1", "nb", "nb", "vdd", "vdd", PL, (10, 2, 10), p) +
           f"Vdd vdd 0 pwl(0 0 1m {vdd})\nVss vss 0 0\n"
           ".control\ntran 10u 20m 0 10u uic\nlinearize\nwrdata r.txt i(vm) v(rs) v(nb) i(vdd) v(st)\n.endc\n.end\n")
    o, f = run(net)
    if "r.txt" not in f: return a, np.nan, np.nan, np.nan
    x = load_wrdata(f["r.txt"])[-1]
    return a, x[1], x[3] / rval(var, temp, code), x[9]
if __name__ == "__main__":
    J = []
    for c in ("tt", "ss", "ff", "sf", "fs"):
        for t in (0, 27, 37, 60):
            for var in (-0.15, 0.0, 0.15): J.append((c, t, var, 1, 1.0))
    J += [("tt", 27, 0.0, 1, v) for v in (0.9, 1.1)] + [("tt", 27, 0.15, c, 1.0) for c in range(4)] + [("tt", 27, -0.15, c, 1.0) for c in range(4)]
    with ProcessPoolExecutor(2) as ex: R = list(ex.map(bench, J))
    tab = {}
    for (c, t, var, code, vdd), io, ic, nb in R: tab[(c, t, var, code, vdd)] = (io, ic, nb)
    print("IB out (nA), code 1, VDD 1.0  [R var -15% / 0 / +15%]")
    for c in ("tt", "ss", "ff", "sf", "fs"):
        print(f"  {c}: " + "  ".join(f"{t:>2}C " + "/".join(f"{tab[(c, t, v, 1, 1.0)][0]*1e9:5.1f}" for v in (-0.15, 0.0, 0.15)) for t in (0, 27, 37, 60)))
    io = [tab[k][0] for k in tab if k[3] == 1 and k[4] == 1.0]
    print(f"  st node (should be ~0): max {max(abs(tab[k][2]) for k in tab):.3g} V")
    print(f"  overall {min(io)*1e9:.1f}-{max(io)*1e9:.1f} nA; core branch tt27 {tab[('tt',27,0.0,1,1.0)][1]*1e9:.2f} nA")
    print("VDD sensitivity tt27: " + ", ".join(f"{v} V: {tab[('tt',27,0.0,1,v)][0]*1e9:.2f} nA" for v in (0.9, 1.0, 1.1)))
    for var in (0.15, -0.15): print(f"trim codes at R {var:+.0%}: " + ", ".join(f"{c}: {tab[('tt',27,var,c,1.0)][0]*1e9:.1f}" for c in range(4)))
    json.dump([(list(a), io, ic, nb) for a, io, ic, nb in R], open("results/v5_iref.json", "w"))
