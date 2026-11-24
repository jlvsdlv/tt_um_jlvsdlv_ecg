"""v4 input impedance at the PAD (TT path: pad 5 pF + 1 TOhm leak, 500 Ohm switch) vs Cpf trim code, across corners and MC."""
import numpy as np, json, re, sys
from concurrent.futures import ProcessPoolExecutor
import noisebias as nb, lv
from lv import header, sup, run, op
from amp import load_wrdata, draw_mismatch
import v4_acdt as A
pt = A.pt
best = [r for r in json.load(open("results/v4_lp300.json")) if abs(r["cpf"] - 0.4e-12) < 1e-15][0]
VCM, CF, CL = best["vcm"], best["Cf"], pt["CLEXT"] / 10
CODES = [0.40e-12, 0.45e-12, 0.50e-12, 0.55e-12]
FR = np.logspace(np.log10(0.5), np.log10(150), 40)
def P(corner="tt", temp=27, mm=None):
    p = nb.params(1e-6, pt["VDD"], VCM); p.update(VBN=pt["VBN"], Cf=CF, CLEXT=CL, M12=tuple(pt["M12"]), M34=tuple(pt["M34"]), corner=corner, temp=temp, mm=mm); return p
PAD = "Rin1 vp1 vi1 500\nCip1 vp1 0 5p\nRil1 vp1 0 1e12\nRin2 vp2 vi2 500\nCip2 vp2 0 5p\nRil2 vp2 0 1e12\n"
def zpad(args):
    cpf, corner, temp, seed = args
    mm = draw_mismatch(np.random.default_rng(5000 + seed))[0] if seed is not None else None
    p = P(corner, temp, mm); cfn = A.mk(5e-12, cpf)
    s = sup(p, vi1_ac="0.5", vi2_ac="0.5 180").replace("Vi1 vi1 0", "Vi1 vp1 0").replace("Vi2 vi2 0", "Vi2 vp2 0")
    net = header(p) + cfn(p) + PAD + s + (".control\nop\nac dec 20 0.05 1e5\nlet zd=(v(vp1)-v(vp2))/(-i(vi1))\nlet y=1/zd\n"
          "wrdata z.txt mag(zd) real(y)\n.endc\n.end\n")
    o, f = run(net)
    if "z.txt" not in f: return (cpf, corner, temp, seed, None)
    a = load_wrdata(f["z.txt"]); fr = a[:, 0]; z = a[:, 1]; g = a[:, 3]
    band = (fr >= 0.5) & (fr <= 150)
    gneg = g[g < 0]; rneg = (1 / gneg.min()) if len(gneg) else None
    return (cpf, corner, temp, seed, dict(zmin=z[band].min() / 1e9, z50=np.interp(50, fr, z) / 1e9, z150=np.interp(150, fr, z) / 1e9,
                                          z05=np.interp(0.5, fr, z) / 1e9, rneg=rneg))
if __name__ == "__main__":
    corners = [("tt", 27), ("ss", 27), ("ff", 27), ("sf", 27), ("fs", 27), ("tt", 0), ("tt", 37), ("tt", 60)]
    jobs = [(c, k, t, None) for c in CODES for k, t in corners] + [(c, "tt", 27, s) for c in CODES for s in range(25)]
    with ProcessPoolExecutor(2) as ex: R = list(ex.map(zpad, jobs))
    print("Differential input impedance at the pad, min over 0.5-150 Hz (GOhm)   [z@0.5 / z@50 / z@150]")
    print(f"{'corner':>8} | " + " | ".join(f"Cpf {c*1e12:.2f} pF".center(30) for c in CODES))
    for k, t in corners:
        row = []
        for c in CODES:
            r = [x for x in R if x[0] == c and x[1] == k and x[2] == t and x[3] is None][0][4]
            row.append("fail".center(30) if r is None else f"{r['zmin']:5.2f} [{r['z05']:.3g}/{r['z50']:.2g}/{r['z150']:.2g}]".center(30))
        print(f"{k+str(t):>8} | " + " | ".join(row))
    print("Monte Carlo (25 seeds, tt27): min-in-band Zin  mean / worst   and worst negative R")
    for c in CODES:
        rs = [x[4] for x in R if x[0] == c and x[3] is not None and x[4]]
        zm = np.array([r["zmin"] for r in rs]); rn = [abs(r["rneg"]) for r in rs if r["rneg"]]
        print(f"  Cpf {c*1e12:.2f} pF: {zm.mean():.2f} / {zm.min():.2f} GOhm   ({(zm>=1).mean()*100:.0f}% >= 1 GOhm)   min |Rneg| {min(rn)/1e9 if rn else float('inf'):.3g} GOhm")
    json.dump([list(x[:4]) + [x[4]] for x in R], open("results/v4_corner_1k.json", "w"))
