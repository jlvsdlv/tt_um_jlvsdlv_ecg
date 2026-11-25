import sys, re, json, numpy as np, v5_tranfinal as TF
from amp import load_wrdata
d = sys.argv[1]; tst, tsk = 0.075, 0.048
x = load_wrdata(open(f"{d}/tf.txt").read()); tt = x[:, 0]; o = open(f"{d}/ng.log", errors="ignore").read()
m = tt >= tsk; T_ = tt[m]
vod, vic, vpd, tail, vo1, g3, wa, wb, idd, n1, nb, bd = (x[m, 1 + 2*i] for i in range(12))
qm = {k: float(v) for k, v in re.findall(r"^(qd[pd])\s*=\s*([-\d.eE+]+)", o, re.M)}
def amp(y, fq):
    fr = [fq] + [h*TF.F0 for h in (1, 2, 3) if abs(h*TF.F0 - fq) > 1e-6] + ([50.0] if abs(fq - 50) > 1e-6 else [])
    A = np.vstack([g(2*np.pi*q*T_) for q in fr for g in (np.sin, np.cos)] + [np.ones_like(T_), T_]).T
    return np.hypot(*np.linalg.lstsq(A, y, rcond=None)[0][:2])
a1 = amp(vod, TF.F0); g = a1/2e-3
r = dict(gain_dB=20*np.log10(g), thd=100*np.hypot(amp(vod, 2*TF.F0), amp(vod, 3*TF.F0))/a1, in50_uVpp=2*amp(vod, 50.0)/g*1e6, ripple_out_uV=amp(vod, TF.FS)*1e6,
         vic_mean=vic.mean(), tail_mean=tail.mean(), vo1=vo1.mean(), g3=g3.mean(), wa=(wa.min(), wa.max()), wb=(wb.min(), wb.max()),
         idd_nA=-qm["qdd"]/(tst-tsk)*1e9, idp_nA=-qm["qdp"]/(tst-tsk)*1e9, n1=n1.mean(), nb=nb.mean())
# start-up: time for I(VDD) and tail to reach 95 % of final
ta = x[:, 0]; I = -x[:, 17]; ti = x[:, 7]
fin_i = I[(ta > 0.020) & (ta < 0.026)].mean(); fin_t = ti[(ta > 0.020) & (ta < 0.026)].mean()
r["t_idd95_ms"] = 1e3*ta[np.argmax(np.abs(I - fin_i) < 0.05*fin_i)]; r["t_tail_1mV_ms"] = 1e3*ta[np.argmax(np.abs(ti - fin_t) < 1e-3)]
print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}, default=float))
