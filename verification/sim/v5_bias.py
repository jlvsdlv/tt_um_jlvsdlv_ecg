"""On-chip bias-electrode driver for 3-electrode use (sets the input common mode; no ideal VCM source anymore).
Loop: body --(input electrodes)--> vi1/vi2 --(M1/M2 source)--> tail  -> stage-1 nfet pair compares tail with
      REF = 3/4 VDD (ladder of 4 identical pfet_lvt diodes, each in its own well -> ratio is process-independent)
      -> stage-2 pFET common source -> pin -> C_ext (100 nF, external) + bias electrode -> body.
C_ext makes the pin node the dominant pole (loop UGB ~ few Hz) and holds the body at 50 Hz passively.
Target tail = 0.75 V  =>  VDS(MB2) = 0.25 V, VDS(M1) = 0.75 - vo (0.16-0.23 V) at all corners."""
import numpy as np, re, json, sys
from concurrent.futures import ProcessPoolExecutor
import v5_sim as S, v5_core as C, v4_corner as V, v5_trim as T
from lv import header, run
from amp import dev, load_wrdata
PL, NL = "sky130_fd_pr__pfet_01v8_lvt", "sky130_fd_pr__nfet_01v8_lvt"
LAD, CEXT = (2, 2, 1), 100e-9
NLAD = 7
MODE = dict(fast=True, cc=10e-12, i2m=4)   # fast=True: active DRL (no C_ext, Miller Cc, class-A stage 2 at i2m x 5 nA)
def driver(p):
    s = ""
    nodes = ["vdd"] + [f"r{i}" for i in range(1, NLAD)] + ["vss"]
    for i in range(NLAD):
        s += dev(f"LD{i}", nodes[i + 1], nodes[i + 1], nodes[i], nodes[i], PL, LAD, p)   # pfet diode, body = source (own well); REF = r1 = (NLAD-1)/NLAD VDD
    s += dev("BP", "nd", "nb", "vdd", "vdd", PL, (2, 2, 1), p)                   # 5 nA from the IB mirror
    s += dev("BN", "nd", "nd", "vss", "vss", NL, (2, 8, 1), p)
    s += dev("S1", "s1", "nd", "vss", "vss", NL, (2, 8, 1), p)                    # stage-1 tail 5 nA
    s += dev("A1", "xa", "tsen", "s1", "vss", NL, (2, 4, 1), p)
    s += "Rts tail tsen 1\n"
    s += dev("A2", "x", "r1", "s1", "vss", NL, (2, 4, 1), p)
    s += dev("PA", "xa", "xa", "vdd", "vdd", PL, (4, 2, 1), p)          # low-Vsg mirror: stage-1 headroom with REF 0.86 V
    s += dev("PB", "x", "xa", "vdd", "vdd", PL, (4, 2, 1), p)
    if MODE["fast"]:
        s += dev("P2", "drl", "x", "vdd", "vdd", PL, (4, 2, 1), p)
        s += dev("S2", "drl", "nd", "vss", "vss", NL, (2, 8, MODE["i2m"]), p) + f"Ccm x drl {MODE['cc']}\n"
    else:
        s += dev("P2", "drl", "x", "vdd", "vdd", PL, (1, 2, 1), p)                    # stage 2 (inverting)
        s += dev("S2", "drl", "nd", "vss", "vss", NL, (2, 16, 1), p)                  # ~2.5 nA sink
    return s
def bench(p, Re=10e6, Ce=1e-9, Reb=1e6, Ceb=47e-9, edo=(0.0, 0.0), sig="", mains=0.0, loopbreak=False):
    """body node bd; electrodes Re||Ce from (bd + EDO + signal) to the pads; bias electrode Reb||Ceb from pin to bd."""
    s = (f"Ve1 vs1 bd dc {edo[0]} {sig.replace('AMP', '1')}\nVe2 vs2 bd dc {edo[1]} {sig.replace('AMP', '-1')}\n"
         f"Re1 vs1 vp1 {Re}\nCe1 vs1 vp1 {Ce}\nRe2 vs2 vp2 {Re*1.1}\nCe2 vs2 vp2 {Ce/1.1}\n" + V.PAD +
         f"Rpd drl pin 500\nCpd pin 0 5p\n" + (f"Cx pin 0 {CEXT}\n" if not MODE["fast"] else "") + f"Reb pin bd {Reb}\nCeb pin bd {Ceb}\n"
         "Cbe bd earth 200p\nCde 0 earth 20p\nRe0 earth 0 1e13\n")
    if mains: s += f"Vm mn earth sin(0 {mains} 50)\nCm mn bd 2p\n"
    if loopbreak: s += "*BREAK\n"
    return s + f"Vdd vdd 0 {p['VDD']}\nVss vss 0 0\n"
def core(p, ct):
    return re.sub(r"\.nodeset.*\n", "", C.mk5(None, S.CPF, ct)(p)) + driver(p)
def ns_guess(p):
    ns, _, _ = S.opv(p, C.mk5(None, S.CPF))           # op of the amp alone at the old (ideal) VCM as a starting point
    ns.update(bd=p["VCM"], vp1=p["VCM"], vp2=p["VCM"], vs1=p["VCM"], vs2=p["VCM"], pin=p["VCM"], drl=p["VCM"], **{f'r{i}': 1 - i / NLAD for i in range(1, NLAD)})
    return S.nodeset({k: v for k, v in ns.items() if k not in ("vdd", "vss", "nd", "x", "xa", "s1")})
def op(kt):
    k, t = kt; p = S.P(k, t); ct = CT.get((k, t), 3.38e-12)
    net = header(p) + core(p, ct) + bench(p) + ns_guess(p) + (".control\nop\nprint v(bd) v(tail) v(vo1) v(vo2) v(r1) v(nw1) v(x) v(drl) v(nb) i(vdd)"
          " @m.xs1.msky130_fd_pr__nfet_01v8_lvt[id] @m.xld0.msky130_fd_pr__pfet_01v8_lvt[id]\n.endc\n.end\n")
    o, f = run(net); v = {a: float(b) for a, b in re.findall(r"^(\S+)\s*=\s*([-\d.e+]+)", o, re.M)}
    return k, t, v
def loop(kt):
    k, t = kt; p = S.P(k, t); ct = CT.get((k, t), 3.38e-12)
    c = core(p, ct).replace("Rts tail tsen 1\n", "Lbrk tail tsen 1e12\nCinj tsen inj 1\nVinj inj 0 dc 0 ac 1\n")
    net = header(p) + c + bench(p) + ns_guess(p) + (".control\nac dec 20 1e-4 1e4\nlet T=-v(tail)/v(tsen)\n"
          "wrdata lg.txt mag(T) ph(T)\n.endc\n.end\n")
    o, f = run(net); a = load_wrdata(f["lg.txt"]); fr, m, ph = a[:, 0], a[:, 1], np.degrees(np.unwrap(a[:, 3]))
    i = np.where(m < 1)[0]; i = i[0] if len(i) else len(fr) - 1
    return k, t, dict(dc_dB=20*np.log10(m[0]), ugb=fr[i], pm=180 + ph[i] if ph[i] < 0 else ph[i] - 180 + 180)
CT = {(r["corner"], r["temp"]): r["trim"]["ct"] for r in json.load(open("results/v5_check2.json"))}
if __name__ == "__main__":
    with ProcessPoolExecutor(2) as ex:
        O = list(ex.map(op, T.CORNERS)); L = list(ex.map(loop, T.CORNERS))
    for (k, t, v), (_, _, l) in zip(O, L):
        g = lambda n: v.get(f"v({n})", float("nan"))
        print(f"{k}{t:>3}: body/VCM {g('bd'):.3f}  tail {g('tail'):.3f} (ref {g('r1'):.3f})  vo {g('vo1'):.3f}/{g('vo2'):.3f}  VDS MB2 {1-g('tail'):.3f} M1 {g('tail')-g('vo1'):.3f} | "
              f"I(VDD) {-v.get('i(vdd)', 0)*1e9:.0f} nA, ladder {abs(v.get('@m.xld0.msky130_fd_pr__pfet_01v8_lvt[id]', 0))*1e9:.2f} nA, stage1 {v.get('@m.xs1.msky130_fd_pr__nfet_01v8_lvt[id]', 0)*1e9:.1f} nA | "
              f"loop: DC {l['dc_dB']:.0f} dB, UGB {l['ugb']:.2g} Hz, PM {l['pm']:.0f} deg", flush=True)
    json.dump(dict(op=O, loop=L), open("results/v5_bias_op2.json", "w"), default=float)
