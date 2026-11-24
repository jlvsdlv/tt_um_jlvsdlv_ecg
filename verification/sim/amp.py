"""Netlist generator + ngspice runner for the Sawigun/Thanapitak 2021 DDA ECG IA, ported to sky130.

Topology (paper Fig. 5):
  MB1..MB4 : pMOS wide-swing cascode mirror, 1:20, IB external sink
  M1,M2    : pMOS input pair (gmA), tail = 20*IB from MB3/MB4, body tied to common source
  M3,M4    : nMOS (gmB), sources at VSS, drains = outputs, gates = feedback nodes
  Rf       : diode-connected pMOS pseudo-resistor from output to own gate node
  Cf       : output -> own gate node,  Cg : between the two gate nodes,  CL : between outputs
"""
import os, re, subprocess, tempfile, math
import numpy as np

PDK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdk")
NFET, PFET = "sky130_fd_pr__nfet_01v8", "sky130_fd_pr__pfet_01v8"

# sky130 1v8 bins top out at W=100um -> split wide devices into fingers (m)
DEFAULT = dict(
    VDD=1.8, VCM=0.6, VB=None, IB=16e-9, corner="tt", temp=27,
    # (W_per_finger, L, m)
    M12=(50, 4, 8),      # 400/4
    M34=(40, 20, 4),     # 160/20
    MRF=(1, 4, 1),
    MB12=(3.6, 1.8, 1),
    MB34=(3.6, 1.8, 20), # 72/1.8 as 20 unit fingers
    Cg=20e-12, Cf=0.35e-12, CL=10e-12,
    PT="pfet_01v8", NT="nfet_01v8",   # flavors for M1/M2 and M3/M4
    NCAS=None, CT="nfet_01v8_lvt", VCN=0.42,  # optional nMOS cascode on M3/M4 (geo, flavor, gate bias)
    RT="pfet_01v8", RSER=1,     # pseudo-resistor flavor and number in series
    cpar=0.0,            # bottom-plate parasitic fraction of each MIM cap (to VSS)
    mm=None,             # dict inst -> dict(mm_vth0=..,mm_voff=..,mm_toxe=..,mm_nfactor=..)
    capmm=None,          # dict cap -> relative error
)


def dev(name, d, g, s, b, kind, geo, p):
    W, L, m = geo
    mm = (p.get("mm") or {}).get(name, {})
    extra = " ".join(f"{k}={v:.6g}" for k, v in mm.items())
    # junction geometry per finger (sky130 diff extension ~0.29 um past poly)
    X = 0.29
    jg = f"ad={W*X:.4g} as={W*X:.4g} pd={2*(W+X):.4g} ps={2*(W+X):.4g}"
    return f"X{name} {d} {g} {s} {b} {kind} w={W} l={L} mult={m} m={m} {jg} {extra}\n"


def core(p):
    """Amplifier core as text. Nodes: vdd vss vi1 vi2 vo1 vo2"""
    VB = p["VB"] if p["VB"] is not None else p["VDD"] - 1.0
    cm = p.get("capmm") or {}
    C = lambda k, base: base * (1 + cm.get(k, 0.0))
    s = ""
    s += f"IB nb vss {p['IB']}\n"
    s += f"VBc vb vss {VB}\n"
    # wide-swing cascode: MB1 gate = nb (bottom of MB2), MB2/MB4 gate = VB
    s += dev("MB1", "nb1", "nb", "vdd", "vdd", PFET, p["MB12"], p)
    s += dev("MB2", "nb", "vb", "nb1", "vdd", PFET, p["MB12"], p)
    s += dev("MB3", "nt1", "nb", "vdd", "vdd", PFET, p["MB34"], p)
    s += dev("MB4", "tail", "vb", "nt1", "vdd", PFET, p["MB34"], p)
    # input pair. Vi1 -> M1 -> drain node vo2 (left), Vi2 -> M2 -> vo1 (right)
    PT, NT = "sky130_fd_pr__" + p["PT"], "sky130_fd_pr__" + p["NT"]
    s += dev("M1", "vo2", "vi1", "tail", "tail", PT, p["M12"], p)
    s += dev("M2", "vo1", "vi2", "tail", "tail", PT, p["M12"], p)
    # gmB
    if p["NCAS"]:
        CT = "sky130_fd_pr__" + p["CT"]
        s += f"VCN vcn vss {p['VCN']}\n"
        s += dev("M5", "vo2", "vcn", "d3", "vss", CT, p["NCAS"], p)
        s += dev("M6", "vo1", "vcn", "d4", "vss", CT, p["NCAS"], p)
        s += dev("M3", "d3", "g3", "vss", "vss", NT, p["M34"], p)
        s += dev("M4", "d4", "g4", "vss", "vss", NT, p["M34"], p)
    else:
        s += dev("M3", "vo2", "g3", "vss", "vss", NT, p["M34"], p)
        s += dev("M4", "vo1", "g4", "vss", "vss", NT, p["M34"], p)
    # pseudo resistors: diode-connected pMOS, gate+body on output side
    RT = "sky130_fd_pr__" + p["RT"]
    for side, g, o in (("3", "g3", "vo2"), ("4", "g4", "vo1")):
        n = p["RSER"]
        nodes = [o] + [f"r{side}_{k}" for k in range(1, n)] + [g]
        for k in range(n):
            nm = f"MR{side}" if k == 0 else f"MR{side}{chr(97+k)}"
            a, b = nodes[k], nodes[k+1]
            s += dev(nm, b, a, a, a, RT, p["MRF"], p)
    s += f"Cf3 vo2 g3 {C('Cf3', p['Cf'])}\n"
    s += f"Cf4 vo1 g4 {C('Cf4', p['Cf'])}\n"
    # Cg split in two antiparallel halves so bottom-plate parasitics are symmetric
    s += f"Cga g3 g4 {C('Cga', p['Cg']/2)}\n"
    s += f"Cgb g4 g3 {C('Cgb', p['Cg']/2)}\n"
    s += f"CLa vo1 vo2 {C('CLa', p['CL']/2)}\n"
    s += f"CLb vo2 vo1 {C('CLb', p['CL']/2)}\n"
    if p["cpar"]:
        k = p["cpar"]
        # bottom plate of each half on the first-listed node
        s += f"Cpga g3 vss {k*p['Cg']/2}\nCpgb g4 vss {k*p['Cg']/2}\n"
        s += f"CpLa vo1 vss {k*p['CL']/2}\nCpLb vo2 vss {k*p['CL']/2}\n"
        s += f"Cpf3 vo2 vss {k*p['Cf']}\nCpf4 vo1 vss {k*p['Cf']}\n"
    vd = p["VDD"]
    s += (f".nodeset v(nb)={VB-0.06+0.0} v(nb1)={vd-0.11} v(nt1)={vd-0.11} v(tail)={p['VCM']+0.8} "
          f"v(vo1)=0.42 v(vo2)=0.42 v(g3)=0.42 v(g4)=0.42\n")
    return s


def header(p):
    return (f"* ECG IA sky130\n.include {PDK}/lib_{p['corner']}.spice\n"
            f".temp {p['temp']}\n.option gmin=1e-15 abstol=1e-16 reltol=1e-5 noacct\n")


def run(netlist, timeout=600):
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "x.sp")
        open(f, "w").write(netlist)
        r = subprocess.run(["ngspice", "-b", f], cwd=d, capture_output=True, text=True, timeout=timeout)
        out = r.stdout + r.stderr
        files = {}
        for fn in os.listdir(d):
            if fn.endswith(".txt") or fn.endswith(".csv"):
                files[fn] = open(os.path.join(d, fn)).read()
    return out, files


def P(**kw):
    p = dict(DEFAULT)
    p.update(kw)
    return p


def load_wrdata(txt):
    """wrdata: columns x y x y ... -> array of floats"""
    rows = [l.split() for l in txt.strip().splitlines() if l.strip() and not l.startswith("#")]
    try:
        float(rows[0][0])
    except ValueError:
        rows = rows[1:]
    return np.array(rows, dtype=float)


# ---------------------------------------------------------------- analyses
def _supplies(p, vdd_ac=0, vss_ac=0, vi1_ac="0", vi2_ac="0", vid=0.0):
    return (f"Vdd vdd 0 dc {p['VDD']} ac {vdd_ac}\nVss vss 0 dc 0 ac {vss_ac}\n"
            f"Vi1 vi1 0 dc {p['VCM']+vid/2} ac {vi1_ac}\nVi2 vi2 0 dc {p['VCM']-vid/2} ac {vi2_ac}\n")


def ac_sweep(p, mode="dm", vid=0.0, fstart=1e-4, fstop=1e5, ppd=40):
    """Returns f, complex H for (vo1-vo2) per unit excitation.
    mode: dm (vid ac 1 differential), cm, vdd, vss, zin (returns Vi1/Ii1 with Vi2 ac grounded)"""
    exc = dict(dm=dict(vi1_ac="0.5", vi2_ac="0.5 180"), cm=dict(vi1_ac="1", vi2_ac="1"),
               vdd=dict(vdd_ac=1), vss=dict(vss_ac=1), zin=dict(vi1_ac="1"),
               zind=dict(vi1_ac="0.5", vi2_ac="0.5 180"))[mode]
    net = header(p) + core(p) + _supplies(p, vid=vid, **exc)
    if mode in ("zin", "zind"):
        sig = "let h = 1/(-i(vi1))" if mode == "zin" else "let h = 1/(-i(vi1))"
    else:
        sig = "let h = v(vo1)-v(vo2)"
    net += (f".control\nac dec {ppd} {fstart} {fstop}\n{sig}\nlet hr=real(h)\nlet hi=imag(h)\n"
            f"wrdata ac.txt hr hi\n.endc\n.end\n")
    out, f = run(net)
    if "ac.txt" not in f:
        raise RuntimeError(out[-2000:])
    a = load_wrdata(f["ac.txt"])
    return a[:, 0], a[:, 1] + 1j * a[:, 3]


def band(f, H):
    g = abs(H)
    k = np.argmax(g)
    kmid = g[k]
    th = kmid / np.sqrt(2)
    lo = np.where(g[:k] < th)[0]
    hi = np.where(g[k:] < th)[0]
    def interp(i0, i1):
        x0, x1 = np.log(f[i0]), np.log(f[i1]); y0, y1 = g[i0], g[i1]
        return float(np.exp(x0 + (th - y0) * (x1 - x0) / (y1 - y0)))
    fH = interp(lo[-1], lo[-1] + 1) if len(lo) else float("nan")
    fL = interp(k + hi[0] - 1, k + hi[0]) if len(hi) else float("nan")
    return kmid, fH, fL   # NB paper naming: fH = highpass corner, fL = lowpass corner


def rpseudo(p, vid=0.0):
    """Small-signal resistance of each pseudo-resistor chain at the op (gate tied to source -> sum of 1/gds)."""
    t = p["RT"]
    names = {"3": ["mr3"] + [f"mr3{chr(97+k)}" for k in range(1, p["RSER"])],
             "4": ["mr4"] + [f"mr4{chr(97+k)}" for k in range(1, p["RSER"])]}
    pr = "".join(f"print @m.x{n}.msky130_fd_pr__{t}[gds] @m.x{n}.msky130_fd_pr__{t}[gbd]\n" for side in "34" for n in names[side])
    net = header(p) + core(p) + _supplies(p, vid=vid) + ".control\nop\n" + pr + ".endc\n.end\n"
    out, _ = run(net)
    g = {}
    for l in out.splitlines():
        m_ = re.match(r"@m\.x(mr\w+)\.\S+\[(gds|gbd)\]\s*=\s*(\S+)", l.strip())
        if m_: g[m_.group(1)] = g.get(m_.group(1), 0.0) + float(m_.group(3))   # channel || drain-body junction
    return sum(1 / g[n] for n in names["3"]), sum(1 / g[n] for n in names["4"])


def noise(p, fstart=0.01, fstop=1e4, ppd=40, vid=0.0):
    """Output noise PSD of v(vo1,vo2) and DM gain on the same grid -> input-referred PSD (V^2/Hz).
    ngspice's noise analysis mis-solves with the zero-bias pMOS pseudo-resistors, so they are replaced by
    linear resistors of their extracted small-signal value (exact for a MOS at Vds=0: 4kT*gds)."""
    r3, r4 = rpseudo(p, vid)
    c = core(p)
    c = re.sub(r"XMR3 .*\n", f"RR3 g3 vo2 {r3:.6g}\n", c)
    c = re.sub(r"XMR4 .*\n", f"RR4 g4 vo1 {r4:.6g}\n", c)
    c = re.sub(r"XMR[34][a-z] .*\n", "", c)
    net = header(p) + c + _supplies(p, vid=vid, vi1_ac="0.5", vi2_ac="0.5 180")
    net += (f".control\nnoise v(vo1,vo2) Vi1 dec {ppd} {fstart} {fstop}\nsetplot noise1\n"
            f"let on2 = onoise_spectrum^2\nwrdata no.txt on2\nsetplot const\n"
            f"ac dec {ppd} {fstart} {fstop}\nlet h=v(vo1)-v(vo2)\nlet hm = mag(h)\nwrdata ac.txt hm\n"
            f".endc\n.end\n")
    out, f = run(net)
    if "no.txt" not in f:
        raise RuntimeError(out[-2000:])
    a = load_wrdata(f["no.txt"]); b = load_wrdata(f["ac.txt"])
    fr = a[:, 0]; on2 = a[:, 1]; g = np.interp(fr, b[:, 0], b[:, 1])
    return fr, on2, on2 / g**2


def integ(f, psd, f1, f2):
    m = (f >= f1) & (f <= f2)
    return float(np.sqrt(np.trapezoid(psd[m], f[m])))


def nef(vrms, itot, bw, T=300.15):
    k, q = 1.380649e-23, 1.602176634e-19
    UT = k * T / q
    return vrms * np.sqrt(2 * itot / (np.pi * UT * 4 * k * T * bw))   # Steyaert NEF


def multi_ac(p, vid=0.0, fstart=1e-4, fstop=1e4, ppd=20, fpts=(50,)):
    """One ngspice run: DM, CM, VDD, VSS transfer (vo1-vo2) + op current. Returns dict of arrays."""
    net = header(p) + core(p) + _supplies(p, vid=vid, vi1_ac="0.5", vi2_ac="0.5 180")
    sw = f"ac dec {ppd} {fstart} {fstop}"
    net += f""".control
op
let idd = -i(vdd)
print idd
{sw}
let h=v(vo1)-v(vo2)
wrdata dm.txt real(h) imag(h)
alter @vi1[acmag]=1
alter @vi2[acmag]=1
alter @vi2[acphase]=0
{sw}
let h=v(vo1)-v(vo2)
wrdata cm.txt real(h) imag(h)
alter @vi1[acmag]=0
alter @vi2[acmag]=0
alter @vdd[acmag]=1
{sw}
let h=v(vo1)-v(vo2)
wrdata vdd.txt real(h) imag(h)
alter @vdd[acmag]=0
alter @vss[acmag]=1
{sw}
let h=v(vo1)-v(vo2)
wrdata vss.txt real(h) imag(h)
.endc
.end
"""
    out, f = run(net)
    r = {}
    for k in ("dm", "cm", "vdd", "vss"):
        if k + ".txt" not in f:
            raise RuntimeError(out[-1500:])
        a = load_wrdata(f[k + ".txt"]); r["f"] = a[:, 0]; r[k] = a[:, 1] + 1j * a[:, 3]
    r["idd"] = [float(l.split("=")[1]) for l in out.splitlines() if l.strip().startswith("idd")][0]
    return r


MMKEYS = ("mm_vth0", "mm_voff", "mm_toxe", "mm_nfactor")
MMDEV = ("MB1", "MB2", "MB3", "MB4", "M1", "M2", "M3", "M4", "M5", "M6", "MR3", "MR4")
CAPSIG = dict(Cf3=0.005, Cf4=0.005, Cga=0.001, Cgb=0.001, CLa=0.002, CLb=0.002)   # assumed MIM matching (1 sigma)


def draw_mismatch(rng):
    mm = {d: {k: float(rng.standard_normal()) for k in MMKEYS} for d in MMDEV}
    cm = {k: float(rng.standard_normal() * s) for k, s in CAPSIG.items()}
    return mm, cm
