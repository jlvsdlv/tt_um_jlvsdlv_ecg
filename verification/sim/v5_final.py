import numpy as np, json
from concurrent.futures import ProcessPoolExecutor
import v5_trim as T, v5_g as G
if __name__ == "__main__":
    jobs = [(0.58e-12, k, t, clf, None, 0) for clf in (1, 2, 3) for k, t in T.CORNERS]
    with ProcessPoolExecutor(2) as ex: R = list(ex.map(G.y, jobs))
    out = []
    for clf in (1, 2, 3):
        print(f"\n== Cpf 0.58 pF fixed, Ct 9-bit x 10 fF (0-5.11 pF), CL/{clf} ==")
        for a, r, g, flp in R:
            if a[3] != clf: continue
            c10, z10 = T.best_ct(r, 10e-15, 9); _, zz, ff = T.zmin_with(r, c10)
            zs = [np.interp(x, ff, zz)/1e9 for x in (0.5, 1, 50, 100, 150)]
            print(f"{a[1]+str(a[2]):>6} fLP {flp:5.0f} Hz | Ct {c10*1e15:5.0f} fF | Zmin {z10/1e9:5.2f} | Z@0.5/1/50/100/150 " + "/".join(f"{x:.3g}" for x in zs))
            out.append(dict(clf=clf, corner=a[1], temp=a[2], flp=flp, ct=c10, zmin=z10, z=zs))
    json.dump(out, open("results/v5_final.json", "w"))
