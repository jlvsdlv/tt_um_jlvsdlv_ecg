"""Noise vs bias: where does flicker noise start to dominate the 0.5-150 Hz input-referred noise?
For each tail current: size the mirror for ~1 nA/sq, raise VDD until a healthy OP exists,
re-centre VCM (max open-loop gain), then split the input-referred PSD into flicker/thermal per device."""
import sys, json, re, numpy as np
from concurrent.futures import ProcessPoolExecutor
from lv import LP, op, header, core, sup, run
from amp import load_wrdata
from lvnoise import rps, opnodes
from amp import nef
from top import FINAL

VMIN = 0.078          # 3*UT headroom on MB2, M1, M3
FR = np.logspace(np.log10(0.5), np.log10(150), 200)

def params(itail, vdd, vcm):
    ib = itail / 20.0
    b = dict(FINAL); b.pop("VCM", None); b.pop("VBNGEN", None)
    b.update(VDD=vdd, IB=ib, VBN=min(0.15, vdd), VCM=vcm)
    if ib > 0.2e-9:                       # mirror sized for ~1 nA/sq, unit 10/2 fingers
        m = max(1, int(round(ib / 5e-9)))
        w = 10.0 if ib >= 5e-9 else max(0.42, 2 * ib / 1e-9)
        b.update(MB1=(w, 2, m), MB2=(w, 2, 20 * m))
    return LP(**b)

def best_op(itail, vdd):
    best = None
    for vcm in np.arange(-0.1, vdd * 0.85, 0.01):
        p = params(itail, vdd, vcm)
        try: d = op(p)
        except Exception: continue
        m = min(abs(d['MB2']['vds']), abs(d['M1']['vds']), d['M3']['vds'])
        if m < VMIN: continue
        if best is None or d['A0'] > best[1]['A0']: best = (vcm, d, p)
    return best

def parse_raw(txt):
    """ASCII rawfile -> dict name -> np.array (real part)"""
    lines = txt.splitlines(); i = 0; names = []; npts = 0
    while i < len(lines):
        l = lines[i]
        if l.startswith("No. Points:"): npts = int(l.split(":")[1])
        if l.startswith("Variables:"):
            i += 1
            while not lines[i].startswith("Values:"):
                t = lines[i].split(); names.append(t[1]); i += 1
            break
        i += 1
    vals = []
    for l in lines[i+1:]:
        t = l.split()
        if not t: continue
        vals.append(float(t[-1].split(",")[0]))
    a = np.array(vals).reshape(npts, len(names))
    return {n: a[:, k] for k, n in enumerate(names)}

def spectra(p):
    """input-referred PSD (V^2/Hz) on FR: total, M1+M2 flicker, M3+M4 flicker, all flicker; plus gain"""
    r = rps(p); c = core(p); ns = opnodes(p)
    c = re.sub(r"\.nodeset.*\n", "", c)
    c += ".nodeset " + " ".join(f"v({k})={v:.6g}" for k, v in ns.items() if k not in ("vdd","vss","vi1","vi2","vbn","vb")) + "\n"
    c = re.sub(r"XMR3 .*\n", f"RR3 g3 vo2 {r:.6g}\n", c); c = re.sub(r"XMR4 .*\n", f"RR4 g4 vo1 {r:.6g}\n", c)
    net = header(p).replace("gmin=1e-15", "gmin=1e-13") + c + sup(p, vi1_ac="0.5", vi2_ac="0.5 180") + (
        ".control\nset filetype=ascii\nnoise v(vo1,vo2) Vi1 dec 30 0.05 1e4 1\nsetplot noise1\nwrite noise.csv all\n"
        "setplot const\nac dec 30 0.05 1e4\nlet hm=mag(v(vo1)-v(vo2))\nwrdata ac.txt hm\n.endc\n.end\n")
    out, f = run(net)
    if "noise.csv" not in f or "ac.txt" not in f: raise RuntimeError(out[-800:])
    try:
        d = parse_raw(f["noise.csv"]); d["frequency"]
    except Exception:
        open(f"results/nb_fail_{p['IB']:.3g}_{p['VDD']}_{p['VCM']:.2f}.txt", "w").write(f["noise.csv"][:3000] + "\n----\n" + out[-3000:])
        raise
    b = load_wrdata(f["ac.txt"])
    fr = d["frequency"]; G2 = np.interp(fr, b[:, 0], b[:, 1]) ** 2
    sq = lambda pat: sum(v ** 2 for k, v in d.items() if re.fullmatch(pat, k))
    tot = d["onoise_spectrum"] ** 2
    f12 = sq(r"onoise\.m\.xm[12]\.\S+\.1overf"); f34 = sq(r"onoise\.m\.xm[34]\.\S+\.1overf")
    fall = sq(r"onoise\.m\.\S+\.1overf")
    I = lambda x: np.interp(FR, fr, x / G2)
    return dict(tot=I(tot), f12=I(f12), f34=I(f34), fall=I(fall), g=np.sqrt(np.interp(FR, fr, G2)))

def one(itail):
    if itail < 2e-9:                      # baseline = the signed-off 0.3 V design (self-biased VBN)
        p = LP(**FINAL); d = op(p); vcm = FINAL["VCM"]; vdd = p["VDD"]
        return finish(itail, vdd, vcm, d, p)
    for vdd in (0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2):
        b = best_op(itail, vdd)
        if b: break
    else:
        return dict(itail=itail, ok=False)
    vcm, d, p = b
    return finish(itail, vdd, vcm, d, p)

def finish(itail, vdd, vcm, d, p):
    s = spectra(p); G2 = 1.0
    irn = lambda x: float(np.sqrt(np.trapezoid(x / G2, FR)))
    tot, th = irn(s["tot"]), irn(s["tot"] - s["fall"])
    thermal_psd = (s["tot"] - s["fall"]) / G2; flick_psd = s["fall"] / G2
    cross = np.where(flick_psd < thermal_psd)[0]
    fc = float(FR[cross[0]]) if len(cross) else 999.0
    ptot = np.trapezoid(s["tot"] / G2, FR)
    return dict(itail=itail, ok=True, vdd=vdd, vcm=float(vcm), idd=d["idd"], A0=d["A0"],
                irn=tot, irn_thermal_only=th, irn_no_m34_flicker=irn(s["tot"] - s["f34"]),
                irn_no_m12_flicker=irn(s["tot"] - s["f12"]),
                flicker_frac=float(np.trapezoid(s["fall"] / G2, FR) / ptot),
                m12_flicker_frac=float(np.trapezoid(s["f12"] / G2, FR) / ptot),
                m34_flicker_frac=float(np.trapezoid(s["f34"] / G2, FR) / ptot),
                fcorner=fc, nef=nef(tot, d["idd"], 150),
                psd_tot=(s["tot"] / G2).tolist(), psd_fl12=(s["f12"] / G2).tolist(), psd_fl34=(s["f34"] / G2).tolist(),
                psd_th=thermal_psd.tolist())

if __name__ == "__main__":
    tails = [1.6e-9, 10e-9, 30e-9, 100e-9, 300e-9, 1e-6]
    with ProcessPoolExecutor(2) as ex: R = list(ex.map(one, tails))
    json.dump(dict(fr=FR.tolist(), rows=R), open("results/noisebias.json", "w"))
    print(f"{'Itail':>8} {'VDD':>5} {'VCM':>6} {'Itot':>8} {'IRN uV':>7} {'thermal-only':>12} {'flicker %':>9} {'M12 fl%':>7} {'M34 fl%':>7} {'1/f corner':>10} {'NEF':>5}")
    for r in R:
        if not r["ok"]: print(f"{r['itail']*1e9:7.1f}n  no healthy OP up to 1.2 V"); continue
        print(f"{r['itail']*1e9:7.1f}n {r['vdd']:5.2f} {r['vcm']:6.2f} {r['idd']*1e9:7.1f}n {r['irn']*1e6:7.2f} {r['irn_thermal_only']*1e6:12.2f} "
              f"{100*r['flicker_frac']:9.1f} {100*r['m12_flicker_frac']:7.1f} {100*r['m34_flicker_frac']:7.1f} {r['fcorner']:9.1f}Hz {r['nef']:5.2f}")
