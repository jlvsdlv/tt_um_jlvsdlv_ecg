import json, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
D = json.load(open("results/v5_freqresp.json"))
INK, MUTED, GRID, BLUE, BAND = "#1f2328", "#6e7781", "#e6e8eb", "#2563eb", "#f1f5fb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": "#c9ced4", "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False})
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 6.2), dpi=200, sharex=True, gridspec_kw=dict(height_ratios=[2.2, 1], hspace=0.08))
for ax in (a1, a2):
    ax.axvspan(0.5, 150, color=BAND, zorder=0); ax.grid(True, which="major", color=GRID, lw=0.8); ax.set_xscale("log")
for d in D:
    if d["f"] is None or (d["corner"], d["temp"]) == ("tt", 27): continue
    f = np.array(d["f"]); a1.plot(f, 20*np.log10(d["mag"]), color="#b8bec6", lw=1.0, zorder=2); a2.plot(f, d["ph"], color="#b8bec6", lw=1.0, zorder=2)
tt = [d for d in D if (d["corner"], d["temp"]) == ("tt", 27)][0]; f = np.array(tt["f"]); g = 20*np.log10(tt["mag"])
a1.plot(f, g, color=BLUE, lw=2.0, zorder=3); a2.plot(f, tt["ph"], color=BLUE, lw=2.0, zorder=3)
a1.set_ylim(0, 40); a1.set_ylabel("Differential gain (dB)"); a2.set_ylabel("Phase (°)"); a2.set_xlabel("Frequency (Hz)")
a2.set_xlim(1e-3, 1e5); a2.set_ylim(-110, 110); a2.set_yticks([-90, 0, 90])
a1.text(0.5*np.sqrt(300), 1.5, "ECG band 0.5–150 Hz", ha="center", color=MUTED, fontsize=9)
a1.annotate("tt, 27 °C: 33.7 dB\nHP 1.9 mHz · LP 2.3 kHz", xy=(20, g[np.argmin(abs(f-20))]), xytext=(2e-3, 22),
            color=INK, fontsize=9.5, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
a1.annotate("other 9 PVT corners\n32.9–34.0 dB, HP <1 to 66 mHz", xy=(3e3, 30.5), xytext=(1.2e3, 37), color=MUTED, fontsize=9, ha="left")
a1.set_title("Post-layout frequency response, tt_um_jlvsdlv_ecg", loc="left", color=INK, fontsize=11.5, pad=10)
fig.text(0.125, -0.005, "Extracted parasitic C back-annotated; Cpf 0.84 pF; per-corner Ct trim; TT 500 Ω / 5 pF pin path + 8.8 pF per output. "
         "Corners: tt/ss/ff/sf/fs at 27 °C, tt/ss at 0 °C, tt at 37/60 °C, ff at 60 °C.", fontsize=7.5, color=MUTED, wrap=True)
plt.savefig("fig_v5_freqresp.png", bbox_inches="tight")
