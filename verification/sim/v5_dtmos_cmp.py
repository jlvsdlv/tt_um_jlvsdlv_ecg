"""AC-coupled DTMOS vs conventional DTMOS vs standard (body-to-source) input pair, same v5 amplifier."""
import re, os, sys, json, numpy as np
os.environ.setdefault("CPF", "0.82e-12")
import v5_core as C, v5_sim as S, v5_bias as B
from lv import header, sup, run
S.CPF = 0.82e-12; S.zin.__defaults__ = (0.82e-12, 0.0, 0); S.noise.__defaults__ = (0.82e-12,)
VAR = os.environ.get("VAR", "acdt")
_orig = C._orig
def xform(t):
    if VAR == "dtmos": t = re.sub(r"^Cbc(\d) (vi\d) (nw\d) \S+", r"Rsh\1 \2 \3 1", t, flags=re.M)
    elif VAR == "std": t = re.sub(r"^Cbc(\d) (vi\d) (nw\d) \S+", r"Rsh\1 \3 tail 1", t, flags=re.M)
    return t
C._orig = lambda cbc, cpf: (lambda f: (lambda p: xform(f(p))))(_orig(cbc, cpf))
DEV = "@m.xm1.msky130_fd_pr__pfet_01v8_lvt"
def one(kt):
    k, t = kt; p = S.P(k, t)
    o, f = run(header(p) + B.core(p, 3.4e-12) + B.bench(p) + B.ns_guess(p) + ".control\nop\nprint v(bd) v(tail) v(vo1) i(vdd)\n.endc\n.end\n")
    v = {a: float(b) for a, b in re.findall(r"^(\S+)\s*=\s*([-\d.e+]+)", o, re.M)}
    p["VCM"] = v["v(bd)"]
    # device small-signal + input current at the closed-loop common mode, and with +/-50 mV differential electrode offset
    cfn = C.mk5(None, S.CPF); res = {}
    for d in (0.0, 0.05, -0.05):
        s = sup(p).replace(f"Vi1 vi1 0 dc {p['VCM']}", f"Vi1 vi1 0 dc {p['VCM']+d/2}").replace(f"Vi2 vi2 0 dc {p['VCM']}", f"Vi2 vi2 0 dc {p['VCM']-d/2}")
        o2, _ = run(header(p) + cfn(p) + s + f".control\nop\nprint {DEV}[gm] {DEV}[gmbs] {DEV}[ibs] {DEV}[ibd] i(vi1) i(vi2) v(nw1) v(tail)\n.endc\n.end\n")
        g = {a: float(b) for a, b in re.findall(r"^\s*(\S+)\s*=\s*([-\d.e+]+)", o2, re.M)}
        res[d] = g
    g0 = res[0.0]
    def gk(name): return [val for key, val in g0.items() if key.endswith(f"[{name}]")][0]
    r = S.zin(p); tr = S.trim(r)
    try: n = S.noise(S.P(k, t) | {"VCM": p["VCM"]})
    except Exception: n = dict(static=float("nan"), sw=float("nan"))
    return dict(var=VAR, corner=k, temp=t, vcm=p["VCM"], tail=v["v(tail)"], idd=-v["i(vdd)"], gm=gk("gm"), gmbs=gk("gmbs"),
                ibody=gk("ibs") + gk("ibd"), iin={str(d): -res[d]["i(vi1)"] for d in res}, vsb=g0.get("v(tail)", 0) - g0.get("v(nw1)", 0),
                gain=r["gain"], ct=tr["ct"], zmin=tr["zmin"], z=tr["z"], static=n["static"], sw=n["sw"])
if __name__ == "__main__":
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(2) as ex: R = list(ex.map(one, [("tt", 27), ("tt", 60)]))
    json.dump(R, open(f"results/dtmos_cmp_{VAR}.json", "w"), default=float)
    for r in R: print(json.dumps({k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()}, default=float), flush=True)
