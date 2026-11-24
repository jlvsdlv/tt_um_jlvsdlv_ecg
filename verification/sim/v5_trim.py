"""v5: 'over-compensated sunk' input trim (after Zheng & Liu, JSSC 2026).
Cpf fixed slightly too large (net negative input C); a binary MIM bank Ct from each input node to ground trims it back.
Ct sits at vi (on-chip side of the 500-Ohm pad switch) so its LSB is NOT multiplied by the closed-loop gain.
One AC sim per (corner, Cpf) gives Y0(f) at the pad; Ct adds jw*Ct/2 to the differential admittance (checked by direct sim)."""
import numpy as np, json, sys
from concurrent.futures import ProcessPoolExecutor
import noisebias as nb
import v4_corner as V
from lv import header, sup, run
from amp import load_wrdata
REC = {(r[0], r[1]): r[2] for r in json.load(open("results/v4_recenter.json"))}   # corner -> re-centred VCM
CORNERS = list(REC.keys())
def y0(args):
    cpf, k, t, ct, seed = args
    V.VCM = REC[(k, t)]
    from amp import draw_mismatch
    mm = draw_mismatch(np.random.default_rng(5000 + seed))[0] if seed is not None else None
    p = V.P(k, t, mm); cfn = V.A.mk(5e-12, cpf)
    s = sup(p, vi1_ac="0.5", vi2_ac="0.5 180").replace("Vi1 vi1 0", "Vi1 vp1 0").replace("Vi2 vi2 0", "Vi2 vp2 0")
    extra = f"Ct1 vi1 0 {ct}\nCt2 vi2 0 {ct}\n" if ct > 0 else ""
    net = header(p) + cfn(p) + V.PAD + extra + s + (".control\nop\nac dec 40 0.2 1e4\nlet y=-i(vi1)/(v(vp1)-v(vp2))\n"
          "wrdata y.txt real(y) imag(y)\n.endc\n.end\n")
    o, f = run(net)
    if "y.txt" not in f: return (cpf, k, t, ct, seed, None)
    a = load_wrdata(f["y.txt"])
    return (cpf, k, t, ct, seed, dict(f=a[:, 0].tolist(), g=a[:, 1].tolist(), b=a[:, 3].tolist()))
BAND = (0.5, 150)
def zmin_with(r, ct):
    f = np.array(r["f"]); g = np.array(r["g"]); b = np.array(r["b"]) + 2 * np.pi * f * ct / 2
    m = (f >= BAND[0]) & (f <= BAND[1]); z = 1 / np.abs(g + 1j * b)
    return z[m].min(), z, f
def best_ct(r, lsb=None, bits=8):
    cts = np.linspace(0, 2e-12, 4001) if lsb is None else np.arange(2 ** bits) * lsb
    zs = [zmin_with(r, c)[0] for c in cts]; i = int(np.argmax(zs)); return cts[i], zs[i]
if __name__ == "__main__":
    CPFS = [0.54e-12, 0.58e-12, 0.62e-12]
    jobs = [(c, k, t, 0.0, None) for c in CPFS for k, t in CORNERS]
    with ProcessPoolExecutor(2) as ex: R = list(ex.map(y0, jobs))
    json.dump(R, open("results/v5_y0.json", "w"))
    for c in CPFS:
        print(f"\n=== Cpf fixed {c*1e12:.2f} pF ===")
        print(f"{'corner':>6} | Ceff@10Hz  Ceff@150Hz (pF, <0 = over-comp) | G@150 (nS) | best Ct (cont.)  Zmin | LSB 10fF: Ct  Zmin | LSB 5fF: Zmin | Z@0.5/50/150 with 10fF trim (GOhm)")
        for k, t in CORNERS:
            r = [x for x in R if x[0] == c and x[1] == k and x[2] == t][0][5]
            if r is None: print(f"{k+str(t):>6} | fail"); continue
            f = np.array(r["f"]); b = np.array(r["b"]); g = np.array(r["g"])
            ce = lambda F: np.interp(F, f, b) / (2 * np.pi * F) * 2   # per-side equivalent C (pF)
            cc, zc = best_ct(r); c10, z10 = best_ct(r, 10e-15); c5, z5 = best_ct(r, 5e-15, 9)
            _, zz, ff = zmin_with(r, c10)
            print(f"{k+str(t):>6} | {ce(10)*1e12:8.3f} {ce(150)*1e12:9.3f} | {np.interp(150, f, g)*1e9:9.3f} | {cc*1e15:6.0f} fF {zc/1e9:7.2f} | {c10*1e15:5.0f} fF {z10/1e9:6.2f} | {z5/1e9:6.2f} | "
                  + "/".join(f"{np.interp(x, ff, zz)/1e9:.3g}" for x in (0.5, 50, 150)))
