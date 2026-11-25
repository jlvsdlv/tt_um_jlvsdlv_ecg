"""Check #1/#2: simulate the GDS-extracted chip netlist (flat, with parasitic C) with the same bench as the schematic
transient, starting from 0 V supplies (power-up, on-chip reference start-up, reset release at a signal zero crossing)."""
import re, json, sys, numpy as np
import v5_sim as S, v5_bias as B, v5_tranfinal as TF
from lv import header, run
from amp import load_wrdata
X = "/home/claude/lay5/simx/"
M = json.load(open(X + "nodemap.json"))
PIN = {"ua[0]": "vi1", "ua[1]": "vi2", "ua[2]": "vo1", "ua[3]": "vo2", "ua[4]": "drl", "ua[5]": "vdd", "VGND": "0"}
CPA = {("tt", 27): (6.31, 7.07), ("ss", 0): (4.03, 5.32), ("ff", 60): (7.80, 8.18), ("sf", 27): (4.03, 5.32), ("fs", 27): (7.80, 8.18)}   # fF/um2 at Vgw 0.38 / 0.45
POST = {(r["corner"], r["temp"]): r for r in json.load(open("results/v5_post_x1_cpf820.json"))}
def chip(k, t):
    cb, ct = CPA[(k, t)]
    out = []
    for l in open(X + "chip_pex.spice"):
        if not l.strip() or l.startswith("*"): continue
        l = l.split(";")[0].rstrip()
        tok = l.split()
        if tok[0].startswith("C") and "XMCLb/B" in tok[1:3]:      # magic names the substrate after p-well island B: parasitic C to substrate -> ground
            tok = [("0" if x == "XMCLb/B" else x) for x in tok]
        tok = [PIN.get(x, M.get(x, x)) for x in tok]
        tok = [re.sub(r"[\[\]/]", "_", x) if "=" not in x and not x.startswith("sky130") else x for x in tok]
        if "sky130_fd_pr__cap_var_lvt" in tok:
            w = float(re.search(r"w=([\d.]+)", l).group(1)); L_ = float(re.search(r"l=([\d.]+)", l).group(1))
            cpa = cb if (w, L_) == (10.0, 8.0) else ct          # Cbc fingers: gate nw (~tail) vs well vi; Ct bits: gate vi vs well ct (~0)
            out.append(f"C{tok[0]} {tok[1]} {tok[2]} {w*L_*cpa*1e-15:.5g}"); continue
        if any(m_ in l for m_ in ("nfet_01v8", "pfet_01v8")):      # magic lumps a shared node's junction onto one device: use per-device geometry instead
            w = float(re.search(r" w=([\d.]+)", l).group(1))
            tok = [x for x in tok if not re.match(r"(ad|as|pd|ps)=", x)] + [f"ad={0.29*w:.4g}", f"as={0.29*w:.4g}", f"pd={2*(w+0.29):.4g}", f"ps={2*(w+0.29):.4g}"]
        if tok[0].startswith("X") and "sky130_fd_pr__" in l and not tok[0].startswith("XX"):
            tok[0] = "X" + tok[0]
        out.append(" ".join(tok))
    return "\n".join(out) + "\n"
def build(k, t, vidpp=4e-3, mains=325, tst=0.075, tsk=0.048, trst=1/37, code=None, itc=(1, 0)):
    p = S.P(k, t)
    if code is None:
        W = [11.3e-15, 22.6e-15, 45.2e-15, 90.5e-15, 181.0e-15, 362.0e-15, 307.0e-15, 611.7e-15, 1219.1e-15, 2438.2e-15]
        cts = [sum(w for i, w in enumerate(W) if (c >> i) & 1) for c in range(1024)]
        code = min(range(1024), key=lambda c: abs(cts[c] - POST[(k, t)]["ct"]))
    a = vidpp / 4
    b = B.bench(p, 10e6, 1e-9, 10e6, 1e-9, sig=f"sin(0 {a} {TF.F0})", mains=mains).replace(f"Ve2 vs2 bd dc 0.0 sin(0 {a} {TF.F0})", f"Ve2 vs2 bd dc 0.0 sin(0 {-a} {TF.F0})")
    b = b.replace(f"Vdd vdd 0 {p['VDD']}\n", f"Vdd vddp 0 pwl(0 0 100u {p['VDD']})\nRsw vddp vdd 500\nCpad vddp 0 5p\n").replace("Vss vss 0 0\n", "")
    H = "1.8"
    dig = f"Vdp VDPWR 0 pwl(0 0 100u {H})\n"
    bits = [(code >> i) & 1 for i in range(10)]
    for i in range(8): dig += f"Vui{i} ui_in_{i}_ 0 {H if bits[i] else 0}\n"
    dig += f"Vb8 uio_in_0_ 0 {H if bits[8] else 0}\nVb9 uio_in_1_ 0 {H if bits[9] else 0}\nVen uio_in_2_ 0 {H}\n"
    dig += f"Vrst uio_in_3_ 0 pwl(0 0 100u {H} {trst} {H} {trst+1e-5} 0)\nVit0 uio_in_4_ 0 {H if itc[0] else 0}\nVit1 uio_in_5_ 0 {H if itc[1] else 0}\n"
    dig += f"Vclk clk 0 pulse(0 {H} 0 1u 1u {0.5/TF.FS-1e-6} {1/TF.FS})\n"
    dig += "Cpwa vbna vdd 0.6p\nCpwb vbnb vdd 0.6p\nRlka vbna 0 1e12\nRlkb vbnb 0 1e12\n"
    hdr = header(p).replace(".temp", ".include /home/claude/amp/pdk/passives_ext.spice\n.temp").replace("reltol=1e-5", "reltol=1e-4 method=gear itl4=200").replace("abstol=1e-17", "abstol=1e-15")
    return hdr + chip(k, t) + b + dig + (
        f".control\ntran 2u {tst} 0 2u uic\nmeas tran qdp integ i(vdp) from={tsk} to={tst}\nmeas tran qdd integ i(vdd) from={tsk} to={tst}\n"
        "linearize\nlet vod=v(vo1)-v(vo2)\nlet vic=(v(vp1)+v(vp2))/2\nlet vpd=v(vp1)-v(vp2)\n"
        "wrdata tf.txt vod vic vpd v(tail) v(vo1) v(g3) v(vbna) v(vbnb) i(vdd) v(n1) v(nb) v(bd)\n.endc\n.end\n")
def job(a):
    k, t = a; tst, tsk = 0.075, 0.048
    o, f = run(build(k, t, tst=tst, tsk=tsk), timeout=14000)
    if "tf.txt" not in f: return k, t, None, o[-1500:]
    x = load_wrdata(f["tf.txt"]); tt = x[:, 0]
    np.save(f"results/chip_tran_{k}{t}.npy", x)
    m = tt >= tsk; T_ = tt[m]
    vod, vic, tail, vo1, g3, wa, wb, idd = (x[m, i] for i in (1, 3, 7, 9, 11, 13, 15, 17))
    qm = {kk: float(v) for kk, v in re.findall(r"^(qd[pd])\s*=\s*([-\d.eE+]+)", o, re.M)}
    def amp(y, fq):
        fr = [fq] + [h * TF.F0 for h in (1, 2, 3) if abs(h * TF.F0 - fq) > 1e-6] + ([50.0] if abs(fq - 50) > 1e-6 else [])
        A = np.vstack([g(2*np.pi*q*T_) for q in fr for g in (np.sin, np.cos)] + [np.ones_like(T_), T_]).T
        c = np.linalg.lstsq(A, y, rcond=None)[0]; return np.hypot(c[0], c[1])
    a1 = amp(vod, TF.F0); g = a1 / 2e-3
    r = dict(gain_dB=20*np.log10(g), thd=100*np.hypot(amp(vod, 2*TF.F0), amp(vod, 3*TF.F0))/a1, in50_uVpp=2*amp(vod, 50.0)/g*1e6, ripple_out_uV=amp(vod, TF.FS)*1e6,
             vic=vic.mean(), tail=tail.mean(), vo1=vo1.mean(), g3=g3.mean(), wa=(wa.min(), wa.max()), wb=(wb.min(), wb.max()),
             idd_nA=-qm.get("qdd", 0)/(tst-tsk)*1e9, idp_nA=-qm.get("qdp", 0)/(tst-tsk)*1e9)
    return k, t, r, ""
if __name__ == "__main__":
    if sys.argv[1] == "net": open("results/chip_tt27.cir", "w").write(build("tt", 27)); sys.exit()
    k, t = sys.argv[1], int(sys.argv[2])
    k, t, r, err = job((k, t))
    print(k, t, json.dumps(r, default=float) if r else "FAILED " + err, flush=True)
