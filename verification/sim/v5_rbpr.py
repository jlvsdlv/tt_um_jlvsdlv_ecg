"""Replica-biased linear pseudo-resistor for the DTMOS well bias (target ~300-500 GOhm).
MR: NS series pfet_01v8 (W,L), gates at vgr; replica: pfet_01v8 diode (source/body = tail, gate=drain=vgr) sunk by IR.
R(Vds->0) ~ Ut / (IR * k), k = (W/L)_MR / NS / (W/L)_rep. Here: test bench R across corners/temps and mismatch."""
import numpy as np, sys
from concurrent.futures import ProcessPoolExecutor
from lv import run
from amp import dev, PDK
P = "sky130_fd_pr__pfet_01v8"
MRG, NS, REP, IR = (2, 20, 1), 4, (10, 1, 48), float(sys.argv[1]) if len(sys.argv) > 1 else 1e-9
def bank(src, dst, tag, p, mm=None):
    s = ""
    nodes = [src] + [f"x{tag}{i}" for i in range(NS - 1)] + [dst]
    for i in range(NS):
        s += dev(f"MR{tag}{i}", nodes[i + 1], f"vgr", nodes[i], "tail" if False else nodes[i], P, MRG, p)
    return s
def rtest(a):
    corner, temp, seed = a
    p = dict(mm=None)
    if seed is not None:   # Vth mismatch on MR devices only (Pelgrom ~5 mV*um for pfet)
        rng = np.random.default_rng(seed); W, L, m = MRG
        p["mm"] = {f"MRa{i}": dict(mm_vth0=float(rng.normal(0, 5e-3 / np.sqrt(W * L * m)))) for i in range(NS)}
    net = (f"* R test\n.include {PDK}/lib_{corner}.spice\n.temp {temp}\n.option gmin=1e-15 abstol=1e-18 reltol=1e-6 noacct\n"
           "Vt tail 0 0.80\nVn nw 0 0.81\n" + dev("MREP", "vgr", "vgr", "tail", "tail", P, REP, {}) + f"Ir vgr 0 {IR}\n"
           + bank("tail", "nw", "a", p) + ".control\nop\nprint i(Vn) v(vgr)\n.endc\n.end\n")
    o, f = run(net)
    import re
    v = dict(re.findall(r"^\s*(i\(vn\)|v\(vgr\))\s*=\s*([-\d.e+]+)", o, re.M | re.I))
    i = abs(float(v.get("i(vn)", "nan"))); return a, 0.01 / i
if __name__ == "__main__":
    J = [(c, t, None) for c in ("tt", "ss", "ff", "sf", "fs") for t in (0, 27, 60)] + [("tt", 27, s) for s in range(30)]
    with ProcessPoolExecutor(2) as ex: R = list(ex.map(rtest, J))
    for (c, t, s), r in R:
        if s is None: print(f"{c}{t}: R = {r/1e9:.0f} GOhm")
    mc = np.array([r for (c, t, s), r in R if s is not None])
    print(f"MC (30, tt27): mean {mc.mean()/1e9:.0f} GOhm, sigma {mc.std()/mc.mean()*100:.1f}%, range {mc.min()/1e9:.0f}-{mc.max()/1e9:.0f}")
