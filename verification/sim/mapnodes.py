import re, json, collections
ref = {}
for l in open("tt_um_ecg_v5_ref.spice"):
    t = l.split()
    if t and t[0].startswith("X"): ref[t[0]] = t[1:5]
TI = {"D": 0, "G": 1, "S": 2, "B": 3, "C1": 0, "C2": 1}
def refname(inst):
    for c in [inst, re.sub(r"[LU]$", "", inst), re.sub(r"_\d+[LU]?$", "", inst), re.sub(r"_\d+[ab]?$", "", inst), re.sub(r"\d$", "", inst)]:
        if c in ref: return c
nodes = set()
for l in open("chip_pex.spice"):
    if l.startswith("X"): nodes.update(l.split()[1:-1])
    elif l.startswith("C"): nodes.update(l.split()[1:3])
nodes = {n for n in nodes if "=" not in n}
M = {}
for n in nodes:
    m = re.match(r"(\w+)/(\w+)$", n)
    if m:
        r = refname(m.group(1)); k = TI.get(m.group(2))
        if r and k is not None and k < len(ref[r]): M[n] = ref[r][k]
inv = collections.defaultdict(list)
for a, b in M.items(): inv[b].append(a)
dup = {k: v for k, v in inv.items() if len(v) > 1}
print("mapped", len(M), "of", len(nodes), "; schematic nets with >1 raw name:", dup)
print("unmapped:", sorted(n for n in nodes if n not in M and not n.startswith(("ua[", "ui_in[", "uio_in[", "uio_out", "uo_out", "uio_oe", "VDPWR", "VGND", "clk", "ena", "rst_n")))[:40])
json.dump(M, open("nodemap.json", "w"), indent=0)
