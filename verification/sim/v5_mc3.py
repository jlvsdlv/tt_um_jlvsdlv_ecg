"""MC (tt27, 40 seeds): mismatch on all devices + Cpf L/R mismatch, WITH magic-extracted parasitic C back-annotated,
Cpf 0.82 pF, the layout's real Ct bit weights (range 0-5.29 pF), DRL sink 40 nA."""
import os, sys, json, numpy as np
os.environ.setdefault("CPF", "0.82e-12"); os.environ.setdefault("CTREAL", "1")
import v5_post                      # patches C._orig (parasitics), S.CT_W (real weights), Cpf defaults
import v5_mc2 as M, v5_sim as S
from concurrent.futures import ProcessPoolExecutor
if __name__ == "__main__":
    nw = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    with ProcessPoolExecutor(nw) as ex: R = list(ex.map(M.one, range(40)))
    ok = [r for s, r in R if r]; print(f"MC: {len(ok)}/{len(R)} converged")
    ctmax = sum(S.CT_W)
    for key, sc, u in (("tail", 1e3, "mV"), ("vcm", 1e3, "mV"), ("off", 1e3, "mV (output)"), ("gain", 1, "dB"), ("idd", 1e9, "nA"), ("ct", 1e15, "fF"), ("zmin", 1e-9, "GOhm"), ("z50", 1e-9, "GOhm")):
        x = np.array([r[key] for r in ok]) * sc
        print(f"  {key:>5}: mean {x.mean():.4g} sd {x.std():.3g} min {x.min():.4g} max {x.max():.4g} {u}")
    ct = np.array([r["ct"] for r in ok])
    print(f"  Ct at range limits: {np.sum(ct <= 0)} at 0, {np.sum(ct >= ctmax - 1e-15)} at max ({ctmax*1e12:.2f} pF)")
    json.dump(R, open("results/v5_mc3.json", "w"), default=float)
