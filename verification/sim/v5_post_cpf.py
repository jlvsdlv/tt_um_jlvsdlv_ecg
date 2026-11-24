import json, sys, numpy as np
import v5_post, v5_sim as S
from concurrent.futures import ProcessPoolExecutor
PRE = {(r["corner"], r["temp"]): r["vcm"] for r in json.load(open("results/v5_final3.json"))}
def run(a):
    (k, t), cpf = a; p = S.P(k, t); p["VCM"] = PRE[(k, t)]
    r = S.zin(p, cpf=cpf); tr = S.trim(r)
    return k, t, cpf, r["gain"], tr["ct"], tr["zmin"], tr["z"]
if __name__ == "__main__":
    cs = [float(x) * 1e-12 for x in sys.argv[1].split(",")]
    ks = [tuple([a.split(":")[0], int(a.split(":")[1])]) for a in sys.argv[2].split(",")]
    with ProcessPoolExecutor(2) as ex:
        for k, t, cpf, g, ct, zm, z in ex.map(run, [(kt, c) for kt in ks for c in cs]):
            print(f"{k}{t:>3} Cpf {cpf*1e15:4.0f} fF gain {g:.1f} | Ct {ct*1e15:5.0f} fF Zmin {zm/1e9:5.2f} G  Z@1/50/150 {z[1]/1e9:.3g}/{z[3]/1e9:.3g}/{z[5]/1e9:.3g}", flush=True)
