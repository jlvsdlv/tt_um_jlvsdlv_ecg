"""Rb (DTMOS well bias) 10 TOhm -> 300 GOhm: fixes the cold-corner bistable DC point. Check noise and full trimmed Zin across corners."""
import numpy as np, json, sys
from concurrent.futures import ProcessPoolExecutor
import v5_trim as T, v5_g as G, v4_corner as V, noisebias as nb
def noise(rb):
    V.A.RB = rb; V.VCM = T.REC[("tt", 27)]; p = V.P("tt", 27); cfn = V.A.mk(5e-12, 0.58e-12); V.lv.core = cfn; nb.core = cfn
    s = nb.spectra(p); F = nb.FR; I = lambda x: float(np.trapezoid(x, F))
    return rb, np.sqrt(I(s["tot"]))*1e6, np.sqrt(I(s["tot"] - s["f34"] + V.A.R7*s["f34"]))*1e6
def yrb(args):
    rb, rest = args; V.A.RB = rb; return G.y(rest)
if __name__ == "__main__":
    with ProcessPoolExecutor(2) as ex:
        N = list(ex.map(noise, [1e13, 1e12, 3e11]))
        R = list(ex.map(yrb, [(3e11, (0.58e-12, k, t, clf, None, 0)) for clf in (1, 2) for k, t in T.CORNERS]))
    for rb, st, sw in N: print(f"Rb {rb:.0e}: IRN static {st:.3f} uV, switched {sw:.3f} uV (0.5-150 Hz)")
    out = []
    for a, r, g, flp in R:
        c10, z10 = T.best_ct(r, 10e-15, 9); _, zz, ff = T.zmin_with(r, c10)
        zs = [np.interp(x, ff, zz)/1e9 for x in (0.5, 1, 50, 100, 150)]
        print(f"Rb 300G CL/{a[3]} {a[1]+str(a[2]):>6} gain {g:.1f} fLP {flp:5.0f} | Ct {c10*1e15:5.0f} fF | Zmin {z10/1e9:5.2f} | Z@0.5/1/50/100/150 " + "/".join(f"{x:.3g}" for x in zs))
        out.append(dict(clf=a[3], corner=a[1], temp=a[2], gain=g, flp=flp, ct=c10, zmin=z10, z=zs))
    json.dump(dict(noise=N, z=out), open("results/v5_rb.json", "w"))
