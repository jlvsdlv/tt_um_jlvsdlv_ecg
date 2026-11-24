"""Switched transient with the TT analog-pin path on the 1.0 V supply: VDD_A enters through ua[5]
(500 ohm switch, 5 pF pad cap, no board decoupling = worst case) plus on-chip vdd cap 1.5 pF and
DNW-to-island junction caps (0.4 pF each, the DNW is tied to vdd)."""
import sys, json
import v5_tranfinal as TF, v5_bias as B
_bench = B.bench
RSW = float(sys.argv[1]) if len(sys.argv) > 1 else 500.0
def bench(p, *a, **k):
    s = _bench(p, *a, **k)
    return s.replace(f"Vdd vdd 0 {p['VDD']}\n", f"Vdd vddp 0 {p['VDD']}\nRsw vddp vdd {RSW}\nCpad vddp 0 5p\nCchip vdd 0 1.5p\nCdnwa vbna vdd 0.4p\nCdnwb vbnb vdd 0.4p\n")
B.bench = bench
if __name__ == "__main__":
    from concurrent.futures import ProcessPoolExecutor
    J = [("tt27 4 mVpp + mains", "tt", 27, 4e-3, 325), ("ss0 4 mVpp + mains", "ss", 0, 4e-3, 325)]
    with ProcessPoolExecutor(2) as ex:
        for tag, r, err in ex.map(TF.job, J):
            if r is None: print(tag, "FAILED", err, flush=True); continue
            print(f"Rsw {RSW:.0f} {tag:22s}: gain {r['gain_dB']:.2f} dB THD {r['thd']:.2f}% | 50 Hz in-ref {r['in50_uVpp']:.2f} uVpp | 2 kHz ripple out {r['ripple_out_uV']:.0f} uV | "
                  f"tail {r['tail_mean']:.3f} | I(VDD) {r['idd_nA']:.0f} nA", flush=True)
