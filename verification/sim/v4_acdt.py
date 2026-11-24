"""AC-coupled DTMOS input pair: well node nwX coupled to gate by Cbc, DC-tied to tail by a pseudo-R (ideal 10 TOhm here),
plus n-well-to-substrate cap Cnw; positive capacitive feedback Cpf vo->vi. Reports Zin, noise (incl. body-R noise), gain."""
import numpy as np, json, re
from concurrent.futures import ProcessPoolExecutor
import noisebias as nb, lv
from lv import header, sup, run, op
from amp import load_wrdata
from lvac import K
from trapmodel import reduction
pt = json.load(open("results/v2_point.json")); BETA = json.load(open("results/trapapply.json"))["beta_han"]
R7 = reduction(nb.FR, 7e3, 1, D=0.5, beta=BETA)
orig_core = lv.core
CNW = 1.5e-12; RB = 1e13
def mk(cbc, cpf):
    def core_ac(p):
        c = orig_core(p)
        c = re.sub(r"(XM1 vo2 vi1 tail) vi1", r"\1 nw1", c); c = re.sub(r"(XM2 vo1 vi2 tail) vi2", r"\1 nw2", c)
        c += f"Cbc1 vi1 nw1 {cbc}\nCbc2 vi2 nw2 {cbc}\nRb1 nw1 tail {RB}\nRb2 nw2 tail {RB}\nCnw1 nw1 0 {CNW}\nCnw2 nw2 0 {CNW}\n"
        if cpf > 0: c += f"Cpf1 vo1 vi1 {cpf}\nCpf2 vo2 vi2 {cpf}\n"
        return c
    return core_ac
FQ = (0.5, 1, 10, 50, 100, 150)
def evaluate(args):
    cbc, cpf = args
    cfn = mk(cbc, cpf); lv.core = cfn; nb.core = cfn
    best = None
    for vcm in np.arange(0.4, 0.85, 0.02):
        p = nb.params(1e-6, pt["VDD"], vcm); p.update(VBN=pt["VBN"], Cf=pt["Cf"], CLEXT=pt["CLEXT"], M12=tuple(pt["M12"]), M34=tuple(pt["M34"]))
        try: d = op(p)
        except Exception: continue
        if min(abs(d['MB2']['vds']), abs(d['M1']['vds']), d['M3']['vds']) < nb.VMIN: continue
        if best is None or d['A0'] > best[1]['A0']: best = (vcm, d, p)
    vcm, d, p = best
    lo, hi = 0.02e-12, 3e-12
    for _ in range(13):
        mid = (lo * hi) ** 0.5; p["Cf"] = mid; k = 20 * np.log10(K(p)[0])
        if k > 37: lo = mid
        else: hi = mid
    k, fH, fL = K(p)
    s = nb.spectra(p); F = nb.FR; I = lambda x: float(np.trapezoid(x, F))
    st = np.sqrt(I(s["tot"])) * 1e6; sw = np.sqrt(I(s["tot"] - s["f34"] + R7 * s["f34"])) * 1e6
    res = {}
    for mode, a1, a2 in (("dm", "0.5", "0.5 180"), ("cm", "1", "1")):
        net = header(p) + cfn(p) + sup(p, vi1_ac=a1, vi2_ac=a2) + (".control\nop\nprint -i(vi1)\nac dec 20 0.1 1e4\nlet y1=-i(vi1)/v(vi1)\n"
              "let zd=(v(vi1)-v(vi2))/(-i(vi1))\nlet zc=v(vi1)/(-i(vi1)-i(vi2))\nwrdata z.txt mag(zd) mag(zc) real(y1)\n.endc\n.end\n")
        o, f = run(net); a = load_wrdata(f["z.txt"]); fr = a[:, 0]
        res[mode] = a[:, 1 if mode == "dm" else 3]
        if mode == "dm": gre = a[:, 5]; iin = [float(l.split("=")[1]) for l in o.splitlines() if "i(vi1)" in l][0]
    band = (fr >= 0.5) & (fr <= 150)
    return dict(cbc=cbc, cpf=cpf, vcm=float(vcm), A0=d["A0"], gain=20*np.log10(k), fL=fL, Cf=p["Cf"], static=st, sw=sw, iin=iin,
                dm=[np.interp(x, fr, res["dm"]) / 1e9 for x in FQ], cm=[np.interp(x, fr, res["cm"]) / 1e9 for x in FQ],
                dmmin=res["dm"][band].min() / 1e9, cmmin=res["cm"][band].min() / 1e9, neg=bool((gre[(fr > 0.1) & (fr < 1e4)] < 0).any()))
if __name__ == "__main__":
    jobs = [(10e-12, 0.0), (5e-12, 0.0), (10e-12, 0.3e-12), (10e-12, 0.4e-12), (10e-12, 0.5e-12), (5e-12, 0.4e-12)]
    with ProcessPoolExecutor(2) as ex: R = list(ex.map(evaluate, jobs))
    for r in R:
        print(f"Cbc {r['cbc']*1e12:4.1f}p Cpf {r['cpf']*1e12:4.2f}p: A0 {r['A0']:.0f}  Iin {r['iin']*1e12:6.2f} pA | IRN static {r['static']:.2f} / switched {r['sw']:.2f} uV | "
              f"Zin DM " + "/".join(f"{x:.2g}" for x in r['dm']) + f" (min {r['dmmin']:.2g}) | CM " + "/".join(f"{x:.2g}" for x in r['cm']) + f" (min {r['cmmin']:.2g}) GOhm | neg Re(Y): {r['neg']}")
    json.dump(R, open("results/v4_acdt.json", "w"))
    print("(Zin at " + "/".join(str(x) for x in FQ) + " Hz)")
