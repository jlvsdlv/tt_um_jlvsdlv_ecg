"""THD attribution (static loads, dry 10M electrodes, 1 mVpp 100 Hz): which v5 change doubled the THD?"""
import sys, json
from concurrent.futures import ProcessPoolExecutor
import v5_tran as V5, v4_tran as B, v5_sim as S, v5_core as C
oP = S.P
def job(a):
    tag, cbc, gx = a
    C.CBC = cbc
    def P2(*x, **k):
        p = oP(*x, **k)
        if gx != 3: p["Cg"] *= gx / 3; p["Cf"] *= gx / 3
        return p
    S.P = P2
    return B.tran((tag, 2000.0, 0, 10e6, 1e-9))
if __name__ == "__main__":
    J = [("Cbc 5p, Cg x3", 5e-12, 3), ("Cbc 20p, Cg x1", 20e-12, 1), ("Cbc 10p, Cg x3", 10e-12, 3), ("Cbc 5p, Cg x1", 5e-12, 1)]
    with ProcessPoolExecutor(2) as ex:
        for tag, r, err in ex.map(job, J):
            print(tag, "FAILED" if r is None else f": gain {r['gain_dB']:.2f} dB THD {r['thd']:.2f}%", flush=True)
