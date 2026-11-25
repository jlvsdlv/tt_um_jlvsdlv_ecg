"""Layout generator for tt_um_ecg_v5 (TT sky130 2x2 analog tile, met1-met4).
Emits build5.tcl for magic. Units um. Coordinates given for each instance are the LOWER-LEFT of the cell bbox.
Scheme (from the 1x2 flow): FET fingers strapped on met2 below the device (D at -1.2, S at -2.6), gate via stack above,
body via stack left; varactors: gate bar on met1 at the top, well bar on met2; MIM terminals as met4 tabs below the cap
with via3 to met3; maze router on met2/met3 (met3 blocked under MIM, met2 free there)."""
import math, sys, json, collections, heapq
from magparse import parse
from shapely.geometry import box as sbox, Point
from shapely.ops import unary_union

TOP = "tt_um_ecg_v5"
W_TILE, H_TILE = 334.88, 225.76
CELLS = {}
def C(n):
    if n not in CELLS: CELLS[n] = parse(n)
    return CELLS[n]
tcl = []
PITCH_G, G0 = 0.8, 0.4
def snap(v): return G0 + round((v - G0) / PITCH_G) * PITCH_G
def box(x1, y1, x2, y2): tcl.append(f"box {x1:.3f}um {y1:.3f}um {x2:.3f}um {y2:.3f}um")
def paint(layer, x1, y1, x2, y2):
    if x1 > x2: x1, x2 = x2, x1
    if y1 > y2: y1, y2 = y2, y1
    box(x1, y1, x2, y2); tcl.append(f"paint {layer}")
def sq(layer, x, y, s): paint(layer, x - s / 2, y - s / 2, x + s / 2, y + s / 2)
SEG = []
def rec(layer, net, x1, y1, x2, y2): SEG.append((layer, net, min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
MIMR = []                      # MIM keep-out rectangles (met3/met4)
def under_mim(x, y, halo=1.0):
    return any(r[0] - halo <= x <= r[2] + halo and r[1] - halo <= y <= r[3] + halo for r in MIMR)
TERMS = {}; M3ONLY = set(); M2ONLY = set()
def term(net, x, y, m3only=False, m2only=False):
    X, Y = snap(x), snap(y)
    TERMS.setdefault(net, []).append((X, Y))
    if m3only: M3ONLY.add((X, Y))
    if m2only: M2ONLY.add((X, Y))
def viastack(net, x, y, start="m1"):
    """pad on start layer -> via(s) -> m2 (and m3 unless under a MIM). Returns grid point."""
    X, Y = snap(x), snap(y)
    m2only = under_mim(X, Y)
    if start == "m2":
        paint("metal2", min(x, X) - 0.3, min(y, Y) - 0.3, max(x, X) + 0.3, max(y, Y) + 0.3)
        rec("m2", net, min(x, X) - 0.3, min(y, Y) - 0.3, max(x, X) + 0.3, max(y, Y) + 0.3)
    else:
        paint("metal1", min(x, X) - 0.15, min(y, Y) - 0.15, max(x, X) + 0.15, max(y, Y) + 0.15)
        sq("metal1", X, Y, 0.6); sq("via1", X, Y, 0.32)
    sq("metal2", X, Y, 0.7)
    rec("m2", net, X - 0.35, Y - 0.35, X + 0.35, Y + 0.35)
    if not m2only:
        sq("via2", X, Y, 0.34); sq("metal3", X, Y, 0.5); rec("m3", net, X - 0.4, Y - 0.4, X + 0.4, Y + 0.4)
    term(net, X, Y, m2only=m2only)
    return X, Y
INST = []; ENV = []
def place(cname, inst, xll, yll):
    b = C(cname)["bbox"]; ox, oy = xll - b[0], yll - b[1]
    INST.append((cname, inst, ox, oy))
    box(ox, oy, ox, oy); tcl.append(f"getcell {cname} child 0 0"); tcl.append(f"identify {inst}")
    return ox, oy, b
_POLY = {}
def m1poly(cname):
    if cname not in _POLY:
        u = unary_union([sbox(*r) for L in ("metal1", "viali", "via1") for r in C(cname)["rects"].get(L, [])])
        _POLY[cname] = list(u.geoms) if hasattr(u, "geoms") else [u]
    return _POLY[cname]
def poly_at(cname, x, y):
    p = Point(x, y)
    for g in m1poly(cname):
        if g.buffer(1e-3).contains(p): return g.bounds
    return None
# ------------------------------------------------------------------ FET
def wire_fet(cname, inst, xll, yll, d, g, s, b, flip=False):
    """flip=True: straps ABOVE the device and gate stack BELOW (for rows that sit on a channel)."""
    ox, oy, bb = place(cname, inst, xll, yll)
    c = C(cname)
    sd = sorted([(l[2], l[3], l[0]) for l in c["labels"] if l[0][0] in "DS" and l[1].endswith("c")])
    if len(sd) > 1:                         # labels exist only for the first fingers: extrapolate by pitch
        pitch = sd[1][0] - sd[0][0]; x = sd[-1][0] + pitch; k = len(sd)
        while x < bb[2] - 0.3:
            sd.append((x, sd[0][1], "DS"[k % 2] + str(k))); x += pitch; k += 1
    strs = []
    for x, y, nm in sd:
        st = poly_at(cname, x, y)
        if st: strs.append((nm[0], ox + (st[0] + st[2]) / 2, oy + st[1], oy + st[3]))
    ybot, ytop = oy + bb[1], oy + bb[3]
    if not flip: yD, yS, ygate = ybot - 1.2, ybot - 2.6, ytop + 1.0
    else: yD, yS, ygate = ytop + 1.2, ytop + 2.6, ybot - 1.0
    dx, sx = [], []
    for kind, cx, y1, y2 in strs:
        tgt = yD if kind == "D" else yS
        if not flip: paint("metal1", cx - 0.15, tgt - 0.3, cx + 0.15, y1 + 0.05)
        else: paint("metal1", cx - 0.15, y2 - 0.05, cx + 0.15, tgt + 0.3)
        sq("metal1", cx, tgt, 0.5); sq("via1", cx, tgt, 0.32); sq("metal2", cx, tgt, 0.6)
        (dx if kind == "D" else sx).append(cx)
    for xs_, yy, net in ((dx, yD, d), (sx, yS, s)):
        xa, xb = min(xs_) - 0.3, max(xs_) + 0.3
        paint("metal2", xa, yy - 0.3, xb, yy + 0.3); rec("m2", net, xa, yy - 0.3, xb, yy + 0.3)
    gl = [l for l in c["labels"] if l[0] == "G"]
    gx = ox + gl[0][2]; gy = oy + gl[0][3]
    if not flip: paint("metal1", gx - 0.2, min(gy, ytop) - 0.1, gx + 0.2, ygate + 0.3)
    else:
        # gate contacts are on top: run met1 from the gate bar around the left edge to below the device
        gyb = oy + gl[0][3]
        xl = ox + bb[0] - 2.6
        paint("metal1", xl - 0.2, gyb - 0.2, gx + 0.2, gyb + 0.2) if False else None
        paint("metal1", gx - 0.2, gy - 0.1, gx + 0.2, ytop + 0.5)
        paint("metal1", xl - 0.2, ytop + 0.1, gx + 0.2, ytop + 0.5)
        paint("metal1", xl - 0.2, ygate - 0.3, xl + 0.2, ytop + 0.5)
        paint("metal1", xl - 0.2, ygate - 0.3, gx + 0.2, ygate + 0.1)
        gx = xl + 0.6
    rl = poly_at(cname, bb[0] + 0.05, 0.0) or poly_at(cname, bb[0] + 0.1, 0.0)
    by = oy + (rl[1] + rl[3]) / 2; bx = ox + rl[0] - 1.2
    paint("metal1", bx - 0.3, by - 0.25, ox + rl[0] + 0.1, by + 0.25)
    viastack(d, dx[0], yD, start="m2"); viastack(s, sx[0], yS, start="m2")
    viastack(g, gx, ygate); viastack(b, bx, by)
    lo = min(yD, yS, ygate) - 0.6; hi = max(yD, yS, ygate) + 0.6
    ENV.append((inst, ox + bb[0] - 1.9, min(lo, ybot), ox + bb[2] + 0.2, max(hi, ytop)))
# ------------------------------------------------------------------ stacked pair sharing D/S straps (input pair)
def wire_pair(inst, xll, yll, d, g, s, b):
    cl, cu = "XP1B", "XP1"
    oxl, oyl, bbl = place(cl, inst + "L", xll, yll)
    hL = bbl[3] - bbl[1]; ybase = yll + hL
    yD, yS = ybase + 1.2, ybase + 2.6
    oxu, oyu, bbu = place(cu, inst + "U", xll, ybase + 3.4)
    dx, sx = [], []
    for cname, ox, oy, up in ((cl, oxl, oyl, True), (cu, oxu, oyu, False)):
        c = C(cname); bb = c["bbox"]
        sd = sorted([(l[2], l[3], l[0]) for l in c["labels"] if l[0][0] in "DS" and l[1].endswith("c")])
        pitch = sd[1][0] - sd[0][0]; x = sd[-1][0] + pitch; k = len(sd)
        while x < bb[2] - 0.3: sd.append((x, sd[0][1], "DS"[k % 2] + str(k))); x += pitch; k += 1
        for x0, y0, nm in sd:
            st = poly_at(cname, x0, y0)
            if not st: continue
            cx = ox + (st[0] + st[2]) / 2; tgt = yD if nm[0] == "D" else yS
            if up: paint("metal1", cx - 0.15, oy + st[3] - 0.05, cx + 0.15, tgt + 0.3)
            else: paint("metal1", cx - 0.15, tgt - 0.3, cx + 0.15, oy + st[1] + 0.05)
            sq("via1", cx, tgt, 0.32); sq("metal2", cx, tgt, 0.6); sq("metal1", cx, tgt, 0.5)
            (dx if nm[0] == "D" else sx).append(cx)
        gl = [l for l in c["labels"] if l[0] == "G"][0]
        gx, gy = ox + gl[2], oy + gl[3]
        if up: paint("metal1", gx - 0.2, oy + bb[1] - 1.3, gx + 0.2, gy + 0.1); viastack(g, gx, oy + bb[1] - 1.0)
        else: paint("metal1", gx - 0.2, gy - 0.1, gx + 0.2, oy + bb[3] + 1.3); viastack(g, gx, oy + bb[3] + 1.0)
        rl = poly_at(cname, bb[0] + 0.05, 0.0) or poly_at(cname, bb[0] + 0.1, 0.0)
        by = oy + (rl[1] + rl[3]) / 2; bx = ox + rl[0] - 1.2
        paint("metal1", bx - 0.3, by - 0.25, ox + rl[0] + 0.1, by + 0.25); viastack(b, bx, by)
    for xs_, yy, net in ((dx, yD, d), (sx, yS, s)):
        xa, xb = min(xs_) - 0.3, max(xs_) + 0.3
        paint("metal2", xa, yy - 0.3, xb, yy + 0.3); rec("m2", net, xa, yy - 0.3, xb, yy + 0.3)
    viastack(d, dx[0], yD, start="m2"); viastack(s, sx[-1], yS, start="m2")
    ENV.append((inst, xll - 1.9, yll - 1.6, xll + (bbl[2] - bbl[0]) + 0.2, ybase + 3.4 + (bbu[3] - bbu[1]) + 1.6))
# ------------------------------------------------------------------ varactor (no labels in the cell: classify met1 shapes)
def var_parts(cname):
    R = C(cname)["rects"]; gs = m1poly(cname); out = {"gate": [], "well": []}
    for g in gs:
        for L, k in (("polycont", "gate"), ("nsubdiffcont", "well")):
            if any(g.intersects(sbox(*r)) for r in R.get(L, [])): out[k].append(g.bounds); break
    return out
def wire_var(cname, inst, xll, yll, gate, well):
    ox, oy, bb = place(cname, inst, xll, yll)
    paint("nwell", ox + bb[0], oy + bb[1] - 0.2, ox + bb[2], oy + bb[3] + 0.2)      # varac.5 fix (generator leaves 0.015 um)
    P = var_parts(cname)
    top = [g for g in P["gate"] if g[1] > 0]
    yt = max(g[3] for g in top)
    xa = min(g[0] for g in top); xb = max(g[2] for g in top)
    # gate: met1 bar joining all top gate strips, raised 0.45 um above the well plates' clearance
    paint("metal1", ox + xa, oy + min(g[1] for g in top), ox + xb, oy + yt)
    gx = ox + xa + 0.3; ygs = oy + bb[3] + 0.9
    paint("metal1", gx - 0.2, oy + yt - 0.1, gx + 0.2, ygs + 0.3)
    viastack(gate, gx, ygs)
    # well: met2 bar through all plate centres + via1 on every plate
    yc = oy + sum((g[1] + g[3]) / 2 for g in P["well"]) / len(P["well"])
    xs = sorted(ox + (g[0] + g[2]) / 2 for g in P["well"])
    for x in xs: sq("via1", x, yc, 0.32); sq("metal1", x, yc, 0.5)
    xw = ox + bb[0] - 1.0
    paint("metal2", xw - 0.3, yc - 0.3, xs[-1] + 0.3, yc + 0.3); rec("m2", well, xw - 0.3, yc - 0.3, xs[-1] + 0.3, yc + 0.3)
    viastack(well, xw, yc, start="m2")
    ENV.append((inst, ox + bb[0] - 1.6, oy + bb[1] - 0.3, ox + bb[2] + 0.2, ygs + 0.6))
# ------------------------------------------------------------------ resistor: nx separate xhigh_po strips joined in series by met1 jumpers
def wire_res(cname, inst, xll, yll, r1, r2):
    """even nx: both terminals at the top. labels R1_k (top), R2_k (bottom)."""
    ox, oy, bb = place(cname, inst, xll, yll)
    lab = {l[0]: (ox + l[2], oy + l[3]) for l in C(cname)["labels"]}
    n = len([k for k in lab if k.startswith("R1_")])
    for k in range(n - 1):
        side = "R2" if k % 2 == 0 else "R1"
        (xa, ya), (xb, yb) = lab[f"{side}_{k}"], lab[f"{side}_{k+1}"]
        paint("metal1", xa - 0.125, ya - 0.3, xb + 0.125, ya + 0.3) if side == "R1" else paint("metal1", xa - 0.125, ya - 0.3, xb + 0.125, ya + 0.3)
    ytop = oy + bb[3]
    for (name, net, dy) in (("R1_0", r1, 1.0), (f"R1_{n-1}", r2, 2.6)):
        px, py = lab[name]
        paint("metal1", px - 0.125, py - 0.3, px + 0.125, ytop + dy + 0.3)
        viastack(net, px, ytop + dy) if n > 2 else viastack(net, px + (-1.0 if name == "R1_0" else 1.0), ytop + dy)
        if n <= 2: paint("metal1", min(px, px + (-1.0 if name == "R1_0" else 1.0)) - 0.15, ytop + dy - 0.15, max(px, px + (-1.0 if name == "R1_0" else 1.0)) + 0.15, ytop + dy + 0.15)
    mx = 1.6 if n <= 2 else 0.6
    ENV.append((inst, ox + bb[0] - mx, oy + bb[1] - 0.3, ox + bb[2] + mx, ytop + 3.4))
# ------------------------------------------------------------------ MIM: labels C1 (top plate, mimcapcontact) and C2 (via3 strip); both on met4
def wire_cap(cname, inst, xll, yll, n1, n2):
    """n1 = top plate (C1), n2 = bottom plate (C2). met4 tabs dropped BELOW the cap, via3 to a met3 pad (router terminal)."""
    ox, oy, bb = place(cname, inst, xll, yll)
    c = C(cname)
    rs = [r for L in ("metal3", "metal4") for r in c["rects"].get(L, [])]
    e = (ox + min(r[0] for r in rs), oy + min(r[1] for r in rs), ox + max(r[2] for r in rs), oy + max(r[3] for r in rs))
    MIMR.append((e[0] - 0.4, e[1] - 4.4, e[2] + 0.4, e[3] + 0.4))
    m4 = c["rects"]["metal4"]
    for l in c["labels"]:
        key = l[0].split("_")[0]; net = n1 if key == "C1" else n2
        lx, ly = ox + l[2], oy + l[3]
        if key == "C1": lx = e[0] + 3.0               # tab from the left part of the top plate
        off = 2.0 if key == "C1" else 3.6
        tx, ty = snap(lx), snap(e[1] - off)
        ybot_shape = e[1] + (0.6 if key == "C1" else 0.2)
        paint("metal4", min(tx, lx) - 0.4, ty - 0.4, max(tx, lx) + 0.4, ty + 0.4)
        paint("metal4", lx - 0.4, ty - 0.4, lx + 0.4, ybot_shape + 0.3)
        sq("via3", tx, ty, 0.36); sq("metal3", tx, ty, 0.5)
        rec("m4", net, tx - 0.4, ty - 0.4, tx + 0.4, ybot_shape + 0.3); rec("m3", net, tx - 0.4, ty - 0.4, tx + 0.4, ty + 0.4)
        term(net, tx, ty, m3only=True)
    return e
# ================================================================== FLOORPLAN
tcl += ["load _scratch_ -silent", "def read tt_analog_2x2.def", f"cellname rename tt_um_template {TOP}", "load " + TOP, "select top cell"]
STRIPES = {"VDPWR": (1.0, 3.0), "VGND": (4.5, 6.5)}
for n, (xa, xb) in STRIPES.items():
    paint("metal4", xa, 5.0, xb, 220.0); rec("m4", n, xa, 5.0, xb, 220.0)
def W_(c):
    rs = [r for L in ("metal3", "metal4") for r in C(c)["rects"].get(L, [])]
    return max(r[2] for r in rs) - C(c)["bbox"][0]
# ---------------- MIM (first, so device via stacks know where met3 is blocked)
for sd, y0 in ((1, 11.6), (2, 52.0)):                                   # Cbc MIM over the varactor blocks
    for k in range(3): wire_cap("C30", f"XCBM{sd}_{k}", 10.0 + 33.6 * k, y0, f"nw{sd}", f"vi{sd}")
for sd, x0 in ((1, 114.0), (2, 186.0)):                                  # Cbc MIM over the input pair
    for k in range(2): wire_cap("C30", f"XCBM{sd}_{3+k}", x0 + 35.0 * k, 92.0, f"nw{sd}", f"vi{sd}")
for sd, y in ((1, 16.0), (2, 52.0)):                                     # Ct MIM bits over the input pair
    xs = 114.0
    for nm, c, k in ((f"XCT{sd}_9a", "C245", 9), (f"XCT{sd}_9b", "C245", 9), (f"XCT{sd}_8", "C245", 8), (f"XCT{sd}_7", "C173", 7), (f"XCT{sd}_6", "C122", 6)):
        wire_cap(c, nm, xs, y, f"vi{sd}", f"ct{sd}_{k}"); xs += W_(c) + 1.6
wire_cap("C2025", "XCPF1", 236.0, 16.0, "vo1", "vi1"); wire_cap("C2025", "XCPF2", 236.0, 52.0, "vo2", "vi2")
for r, y in enumerate((95.6, 130.8, 166.0)):                              # Cg: 8 x C30 over DNW / well-bias band
    for k in range(3):
        idx = 3 * r + k
        if idx < 8:
            a, b_ = ("g3", "g4") if idx % 2 == 0 else ("g4", "g3")
            wire_cap("C30", f"XCG_{idx}", 10.0 + 33.6 * k, y, a, b_)
wire_cap("C236", "XCF3", 157.0, 133.5, "vo2", "g3"); wire_cap("C236", "XCF4", 184.4, 133.5, "vo1", "g4")
for k, x in enumerate((211.8, 245.4, 279.0)): wire_cap("C30", f"XCCM_{k}", x, 133.5, "x", "drl")
for k, x in enumerate((262.0, 296.0)): wire_cap("C30", f"XCCM_{3+k}", x, 182.0, "x", "drl")
for k, (x, y) in enumerate(((77.2, 166.0), (296.0, 12.0), (227.8, 186.4))): wire_cap("C30", f"XCCA_{k}", x, y, "drva", "vbna")
for k, (x, y) in enumerate(((296.0, 47.0), (262.0, 47.0), (296.0, 82.0))): wire_cap("C30", f"XCCB_{k}", x, y, "drvb", "vbnb")
wire_cap("C7", "XCST", 313.0, 166.0, "vdd", "st")
# ---------------- Cbc varactors: 3 rows x VAR9G per side (left)
for sd, y0 in ((1, 7.0), (2, 48.4)):
    for r in range(3): wire_var("VAR9G", f"XCBC{sd}_{r}", 11.5, y0 + 13.4 * r, f"nw{sd}", f"vi{sd}")
# ---------------- input pair: 8 stacked pairs (each pair = one device, 2 x 100 um), cross-quad over 4 columns x 2 rows
pat = [["1", "2", "2", "1"], ["2", "1", "1", "2"]]
cnt = {"1": 0, "2": 0}
for r, y in enumerate((7.6, 68.4)):
    for col in range(4):
        sd = pat[r][col]; n = cnt[sd]; cnt[sd] += 1
        wire_pair(f"XM{sd}_{n}", 113.0 + 37.2 * col, y, d=("vo2" if sd == "1" else "vo1"), g=f"vi{sd}", s="tail", b=f"nw{sd}")
# ---------------- Ct varactor bits + switches (right column, x 260-305)
for sd, y0 in ((1, 7.0), (2, 47.0)):
    wire_var("VB0G", f"XCT{sd}_0", 262.0, y0, f"vi{sd}", f"ct{sd}_0"); wire_var("VB1G", f"XCT{sd}_1", 267.0, y0, f"vi{sd}", f"ct{sd}_1")
    wire_var("VB2G", f"XCT{sd}_2", 275.5, y0, f"vi{sd}", f"ct{sd}_2"); wire_var("VB4G", f"XCT{sd}_4", 291.0, y0, f"vi{sd}", f"ct{sd}_4")
    wire_var("VB3G", f"XCT{sd}_3", 262.0, y0 + 5.6, f"vi{sd}", f"ct{sd}_3"); wire_var("VB5G", f"XCT{sd}_5", 291.0, y0 + 11.6, f"vi{sd}", f"ct{sd}_5")
    for k in range(10):
        wire_fet("N1L05", f"XSCT{sd}_{k}", 264.0 + 5.4 * (k % 5), y0 + 17.0 + 7.6 * (k // 5), d=f"ct{sd}_{k}", g=f"b{k}", s="VGND", b="VGND")
# ---------------- reference: resistors (far right) + device rows
wire_res("RXB", "XRR1", 304.6, 9.0, "rt1", "rt2"); wire_res("RXC", "XRR2", 310.8, 9.0, "rt2", "VGND"); wire_res("RXA", "XRR0", 316.6, 7.0, "rs", "rt1")
wire_fet("NL2L8x8", "XRN2", 262.0, 89.5, d="n2", g="n1", s="rs", b="VGND")
wire_fet("NL2L8x5", "XRN3", 262.0, 98.1, d="nb", g="n1", s="VGND", b="VGND")
wire_fet("NL2L8", "XRN1", 307.5, 98.1, d="n1", g="n1", s="VGND", b="VGND")
wire_fet("NL042L1", "XRMI", 319.6, 98.1, d="st", g="n1", s="VGND", b="VGND"); wire_fet("N042L1", "XRMK", 325.6, 98.1, d="n2", g="st", s="VGND", b="VGND")
wire_fet("PL4L8", "XRP1", 262.0, 106.7, d="n1", g="n2", s="vdd", b="vdd"); wire_fet("PL4L8", "XRP2", 276.0, 106.7, d="n2", g="n2", s="vdd", b="vdd")
wire_fet("P042L4", "XRML", 290.0, 106.7, d="st", g="vdd", s="vdd", b="vdd")
wire_fet("N1L05", "XRS1", 300.0, 106.7, d="rt1", g="it0", s="rt2", b="VGND"); wire_fet("N1L05", "XRS2", 305.4, 106.7, d="rt2", g="it1", s="VGND", b="VGND")
# ---------------- one DNW: island A (4 rows) | n-well divider | island B (4 rows); loads as single-finger L=64 cells
DNW = (10.0, 91.0, 106.0, 171.4)
DIV = (129.4, 132.6)
ISL = {"A": (96.4, "vbna"), "B": (136.6, "vbnb")}
for isl, (y0, wnet) in ISL.items():
    for k, (nm, dn, gn) in enumerate(((f"XM3{isl}_0", "vo2", "g3"), (f"XM3{isl}_1", "vo2", "g3"), (f"XM4{isl}_0", "vo1", "g4"), (f"XM4{isl}_1", "vo1", "g4"))):
        wire_fet("M34S", nm, 16.0, y0 + 8.8 * k, d=dn, g=gn, s="VGND", b=wnet)
    wire_fet("N2L05", f"XMCL{isl.lower()}", 88.0, y0, d="VGND", g="VGND", s="VGND", b=wnet)
# ---------------- tail mirror, bias-electrode loop
for k in range(4): wire_fet("MB2Q", f"XMB2_{k}", 157.0, 131.4 + 8.6 * k, d="tail", g="nb", s="vdd", b="vdd")
wire_fet("MB1", "XMB1", 157.0, 166.0, d="nb", g="nb", s="vdd", b="vdd")
for i in range(7):
    a = "vdd" if i == 0 else f"r{i}"; bnet = "VGND" if i == 6 else f"r{i+1}"
    wire_fet("MLAD", f"XLD{i}", 188.0 + 6.4 * i, 166.0, d=bnet, g=bnet, s=a, b=a)
wire_fet("PL2L2", "XBP", 234.0, 166.0, d="nd", g="nb", s="vdd", b="vdd")
wire_fet("PL4L2", "XPA", 241.0, 166.0, d="xa", g="xa", s="vdd", b="vdd"); wire_fet("PL4L2", "XPB", 248.0, 166.0, d="x", g="xa", s="vdd", b="vdd")
wire_fet("PL4L2", "XP2", 255.0, 166.0, d="drl", g="x", s="vdd", b="vdd")
for nm, c, x, dn, gn, sn in (("XBN", "NL2L8", 157.0, "nd", "nd", "VGND"), ("XS1", "NL2L8", 170.0, "s1", "nd", "VGND"), ("XA1", "NL2L4", 183.0, "xa", "tail", "s1"),
                             ("XA2", "NL2L4", 192.0, "x", "r1", "s1"), ("XS2", "NL2L8x4", 201.0, "drl", "nd", "VGND"), ("XIRBM", "MIRB", 262.0, "vgr", "nd", "VGND"), ("XS2B", "NL2L8x4", 283.0, "drl", "nd", "VGND")):
    wire_fet(c, nm, x, 176.6, d=dn, g=gn, s=sn, b="VGND")
# ---------------- well bias (replica pseudo-R), feedback pseudo-R, reset switches (above the DNW)
wire_fet("MREP", "XMREP", 12.0, 176.4, d="vgr", g="vgr", s="tail", b="tail")
for sd in (1, 2):
    nodes = ["tail"] + [f"xr{sd}{i}" for i in range(3)] + [f"nw{sd}"]
    for i in range(4): wire_fet("MRB", f"XMRB{sd}{i}", 80.0 + 26.0 * (sd - 1), 176.4 + 8.6 * i, d=nodes[i + 1], g="vgr", s=nodes[i], b=nodes[i])
wire_fet("P042L4", "XMR3", 134.0, 176.4, d="g3", g="vo2", s="vo2", b="vo2"); wire_fet("P042L4", "XMR4", 134.0, 185.0, d="g4", g="vo1", s="vo1", b="vo1")
for k, (nm, a, bnet) in enumerate((("XSWF3", "g3", "vo2"), ("XSWF4", "g4", "vo1"), ("XSWB1", "nw1", "tail"), ("XSWB2", "nw2", "tail"))):
    wire_fet("MSWP", nm, 134.0 + 6.0 * (k % 2), 193.6 + 8.6 * (k // 2), d=a, g="rstb", s=bnet, b=bnet)
# ---------------- 1.8 V logic
def inv(nm, o, i, x, y, cp="P1L05", cn="N05L05"):
    hN = C(cn)["bbox"][3] - C(cn)["bbox"][1]
    wire_fet(cp, nm + "P", x, y + hN + 5.0, d=o, g=i, s="VDPWR", b="VDPWR"); wire_fet(cn, nm + "N", x, y, d=o, g=i, s="VGND", b="VGND")
def nand(nm, o, a, b_, x, y):
    wire_fet("P1L05", nm + "P1", x, y + 7.8, d=o, g=a, s="VDPWR", b="VDPWR"); wire_fet("P1L05", nm + "P2", x + 5.0, y + 7.8, d=o, g=b_, s="VDPWR", b="VDPWR")
    wire_fet("N1L05", nm + "N1", x, y, d=o, g=a, s=nm.lower() + "m", b="VGND"); wire_fet("N1L05", nm + "N2", x + 5.0, y, d=nm.lower() + "m", g=b_, s="VGND", b="VGND")
LX, LY = 157.0, 189.0
inv("XIRST", "rstb", "rst", LX + 0, LY); inv("XIKC", "clkb", "clk", LX + 5.5, LY)
xx = LX + 11.0
for ph, ck in (("a", "clk"), ("b", "clkb")):
    nand(f"XNDA{ph}", f"x1{ph}", ck, "en", xx, LY); xx += 10.5
    inv(f"XI1{ph}", f"x2{ph}", f"x1{ph}", xx, LY, "P2L05", "N1L05"); xx += 5.5
    inv(f"XI2{ph}", f"drv{ph}", f"x2{ph}", xx, LY, "P4L05", "N2L05"); xx += 5.5
# ---------------- DNW structure: ring + divider, all tied to vdd
x1, y1, x2, y2 = DNW
paint("dnwell", x1, y1, x2, y2)
ro, ri = 0.5, 1.8
for (a, b_, c_, d_) in ((x1 - ro, y1 - ro, x2 + ro, y1 + ri), (x1 - ro, y2 - ri, x2 + ro, y2 + ro), (x1 - ro, y1 - ro, x1 + ri, y2 + ro), (x2 - ri, y1 - ro, x2 + ro, y2 + ro),
                        (x1 - ro, DIV[0], x2 + ro, DIV[1])):
    paint("nwell", a, b_, c_, d_)
tw, tin = 0.6, 0.5
for (a, b_, c_, d_) in ((x1 + tin, y1 + tin, x2 - tin, y1 + tin + tw), (x1 + tin, y2 - tin - tw, x2 - tin, y2 - tin),
                        (x1 + tin, y1 + tin, x1 + tin + tw, y2 - tin), (x2 - tin - tw, y1 + tin, x2 - tin, y2 - tin),
                        (x1 + tin, (DIV[0] + DIV[1]) / 2 - tw / 2, x2 - tin, (DIV[0] + DIV[1]) / 2 + tw / 2)):
    paint("nsubdiff", a, b_, c_, d_); paint("locali", a, b_, c_, d_)
lx = x1 + tin + tw / 2
for k in range(int((y2 - y1 - 2) / 1.0)):
    yy = y1 + 1.2 + k * 1.0; sq("nsubdiffcont", lx, yy, 0.17); sq("viali", lx, yy, 0.17)
paint("metal1", lx - 0.2, y1 + 1.0, lx + 0.2, y2 - 1.0)
viastack("vdd", lx - 2.0, (y1 + y2) / 2); paint("metal1", lx - 2.3, (y1 + y2) / 2 - 0.25, lx + 0.2, (y1 + y2) / 2 + 0.25)
DNW = {"ALL": (x1, y1, x2, y2, "vdd")}
# ---- pins (bottom analog, met4 -> via3 -> met3 terminal at y 3.5)
APIN = {"vi1": 152.26, "vi2": 132.94, "vo1": 113.62, "vo2": 94.30, "drl": 74.98, "vdd": 55.66}
for net, px in APIN.items():
    X, Y = snap(px), snap(3.5)
    paint("metal4", px - 0.45, 0.0, px + 0.45, 4.0); paint("metal4", min(px, X) - 0.4, Y - 0.4, max(px, X) + 0.4, Y + 0.4)
    sq("via3", X, Y, 0.36); sq("metal3", X, Y, 0.5)
    rec("m4", net, px - 0.45, 0.0, px + 0.45, 4.0); term(net, X, Y, m3only=True)
# ---- top digital inputs used (met4 drop to y 214, via3, met3 terminal)
DPIN = {**{f"b{k}": 138.46 - 2.76 * k for k in range(8)}, "b8": 116.38, "b9": 113.62, "en": 110.86, "rst": 108.10, "it0": 105.34, "it1": 102.58, "clk": 143.98}
for net, px in DPIN.items():
    yv = 214.0 if net != "clk" else 216.0
    paint("metal4", px - 0.15, yv - 0.4, px + 0.15, H_TILE)
    X, Y = snap(px), snap(yv)
    paint("metal4", min(px, X) - 0.4, Y - 0.4, max(px, X) + 0.4, Y + 0.4); sq("via3", X, Y, 0.36); sq("metal3", X, Y, 0.5)
    rec("m4", net, px - 0.4, Y - 0.4, px + 0.4, H_TILE); term(net, X, Y, m3only=True)
# ---- unused outputs -> VGND (met3 bus y 222.6, x 29-95)
OUTX = [30.82 + 2.76 * i for i in range(8)] + [52.9 + 2.76 * i for i in range(8)] + [74.98 + 2.76 * i for i in range(8)]
bus_y = 222.6
paint("metal3", 4.6, bus_y - 0.4, max(OUTX) + 0.6, bus_y + 0.4); rec("m3", "VGND", 4.6, bus_y - 0.4, max(OUTX) + 0.6, bus_y + 0.4)
paint("metal4", 4.5, 219.0, 6.5, bus_y + 0.4); sq("via3", 5.5, bus_y, 0.36)
for x in OUTX:
    paint("metal4", x - 0.15, bus_y - 0.4, x + 0.15, H_TILE); sq("via3", x, bus_y, 0.36); sq("metal4", x, bus_y, 0.5)
json.dump(dict(TERMS={k: v for k, v in TERMS.items()}, M3ONLY=list(M3ONLY), M2ONLY=list(M2ONLY), SEG=SEG, MIMR=MIMR, ENV=ENV, INST=INST,
               DNW=DNW, STRIPES=STRIPES), open("prerouted.json", "w"))
open("build5_place.tcl", "w").write("\n".join(tcl) + "\n")
# ---- envelope overlap check (device envelopes incl. straps/stacks)
def ov(a, b, g): return not (a[2] + g <= b[0] or b[2] + g <= a[0] or a[3] + g <= b[1] or b[3] + g <= a[1])
bad = [(ENV[i][0], ENV[j][0]) for i in range(len(ENV)) for j in range(i + 1, len(ENV)) if ov(ENV[i][1:], ENV[j][1:], 0.2)]
outside = [e[0] for e in ENV if e[1] < 7.0 or e[3] > W_TILE - 0.5 or e[2] < 4.6 or e[4] > 221.5]
print(f"instances {len(INST)}, envelopes {len(ENV)}, overlaps {len(bad)}, outside {outside}", file=sys.stderr)
for b in bad[:60]: print("  OVL", b, file=sys.stderr)
