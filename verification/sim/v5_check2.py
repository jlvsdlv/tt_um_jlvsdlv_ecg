import numpy as np, json
from concurrent.futures import ProcessPoolExecutor
import v5_sim as S, v5_trim as T
def one(kt):
    k, t = kt; p = S.P(k, t); r = S.zin(p); tr = S.trim(r)
    nw = r["ns"]["tail"] - r["ns"]["nw1"]
    n = S.noise(S.P(k, t))
    return k, t, r["gain"], r["flp"], r["rb"], r["idd"], nw, tr, n
if __name__ == "__main__":
    with ProcessPoolExecutor(2) as ex: R = list(ex.map(one, T.CORNERS))
    out = []
    for k, t, g, flp, rb, idd, nw, tr, n in R:
        ns = f" | IRN {n['static']:.3f}/{n['sw']:.3f} uV" if n else ""
        print(f"{k}{t:>3}: gain {g:.1f} dB fLP {flp:5.0f} Hz | Rb {rb/1e9:4.0f} G tail-nw {nw*1e3:5.1f} mV | I {idd*1e9:5.0f} nA | Ct {tr['ct']*1e15:5.0f} fF Zmin {tr['zmin']/1e9:5.2f} G, Z@1/50/150 {tr['z'][1]/1e9:.3g}/{tr['z'][3]/1e9:.3g}/{tr['z'][5]/1e9:.3g} G{ns}", flush=True)
        out.append(dict(corner=k, temp=t, gain=g, flp=flp, rb=rb, idd=idd, nw=nw, trim=tr, noise=n))
    json.dump(out, open("results/v5_check2.json", "w"), default=float)
