"""Low-voltage (0.25-0.3 V) variant of the DDA ECG IA.
- simple 2-transistor pMOS mirror MB1 (diode) / MB2 (tail), optional DTMOS on both
- M1/M2: pMOS DTMOS (body = gate = input)
- M3/M4: nMOS in deep n-well with static forward body bias, body = VBN
- Rf pseudo-resistors, Cf, Cg, CL as before. No cascodes.
"""
import re, numpy as np
from amp import dev, run, load_wrdata, band, integ, PDK

LV = dict(VDD=0.3, VCM=0.0, IB=1e-9, VBN=None, corner="tt", temp=27,
          PT="pfet_01v8_lvt", NT="nfet_01v8_lvt", BT="pfet_01v8_lvt", DTB=False,
          M12=(50, 2, 16), M34=(40, 8, 4), MB1=(3.6, 1.8, 1), MB2=(3.6, 1.8, 20),
          MRF=(1, 4, 1), RT="pfet_01v8",
          Cg=20e-12, Cf=1.3e-12, CL=10e-12, mm=None,
          VBNGEN=None)   # None: ideal VBN source; else (type,W,L,m,'n'|'p') diode from VDD to vbn


def LP(**kw):
    p = dict(LV); p.update(kw)
    if p["VBN"] is None: p["VBN"] = p["VDD"]
    return p


def core(p):
    f = lambda t: "sky130_fd_pr__" + t
    s = f"IB nb vss {p['IB']}\n"
    if p.get("VBNGEN"):
        t,W,L,m,kind = p["VBNGEN"]
        if kind=="p": s += dev("MVG","vbn","vbn","vdd","vdd","sky130_fd_pr__"+t,(W,L,m),p)
        else:         s += dev("MVG","vdd","vdd","vbn","vss","sky130_fd_pr__"+t,(W,L,m),p)
        s += "VBN vbnx vss 0\n"
    else:
        s += f"VBN vbn vss {p['VBN']}\n"
    bb = "nb" if p["DTB"] else "vdd"
    s += dev("MB1", "nb", "nb", "vdd", bb, f(p["BT"]), p["MB1"], p)
    s += dev("MB2", "tail", "nb", "vdd", bb, f(p["BT"]), p["MB2"], p)
    s += dev("M1", "vo2", "vi1", "tail", "vi1", f(p["PT"]), p["M12"], p)
    s += dev("M2", "vo1", "vi2", "tail", "vi2", f(p["PT"]), p["M12"], p)
    s += dev("M3", "vo2", "g3", "vss", "vbn", f(p["NT"]), p["M34"], p)
    s += dev("M4", "vo1", "g4", "vss", "vbn", f(p["NT"]), p["M34"], p)
    s += dev("MR3", "g3", "vo2", "vo2", "vo2", f(p["RT"]), p["MRF"], p)
    s += dev("MR4", "g4", "vo1", "vo1", "vo1", f(p["RT"]), p["MRF"], p)
    s += f"Cf3 vo2 g3 {p['Cf']}\nCf4 vo1 g4 {p['Cf']}\n"
    s += f"Cga g3 g4 {p['Cg']/2}\nCgb g4 g3 {p['Cg']/2}\n"
    if p.get("CLEXT") is not None:      # outputs straight to pads: TT analog switch + pad + external cap to ground
        s += (f"Rtg1 vo1 pd1 500\nCpd1 pd1 0 5p\nCx1 pd1 0 {p['CLEXT']}\nRld1 pd1 0 {p.get('RLOAD', 1e12)}\n"
              f"Rtg2 vo2 pd2 500\nCpd2 pd2 0 5p\nCx2 pd2 0 {p['CLEXT']}\nRld2 pd2 0 {p.get('RLOAD', 1e12)}\n")
    else:
        s += f"CLa vo1 vo2 {p['CL']/2}\nCLb vo2 vo1 {p['CL']/2}\n"
    v = p["VDD"]
    s += f".nodeset v(nb)={v*0.4} v(tail)={v*0.65} v(vo1)={v*0.3} v(vo2)={v*0.3} v(g3)={v*0.3} v(g4)={v*0.3}\n"
    return s


def header(p):
    return (f"* LV ECG IA\n.include {PDK}/lib_{p['corner']}.spice\n.temp {p['temp']}\n"
            ".option gmin=1e-15 abstol=1e-17 reltol=1e-5 noacct\n")


def sup(p, vid=0.0, vdd_ac=0, vi1_ac="0", vi2_ac="0", vcm_ac=False):
    return (f"Vdd vdd 0 dc {p['VDD']} ac {vdd_ac}\nVss vss 0 0\n"
            f"Vi1 vi1 0 dc {p['VCM']+vid/2} ac {vi1_ac}\nVi2 vi2 0 dc {p['VCM']-vid/2} ac {vi2_ac}\n")


def op(p):
    t = lambda n, ty: f"@m.x{n}.msky130_fd_pr__{ty}"
    pr = ""
    for n, ty in (("m1", p["PT"]), ("m3", p["NT"]), ("mb2", p["BT"]), ("mb1", p["BT"])):
        b = t(n, ty)
        pr += f"print {b}[id] {b}[gm] {b}[gmbs] {b}[gds] {b}[vgs] {b}[vds]\n"
    net = header(p) + core(p) + sup(p) + (".control\nop\nlet idd=-i(vdd)\nlet ivbn=-i(vbn)\nlet iin=-i(vi1)\n"
                                         "print idd ivbn iin v(nb) v(tail) v(vo1) v(vo2) v(g3)\n" + pr + ".endc\n.end\n")
    out, _ = run(net)
    d = {}
    for l in out.splitlines():
        m_ = re.match(r"@m\.x(\w+)\.\S+\[(\w+)\]\s*=\s*(\S+)", l.strip())
        if m_: d.setdefault(m_.group(1).upper(), {})[m_.group(2)] = float(m_.group(3))
        m2 = re.match(r"(idd|ivbn|iin|v\(\w+\))\s*=\s*(\S+)", l.strip())
        if m2: d[m2.group(1)] = float(m2.group(2))
    if "idd" not in d:
        raise RuntimeError(out[-1500:])
    # derived
    M1, M3 = d["M1"], d["M3"]
    gmA = M1["gm"] + abs(M1.get("gmbs", 0))      # DTMOS: body moves with gate
    gmB = M3["gm"]
    d["gmA"], d["gmB"] = gmA, gmB
    d["A0"] = gmA / (M1["gds"] + M3["gds"])
    d["Kdc_est"] = gmA / gmB
    return d


def ac(p, mode="dm", vid=0.0, fstart=1e-3, fstop=1e5, ppd=20):
    exc = dict(dm=dict(vi1_ac="0.5", vi2_ac="0.5 180"), cm=dict(vi1_ac="1", vi2_ac="1"), vdd=dict(vdd_ac=1))[mode]
    net = header(p) + core(p) + sup(p, vid=vid, **exc)
    net += (f".control\nac dec {ppd} {fstart} {fstop}\nlet h=v(vo1)-v(vo2)\nlet hr=real(h)\nlet hi=imag(h)\n"
            f"wrdata ac.txt hr hi\n.endc\n.end\n")
    out, fl = run(net)
    if "ac.txt" not in fl: raise RuntimeError(out[-1500:])
    a = load_wrdata(fl["ac.txt"]); return a[:, 0], a[:, 1] + 1j * a[:, 3]


def transfer(p, span=0.15):
    net = header(p) + core(p) + sup(p).replace(f"Vi2 vi2 0 dc {p['VCM']} ac 0", f"Bi2 vi2 0 V={2*p['VCM']}-v(vi1)")
    net += f".control\ndc Vi1 {p['VCM']-span/2} {p['VCM']+span/2} 0.001\nlet vid=v(vi1)-v(vi2)\nlet vod=v(vo1)-v(vo2)\nwrdata tr.txt vid vod\n.endc\n.end\n"
    out, fl = run(net)
    a = load_wrdata(fl["tr.txt"]); return a[:, 1], a[:, 3]
