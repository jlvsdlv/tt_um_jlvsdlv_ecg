import numpy as np, sys, json
from concurrent.futures import ProcessPoolExecutor
import v5_bias as B
from lv import header, run
from amp import load_wrdata
import v5_sim as S
def lg(a):
    cc, i2m, Reb, Ceb, k, t = a
    B.MODE.update(fast=True, cc=cc, i2m=i2m); p = S.P(k, t); ct = B.CT.get((k, t), 3.38e-12)
    c = B.core(p, ct).replace("Rts tail tsen 1\n", "Lbrk tail tsen 1e12\nCinj tsen inj 1\nVinj inj 0 dc 0 ac 1\n")
    net = header(p) + c + B.bench(p, Reb=Reb, Ceb=Ceb) + B.ns_guess(p) + ".control\nac dec 20 1e-2 1e5\nlet T=-v(tail)/v(tsen)\nwrdata lg.txt mag(T) ph(T)\n.endc\n.end\n"
    o, f = run(net)
    if "lg.txt" not in f: return a, None
    x = load_wrdata(f["lg.txt"]); fr, m, ph = x[:, 0], x[:, 1], np.degrees(np.unwrap(x[:, 3]))
    i = np.where(m < 1)[0][0]; g50 = 20*np.log10(np.interp(50, fr, m))
    pm = 180 + (ph[i] - ph[0]) + (0 if ph[0] > -90 else 0)
    return a, dict(dc=20*np.log10(m[0]), g50=g50, ugb=fr[i], pm=180 - abs(ph[i] - ph[0]) if True else pm)
if __name__ == "__main__":
    J = [(cc, i2m, Reb, Ceb, k, t) for cc in (10e-12, 30e-12) for i2m in (4,) for (Reb, Ceb) in ((10e6, 1e-9), (1e6, 47e-9)) for k, t in (("tt", 27), ("ss", 0), ("ff", 60))]
    with ProcessPoolExecutor(2) as ex:
        for a, r in ex.map(lg, J):
            print(f"Cc {a[0]*1e12:.0f}p I2 {a[1]*5} nA bias-el {a[2]/1e6:.0f}M {a[4]}{a[5]}: " + ("FAIL" if r is None else f"DC {r['dc']:.0f} dB, @50 Hz {r['g50']:.1f} dB, UGB {r['ugb']:.3g} Hz, PM {r['pm']:.0f}"), flush=True)
