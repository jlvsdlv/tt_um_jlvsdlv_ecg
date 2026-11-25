"""Publication-style schematic of the v4 amplifier (SVG -> PNG)."""
import cairosvg
W, H = 1330, 860
el = []
def L(x1, y1, x2, y2, w=1.6): el.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#000" stroke-width="{w}" stroke-linecap="round"/>')
def PL(pts, w=1.6): el.append('<polyline points="' + " ".join(f"{x},{y}" for x, y in pts) + f'" fill="none" stroke="#000" stroke-width="{w}" stroke-linejoin="round"/>')
def D(x, y): el.append(f'<circle cx="{x}" cy="{y}" r="3.2" fill="#000"/>')
def T(x, y, s, a="middle", sz=15, it=False, b=False, col="#000", halo=False):
    st = ("font-style:italic;" if it else "") + ("font-weight:bold;" if b else "")
    # split into (text, is_sub) segments; sub() marks subscripts with \x02..\x03
    segs, buf, insub = [], "", False
    for ch in s:
        if ch == "\x02": segs.append((buf, False)); buf = ""; insub = True
        elif ch == "\x03": segs.append((buf, True)); buf = ""; insub = False
        else: buf += ch
    segs.append((buf, insub)); segs = [g for g in segs if g[0]]
    WD = {"M": .83, "W": .94, "I": .28, "J": .5, "m": .83, "w": .72, "i": .22, "l": .22, "j": .22, "f": .28, "t": .28, "r": .33,
          " ": .278, ".": .278, ",": .278, ":": .278, "(": .333, ")": .333, "[": .278, "]": .278, "–": .556, "→": 1.0, "Φ": .76,
          "×": .584, "µ": .576, "Ω": .768, "≈": .584, "=": .584, "+": .584, "−": .584, "/": .278, "_": .556}
    cw = lambda t, ss: sum(WD.get(c, 0.667 if c.isupper() else 0.556) for c in t) * ss
    widths = [cw(t, sz * (0.72 if sb else 1.0)) for t, sb in segs]; tot = sum(widths)
    x0 = x if a == "start" else (x - tot / 2 if a == "middle" else x - tot)
    if halo: el.append(f'<rect x="{x0-2}" y="{y-sz*0.62}" width="{tot+4}" height="{sz*1.35}" fill="#fff"/>')
    for (t, sb), w in zip(segs, widths):
        ss = sz * (0.72 if sb else 1.0); yy = y + (sz * 0.32 if sb else 0)
        el.append(f'<text xml:space="preserve" x="{x0:.1f}" y="{yy:.1f}" text-anchor="start" dominant-baseline="central" style="font-family:Helvetica,Arial,sans-serif;font-size:{ss:.1f}px;{st}" fill="{col}">{t}</text>')
        x0 += w
def sub(n, s): return f"{n}\x02{s}\x03"
def mos(x, y, typ="p", s=1, name="", nm_side=None):
    """channel at x, centre y. s=+1: gate on left, stubs to the right. returns terminal dict"""
    cx = x
    L(cx, y - 18, cx, y + 18, 2.4)                       # channel
    gx = cx - s * 8
    L(gx, y - 14, gx, y + 14, 2.0)                       # gate plate
    if typ == "p":
        el.append(f'<circle cx="{gx - s*5}" cy="{y}" r="4" fill="#fff" stroke="#000" stroke-width="1.5"/>')
        L(gx - s * 9, y, gx - s * 26, y)
    else:
        L(gx, y, gx - s * 26, y)
    top, bot = (cx + s * 16, y - 32), (cx + s * 16, y + 32)
    PL([(cx, y - 12), (cx + s * 16, y - 12), top]); PL([(cx, y + 12), (cx + s * 16, y + 12), bot])
    # body stub with arrow
    L(cx, y, cx + s * 30, y, 1.4)
    ax = cx + s * 9
    if typ == "n": el.append(f'<polygon points="{cx+s*2},{y} {ax},{y-4} {ax},{y+4}" fill="#000"/>')
    else: el.append(f'<polygon points="{ax},{y} {cx+s*2},{y-4} {cx+s*2},{y+4}" fill="#000"/>')
    if name: T(cx - s * 30 if nm_side is None else nm_side, y - 26, name, a="end" if s > 0 else "start", sz=14)
    return dict(G=(gx - s * 26, y), S=top if typ == "p" else bot, D=bot if typ == "p" else top, B=(cx + s * 30, y))
def capv(x, y1, y2, lab="", side=1, labx=None):
    m = (y1 + y2) / 2; L(x, y1, x, m - 5); L(x, m + 5, x, y2); L(x - 12, m - 5, x + 12, m - 5, 2.4); L(x - 12, m + 5, x + 12, m + 5, 2.4)
    if lab: T(x + side * 18 if labx is None else labx, m, lab, a="start" if side > 0 else "end", sz=14)
def caph(x1, x2, y, lab="", up=True):
    m = (x1 + x2) / 2; L(x1, y, m - 5, y); L(m + 5, y, x2, y); L(m - 5, y - 12, m - 5, y + 12, 2.4); L(m + 5, y - 12, m + 5, y + 12, 2.4)
    if lab: T(m, y - 22 if up else y + 24, lab, sz=14)
def resv(x, y1, y2, lab="", side=1):
    n = 6; h = (y2 - y1 - 20) / n; pts = [(x, y1), (x, y1 + 10)]
    for i in range(n): pts.append((x + (7 if i % 2 == 0 else -7), y1 + 10 + h * (i + 0.5)))
    pts += [(x, y2 - 10), (x, y2)]; PL(pts, 1.5)
    if lab: T(x + side * 14, (y1 + y2) / 2, lab, a="start" if side > 0 else "end", sz=14)
def gnd(x, y):
    L(x, y, x, y + 8); L(x - 10, y + 8, x + 10, y + 8, 1.8); L(x - 6, y + 12, x + 6, y + 12, 1.6); L(x - 2.5, y + 16, x + 2.5, y + 16, 1.4)
def isrc(x, y1, y2, lab):
    m = (y1 + y2) / 2; L(x, y1, x, m - 14); L(x, m + 14, x, y2)
    el.append(f'<circle cx="{x}" cy="{m}" r="14" fill="#fff" stroke="#000" stroke-width="1.6"/>')
    L(x, m - 8, x, m + 8, 1.6); el.append(f'<polygon points="{x},{m+9} {x-4},{m+2} {x+4},{m+2}" fill="#000"/>')
    T(x - 22, m, lab, a="end", sz=14)

VDD, GND = 70, 610
L(70, VDD, 1050, VDD, 2.0); T(74, VDD - 16, sub("V", "DD") + " = 1.0 V", a="start", sz=14)
# ---------------- bias mirror
mb1 = mos(150, 120, "p", s=-1, name=sub("M", "B1"), nm_side=200)
L(mb1["S"][0], mb1["S"][1], mb1["S"][0], VDD)
mb2 = mos(560, 120, "p", s=1, name=sub("M", "B2"), nm_side=520)
L(mb2["S"][0], mb2["S"][1], mb2["S"][0], VDD)
L(mb1["G"][0], 120, mb2["G"][0], 120); D(mb1["G"][0], 120)
L(mb1["G"][0], 120, mb1["G"][0], 175); L(mb1["G"][0], 175, mb1["D"][0], 175); D(mb1["D"][0], 175)
L(mb1["D"][0], mb1["D"][1], mb1["D"][0], 200)
isrc(mb1["D"][0], 200, 290, sub("I", "B") + " ≈ 50 nA"); gnd(mb1["D"][0], 290); T(mb1["D"][0] - 22, 263, "(on-chip ref.)", a="end", sz=11)
L(mb1["B"][0], 120, mb1["B"][0], VDD); L(mb2["B"][0], 120, mb2["B"][0], VDD)
TAIL = 190
L(mb2["D"][0], mb2["D"][1], mb2["D"][0], TAIL); D(mb2["D"][0], TAIL); T(mb2["D"][0] + 10, TAIL - 12, "tail", a="start", sz=13, it=True)
# ---------------- input pair (pMOS), AC-coupled DTMOS bodies
XL, XR = 430, 690
m1 = mos(XL, 250, "p", s=1, name=sub("M", "1"), nm_side=XL - 34)
m2 = mos(XR, 250, "p", s=-1, name=sub("M", "2"), nm_side=XR + 34)
L(m1["S"][0], TAIL, m2["S"][0], TAIL); L(m1["S"][0], TAIL, m1["S"][0], m1["S"][1]); L(m2["S"][0], TAIL, m2["S"][0], m2["S"][1])
# bodies -> nw nodes, Rb to tail, Cbc to gate
for m, s, nm in ((m1, 1, "1"), (m2, -1, "2")):
    bx = m["B"][0]; L(bx, 250, bx + s * 22, 250); nx = bx + s * 22; D(nx, 250)
    T(nx + s * 6, 262, sub("nw", nm), a="start" if s > 0 else "end", sz=13, it=True)
    resv(nx, TAIL + 6, 250 - 4, sub("R", "b") if s > 0 else "", side=s); L(nx, TAIL, nx, TAIL + 6); D(nx, TAIL) if False else None
    L(nx, TAIL, m["S"][0], TAIL)
    # Cbc from gate node (left/right of gate) down and across to nw
    gx = m["G"][0]; L(gx, 250, gx - s * 34, 250); D(gx - s * 20, 250)
    PL([(gx - s * 20, 250), (gx - s * 20, 300)]); caph(min(gx - s * 20, nx), max(gx - s * 20, nx), 300, "")
    L(nx, 250, nx, 300)
T(m1["G"][0] - 20 + (m1["B"][0] + 22 - (m1["G"][0] - 20)) / 2, 320, sub("C", "bc"), sz=14)
T(m2["G"][0] + 20 - ((m2["G"][0] + 20) - (m2["B"][0] - 22)) / 2, 320, sub("C", "bc"), sz=14)
VI1x, VI2x = m1["G"][0] - 34, m2["G"][0] + 34
D(VI1x, 250); D(VI2x, 250); T(VI1x - 8, 250, sub("v", "i1"), a="end", sz=16, it=True); T(VI2x + 8, 250, sub("v", "i2"), a="start", sz=16, it=True)
# PF caps from inputs to the opposite-side label (vo1 -> vi1, vo2 -> vi2)
for vx, s, lab in ((VI1x, 1, sub("v", "o1")), (VI2x, -1, sub("v", "o2"))):
    L(vx, 250, vx, 215); caph(vx - s * 0, vx - s * 0, 215) if False else None
    PL([(vx, 250), (vx, 205)]); L(vx, 205, vx - s * 18, 205); caph(min(vx - s * 18, vx - s * 62), max(vx - s * 18, vx - s * 62), 205, "")
    T(vx - s * 70, 205, lab, a="end" if s > 0 else "start", sz=15, it=True)
    T(vx - s * 40, 180, sub("C", "pf") + " (fixed)", sz=13)
    # v5: input-node trim bank Ct to ground (LSB not multiplied by the gain)
    cx = vx - s * 22; PL([(vx, 250), (vx, 264), (cx, 264)]); D(vx, 264); capv(cx, 264, 322, "", side=-s); gnd(cx, 322)
    T(cx - s * 26, 296, sub("C", "t"), a="end" if s > 0 else "start", sz=14); T(cx - s * 26, 312, "(10-bit)", a="end" if s > 0 else "start", sz=10)
# ---------------- outputs
VO = 370
L(m1["D"][0], m1["D"][1], m1["D"][0], VO); L(m2["D"][0], m2["D"][1], m2["D"][0], VO)
# ---------------- split loads M3A/M3B (left), M4A/M4B (right) in deep n-wells
YL = 450
def loadpair(xa, xb, s, names, wells):
    ma = mos(xa, YL, "n", s=s, name=names[0], nm_side=xa - s * 30); mb = mos(xb, YL, "n", s=s, name=names[1], nm_side=xb - s * 30)
    for m, w in ((ma, wells[0]), (mb, wells[1])):
        T(m["B"][0] + s * 4, YL - 11, w, a="start" if s > 0 else "end", sz=13, it=True)
        L(m["S"][0], m["S"][1], m["S"][0], GND)
    return ma, mb
m3a, m3b = loadpair(340, 420, 1, (sub("M", "3A"), sub("M", "3B")), (sub("w", "A"), sub("w", "B")))
m4a, m4b = loadpair(780, 700, -1, (sub("M", "4A"), sub("M", "4B")), (sub("w", "A"), sub("w", "B")))
# drains to vo nodes
L(m3a["D"][0], m3a["D"][1], m3a["D"][0], VO); L(m3b["D"][0], m3b["D"][1], m3b["D"][0], VO)
L(m3a["D"][0], VO, m1["D"][0], VO); D(m3b["D"][0], VO); D(m1["D"][0], VO)
L(m4a["D"][0], m4a["D"][1], m4a["D"][0], VO); L(m4b["D"][0], m4b["D"][1], m4b["D"][0], VO)
L(m4a["D"][0], VO, m2["D"][0], VO); D(m4b["D"][0], VO); D(m2["D"][0], VO)
# gates -> g3 / g4 buses (below)
GB = 540
for m in (m3a, m3b): PL([m["G"], (m["G"][0], GB)]); D(m["G"][0], GB)
for m in (m4a, m4b): PL([m["G"], (m["G"][0], GB)]); D(m["G"][0], GB)
# vo2 left node, feedback Rf || Cf to g3
XF = 215
L(XF, VO, m3a["D"][0], VO); D(m3a["D"][0], VO); D(XF + 40, VO)
T(XF + 40, VO - 14, sub("v", "o2"), sz=16, it=True)
L(XF, VO, XF, 420); L(XF + 50, VO, XF + 50, 420)
L(XF, 420, XF + 50, 420); resv(XF, 420, 510, sub("R", "f"), side=-1); capv(XF + 50, 420, 510, sub("C", "f"), side=1, labx=XF + 64)
L(XF, 510, XF + 50, 510); L(XF + 25, 510, XF + 25, GB); D(XF + 25, GB)
L(XF + 25, GB, m3b["G"][0], GB); T(XF + 25, GB + 18, sub("g", "3"), sz=15, it=True)
XFR = 905
L(XFR, VO, m4a["D"][0], VO); D(m4a["D"][0], VO); D(XFR - 40, VO)
T(XFR - 40, VO - 14, sub("v", "o1"), sz=16, it=True)
L(XFR, VO, XFR, 420); L(XFR - 50, VO, XFR - 50, 420); L(XFR, 420, XFR - 50, 420)
resv(XFR, 420, 510, sub("R", "f"), side=1); capv(XFR - 50, 420, 510, sub("C", "f"), side=-1, labx=XFR - 64)
L(XFR, 510, XFR - 50, 510); L(XFR - 25, 510, XFR - 25, GB); D(XFR - 25, GB)
L(XFR - 25, GB, m4b["G"][0], GB); T(XFR - 25, GB + 18, sub("g", "4"), sz=15, it=True)
# cross-coupled Cg between g3 and g4
L(m3b["G"][0], GB, m3b["G"][0], 575); L(m4b["G"][0], GB, m4b["G"][0], 575)
caph(m3b["G"][0], m4b["G"][0], 575, "", up=True); T(560, 552, sub("C", "g"), sz=14)
# outputs to pads
for x, s, lab in ((XF, -1, "ua[3]"), (XFR, 1, "ua[2]")):
    L(x, VO, x + s * 70, VO); el.append(f'<circle cx="{x + s*76}" cy="{VO}" r="6" fill="#fff" stroke="#000" stroke-width="1.6"/>')
    T(x + s * 76, VO + 20, lab, sz=13)
    T(x + s * 76, VO + 38, "pad + " + sub("C", "L,ext"), sz=12)
# ground rail
L(70, GND, 1050, GND, 2.0); T(60, GND, "GND", a="end", sz=14)
# deep n-well boxes
for x0, x1 in ((300, 470), (650, 820)):
    el.append(f'<rect x="{x0}" y="{YL-48}" width="{x1-x0}" height="96" rx="8" fill="none" stroke="#555" stroke-width="1.2" stroke-dasharray="6,4"/>')
T(385, YL + 60, "deep n-well, split p-wells", sz=12, col="#333", halo=True); T(735, YL + 60, "deep n-well, split p-wells", sz=12, col="#333", halo=True)
# ---------------- two-phase bulk driver (bottom)
Y0 = 680
el.append(f'<rect x="80" y="{Y0-36}" width="960" height="150" rx="6" fill="none" stroke="#000" stroke-width="1.2"/>')
T(92, Y0 - 22, "Two-phase bulk-switching driver (1.8 V domain)", a="start", sz=14, b=True)
def gate_nand(x, y):
    el.append(f'<path d="M{x},{y-16} L{x+18},{y-16} A16,16 0 0 1 {x+18},{y+16} L{x},{y+16} Z" fill="#fff" stroke="#000" stroke-width="1.6"/>')
    el.append(f'<circle cx="{x+38}" cy="{y}" r="3.5" fill="#fff" stroke="#000" stroke-width="1.4"/>'); return (x + 42, y)
def buf(x, y):
    el.append(f'<polygon points="{x},{y-14} {x+26},{y} {x},{y+14}" fill="#fff" stroke="#000" stroke-width="1.6"/>'); return (x + 26, y)
for i, (ph, w, inv) in enumerate((("A", sub("w", "A"), False), ("B", sub("w", "B"), True))):
    y = Y0 + 18 + i * 52
    T(150, y - 8, "clk" if not inv else "clk", a="end", sz=13); L(155, y - 8, 230, y - 8)
    if inv: el.append(f'<circle cx="226" cy="{y-8}" r="3.5" fill="#fff" stroke="#000" stroke-width="1.4"/>'); L(155, y - 8, 222, y - 8)
    T(150, y + 9, "en (uio[2])", a="end", sz=12); L(155, y + 9, 230, y + 9)
    o = gate_nand(230, y); L(o[0], y, 300, y); o = buf(300, y); L(o[0], y, 350, y); o = buf(350, y)
    L(o[0], y, 430, y); T(400, y - 12, sub("Φ", ph), sz=14, it=True)
    caph(430, 500, y, "", up=True); T(465, y - 24, sub("C", "c" + ph) + " 5 pF", sz=13)
    L(500, y, 560, y); D(540, y)
    # clamp diode to ground
    L(540, y, 540, y + 6)
    el.append(f'<polygon points="{533},{y+6} {547},{y+6} {540},{y+18}" fill="#fff" stroke="#000" stroke-width="1.4"/>'); L(533, y + 18, 547, y + 18, 1.6)
    L(540, y + 18, 540, y + 24); L(534, y + 24, 546, y + 24, 1.6)
    T(560 + 6, y, "→ " + w, a="start", sz=15, it=True)
T(548, Y0 + 104, "clamp: n+/p-well", sz=11, col="#333")
# waveform inset
def wave(x, y, phase):
    pts = []; xx = x; hi, lo = y - 10, y + 14
    lvl = hi if phase == 0 else lo
    for k in range(6):
        pts += [(xx, lvl), (xx + 30, lvl)]; xx += 30; lvl = lo if lvl == hi else hi; pts.append((xx, lvl))
    PL(pts, 1.5)
wave(700, Y0 + 14, 0); T(692, Y0 + 14, sub("v", "wA"), a="end", sz=14, it=True)
wave(700, Y0 + 66, 1); T(692, Y0 + 66, sub("v", "wB"), a="end", sz=14, it=True)
T(905, Y0 + 4, "+0.03 V (inversion)", a="start", sz=11); T(905, Y0 + 28, "−1.38 V (accum.)", a="start", sz=11)
T(905, Y0 + 56, "complementary:", a="start", sz=11); T(905, Y0 + 72, "one half always on", a="start", sz=11)
# ---------------- sizing table (right)
tab = [sub("M","1") + ", " + sub("M","2") + ": pfet lvt 800/8 (32×25/8)", sub("M","3A") + "–" + sub("M","4B") + ": nfet lvt 2×(2.5/64)", sub("M","B1") + " : " + sub("M","B2") + " = 1 : 20,  " + sub("I","tail") + " = 1 µA",
       sub("C","bc") + " ≈ 17–22 pF (var || MIM),  " + sub("R","b") + " ≈ 0.4–0.9 TΩ", "  (" + sub("R","b") + ": replica-biased pseudo-R, 0.5 nA)", sub("C","pf") + " = 0.82 pF,  " + sub("C","t") + " = 0–5.3 pF (≈11 fF res.)",
       sub("C","g") + " = 15 pF,  " + sub("C","f") + " = 1.12 pF,  " + sub("R","f") + ": pfet 0.42/4", sub("R","f") + ", " + sub("R","b") + " reset sw.: pfet lvt 0.42/0.5", sub("C","L,ext") + " ≈ 8.8 pF,  gain ≈ 33.7 dB,  " + sub("f","s") + " = 2 kHz"]
el.append(f'<rect x="1068" y="94" width="262" height="{len(tab)*21+30}" fill="#fff" stroke="#000" stroke-width="1"/>')
T(1076, 104, "Device values", a="start", sz=12, b=True)
for i, s in enumerate(tab): T(1076, 126 + 21 * i, s, a="start", sz=11.5)
# bias-electrode driver (block level)
BY = 330
el.append(f'<rect x="1068" y="{BY}" width="262" height="250" fill="#fff" stroke="#000" stroke-width="1"/>')
T(1076, BY + 12, "Bias-electrode driver (CM loop)", a="start", sz=12, b=True)
el.append(f'<polygon points="1150,{BY+40} 1150,{BY+110} 1210,{BY+75}" fill="#fff" stroke="#000" stroke-width="1.6"/>')
T(1158, BY + 55, "−", a="start", sz=15); T(1158, BY + 96, "+", a="start", sz=13)
L(1100, BY + 55, 1150, BY + 55); T(1096, BY + 55, "tail", a="end", sz=12, it=True)
L(1120, BY + 96, 1150, BY + 96); L(1120, BY + 96, 1120, BY + 130); T(1145, BY + 144, sub("V","REF") + " = (6/7) " + sub("V","DD"), sz=11)
T(1150, BY + 158, "(7 matched pfet diodes)", sz=10)
L(1210, BY + 75, 1250, BY + 75); D(1250, BY + 75); L(1250, BY + 75, 1284, BY + 75)
el.append(f'<circle cx="1290" cy="{BY+75}" r="6" fill="#fff" stroke="#000" stroke-width="1.6"/>')
T(1288, BY + 96, "ua[4]", sz=11); T(1286, BY + 110, "bias electrode", sz=10)
T(1180, BY + 186, "2-stage OTA, Miller 10 pF, ~31 nA", sz=11)
T(1180, BY + 204, "locks tail at 0.85 V at all corners", sz=11)
T(1180, BY + 222, "input CM settles at 0.37–0.70 V", sz=11)
svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="#fff"/>' + "".join(el) + "</svg>"
open("/home/claude/amp/fig_v5.svg", "w").write(svg)
cairosvg.svg2png(bytestring=svg.encode(), write_to="/home/claude/amp/fig_v5_schematic.png", output_width=2800)
print("ok")
