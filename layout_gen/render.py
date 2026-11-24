import gdstk, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
lib = gdstk.read_gds("out/gds/tt_um_ecg_v5.gds"); top = [c for c in lib.top_level() if c.name == "tt_um_ecg_v5"][0]
# sky130 GDS layer numbers
L = [("nwell", (64, 20), "#d8c8a0", 0.35), ("dnwell", (64, 18), "#b0a0d8", 0.25), ("diff", (65, 20), "#6ab04c", 0.6),
     ("poly", (66, 20), "#d63031", 0.6), ("li1", (67, 20), "#a29bfe", 0.35), ("met1", (68, 20), "#0984e3", 0.35),
     ("met2", (69, 20), "#e17055", 0.4), ("met3", (70, 20), "#00b894", 0.35), ("capm", (89, 44), "#fdcb6e", 0.45), ("met4", (71, 20), "#636e72", 0.25)]
polys = top.get_polygons(apply_repetitions=True, include_paths=True)
fig, ax = plt.subplots(figsize=(16, 10.8), dpi=150)
for name, (l, d), col, a in L:
    ps = [p.points for p in polys if p.layer == l and p.datatype == d]
    ax.add_collection(PolyCollection(ps, facecolors=col, edgecolors="none", alpha=a, label=name))
ax.set_xlim(0, 334.88); ax.set_ylim(0, 225.76); ax.set_aspect(1)
ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=8, frameon=False)
ax.set_xlabel("µm"); ax.set_title("tt_um_ecg_v5 — TT 2×2 analog tile (334.88 × 225.76 µm)", fontsize=11)
plt.savefig("/home/claude/repo/tt_um_ecg_v5/docs/layout.png", bbox_inches="tight")
