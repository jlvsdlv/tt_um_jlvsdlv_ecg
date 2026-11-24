import v5_bias as B, v5_bias_tran as BT
from concurrent.futures import ProcessPoolExecutor
def job(a):
    B.MODE.update(fast=True, cc=10e-12, i2m=4); return BT.tran(a)
if __name__ == "__main__":
    J = [("FAST tt27 dry in / dry bias, mains", "tt", 27, 10e6, 1e-9, 10e6, 1e-9, 325), ("FAST ss0 dry in / dry bias, mains", "ss", 0, 10e6, 1e-9, 10e6, 1e-9, 325),
         ("FAST tt27 dry in / wet bias, mains", "tt", 27, 10e6, 1e-9, 1e6, 47e-9, 325), ("FAST ff60 dry in / dry bias, mains", "ff", 60, 10e6, 1e-9, 10e6, 1e-9, 325)]
    with ProcessPoolExecutor(2) as ex:
        for tag, r in ex.map(job, J):
            print(tag, "FAILED" if r is None else f": gain {r['gain_dB']:.2f} dB | 50 Hz input-referred {r['in_ref_50Hz_uVpp']:.2f} uVpp | input CM {r['vic_mean']:.3f} V, ripple {r['vic_pp_mV']:.2f} mVpp | tail pp {r['tail_pp_mV']:.2f} mV", flush=True)
