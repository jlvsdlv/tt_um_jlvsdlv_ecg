"""Why the trimmed Zin stalls at ~1.8 GOhm: negative input conductance G<0 from amplifier phase lag through Cpf (G ~ f^2/fLP).
Test (a) raising the output LP corner (CL/2, CL/3) and (b) an ideal series-RC 'G canceller' at the input, with continuous+10fF trim."""
import numpy as np, json
from concurrent.futures import ProcessPoolExecutor
import v5_trim as T, v4_corner as V
from lv import header, sup, run
from amp import load_wrdata
from lvac import K
def y(args):
    cpf, k, t, clf, rg, cg = args
    V.VCM = T.REC[(k, t)]; p = V.P(k, t); p["CLEXT"] = V.CL / clf; cfn = V.A.mk(5e-12, cpf)
    s = sup(p, vi1_ac="0.5", vi2_ac="0.5 180").replace("Vi1 vi1 0", "Vi1 vp1 0").replace("Vi2 vi2 0", "Vi2 vp2 0")
    ex = f"Rg1 vi1 ng1 {rg}\nCg1 ng1 0 {cg}\nRg2 vi2 ng2 {rg}\nCg2 ng2 0 {cg}\n" if rg else ""
    net = header(p) + cfn(p) + V.PAD + ex + s + (".control\nop\nac dec 40 0.2 1e4\nlet y=-i(vi1)/(v(vp1)-v(vp2))\nlet h=v(vo1)-v(vo2)\n"
          "wrdata y.txt real(y) imag(y) mag(h)\n.endc\n.end\n")
    o, f = run(net); a = load_wrdata(f["y.txt"])
    fr = a[:, 0]; h = a[:, 5]; g0 = h[np.argmin(abs(fr - 20))]; flp = fr[(fr > 20) & (h < g0 / 2**0.5)][0]
    return args, dict(f=fr.tolist(), g=a[:, 1].tolist(), b=a[:, 3].tolist()), 20*np.log10(g0), flp
if __name__ == "__main__":
    C = [("tt", 27), ("ss", 27), ("sf", 27), ("ff60", None)]
    corners = [("tt", 27), ("ss", 27), ("sf", 27), ("fs", 27), ("ff", 60), ("tt", 60)]
    jobs = [(0.54e-12, k, t, clf, None, 0) for clf in (1, 2, 3) for k, t in corners]
    jobs += [(0.54e-12, k, t, 1, rg, 1e-12) for rg in (5e8, 7e8) for k, t in corners]
    with ProcessPoolExecutor(2) as ex: R = list(ex.map(y, jobs))
    print("variant              corner | gain dB  fLP Hz | G@150 nS | Zmin(cont trim) | Zmin(10fF trim)  Ct | Z@50 Z@150 (GOhm)")
    for a, r, g, flp in R:
        cpf, k, t, clf, rg, cg = a
        f = np.array(r["f"]); G = np.interp(150, f, r["g"])
        cc, zc = T.best_ct(r); c10, z10 = T.best_ct(r, 10e-15); _, zz, ff = T.zmin_with(r, c10)
        name = f"CL/{clf}" if rg is None else f"RgCg {rg/1e6:.0f}M/1p"
        print(f"{name:>16} {k+str(t):>8} | {g:6.1f} {flp:7.0f} | {G*1e9:7.3f} | {zc/1e9:7.2f} | {z10/1e9:7.2f} {c10*1e15:5.0f}fF | {np.interp(50, ff, zz)/1e9:.3g} {np.interp(150, ff, zz)/1e9:.3g}")
    json.dump([(a, g, flp) for a, r, g, flp in R], open("results/v5_g.json", "w"))
