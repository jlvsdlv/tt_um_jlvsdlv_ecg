import numpy as np, json
from concurrent.futures import ProcessPoolExecutor
import v5_sim as S
def one(seed):
    try:
        r = S.zin(S.P("tt", 27, seed)); tr = S.trim(r); ns = r["ns"]
        return seed, r["gain"], (ns["vo1"] - ns["vo2"]), tr["ct"], tr["zmin"], tr["z"][3], r["idd"], ns["tail"] - ns["nw1"]
    except Exception as e: return seed, None, str(e)[:80], 0, 0, 0, 0, 0
if __name__ == "__main__":
    with ProcessPoolExecutor(2) as ex: R = list(ex.map(one, range(40)))
    ok = [r for r in R if r[1] is not None]; bad = [r for r in R if r[1] is None]
    a = np.array([r[1:] for r in ok], float)
    print(f"MC tt27: {len(ok)}/{len(R)} ok")
    for i, name, sc, u in ((0, "gain", 1, "dB"), (1, "output offset", 1e3, "mV"), (2, "Ct code", 1e15, "fF"), (3, "Zmin (trimmed)", 1e-9, "GOhm"), (4, "Z@50Hz", 1e-9, "GOhm"), (5, "I(VDD)", 1e9, "nA"), (6, "tail-nw", 1e3, "mV")):
        x = a[:, i] * sc; print(f"  {name:>15}: mean {x.mean():.3g}  sd {x.std():.3g}  min {x.min():.3g}  max {x.max():.3g} {u}")
    for b in bad: print("  fail", b[0], b[2])
    json.dump([list(map(lambda v: v if isinstance(v, (int, str)) or v is None else float(v), r)) for r in R], open("results/v5_mc.json", "w"))
