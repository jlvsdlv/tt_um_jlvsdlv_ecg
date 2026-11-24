import numpy as np, json, re
from concurrent.futures import ProcessPoolExecutor
import v5_sim as S, v5_bias as B, v5_trim as T
from lv import header, run
def vcm_drl(k, t):
    p = S.P(k, t); ct = B.CT.get((k, t), 3.38e-12)
    o, f = run(header(p) + B.core(p, ct) + B.bench(p) + B.ns_guess(p) + ".control\nop\nprint v(bd) v(tail)\n.endc\n.end\n")
    return float(re.findall(r"v\(bd\)\s*=\s*([-\d.e+]+)", o)[0])
def job(a):
    cpf, k, t = a; p = S.P(k, t); p["VCM"] = vcm_drl(k, t); r = S.zin(p, cpf)
    f, b = r["f"], r["b"]; ce = lambda F: np.interp(F, f, b) / (2*np.pi*F) * 2
    return a, p["VCM"], r["gain"], ce(10), ce(150)
if __name__ == "__main__":
    J = [(c, k, t) for c in (0.8e-12, 1.0e-12) for k, t in (("tt", 27), ("ff", 27), ("ff", 60), ("fs", 27), ("ss", 0))]
    with ProcessPoolExecutor(2) as ex:
        for a, vcm, g, c10, c150 in ex.map(job, J):
            print(f"Cpf {a[0]*1e12:.1f}p {a[1]}{a[2]}: VCM(DRL) {vcm:.3f} gain {g:.1f} dB  Ceff@10/150 Hz {c10*1e12:+.2f}/{c150*1e12:+.2f} pF", flush=True)
