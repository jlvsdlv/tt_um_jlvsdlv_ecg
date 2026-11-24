"""Steady-state transient with the bias driver closing the CM loop: 1 mVpp 10 Hz differential ECG-like tone,
mains 230 Vrms (325 V peak) coupled to the body by 2 pF (body-earth 200 pF, chip-earth 20 pF), input electrodes
with 10% Re/Ce mismatch. Static loads (no bulk switching) to keep runtime short."""
import numpy as np, re, json
from concurrent.futures import ProcessPoolExecutor
import v5_bias as B, v5_sim as S
from lv import header, run
from amp import load_wrdata
F0, AMP, TST, TSK = 10.0, 1e-3, 0.5, 0.2
def tran(a):
    tag, k, t, Re, Ce, Reb, Ceb, mains = a
    p = S.P(k, t); ct = B.CT.get((k, t), 3.38e-12)
    sig = f"sin(0 {AMP/2}*AMP {F0})".replace("*AMP", "")
    bench = B.bench(p, Re, Ce, Reb, Ceb, sig=f"sin(0 {AMP/2} {F0})", mains=mains).replace(f"Ve2 vs2 bd dc 0.0 sin(0 {AMP/2} {F0})", f"Ve2 vs2 bd dc 0.0 sin(0 {-AMP/2} {F0})")
    hdr = header(p).replace("reltol=1e-5", "reltol=1e-4 method=gear").replace("abstol=1e-17", "abstol=1e-15")
    net = hdr + B.core(p, ct) + bench + B.ns_guess(p) + (f".control\ntran 20u {TST} 0 20u\nlinearize\nlet vod=v(vo1)-v(vo2)\nlet vic=(v(vp1)+v(vp2))/2\n"
          "wrdata tr.txt vod vic v(bd) v(tail)\n.endc\n.end\n")
    o, f = run(net, timeout=7000)
    if "tr.txt" not in f: return tag, None
    x = load_wrdata(f["tr.txt"]); tt = x[:, 0]; m = tt >= TSK; tt = tt[m]
    vod, vic, bd, tail = (x[m, i] for i in (1, 3, 5, 7))
    fit = lambda y, fq: np.linalg.lstsq(np.vstack([np.sin(2*np.pi*fq*tt), np.cos(2*np.pi*fq*tt), np.ones_like(tt)]).T, y, rcond=None)[0]
    a10 = np.hypot(*fit(vod, F0)[:2]); a50 = np.hypot(*fit(vod, 50)[:2]); g = a10 / AMP
    return tag, dict(gain_dB=20*np.log10(g), in_ref_50Hz_uVpp=2*a50/g*1e6, vic_pp_mV=np.ptp(vic)*1e3, vic_mean=vic.mean(), tail_pp_mV=np.ptp(tail)*1e3)
if __name__ == "__main__":
    J = [("tt27 dry 10M in / wet bias, no mains", "tt", 27, 10e6, 1e-9, 1e6, 47e-9, 0),
         ("tt27 dry 10M in / wet bias, mains", "tt", 27, 10e6, 1e-9, 1e6, 47e-9, 325),
         ("tt27 dry 10M in / dry 10M bias, mains", "tt", 27, 10e6, 1e-9, 10e6, 1e-9, 325),
         ("ss0 dry 10M in / dry 10M bias, mains", "ss", 0, 10e6, 1e-9, 10e6, 1e-9, 325)]
    with ProcessPoolExecutor(2) as ex:
        for tag, r in ex.map(tran, J):
            print(tag, "FAILED" if r is None else f": gain {r['gain_dB']:.2f} dB | 50 Hz input-referred {r['in_ref_50Hz_uVpp']:.2f} uVpp | input CM {r['vic_mean']:.3f} V, ripple {r['vic_pp_mV']:.2f} mVpp | tail pp {r['tail_pp_mV']:.2f} mV", flush=True)
