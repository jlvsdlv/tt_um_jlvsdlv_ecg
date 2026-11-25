"""Negotiated-congestion (PathFinder) maze router, layers m2(H) m3(V) m4(H), 0.8 um grid.
Reads prerouted.json + build5_place.tcl, writes build5_route.tcl + routed.json."""
import json, math, sys, heapq, collections, time
d = json.load(open("prerouted.json"))
TERMS = d["TERMS"]; M3ONLY = set(map(tuple, d["M3ONLY"])); M2ONLY = set(map(tuple, d["M2ONLY"]))
SEG = [tuple(s) for s in d["SEG"]]; MIMR = d["MIMR"]; STRIPES = d["STRIPES"]
W_TILE, H_TILE = 334.88, 225.76
tcl = [l for l in open("build5_place.tcl").read().splitlines() if not l.startswith("save ")]
def box(x1, y1, x2, y2): tcl.append(f"box {x1:.3f}um {y1:.3f}um {x2:.3f}um {y2:.3f}um")
def paint(layer, x1, y1, x2, y2): box(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)); tcl.append(f"paint {layer}")
def sq(layer, x, y, s): paint(layer, x - s / 2, y - s / 2, x + s / 2, y + s / 2)
PITCH = 0.8; G0 = 0.4
NX = int((W_TILE - 0.8) / PITCH); NY = int((H_TILE - 0.8) / PITCH)
def gx(i): return G0 + i * PITCH
def node_of(x, y): return (int(round((x - G0) / PITCH)), int(round((y - G0) / PITCH)))
HW = 0.2
LAY = ("m2", "m3", "m4"); LI = {L: k for k, L in enumerate(LAY)}
SPC = {"m2": 0.14, "m3": 0.3, "m4": 0.3}
PREF = {"m2": "H", "m3": "V", "m4": "H"}
BLK = [dict() for _ in LAY]        # static: node -> set(nets)  (wire halo)
VBK = [dict() for _ in LAY]        # static, via-pad halo
def _mark(B, li, net, x1, y1, x2, y2, halo):
    i1 = max(0, int(math.floor((x1 - halo - G0) / PITCH))); i2 = min(NX, int(math.ceil((x2 + halo - G0) / PITCH)))
    j1 = max(0, int(math.floor((y1 - halo - G0) / PITCH))); j2 = min(NY, int(math.ceil((y2 + halo - G0) / PITCH)))
    for i in range(i1, i2 + 1):
        xi = gx(i)
        if not (x1 - halo < xi < x2 + halo): continue
        for j in range(j1, j2 + 1):
            if y1 - halo < gx(j) < y2 + halo: B[li].setdefault((i, j), set()).add(net)
def mark(L, net, x1, y1, x2, y2, halo=None):
    if halo is None: halo = HW + SPC[L] + 0.01
    _mark(BLK, LI[L], net, x1, y1, x2, y2, halo); _mark(VBK, LI[L], net, x1, y1, x2, y2, halo + 0.07)
# ---- power rails (m3 under the m4 stripes) + right-edge VGND rail fed by the top tie bus
RAIL = {}
for n, (xa, xb) in STRIPES.items():
    X = gx(node_of((xa + xb) / 2, 0)[0])
    paint("metal3", X - 0.35, 7.6, X + 0.35, 219.6); SEG.append(("m3", n, X - 0.35, 7.6, X + 0.35, 219.6))
    for k in range(21): sq("via3", X, 9.0 + k * 10.0, 0.36)
    RAIL[n] = [X]
XR = gx(node_of(332.0, 0)[0])
paint("metal3", 94.0, 222.2, XR + 0.35, 223.0); SEG.append(("m3", "VGND", 94.0, 222.2, XR + 0.35, 223.0))
paint("metal3", XR - 0.35, 7.6, XR + 0.35, 223.0); SEG.append(("m3", "VGND", XR - 0.35, 7.6, XR + 0.35, 223.0))
RAIL["VGND"].append(XR)
for (L, net, x1, y1, x2, y2) in SEG:
    if L in LI: mark(L, net, x1, y1, x2, y2)
for (xa, xb) in STRIPES.values(): mark("m4", "__stripe__", xa, 5.0, xb, 220.0)
for r in MIMR:
    e = (r[0] + 0.4, r[1] + 4.4, r[2] - 0.4, r[3] - 0.4)
    mark("m3", "__mim__", *e, halo=1.36 + HW + 0.01)                     # capm.11
    mark("m4", "__mim__", r[0], r[1], r[2], r[3], halo=0.4 + HW + 0.01)  # top plates + tabs (wide m4 spacing)
mark("m4", "__edge__", 0, 213.0, W_TILE, H_TILE)                       # pin drops / top area kept for m4 pins
mark("m4", "__edge__", 0, 0, W_TILE, 4.6)
TN = collections.defaultdict(set)
def term_nodes(x, y):
    n = node_of(x, y)
    if (x, y) in M3ONLY: return [("m3", n)]
    if (x, y) in M2ONLY: return [("m2", n)]
    return [("m3", n), ("m2", n)]
for net, pts in TERMS.items():
    for (x, y) in pts:
        for (L, n) in term_nodes(x, y): TN[(LI[L], n)].add(net)
# same-net 'near miss' nodes: wire/pad square would sit within spacing of a same-net fixed shape without overlapping it
NEAR = collections.defaultdict(set)
for (L, net, x1, y1, x2, y2) in SEG:
    if L not in LI: continue
    li = LI[L]; sp = SPC[L] + 0.02; m = 0.25 + sp
    for i in range(max(0, int((x1 - m - G0) / PITCH)), min(NX, int((x2 + m - G0) / PITCH) + 2)):
        for j in range(max(0, int((y1 - m - G0) / PITCH)), min(NY, int((y2 + m - G0) / PITCH) + 2)):
            X, Y = gx(i), gx(j)
            ov = (X + HW > x1 and X - HW < x2 and Y + HW > y1 and Y - HW < y2)          # wire square overlaps -> connects
            dx = max(x1 - (X + 0.25), (X - 0.25) - x2, 0); dy = max(y1 - (Y + 0.25), (Y - 0.25) - y2, 0)
            near = (dx < sp and dy < sp)
            if near and not ov: NEAR[(li, (i, j))].add(net)
            # partial overlap of the pad also creates notches: require wire square to lie fully inside OR overlap >= 0.2
            if ov:
                ox = min(X + HW, x2) - max(X - HW, x1); oy = min(Y + HW, y2) - max(Y - HW, y1)
                if min(ox, oy) < 0.14: NEAR[(li, (i, j))].add(net)
for (li, (i, j)), nets in list(TN.items()):
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (0, 0)):
        k = (li, (i + di, j + dj))
        if k in NEAR: NEAR[k] -= nets
def sfree(li, n, net):
    i, j = n
    if i < 1 or j < 1 or i >= NX or j >= NY: return False
    if net in TN.get((li, n), ()): return True
    if net in NEAR.get((li, n), ()): return False
    b = BLK[li].get(n)
    return (not b) or b == {net}
def vfree(li, n, net):
    if net in TN.get((li, n), ()): return True
    b = VBK[li].get(n)
    return (not b) or b == {net}
OCC = collections.defaultdict(set)     # (li,n) -> nets using it (dynamic)
HIST = collections.defaultdict(float)
PF = [0.5]
def ncost(li, n, net):
    o = OCC.get((li, n)); k = len(o - {net}) if o else 0
    return (1.0 + HIST[(li, n)]) * (1.0 + PF[0] * k)
def astar(net, starts, goal):
    gli, (gi, gj) = goal
    def h(s): return abs(s[1][0] - gi) + abs(s[1][1] - gj) + (2.0 if s[0] != gli else 0)
    openq = []; best = {}; prev = {}
    for s_ in starts:
        if sfree(s_[0], s_[1], net):
            best[s_] = 0; prev[s_] = None; heapq.heappush(openq, (h(s_), 0, s_))
    while openq:
        f, g, cur = heapq.heappop(openq)
        if cur == goal:
            path = [cur]
            while prev[path[-1]] is not None: path.append(prev[path[-1]])
            return path[::-1]
        if g > best.get(cur, 1e18): continue
        li, (i, j) = cur; H = PREF[LAY[li]] == "H"
        cand = []
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cand.append(((li, (i + di, j + dj)), 1.0 if (dj == 0) == H else 3.0))
        for lj in (li - 1, li + 1):
            if 0 <= lj < 3 and vfree(li, (i, j), net) and vfree(lj, (i, j), net): cand.append(((lj, (i, j)), 4.0))
        for nb, c in cand:
            if not sfree(nb[0], nb[1], net): continue
            ng = g + c * ncost(nb[0], nb[1], net)
            if ng < best.get(nb, 1e18): best[nb] = ng; prev[nb] = cur; heapq.heappush(openq, (ng + 1.1 * h(nb), ng, nb))
    return None
import os, random
RSEED = int(os.environ.get("RSEED", "0"))
ORDER = sorted(TERMS, key=lambda n: (n in ("VGND", "VDPWR", "vdd"), len(TERMS[n])))
if RSEED:
    random.seed(RSEED); head = [n for n in ORDER if n not in ("VGND", "VDPWR", "vdd")]; random.shuffle(head)
    head.sort(key=lambda n: n.startswith("ct"), reverse=True)        # route the congested Ct nets first
    ORDER = head + [n for n in ORDER if n in ("VGND", "VDPWR", "vdd")]
ROUTES = {}
def route_net(net):
    pts = [tuple(p) for p in TERMS[net]]
    if net in RAIL:
        tree = set()
        for X in RAIL[net]:
            i = node_of(X, 0)[0]; tree |= {(1, (i, j)) for j in range(node_of(0, 8.0)[1], node_of(0, 219.0)[1])}
        todo = pts[:]
    else:
        tree = {(LI[L], n) for (L, n) in term_nodes(*pts[0])}; todo = pts[1:]
    paths = []; fails = []
    while todo:
        tl = [t[1] for t in tree]; step = max(1, len(tl) // 150)
        todo.sort(key=lambda p: min(abs(node_of(*p)[0] - a) + abs(node_of(*p)[1] - b) for a, b in tl[::step]))
        x, y = todo.pop(0); path = None
        for (L, n) in term_nodes(x, y):
            if (LI[L], n) in tree: path = [(LI[L], n)]; break
            path = astar(net, list(tree), (LI[L], n))
            if path: break
        if path is None: fails.append((net, x, y)); continue
        tree.update(path); paths.append(path)
    return paths, fails, tree
t0 = time.time()
LOAD = len(sys.argv) > 1 and sys.argv[1] == "load"
if LOAD:
    rj = json.load(open("routed.json")); over = []; FAIL = rj["FAIL"]
    for k, v in rj["ROUTES"].items():
        pa = [[(LI[L], tuple(n)) for L, n in p] for p in v]; ROUTES[k] = (pa, [], {q for p in pa for q in p})
for it in range(0 if LOAD else (int(sys.argv[1]) if len(sys.argv) > 1 else 25)):
    FAIL = []
    for net in ORDER:
        if net in ROUTES:
            for p in ROUTES[net][2]: OCC[p].discard(net)
        paths, fails, tree = route_net(net)
        ROUTES[net] = (paths, fails, {p for pa in paths for p in pa})
        for p in ROUTES[net][2]: OCC[p].add(net)
        FAIL += fails
    over = [k for k, v in OCC.items() if len(v) > 1]
    for k in over: HIST[k] += 1.0
    print(f"iter {it}: overused {len(over)}, unroutable {len(FAIL)}, {time.time()-t0:.0f}s", file=sys.stderr, flush=True)
    if not over and not FAIL: break
    PF[0] *= 1.7
print("over:", [(LAY[k[0]], gx(k[1][0]), gx(k[1][1]), sorted(OCC[k])) for k in over][:30], "\nfail:", FAIL[:30], file=sys.stderr)
LN = {0: "metal2", 1: "metal3", 2: "metal4"}; VIA = {(0, 1): "via2", (1, 2): "via3"}
for net, (paths, _, _) in ROUTES.items():
    for path in paths:
        for a, b in zip(path, path[1:]):
            (la, na), (lb, nb_) = a, b
            if la != lb:
                X, Y = gx(na[0]), gx(na[1]); lo, hi = min(la, lb), max(la, lb)
                sq(VIA[(lo, hi)], X, Y, 0.32 if lo == 0 else 0.36); sq(LN[lo], X, Y, 0.5); sq(LN[hi], X, Y, 0.5)
            else:
                x1, y1, x2, y2 = gx(na[0]), gx(na[1]), gx(nb_[0]), gx(nb_[1])
                paint(LN[la], min(x1, x2) - HW, min(y1, y2) - HW, max(x1, x2) + HW, max(y1, y2) + HW)
# ---- same-net notch fill: bbox hull of a route square and a same-net fixed shape that are closer than the spacing rule
FIX = collections.defaultdict(list)
for (L, net, x1, y1, x2, y2) in SEG:
    if L not in LI: continue
    if L in ("m3", "m4") and abs((x2 - x1) - 0.8) < 1e-3 and abs((y2 - y1) - 0.8) < 1e-3: x1, y1, x2, y2 = x1 + 0.15, y1 + 0.15, x2 - 0.15, y2 - 0.15
    FIX[(LI[L], net)].append((x1, y1, x2, y2))
OTHER = collections.defaultdict(list)
for (L, net, x1, y1, x2, y2) in SEG:
    if L in LI: OTHER[LI[L]].append((net, x1, y1, x2, y2))
for net, (paths, _, nodes) in ROUTES.items():
    for (li, (i, j)) in nodes: OTHER[li].append((net, gx(i) - 0.25, gx(j) - 0.25, gx(i) + 0.25, gx(j) + 0.25))
nfill = 0; nskip = 0
for net, (paths, _, nodes) in ROUTES.items():
    for (li, (i, j)) in nodes:
        X, Y = gx(i), gx(j); sp = SPC[LAY[li]] + 0.01
        hw = 0.25 if any((lk, (i, j)) in nodes for lk in (li - 1, li + 1)) else HW
        w = (X - hw, Y - hw, X + hw, Y + hw)
        for f in FIX.get((li, net), []):
            dx = max(f[0] - w[2], w[0] - f[2], 0); dy = max(f[1] - w[3], w[1] - f[3], 0)
            if (dx > 0 or dy > 0) and dx < sp and dy < sp:
                h = (min(w[0], f[0]), min(w[1], f[1]), max(w[2], f[2]), max(w[3], f[3]))
                bad = any(o[0] != net and not (o[3] + sp <= h[0] or h[2] + sp <= o[1] or o[4] + sp <= h[1] or h[3] + sp <= o[2]) for o in OTHER[li])
                if bad: nskip += 1; continue
                paint(LN[li], *h); nfill += 1
print("notch fills", nfill, "skipped", nskip, file=sys.stderr)
for n, (xa, xb) in STRIPES.items():
    box(xa, 5.0, xb, 220.0); tcl.append(f"label {n} FreeSans 0.25u -metal4")
    tcl += ["port make", f"port use {'ground' if n == 'VGND' else 'power'}", "port class bidirectional"]
tcl += ["select top cell", "save tt_um_ecg_v5"]
open("build5_route.tcl", "w").write("\n".join(tcl) + "\n")
json.dump(dict(FAIL=FAIL, OVER=len(over), ROUTES={k: [[[LAY[p[0]], p[1]] for p in pa] for pa in v[0]] for k, v in ROUTES.items()}), open("routed.json", "w"))
