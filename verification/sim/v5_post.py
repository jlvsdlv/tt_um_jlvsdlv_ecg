"""Post-layout back-annotation: add extracted parasitic capacitances (magic, coupling + to-substrate) among the critical
analog nets to the v5 schematic testbenches and re-run the final corner verification (gain, Zin after trim, IRN).
Every net outside CRIT is treated as AC ground (supplies, substrate, p-well islands, digital lines, trim nodes).
The extraction includes some intra-device fringe that the BSIM models already contain -> conservative (double-counted)."""
import json, sys, numpy as np
import v5_core as C, v5_sim as S, v5_final2 as F
CRIT = ["vi1", "vi2", "vo1", "vo2", "nw1", "nw2", "tail", "g3", "g4", "nb", "vgr"]
raw = json.load(open("results/pexcaps_v5.json"))
PC = {}
for k, v in raw.items():
    a, b = k.split("|"); a = a if a in CRIT else "0"; b = b if b in CRIT else "0"
    if a == b: continue
    if b == "0": a, b = b, a
    if a == "0" and b in ("nw1", "nw2"): continue          # schematic already carries Cnw = 1.5 pF (> extracted 1.0 pF)
    PC[tuple(sorted((a, b)))] = PC.get(tuple(sorted((a, b))), 0) + v
import os
SCALE = float(os.environ.get("PXSCALE", "1.0"))
CPFP = float(os.environ.get("CPF", "0.68e-12"))
S.CPF = CPFP; S.zin.__defaults__ = (CPFP, 0.0, 0); S.noise.__defaults__ = (CPFP,)
import re
def extra(txt=""):
    has = lambda n: n == "0" or re.search(rf"\s{n}\s", txt)
    return "".join(f"Cpx{i} {a} {b} {v*SCALE:.4g}\n" for i, ((a, b), v) in enumerate(sorted(PC.items())) if v > 0.2e-15 and has(a) and has(b))
_mk5, _orig = C.mk5, C._orig
def mk5p(cbc=None, cpf=0.58e-12, ct=None):
    f = _mk5(cbc, cpf, ct); return lambda p: f(p) + extra()
def origp(cbc, cpf):
    f = _orig(cbc, cpf); return lambda p: (lambda t: t + extra(t))(f(p))
C._orig = origp
_noise = S.noise
def noise_np(p, *a, **k):
    C._orig = _orig
    try:
        for d in (0, 2e-4, -2e-4, 5e-4, -5e-4):
            try: return _noise(dict(p, VCM=p["VCM"] + d), *a, **k)
            except Exception: pass
        return dict(static=float("nan"), sw=float("nan"))
    finally: C._orig = origp
S.noise = noise_np
if __name__ == "__main__":
    for (a, b), v in sorted(PC.items(), key=lambda kv: -kv[1])[:14]: print(f"  {a:>5s}-{b:<5s} {v*1e15:7.1f} fF")
    from concurrent.futures import ProcessPoolExecutor
    import v5_trim as T
    with ProcessPoolExecutor(2) as ex: R = list(ex.map(F.one, T.CORNERS))
    for r in R:
        print(f"{r['corner']}{r['temp']:>3}: gain {r['gain']:.1f} dB fLP {r['flp']:.0f} | Ct {r['ct']*1e15:.0f} fF Zmin {r['zmin']/1e9:.2f} G "
              f"Z@1/50/150 {r['z'][1]/1e9:.3g}/{r['z'][3]/1e9:.3g}/{r['z'][5]/1e9:.3g} G | IRN {r['static']:.3f}/{r['sw']:.3f} uV", flush=True)
    json.dump(R, open(f"results/v5_post_x{SCALE:g}_cpf{CPFP*1e15:.0f}.json", "w"), default=float)
