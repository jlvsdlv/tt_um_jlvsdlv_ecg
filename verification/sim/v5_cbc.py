"""Cold-start fix: Rb 300-500 GOhm (well-defined well DC) with larger Cbc to push Rb noise below band. Noise at tt27 + DC state at cold corners."""
import numpy as np, json, re
from concurrent.futures import ProcessPoolExecutor
import v5_trim as T, v4_corner as V, noisebias as nb, lv
from lv import header, sup, run
def job(a):
    cbc, rb = a; V.A.RB = rb
    out = dict(cbc=cbc, rb=rb, dc={})
    for k, t in [("tt", 0), ("ss", 0), ("sf", 0), ("fs", 0), ("ss", 27)]:
        V.VCM = T.REC.get((k, t), T.REC[("ss", 0)] if k in ("ss", "sf") else T.REC[("tt", 0)]); p = V.P(k, t); cfn = V.A.mk(cbc, 0.58e-12)
        s = sup(p, vi1_ac="0.5", vi2_ac="0.5 180").replace("Vi1 vi1 0", "Vi1 vp1 0").replace("Vi2 vi2 0", "Vi2 vp2 0")
        o, f = run(header(p) + cfn(p) + V.PAD + s + ".control\nop\nprint v(nw1) v(tail) v(vo1)\n.endc\n.end\n")
        v = {x: float(y) for x, y in re.findall(r"^\s*v\((\w+)\)\s*=\s*([-\d.e+]+)", o, re.M)}
        out["dc"][k + str(t)] = (v["tail"] - v["nw1"], v["vo1"])
    V.VCM = T.REC[("tt", 27)]; p = V.P("tt", 27); cfn = V.A.mk(cbc, 0.58e-12); lv.core = cfn; nb.core = cfn
    s = nb.spectra(p); F = nb.FR; I = lambda x: float(np.trapezoid(x, F))
    out["static"] = np.sqrt(I(s["tot"]))*1e6; out["sw"] = np.sqrt(I(s["tot"] - s["f34"] + V.A.R7*s["f34"]))*1e6
    return out
if __name__ == "__main__":
    jobs = [(20e-12, 5e11), (30e-12, 3e11), (30e-12, 5e11), (40e-12, 3e11)]
    with ProcessPoolExecutor(2) as ex: R = list(ex.map(job, jobs))
    for r in R:
        dc = " ".join(f"{k}:{'OK' if v[1] > 0.4 else 'BAD'}({v[0]*1e3:.0f}mV)" for k, v in r["dc"].items())
        print(f"Cbc {r['cbc']*1e12:4.0f}p Rb {r['rb']:.0e}: IRN static {r['static']:.3f} switched {r['sw']:.3f} uV | {dc}")
    json.dump(R, open("results/v5_cbc2.json", "w"))
