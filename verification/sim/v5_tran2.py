import json, sys
from concurrent.futures import ProcessPoolExecutor
import v5_tran as V5, v4_tran as B, v5_sim as S
oP = S.P
def job(a):
    tag, clf, en = a
    S.P = lambda *x, **k: oP(*x, clf=clf, **{kk: v for kk, v in k.items() if kk != "clf"})
    return B.tran((tag, 2000.0, en, 10e6, 1e-9))
if __name__ == "__main__":
    with ProcessPoolExecutor(2) as ex:
        for tag, r, err in ex.map(job, [("CL/1 dry 10M sw", 1, 1), ("CL/2 dry 10M static", 2, 0)]):
            print(tag, "FAILED" if r is None else f"gain {r['gain_dB']:.2f} THD {r['thd']:.2f}% ripple {r['ripple_out_uV']:.1f} uV resid {r['res_rms_first']:.0f}/{r['res_rms_second']:.0f} uV", flush=True)
