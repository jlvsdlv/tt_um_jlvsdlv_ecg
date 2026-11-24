"""Monte Carlo (tt27) with mismatch on every device incl. the v5 additions (pseudo-R Rb, replica, ladder, DRL OTA, Rf),
plus 0.5% (1 sigma) left/right mismatch on Cpf. DRL closes the CM loop; then pad Zin with a common 10-bit Ct code."""
import numpy as np, re, json
from concurrent.futures import ProcessPoolExecutor
import v5_sim as S, v5_bias as B, v5_core as C
from lv import header, run
from amp import MMKEYS
NEW = ["MREP"] + [f"MRB{s}{i}" for s in (1, 2) for i in range(C.NS)] + [f"LD{i}" for i in range(B.NLAD)] + \
      ["BP", "BN", "S1", "A1", "A2", "PA", "PB", "P2", "S2", "MR3s0", "MR4s0"]
def one(seed):
    rng = np.random.default_rng(9000 + seed)
    p = S.P("tt", 27, seed)
    for d in NEW: p["mm"][d] = {k: float(rng.standard_normal()) for k in MMKEYS}
    e1, e2 = rng.standard_normal(2) * 0.005
    fix = lambda s: re.sub(r"Cpf1 (\S+) (\S+) (\S+)", lambda m: f"Cpf1 {m.group(1)} {m.group(2)} {float(m.group(3))*(1+e1):.6g}",
                     re.sub(r"Cpf2 (\S+) (\S+) (\S+)", lambda m: f"Cpf2 {m.group(1)} {m.group(2)} {float(m.group(3))*(1+e2):.6g}", s))
    o, f = run(header(p) + fix(B.core(p, 2.69e-12)) + B.bench(p) + B.ns_guess(p) + ".control\nop\nprint v(bd) v(tail) v(vo1) v(vo2) v(r1) i(vdd)\n.endc\n.end\n")
    v = {a: float(b) for a, b in re.findall(r"^(\S+)\s*=\s*([-\d.e+]+)", o, re.M)}
    if not v or -v.get("i(vdd)", 0) < 5e-7: return seed, None
    p["VCM"] = v["v(bd)"]
    om = C.mk5
    C.mk5 = lambda *a, **k: (lambda fn: (lambda q: fix(fn(q))))(om(*a, **k))
    try: r = S.zin(p); tr = S.trim(r)
    finally: C.mk5 = om
    return seed, dict(vcm=v["v(bd)"], tail=v["v(tail)"], ref=v["v(r1)"], off=v["v(vo1)"] - v["v(vo2)"], idd=-v["i(vdd)"], gain=r["gain"], ct=tr["ct"], zmin=tr["zmin"], z50=tr["z"][3])
if __name__ == "__main__":
    with ProcessPoolExecutor(2) as ex: R = list(ex.map(one, range(40)))
    ok = [r for s, r in R if r]; print(f"MC: {len(ok)}/{len(R)} converged")
    for key, sc, u in (("tail", 1e3, "mV"), ("ref", 1e3, "mV"), ("vcm", 1e3, "mV"), ("off", 1e3, "mV (output)"), ("gain", 1, "dB"), ("idd", 1e9, "nA"), ("ct", 1e15, "fF"), ("zmin", 1e-9, "GOhm"), ("z50", 1e-9, "GOhm")):
        x = np.array([r[key] for r in ok]) * sc
        print(f"  {key:>5}: mean {x.mean():.4g} sd {x.std():.3g} min {x.min():.4g} max {x.max():.4g} {u}")
    json.dump(R, open("results/v5_mc2.json", "w"), default=float)
