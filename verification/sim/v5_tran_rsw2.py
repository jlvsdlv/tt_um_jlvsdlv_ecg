"""Short A/B: same switched transient, ideal supply vs supply through the TT ua[5] path (500 ohm, 5 pF pad, no board decap)."""
import sys, json
import v5_tranfinal as TF, v5_bias as B
RSW = float(sys.argv[1])
TF.TST, TF.TSK = 0.075, 0.048        # reset releases at 27 ms; analyse 48-75 ms (1 signal period of 37 Hz)
_bench = B.bench
def bench(p, *a, **k):
    s = _bench(p, *a, **k)
    return s.replace(f"Vdd vdd 0 {p['VDD']}\n", f"Vdd vddp 0 {p['VDD']}\nRsw vddp vdd {max(RSW,1e-3)}\nCpad vddp 0 5p\nCchip vdd 0 1.5p\nCdnwa vbna vdd 0.4p\nCdnwb vbnb vdd 0.4p\n")
B.bench = bench
import v5_tranfinal
src = open(v5_tranfinal.__file__).read()
tag, r, err = TF.job(("tt27 4 mVpp + mains", "tt", 27, 4e-3, 325))
print(RSW, json.dumps(r, default=float) if r else err, flush=True)
