"""Post-layout differential frequency response (Cpf 0.84 pF, extracted C back-annotated, per-corner trimmed Ct, TT pin path + 8.8 pF)."""
import os, re, json, numpy as np
os.environ.setdefault("CPF", "0.84e-12")
import v5_post, v5_sim as S, v5_core as C, v4_corner as V
from lv import header, sup, run
from amp import load_wrdata
nodeset = S.nodeset
from concurrent.futures import ProcessPoolExecutor
R = {(r["corner"], r["temp"]): r for r in json.load(open("results/v5_post_x1_cpf840.json"))}
def ac(kt):
    k, t = kt; r0 = R[kt]; p = S.P(k, t); p["VCM"] = r0["vcm"]
    for d in (0, 2e-4, -2e-4, 4e-4, -4e-4):
        q = dict(p, VCM=p["VCM"] + d)
        cfn = C.mk5(None, S.CPF, r0["ct"]); ns, rb, idd = S.opv(q, cfn)
        s = sup(q, vi1_ac="0.5", vi2_ac="0.5 180").replace("Vi1 vi1 0", "Vi1 vp1 0").replace("Vi2 vi2 0", "Vi2 vp2 0")
        net = header(q) + re.sub(r"\.nodeset.*\n", "", cfn(q)) + V.PAD + nodeset(ns) + s + (
            ".control\nac dec 50 1e-3 1e5\nlet h=v(vo1)-v(vo2)\nwrdata h.txt mag(h) cph(h)\n.endc\n.end\n")
        o, f = run(net); a = load_wrdata(f["h.txt"]); fr, m, ph = a[:, 0], a[:, 1], a[:, 3]
        g0 = m[np.argmin(abs(fr - 20))]
        if 20 * np.log10(g0) < 40: return k, t, fr.tolist(), m.tolist(), np.degrees(np.unwrap(ph)).tolist()
    return k, t, None, None, None
if __name__ == "__main__":
    with ProcessPoolExecutor(2) as ex: out = list(ex.map(ac, list(R)))
    json.dump([dict(corner=k, temp=t, f=f, mag=m, ph=p) for k, t, f, m, p in out], open("results/v5_freqresp.json", "w"))
    for k, t, f, m, p in out:
        if f is None: print(k, t, "FAILED"); continue
        f = np.array(f); g = 20 * np.log10(np.array(m)); g0 = g[np.argmin(abs(f - 20))]
        hp = f[(f < 20) & (g >= g0 - 3)].min(); lp = f[(f > 20) & (g >= g0 - 3)].max()
        print(f"{k}{t:>3}: {g0:.2f} dB  HP {hp*1e3:.1f} mHz  LP {lp:.0f} Hz")
