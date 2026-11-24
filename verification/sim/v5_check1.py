import numpy as np, json, re
from concurrent.futures import ProcessPoolExecutor
import v5_core, v5_trim as T, v5_g as G, v4_corner as V, noisebias as nb, lv
from lv import header, sup, run
def dc(kt):
    k, t = kt; V.VCM = T.REC[(k, t)]; p = V.P(k, t); cfn = V.A.mk(0, 0.58e-12)
    s = sup(p, vi1_ac="0.5", vi2_ac="0.5 180").replace("Vi1 vi1 0", "Vi1 vp1 0").replace("Vi2 vi2 0", "Vi2 vp2 0")
    o, f = run(header(p) + cfn(p) + V.PAD + s + ".control\nop\nprint v(nw1) v(tail) v(vo1) i(vdd)\n.endc\n.end\n")
    v = {x: float(y) for x, y in re.findall(r"^\s*(\S+)\s*=\s*([-\d.e+]+)", o, re.M)}
    return k, t, v
def noise(kt):
    k, t = kt; V.VCM = T.REC[(k, t)]; p = V.P(k, t); cfn = V.A.mk(0, 0.58e-12); lv.core = cfn; nb.core = cfn
    s = nb.spectra(p); F = nb.FR; I = lambda x: float(np.trapezoid(x, F))
    return k, t, np.sqrt(I(s["tot"]))*1e6, np.sqrt(I(s["tot"] - s["f34"] + V.A.R7*s["f34"]))*1e6
if __name__ == "__main__":
    with ProcessPoolExecutor(2) as ex:
        D = list(ex.map(dc, T.CORNERS))
        for k, t, v in D: print(f"{k}{t}: tail-nw {(v['v(tail)']-v['v(nw1)'])*1e3:.1f} mV vo {v['v(vo1)']:.3f} I(VDD) {abs(v['i(vdd)'])*1e9:.0f} nA", flush=True)
        N = list(ex.map(noise, [("tt", 27), ("ss", 27), ("ff", 27), ("tt", 0), ("tt", 60), ("ss", 0)]))
        for k, t, st, sw in N: print(f"{k}{t}: IRN static {st:.3f} uV, switched {sw:.3f} uV", flush=True)
        R = list(ex.map(G.y, [(0.58e-12, k, t, 2, None, 0) for k, t in T.CORNERS]))
    out = []
    for a, r, g, flp in R:
        c10, z10 = T.best_ct(r, 10e-15, 10); _, zz, ff = T.zmin_with(r, c10)
        zs = [np.interp(x, ff, zz)/1e9 for x in (0.5, 1, 50, 100, 150)]
        print(f"CL/2 {a[1]+str(a[2]):>6} gain {g:.1f} fLP {flp:5.0f} | Ct {c10*1e15:5.0f} fF | Zmin {z10/1e9:5.2f} | Z@0.5/1/50/100/150 " + "/".join(f"{x:.3g}" for x in zs))
        out.append(dict(corner=a[1], temp=a[2], gain=g, flp=flp, ct=c10, zmin=z10, z=zs))
    json.dump(dict(dc=D, noise=N, z=out), open("results/v5_check1.json", "w"))
