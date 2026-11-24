"""Input range: THD and gain vs differential amplitude (v5 baseline, dry 10M electrodes)."""
from concurrent.futures import ProcessPoolExecutor
import v5_tran as V5, v4_tran as B
def job(a):
    amp, en = a; B.AMP = amp
    return B.tran((f"{amp*1e3:.0f} mVpp {'sw' if en else 'static'}", 2000.0, en, 10e6, 1e-9))
if __name__ == "__main__":
    with ProcessPoolExecutor(2) as ex:
        for tag, r, err in ex.map(job, [(2e-3, 0), (4e-3, 0), (4e-3, 1), (8e-3, 0)]):
            print(tag, "FAILED" if r is None else f": gain {r['gain_dB']:.2f} dB THD {r['thd']:.2f}%", flush=True)
