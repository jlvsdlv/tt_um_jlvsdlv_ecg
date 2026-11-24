"""Replace the ideal linear 10-TOhm DTMOS well resistor Rb with a real back-to-back pseudo-resistor (2x pfet_01v8 diode).
A pseudo-R is ~TOhm near 0 V but drops steeply at a few hundred mV, so it should kill the cold-corner second DC state
(well 250 mV below tail) without the in-band noise cost of a small linear Rb."""
import numpy as np, json, re, sys
from concurrent.futures import ProcessPoolExecutor
import v5_trim as T, v5_g as G, v4_corner as V, noisebias as nb, lv
from amp import dev
from lv import header, sup, run
orig = V.A.mk
def mkp(cbc, cpf, geo=(1, 4, 1)):
    base = orig(cbc, cpf)
    def c(p):
        s = base(p)
        s = re.sub(r"Rb1 nw1 tail \S+\n", "", s); s = re.sub(r"Rb2 nw2 tail \S+\n", "", s)
        for i in (1, 2):
            s += dev(f"MRB{i}a", f"nw{i}", f"xb{i}", f"xb{i}", f"xb{i}", "sky130_fd_pr__pfet_01v8", geo, p)
            s += dev(f"MRB{i}b", "tail", f"xb{i}", f"xb{i}", f"xb{i}", "sky130_fd_pr__pfet_01v8", geo, p)
        return s
    return c
V.A.mk = mkp
def dc(kt):
    k, t = kt; V.VCM = T.REC[(k, t)]; p = V.P(k, t); cfn = mkp(5e-12, 0.58e-12)
    s = sup(p, vi1_ac="0.5", vi2_ac="0.5 180").replace("Vi1 vi1 0", "Vi1 vp1 0").replace("Vi2 vi2 0", "Vi2 vp2 0")
    o, f = run(header(p) + cfn(p) + V.PAD + s + ".control\nop\nprint v(nw1) v(tail) v(vo1)\n.endc\n.end\n")
    v = dict(re.findall(r"^\s*v\((\w+)\)\s*=\s*([-\d.e+]+)", o, re.M)); return k, t, {a: float(b) for a, b in v.items()}
def noise(_):
    V.VCM = T.REC[("tt", 27)]; p = V.P("tt", 27); cfn = mkp(5e-12, 0.58e-12); lv.core = cfn; nb.core = cfn
    s = nb.spectra(p); F = nb.FR; I = lambda x: float(np.trapezoid(x, F))
    return np.sqrt(I(s["tot"]))*1e6, np.sqrt(I(s["tot"] - s["f34"] + V.A.R7*s["f34"]))*1e6
if __name__ == "__main__":
    with ProcessPoolExecutor(2) as ex:
        D = list(ex.map(dc, T.CORNERS)); N = list(ex.map(noise, [0]))
        R = list(ex.map(G.y, [(0.58e-12, k, t, clf, None, 0) for clf in (1, 2) for k, t in T.CORNERS]))
    for k, t, v in D: print(f"{k}{t}: nw {v['nw1']:.3f} tail {v['tail']:.3f} vo {v['vo1']:.3f}")
    print(f"IRN static {N[0][0]:.3f} uV, switched {N[0][1]:.3f} uV")
    out = []
    for a, r, g, flp in R:
        c10, z10 = T.best_ct(r, 10e-15, 10); _, zz, ff = T.zmin_with(r, c10)
        zs = [np.interp(x, ff, zz)/1e9 for x in (0.5, 1, 50, 100, 150)]
        print(f"pR CL/{a[3]} {a[1]+str(a[2]):>6} gain {g:.1f} fLP {flp:5.0f} | Ct {c10*1e15:5.0f} fF | Zmin {z10/1e9:5.2f} | Z@0.5/1/50/100/150 " + "/".join(f"{x:.3g}" for x in zs))
        out.append(dict(clf=a[3], corner=a[1], temp=a[2], gain=g, flp=flp, ct=c10, zmin=z10, z=zs))
    json.dump(dict(dc=D, noise=N, z=out), open("results/v5_prb.json", "w"))
