import gdstk, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Rectangle
lib = gdstk.read_gds("out/gds/tt_um_ecg_v5.gds"); top = [c for c in lib.top_level() if c.name == "tt_um_ecg_v5"][0]
L = [((64, 20), "#e8dcc0", 0.5), ((64, 18), "#cfc4ea", 0.45), ((65, 20), "#8bc34a", 0.55), ((66, 20), "#d9534f", 0.55),
     ((68, 20), "#5b9bd5", 0.25), ((69, 20), "#e8a07a", 0.35), ((70, 20), "#7fcdbb", 0.3), ((89, 44), "#f2c94c", 0.35)]
polys = top.get_polygons(apply_repetitions=True, include_paths=True)
fig, ax = plt.subplots(figsize=(10, 6.75), dpi=220)
for (l, d), col, a in L:
    ax.add_collection(PolyCollection([p.points for p in polys if p.layer == l and p.datatype == d], facecolors=col, edgecolors="none", alpha=a))
B = [((10, 6, 97, 82), "Cbc: varactor ∥ MIM\n(AC-coupled DTMOS body)"),
     ((10, 90, 97, 82), "M3/M4 split loads, 2 isolated\np-wells in deep n-well\n(bulk-switched) + Cg MIM"),
     ((10, 174, 124, 34), "well-bias pseudo-R + replica,\nfeedback pseudo-R, reset switches"),
     ((112, 6, 148, 124), "M1/M2 DTMOS input pair\n(cross-quad, 2×800/8 µm)\nunder Cbc / Ct / Cpf MIM"),
     ((156, 130, 128, 34), "tail mirror + Cf, DRL Miller C"),
     ((156, 164, 104, 19), "bias-electrode (DRL) OTA"),
     ((156, 186, 56, 22), "2-phase switch\ndriver logic"),
     ((227, 182, 102, 36), "bulk-switch Cc (MIM)"),
     ((261, 6, 40, 78), "Ct\n10-bit\ntrim"),
     ((261, 86, 72, 30), "bias reference (β-mult.)"),
     ((302, 6, 31, 78), "xhigh-po\nR (trim)")]
for (x, y, w, h), t in B:
    ax.add_patch(Rectangle((x, y), w, h, fill=False, ec="#1f4e79", lw=1.3, ls="--"))
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=7.2, color="#0d2b45", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.85))
ax.set_xlim(0, 334.88); ax.set_ylim(0, 225.76); ax.set_aspect(1); ax.set_xticks([0, 100, 200, 300]); ax.set_yticks([0, 100, 200])
ax.tick_params(labelsize=7); ax.set_xlabel("µm", fontsize=7)
for s in ax.spines.values(): s.set_color("#888")
plt.savefig("/home/claude/pitch/layout_ann.png", bbox_inches="tight", pad_inches=0.02)
