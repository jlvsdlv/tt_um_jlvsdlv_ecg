"""v5 full transient: v4 transient bench (2-phase bulk-switched loads, TT pad path, electrode models) on the v5 core:
Cbc 20 pF + replica pseudo-R well bias, Cg/Cf x3, min-width Rf, Cpf 0.58 pF fixed + Ct trim (tt27 code), CL/2."""
import numpy as np, json, re, sys
from concurrent.futures import ProcessPoolExecutor
import v4_tran as B, v5_sim as S, v5_core as C
from lv import header
CT = json.load(open("results/v5_check2.json"))[0]["trim"]["ct"]       # tt27 trim code
def build(fs, en, Re, Ce):
    p = S.P("tt", 27); B.VCM = p["VCM"]
    c = re.sub(r"\.nodeset.*\n", "", C.mk5(None, S.CPF, CT)(p))
    R = 1 / (2 * np.pi * 0.5 * p["Cf"])
    c = re.sub(r"XMR3s0 .*\n", f"RR3 g3 vo2 {R:.4g}\nSF3 g3 vo2 fst 0 swf\n", c); c = re.sub(r"XMR4s0 .*\n", f"RR4 g4 vo1 {R:.4g}\nSF4 g4 vo1 fst 0 swf\n", c)
    c += "SB1 nw1 tail fst 0 swf\nSB2 nw2 tail fst 0 swf\n"
    c += f"Vfst fst 0 pwl(0 1 {B.TSET} 1 {B.TSET+1e-4} 0)\n.model swf sw vt=0.5 vh=0.05 ron=1e8 roff=1e16\n"
    c = B.T2.split_loads(c, p); drv = B.T2.driver(p, 5e-12, en, fs)
    src = (f"Vs1 vs1 0 dc {p['VCM']} sin({p['VCM']} {B.AMP/2} {B.F0})\nVs2 vs2 0 dc {p['VCM']} sin({p['VCM']} {-B.AMP/2} {B.F0})\n"
           f"Re1 vs1 vp1 {Re}\nCe1 vs1 vp1 {Ce}\nRe2 vs2 vp2 {Re}\nCe2 vs2 vp2 {Ce}\n"
           "Rin1 vp1 vi1 500\nCip1 vp1 0 5p\nRil1 vp1 0 1e12\nRin2 vp2 vi2 500\nCip2 vp2 0 5p\nRil2 vp2 0 1e12\n")
    hdr = header(p).replace("reltol=1e-5", "reltol=1e-4 method=gear itl4=200").replace("abstol=1e-17", "abstol=1e-15")
    return hdr + c + drv + src + (f"Vdd vdd 0 {p['VDD']}\nVss vss 0 0\n.nodeset v(vbna)=0.03 v(vgr)={p['VCM']-0.2:.3f}\n.ic v(vbnb)=-1.38\n"
        f".control\ntran 0.5u {B.TSTOP} 0 0.5u\nmeas tran qdp integ i(vdp) from={B.TSKIP} to={B.TSTOP}\nmeas tran qdd integ i(vdd) from={B.TSKIP} to={B.TSTOP}\n"
        "linearize\nlet vod=v(pd1)-v(pd2)\nlet voc=(v(pd1)+v(pd2))/2\nlet vpd=v(vp1)-v(vp2)\nlet vpc=(v(vp1)+v(vp2))/2\n"
        "wrdata tt.txt vod voc vpd vpc\n.endc\n.end\n")
B.build = build
if __name__ == "__main__":
    jobs = [("wet 1M||47n, sw 2 kHz", 2000.0, 1, 1e6, 47e-9), ("dry 10M||1n, sw 2 kHz", 2000.0, 1, 10e6, 1e-9),
            ("dry 20M||0.5n, sw 2 kHz", 2000.0, 1, 20e6, 0.5e-9), ("dry 50M||0.2n, sw 2 kHz", 2000.0, 1, 50e6, 0.2e-9)]
    res = []
    with ProcessPoolExecutor(2) as ex:
        for tag, r, err in ex.map(B.tran, jobs):
            if r is None: print(tag, "FAILED", err[:400], flush=True); continue
            res.append((tag, r))
            print(f"{tag:26s}: gain(src->out) {r['gain_dB']:.2f} dB THD {r['thd']:.2f}% | out ripple {r['ripple_out_uV']:.1f} uV | kick at electrode diff {r['kick_diff_uV']:.2f} / CM {r['kick_cm_uV']:.1f} uV | "
                  f"residual 1st/2nd half {r['res_rms_first']:.0f}/{r['res_rms_second']:.0f} uV | I(VDD) {r['idd_nA']:.0f} nA, driver {r['idp_nA']:.1f} nA", flush=True)
    json.dump(res, open("results/v5_tran.json", "w"))
