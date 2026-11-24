"""v5 core = v4 (AC-DTMOS + Cpf) with:
 - Cbc 20 pF (was 5 pF)
 - DTMOS well bias: replica-biased linear pseudo-R (4 series pfet_01v8 2/20 per side, gates at vgr) instead of ideal 10 TOhm;
   replica pfet_01v8 10/1 x48 diode from tail, sunk by IRB = 0.5 nA  ->  R ~ 300-410 GOhm over PVT
 - optional input-node trim Ct (each vi to gnd)
Importing this module monkey-patches v4_acdt.mk so all v4/v5 scripts pick it up."""
import re
import v4_acdt as A
from amp import dev
CBC, IRB, MRG, NS, REP = 20e-12, 0.5e-9, (2, 20, 1), 4, (10, 1, 48)
CT = 0.0
VARCAP = dict(on=False, w=10, l=2, n=170)   # Cbc as accumulation varactor: poly gate on nw (higher), n-well on vi
def varcap(s, p):
    """replace ideal Cbc by sky130_fd_pr__cap_var_lvt (gate = nw, well = vi) + n-well bottom-plate cap at vi"""
    if not VARCAP["on"]: return s
    w, l, n = VARCAP["w"], VARCAP["l"], VARCAP["n"]
    a = w * l * n
    for i in (1, 2):
        s = re.sub(rf"Cbc{i} vi{i} nw{i} \S+\n", f"XCbc{i} nw{i} vi{i} 0 sky130_fd_pr__cap_var_lvt w={w} l={l} vm={n}\nCjw{i} vi{i} 0 {a*1.4*0.08e-15:.4g}\n", s)
    return s
NF = 1          # feedback pseudo-R Rf (MR3/MR4): NF diode-connected devices in series (was 1)
def stack(s, rlin=None):
    """MR3: g3 <- vo2, MR4: g4 <- vo1. Replace by NF series diode-connected devices, or by a linear resistor rlin (noise runs)."""
    for n, (d, top) in (("3", ("g3", "vo2")), ("4", ("g4", "vo1"))):
        m = re.search(rf"XMR{n} (\S+) (\S+) (\S+) (\S+) (\S+) (.*)\n", s)
        if not m: continue
        if rlin is not None: rep = f"RR{n} {d} {top} {rlin:.6g}\n"
        else:
            nodes = [d] + [f"xf{n}{i}" for i in range(NF - 1)] + [top]
            rep = "".join(f"XMR{n}s{i} {nodes[i]} {nodes[i+1]} {nodes[i+1]} {nodes[i+1]} {m.group(5)} {m.group(6)}\n" for i in range(NF))
        s = s[:m.start()] + rep + s[m.end():]
    return s
_orig = A.mk
P = "sky130_fd_pr__pfet_01v8"
def mk5(cbc=None, cpf=0.58e-12, ct=None):
    base = _orig(CBC, cpf); ct = CT if ct is None else ct
    def c(p):
        s = varcap(stack(base(p)), p)
        s = re.sub(r"Rb[12] nw[12] tail \S+\n", "", s)
        s += dev("MREP", "vgr", "vgr", "tail", "tail", P, REP, p) + f"IRB vgr vss {IRB}\n"
        for side in (1, 2):
            nodes = ["tail"] + [f"xr{side}{i}" for i in range(NS - 1)] + [f"nw{side}"]
            for i in range(NS):
                s += dev(f"MRB{side}{i}", nodes[i + 1], "vgr", nodes[i], nodes[i], P, MRG, p)
        if ct > 0: s += f"Ct1 vi1 0 {ct}\nCt2 vi2 0 {ct}\n"
        return s
    return c
A.mk = lambda cbc, cpf: mk5(cbc, cpf)
