"""Final-settings transient: bulk switching (2 kHz) + bias-electrode DRL + electrodes + optional mains, real reset for 30 ms.
Gain 32.7 dB, tail 0.8 V, Cpf 0.68 pF + Ct trim, Cbc 20 pF, replica pseudo-R Rb, real Rf pseudo-R."""
import numpy as np, re, json, sys
from concurrent.futures import ProcessPoolExecutor
import v5_sim as S, v5_bias as B, v5_powerup as PU
import v2_tran4 as T2
T2.pt["M34"] = (2.5, 64, 4)   # split -> two halves of 2 fingers each (as v2/v4)
# driver logic at L = 0.5 um (min-L gates leaked ~120 nA at ff60)
def _inv(name, o, i, p, wp=1, wn=0.5):
    return dev(name + "P", o, i, "vdp", "vdp", T2.pp, (wp, 0.5, 1), p) + dev(name + "N", o, i, "0", "0", T2.n, (wn, 0.5, 1), p)
def _nand(name, o, a, b, p):
    return (dev(name + "P1", o, a, "vdp", "vdp", T2.pp, (1, 0.5, 1), p) + dev(name + "P2", o, b, "vdp", "vdp", T2.pp, (1, 0.5, 1), p) +
            dev(name + "N1", o, a, name + "m", "0", T2.n, (1, 0.5, 1), p) + dev(name + "N2", name + "m", b, "0", "0", T2.n, (1, 0.5, 1), p))
T2.inv, T2.nand = _inv, _nand
from lv import header, run
from amp import load_wrdata, dev
F0, TRST, TSK, TST, FS = 37.0, 1 / 37.0, 0.08, 0.3, 2000.0   # reset released at a signal zero crossing (MCU syncs to baseline)
OPT = dict(linrf=False, en=1, rst=True, split=True, irbm=True, step=0.5e-6)
def build(k, t, vidpp, mains, Re=10e6, Ce=1e-9, Reb=10e6, Ceb=1e-9, en=None):
    en = OPT['en'] if en is None else en
    p = S.P(k, t); ct = B.CT.get((k, t), 3.4e-12)
    c = B.core(p, ct) + (PU.rst_sw(p) if OPT['rst'] else 'Vdum rst 0 0\n')
    if OPT['irbm']: c = re.sub(r"IRB vgr vss \S+\n", "", c) + dev("IRBM", "vgr", "nd", "vss", "vss", "sky130_fd_pr__nfet_01v8_lvt", (0.42, 16, 1), p)
    if OPT["linrf"]:
        R = 60e12
        c = re.sub(r"XMR3s0 .*\n", f"RR3 g3 vo2 {R:.4g}\n", c); c = re.sub(r"XMR4s0 .*\n", f"RR4 g4 vo1 {R:.4g}\n", c)
    c = (T2.split_loads(c, p) + T2.driver(p, 5e-12, en, FS)) if OPT['split'] else c
    a = vidpp / 4
    b = B.bench(p, Re, Ce, Reb, Ceb, sig=f"sin(0 {a} {F0})", mains=mains).replace(f"Ve2 vs2 bd dc 0.0 sin(0 {a} {F0})", f"Ve2 vs2 bd dc 0.0 sin(0 {-a} {F0})")
    hdr = header(p).replace("reltol=1e-5", "reltol=1e-4 method=gear itl4=200").replace("abstol=1e-17", "abstol=1e-15")
    return hdr + c + b + B.ns_guess(p) + (f"Vrst rst 0 pwl(0 1.8 {TRST} 1.8 {TRST+1e-5} 0)\n" if OPT["rst"] else "") + (".ic v(vbnb)=-1.38\n" if OPT["split"] else "") + (
        f".control\ntran {OPT['step']} {TST} 0 {OPT['step']}\nmeas tran qdp integ i(vdp) from={TSK} to={TST}\nmeas tran qdd integ i(vdd) from={TSK} to={TST}\n"
        "linearize\nlet vod=v(vo1)-v(vo2)\nlet vic=(v(vp1)+v(vp2))/2\nlet vpd=v(vp1)-v(vp2)\nwrdata tf.txt vod vic vpd v(tail) v(vo1) v(g3) v(vbna) v(vbnb)\n.endc\n.end\n")
def job(a):
    tag, k, t, vidpp, mains = a
    o, f = run(build(k, t, vidpp, mains), timeout=7100)
    if "tf.txt" not in f: return tag, None, o[-500:]
    x = load_wrdata(f["tf.txt"]); tt = x[:, 0]
    if np.all(x[-50:, 1] == 0): return tag, None, "aborted"
    m = tt >= TSK; tt = tt[m]; vod, vic, vpd, tail, vo1, g3, wa, wb = (x[m, i] for i in (1, 3, 5, 7, 9, 11, 13, 15))
    qm = {kk: float(v) for kk, v in re.findall(r"^(qd[pd])\s*=\s*([-\d.eE+]+)", o, re.M)}
    def amp(y, fq):
        fr = [fq] + [h * F0 for h in (1, 2, 3) if abs(h * F0 - fq) > 1e-6] + ([50.0] if abs(fq - 50) > 1e-6 else [])   # no duplicate regressors
        A = np.vstack([f_(2*np.pi*x*tt) for x in fr for f_ in (np.sin, np.cos)] + [np.ones_like(tt), tt]).T
        c = np.linalg.lstsq(A, y, rcond=None)[0]; return np.hypot(c[0], c[1])
    a1, a2, a3 = amp(vod, F0), amp(vod, 2*F0), amp(vod, 3*F0); g = a1 / (vidpp / 2)
    a50 = amp(vod, 50.0); rip = amp(vod, FS)
    return tag, dict(gain_dB=20*np.log10(g), thd=100*np.hypot(a2, a3)/a1, in50_uVpp=2*a50/g*1e6, ripple_out_uV=rip*1e6, vic_mean=vic.mean(), vic_pp_mV=np.ptp(vic)*1e3,
                     tail_mean=tail.mean(), vo1=vo1.mean(), g3=g3.mean(), g3_drift=(g3[-100:].mean()-g3[:100].mean())*1e3, wa=(wa.min(), wa.max()), wb=(wb.min(), wb.max()), idd_nA=-qm.get("qdd", 0)/(TST-TSK)*1e9, idp_nA=-qm.get("qdp", 0)/(TST-TSK)*1e9), ""
if __name__ == "__main__":
    J = [("tt27 4 mVpp + mains", "tt", 27, 4e-3, 325), ("tt27 10 mVpp, no mains", "tt", 27, 10e-3, 0),
         ("ss0 4 mVpp + mains", "ss", 0, 4e-3, 325), ("ff60 4 mVpp + mains", "ff", 60, 4e-3, 325)]
    R = []
    with ProcessPoolExecutor(2) as ex:
        for tag, r, err in ex.map(job, J):
            if r is None: print(tag, "FAILED", err, flush=True); continue
            R.append((tag, r))
            print(f"{tag:24s}: gain {r['gain_dB']:.2f} dB THD {r['thd']:.2f}% | 50 Hz in-ref {r['in50_uVpp']:.2f} uVpp | 2 kHz ripple out {r['ripple_out_uV']:.0f} uV | "
                  f"input CM {r['vic_mean']:.3f} V ({r['vic_pp_mV']:.1f} mVpp) tail {r['tail_mean']:.3f} | I(VDD) {r['idd_nA']:.0f} nA, I(1.8V) {r['idp_nA']:.1f} nA", flush=True)
    json.dump(R, open("results/v5_tranfinal.json", "w"))
