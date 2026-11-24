"""Power-up from 0 V with the bias-electrode DRL closed, electrodes attached, static loads.
Reset switches (nfet_01v8 0.42/0.5, gate = rst at 1.8 V from a ui_in pin) across Rf (g3-vo2, g4-vo1) and Rb (nw-tail).
IB and the supply ramp together over 1 ms; IRB comes from the DRL bias mirror (nfet 0.42/16 off nd)."""
import numpy as np, re, json, sys
from concurrent.futures import ProcessPoolExecutor
import v5_sim as S, v5_bias as B
from lv import header, run
from amp import load_wrdata, dev
NL = "sky130_fd_pr__nfet_01v8"
USE_REF = '--ref' in sys.argv
def rst_sw(p):
    s = ""
    # isolated p-well (deep n-well) with the body bootstrapped to the low-impedance side -> ~0 V across the junction at the TOhm node
    # v5 layout version: pfet_01v8_lvt switches, n-well (body) = low-impedance side -> self-bootstrapped, no DNW islands needed;
    # gate = rstb (1.8 V logic): on at rstb = 0 (Vsg = 0.65-0.85 V), off at rstb = 1.8 V
    for nm, a, b in (("SWF3", "g3", "vo2"), ("SWF4", "g4", "vo1"), ("SWB1", "nw1", "tail"), ("SWB2", "nw2", "tail")):
        s += dev(nm, a, "rstb", b, b, "sky130_fd_pr__pfet_01v8_lvt", (0.42, 0.5, 1), p)
    return s + "Brstb rstb 0 v={1.8-v(rst)}\n"
def net(k, t, trst, tstop):
    p = S.P(k, t); ct = B.CT.get((k, t), 3.4e-12)
    c = B.core(p, ct) + rst_sw(p)
    if USE_REF:
        import v5_iref as IR
        c = re.sub(r"IB nb vss (\S+)\n", "", c) + IR.ref(p, 0.0, 1, t)
    else:
        c = re.sub(r"IB nb vss (\S+)\n", lambda m: f"IB nb vss pwl(0 0 1m {m.group(1)})\n", c)
    c = re.sub(r"IRB vgr vss \S+\n", "", c) + dev("IRBM", "vgr", "nd", "vss", "vss", "sky130_fd_pr__nfet_01v8_lvt", (0.42, 16, 1), p)
    b = B.bench(p).replace(f"Vdd vdd 0 {p['VDD']}", "Vdd vdd 0 pwl(0 0 1m 1.0)")
    rs = f"Vrst rst 0 pwl(0 0 0.2m 1.8 {trst} 1.8 {trst+1e-5} 0)\n" if trst > 0 else "Vrst rst 0 0\n"
    hdr = header(p).replace("reltol=1e-5", "reltol=1e-4 method=gear").replace("abstol=1e-17", "abstol=1e-15")
    return hdr + c + b + rs + (f".control\ntran 20u {tstop} 0 50u uic\nlinearize\nwrdata pu.txt v(bd) v(tail) v(vo1) v(vo2) v(nw1) v(g3) v(vi1) v(vi2) i(vdd)\n.endc\n.end\n")
def job(a):
    k, t, trst, tstop = a
    o, f = run(net(k, t, trst, tstop), timeout=6000)
    if "pu.txt" not in f: return a, None, o[-400:]
    x = load_wrdata(f["pu.txt"]); tt = x[:, 0]; names = ["bd", "tail", "vo1", "vo2", "nw1", "g3", "vi1", "vi2", "idd"]
    d = {n: x[:, 1 + 2 * i] for i, n in enumerate(names)}
    fin = {n: float(d[n][-1]) for n in names}
    # settling: last time the differential output or tail is more than 5 mV from its final value
    err = np.maximum(abs(d["vo1"] - d["vo2"] - (fin["vo1"] - fin["vo2"])), abs(d["tail"] - fin["tail"]))
    ts = float(tt[np.where(err > 5e-3)[0][-1]]) if (err > 5e-3).any() else 0.0
    np.save(f"results/pu_{k}{t}_{trst}.npy", np.column_stack([tt] + [d[n] for n in names]))
    return a, dict(final=fin, settle=ts, nwoff=fin["tail"] - fin["nw1"]), ""
if __name__ == "__main__":
    J = [tuple(x) for x in json.loads(sys.argv[1])] if len(sys.argv) > 1 and sys.argv[1][0] == '[' else [("tt", 27, 0.02, 0.3), ("ss", 0, 0.02, 0.3), ("ff", 60, 0.02, 0.3), ("tt", 27, 0, 0.3)]
    with ProcessPoolExecutor(2) as ex:
        for a, r, err in ex.map(job, J):
            if r is None: print(a, "FAILED", err); continue
            fi = r["final"]
            print(f"{a[0]}{a[1]} rst {a[2]*1e3:.0f} ms: at {a[3]} s  bd {fi['bd']:.3f} tail {fi['tail']:.3f} vo {fi['vo1']:.3f}/{fi['vo2']:.3f} nw-off {r['nwoff']*1e3:.1f} mV g3 {fi['g3']:.3f} I(VDD) {-fi['idd']*1e9:.0f} nA | settled (5 mV) at {r['settle']*1e3:.0f} ms", flush=True)
