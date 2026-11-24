import re, collections, json, sys
ref = {}
ALIAS = {}
for l in open("tt_um_ecg_v5_ref.spice"):
    t = l.split()
    if not t or not t[0].startswith("X"): continue
    ref[t[0]] = t[1:5]
src = open("../ref_netlist.py").read()
al = dict(re.findall(r'"(\w+)": "(u\w+\[\d\])"', src))
al.update({f"b{k}": f"ui_in[{k}]" for k in range(8)})
inv = {v: k for k, v in al.items()}
TI = {"D": 0, "G": 1, "S": 2, "B": 3, "C1": 0, "C2": 1}
def refname(inst):
    cands = [inst, re.sub(r"[LU]$", "", inst), re.sub(r"_\d+[LU]?$", "", inst), re.sub(r"_\d+[ab]?$", "", inst), re.sub(r"\d$", "", inst)]
    for c in cands:
        if c in ref: return c
    return None
def name(n):
    if n in inv: return inv[n]
    if n in ("VGND", "VDPWR"): return n
    m = re.match(r"(\w+)/(\w+)$", n)
    if m:
        r = refname(m.group(1)); k = TI.get(m.group(2))
        if r is not None and k is not None and k < len(ref[r]):
            v = ref[r][k]; return inv.get(v, v)
    return n
caps = collections.defaultdict(float); unk = set()
for l in open("tt_um_ecg_v5_pex.spice"):
    if not l.startswith("C"): continue
    _, a, b, v = l.split()[:4]
    sc = {"f": 1e-15, "p": 1e-12, "a": 1e-18, "n": 1e-9}
    v = float(v[:-1]) * sc[v[-1]] if v[-1] in sc else float(v)
    A, B = name(a), name(b)
    for x, y in ((a, A), (b, B)):
        if x == y and x not in ("VGND", "VDPWR") and "[" not in x: unk.add(x)
    if B in ("VGND",) or B.startswith("VSUBS") or B == "0": caps[(A, "gnd")] += v
    elif A in ("VGND",) or A.startswith("VSUBS") or A == "0": caps[(B, "gnd")] += v
    else: caps[tuple(sorted((A, B)))] += v
print("unmapped:", sorted(unk)[:30])
crit = ["vi1", "vi2", "vo1", "vo2", "nw1", "nw2", "tail", "g3", "g4", "vbna", "vbnb", "nb", "vgr", "drl", "x"]
tot = collections.defaultdict(float)
for (a, b), v in caps.items():
    tot[a] += v; tot[b] += v
for n in crit:
    print(f"{n:5s} total {tot[n]*1e15:8.1f} fF   ", ", ".join(f"{(b if a==n else a)}:{v*1e15:.1f}" for (a, b), v in sorted(caps.items(), key=lambda kv: -kv[1]) if n in (a, b) and v > 0.5e-15)[:300])
json.dump({f"{a}|{b}": v for (a, b), v in caps.items()}, open("pexcaps.json", "w"))
