"""Final v5 corner verification with the bias-electrode DRL setting the input CM (VCM taken from the DRL-closed op).
Cf 1.12 pF (gain ~32.7 dB), Cpf 0.68 pF fixed + 10-bit Ct, tail target 0.8 V (5-diode ladder)."""
import numpy as np, json, re
from concurrent.futures import ProcessPoolExecutor
import v5_sim as S, v5_bias as B, v5_trim as T, v5_cpf as CP
from lv import header, run
def one(kt):
    k, t = kt; p = S.P(k, t)
    o, f = run(header(p) + B.core(p, 3.4e-12) + B.bench(p) + B.ns_guess(p) + ".control\nop\nprint v(bd) v(tail) v(vo1) i(vdd) i(vss)\n.endc\n.end\n")
    v = {a: float(b) for a, b in re.findall(r"^(\S+)\s*=\s*([-\d.e+]+)", o, re.M)}
    p["VCM"] = v["v(bd)"]; r = S.zin(p); tr = S.trim(r); n = S.noise(S.P(k, t) | {"VCM": v["v(bd)"]})
    return dict(corner=k, temp=t, vcm=v["v(bd)"], tail=v["v(tail)"], vo=v["v(vo1)"], idd_total=-v["i(vdd)"], gain=r["gain"], flp=r["flp"], rb=r["rb"],
                ct=tr["ct"], zmin=tr["zmin"], z=tr["z"], static=n["static"], sw=n["sw"])
if __name__ == "__main__":
    with ProcessPoolExecutor(2) as ex: R = list(ex.map(one, T.CORNERS))
    for r in R:
        print(f"{r['corner']}{r['temp']:>3}: VCM {r['vcm']:.3f} tail {r['tail']:.3f} vo {r['vo']:.3f} | I(VDD) {r['idd_total']*1e9:.0f} nA | gain {r['gain']:.1f} dB fLP {r['flp']:.0f} | "
              f"Ct {r['ct']*1e15:.0f} fF Zmin {r['zmin']/1e9:.2f} G Z@1/50/150 {r['z'][1]/1e9:.3g}/{r['z'][3]/1e9:.3g}/{r['z'][5]/1e9:.3g} G | IRN {r['static']:.3f}/{r['sw']:.3f} uV", flush=True)
    json.dump(R, open("results/v5_final3.json", "w"), default=float)
