"""v5 simulation helpers (robust against ngspice re-solve issues with the TOhm-level pseudo-R nodes):
 - every AC/noise netlist gets a full .nodeset from a pad-less op, and the AC is the FIRST analysis (no preceding 'op')
 - noise uses the linear small-signal equivalent of the replica pseudo-R (series 1/gds of the 4 devices, extracted per corner)
"""
import numpy as np, re
import v5_core as C
import v4_acdt as A, v4_corner as V, v5_trim as T, noisebias as nb, lv, lvnoise
from lv import header, sup, run
from amp import load_wrdata, draw_mismatch
CPF = 0.68e-12
def P(k, t, seed=None, clf=2):
    V.VCM = T.REC[(k, t)]
    mm = draw_mismatch(np.random.default_rng(5000 + seed))[0] if seed is not None else None
    p = V.P(k, t, mm); p["CLEXT"] = V.CL / clf
    p["Cg"] *= 3; p["Cf"] *= 9; p["MRF"] = (0.42, 4, 1)
    p["M34"] = (2.5, 64, 2); p["VBN"] = 0.03
    p["MB1"] = (2.0, 2, 10); p["MB2"] = (2.0, 2, 200)   # tail mirror shrunk 5x in W (area)   # instantaneous switched config: ONE half (2 fingers of 2.5/64) on, its well at +0.03 V (the clamp level)      # v5: Cg 15 pF, Cf 1.12 pF (gain 32.6 dB for +-5 mV range), min-width Rf pseudo-R
    return p
def opv(p, cfn):
    q = "".join(f" @m.xmrb1{i}.msky130_fd_pr__pfet_01v8[gds] @m.xmrb1{i}.msky130_fd_pr__pfet_01v8[gbd]" for i in range(C.NS)) + "".join(f" @m.xmr3s{i}.msky130_fd_pr__pfet_01v8[gds] @m.xmr3s{i}.msky130_fd_pr__pfet_01v8[gbd]" for i in range(C.NF))
    o, _ = run(header(p) + cfn(p) + sup(p) + f".control\nop\nprint all\nprint{q} i(vdd)\n.endc\n.end\n")
    ns = {m.group(1): float(m.group(2)) for m in re.finditer(r"^(\w+)\s*=\s*([-\d.e+]+)$", o, re.M) if m.group(1) not in ("vdd", "vss", "vi1", "vi2")}
    gg = [float(x) for x in re.findall(r"\[g(?:ds|bd)\]\s*=\s*([-\d.e+]+)", o)]
    g = [gg[i] + gg[i + 1] for i in range(0, len(gg), 2)]
    idd = float(re.findall(r"i\(vdd\)\s*=\s*([-\d.e+]+)", o)[0])
    global RF; RF = sum(1 / x for x in g[C.NS:])
    return ns, sum(1 / x for x in g[:C.NS]), -idd
def nodeset(ns): return ".nodeset " + " ".join(f"v({k})={v:.6g}" for k, v in ns.items()) + "\n"
def zin(p, cpf=CPF, ct=0.0, _try=0):
    cfn = C.mk5(None, cpf, ct); ns, rb, idd = opv(p, cfn)
    s = sup(p, vi1_ac="0.5", vi2_ac="0.5 180").replace("Vi1 vi1 0", "Vi1 vp1 0").replace("Vi2 vi2 0", "Vi2 vp2 0")
    body = re.sub(r"\.nodeset.*\n", "", cfn(p))
    net = header(p) + body + V.PAD + nodeset(ns) + s + (".control\nac dec 40 0.2 1e4\nlet y=-i(vi1)/(v(vp1)-v(vp2))\nlet h=v(vo1)-v(vo2)\n"
          "wrdata y.txt real(y) imag(y) mag(h)\n.endc\n.end\n")
    o, f = run(net); a = load_wrdata(f["y.txt"]); fr = a[:, 0]; h = a[:, 5]
    g0 = h[np.argmin(abs(fr - 20))]; above = fr[(fr > 20) & (h < g0 / 2**0.5)]
    r = dict(f=fr, g=a[:, 1], b=a[:, 3], h=h, gain=20*np.log10(g0), flp=above[0] if len(above) else np.nan, rb=rb, idd=idd, ns=ns)
    if (r["gain"] > 40 or not r["flp"] > 1000) and _try < 4:      # ngspice landed on the spurious TOhm-node solution: nudge VCM and re-solve
        q = dict(p); q["VCM"] = p["VCM"] + 2e-4 * (1 if _try % 2 == 0 else -1) * (_try // 2 + 1); return zin(q, cpf, ct, _try + 1)
    return r
def noise(p, cpf=CPF):
    """IRN with the pseudo-R replaced by its extracted linear equivalent (4kT/R noise)."""
    cfn = C.mk5(None, cpf); ns, rb, idd = opv(p, cfn)
    A.RB = rb; rf = RF; base = C._orig(C.CBC, cpf); lin = lambda q: C.stack(base(q), rlin=rf)
    lv.core = lin; nb.core = lin; lvnoise.core = lin; nb.rps = lambda q: rf
    s = nb.spectra(p); F = nb.FR; I = lambda x: float(np.trapezoid(x, F))
    return dict(rb=rb, rf=rf, static=np.sqrt(I(s["tot"]))*1e6, sw=np.sqrt(I(s["tot"] - s["f34"] + A.R7*s["f34"]))*1e6, gain=float(20*np.log10(np.median(s["g"]))))
CT_W = None   # actual per-bit Ct weights (F); None -> ideal binary
def trim(r, lsb=10e-15, bits=10):
    cts = np.arange(2 ** bits) * lsb if CT_W is None else np.array([sum(w for k, w in enumerate(CT_W) if (c >> k) & 1) for c in range(2 ** len(CT_W))])
    f, g, b = r["f"], r["g"], r["b"]; m = (f >= 0.5) & (f <= 150)
    best = (0, -1, None)
    for c in cts:
        z = 1 / np.abs(g + 1j * (b + 2 * np.pi * f * c / 2))
        if z[m].min() > best[1]: best = (c, z[m].min(), z)
    c, zmin, z = best
    code = int(np.argmin(abs(cts - c)))
    return dict(code=code, ct=c, zmin=zmin, z=[float(np.interp(x, f, z)) for x in (0.5, 1, 10, 50, 100, 150)])
