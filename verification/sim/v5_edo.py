"""Differential electrode offset (EDO) tolerance: steady-state DC op with the DRL closed (Rf at DC -> M3 diode, DC gain ~ gm1/gm3),
then the 10 Hz AC gain and output headroom with that offset present."""
import numpy as np, re, sys
from concurrent.futures import ProcessPoolExecutor
import v5_sim as S, v5_bias as B
from lv import header, run
from amp import load_wrdata
def one(a):
    k, t, edo = a; p = S.P(k, t); ct = B.CT.get((k, t), 2.7e-12)
    b = B.bench(p, 1.0, 1e-15, edo=(edo / 2, -edo / 2))
    b = b.replace(f"Ve1 vs1 bd dc {edo/2} ", f"Ve1 vs1 bd dc {edo/2} ac 0.5 ").replace(f"Ve2 vs2 bd dc {-edo/2} ", f"Ve2 vs2 bd dc {-edo/2} ac 0.5 180 ")
    o, f = run(header(p) + B.core(p, ct) + b + B.ns_guess(p) + ".control\nop\nprint v(vo1) v(vo2) v(tail) v(bd)\nac dec 10 0.001 1e3\nlet h=mag(v(vo1)-v(vo2))\nwrdata e.txt h\n.endc\n.end\n")
    v = {x: float(y) for x, y in re.findall(r"^v\((\w+)\)\s*=\s*([-\d.e+]+)", o, re.M)}; x = load_wrdata(f["e.txt"])
    g = lambda F: 20*np.log10(np.interp(F, x[:, 0], x[:, 1]))
    return a, v, g(0.001), g(10)
if __name__ == "__main__":
    J = [("tt", 27, e) for e in (0, 0.02, 0.05, 0.1, 0.2)] + [("ss", 0, 0.05), ("ff", 60, 0.05)]
    with ProcessPoolExecutor(2) as ex:
        for (k, t, e), v, g0, g10 in ex.map(one, J):
            print(f"{k}{t} EDO {e*1e3:5.0f} mV: vo1 {v['vo1']:.3f} vo2 {v['vo2']:.3f} (diff {(v['vo1']-v['vo2'])*1e3:+.0f} mV) tail {v['tail']:.3f} | gain @1 mHz {g0:.1f} dB, @10 Hz {g10:.1f} dB", flush=True)
