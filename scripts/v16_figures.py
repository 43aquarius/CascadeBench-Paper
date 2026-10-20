#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.6 figure: regenerate fig8 (paper Fig. 4, real-validation) with the
Whisper large-v3-turbo six-level curve added to the released v1.5.1 design.
Conventions (canvas, fonts, colors, series) are kept identical to
v15_figures.py; the only change is one added series per panel."""
import os, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
for fcand in ['/usr/share/fonts/truetype/chinese/NotoSansSC[wght].ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
    try:
        fm.fontManager.addfont(fcand)
    except Exception:
        pass
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Noto Sans SC']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams.update({'font.size': 10, 'axes.titlesize': 11, 'axes.labelsize': 10.5,
                     'legend.fontsize': 9.5, 'xtick.labelsize': 9.5, 'ytick.labelsize': 9.5})

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)              # repository root
FIG = os.path.join(ROOT, "figures")
X = json.load(open(f"{ROOT}/results/analysis_ext.json"))
V15 = json.load(open(f"{ROOT}/results/analysis_v15_real.json"))
V16 = json.load(open(f"{ROOT}/results/analysis_v16_whisper_curve.json"))
C = {"para16k": "#1f77b4", "para8k": "#17becf", "q31": "#d62728", "q3": "#ff7f0e",
     "whisper": "#7f7f7f", "lg3t": "#2ca02c"}

snr = X["snr_curves_v2"]
lad = V15["asr_real_all"]
turbo = V16["ladder"]
RB = [("rb10", 10), ("rb5", 5), ("rb25", 2.5), ("rb0", 0), ("rbm25", -2.5), ("rbm5", -5)]
NAME8 = {"para16k": "Paraformer-RT-v2", "para8k": "Paraformer-RT-8K (zh)",
         "q31": "Qwen-Audio-3.1", "q3": "Qwen3-ASR",
         "whisper": "Whisper small (non-vendor, local)",
         "lg3t": "Whisper lg-v3-turbo (non-vendor, local)"}

fig, axes = plt.subplots(1, 2, figsize=(8.6, 4.0), sharey=True, constrained_layout=True)
for ai, lang in enumerate(["zh", "en"]):
    ax = axes[ai]
    for sysk in ["para16k", "para8k", "q31", "q3"]:
        if sysk == "para8k" and lang != "zh":
            continue
        col = C[sysk]
        pts = snr.get(sysk, {}).get(lang, [])
        if pts:
            xs = [p["snr"] for p in pts]
            ys = [p["mean"] for p in pts]
            lo = [p["ci_lo"] for p in pts]
            hi = [p["ci_hi"] for p in pts]
            ax.plot(xs, ys, "-", color=col, lw=1.0, alpha=0.7,
                    label=f"{NAME8[sysk]} (synth.)" if ai == 0 else None)
            ax.fill_between(xs, lo, hi, color=col, alpha=0.07, linewidth=0)
        xs2, ys2 = [], []
        for cond, s in RB:
            cell = lad.get(sysk, {}).get(f"{cond}/{lang}")
            if cell:
                xs2.append(s)
                ys2.append(cell["err"])
        if xs2:
            ax.plot(xs2, ys2, "--o", color=col, lw=2.0, markersize=4.5,
                    label=f"{NAME8[sysk]} (real)" if ai == 0 else None,
                    markeredgecolor="white", markeredgewidth=0.6)
    # Whisper small: four tested conditions (released series)
    xs3, ys3 = [], []
    for cond, s in [("rb5", 5), ("rb0", 0), ("rbm5", -5)]:
        cell = lad.get("whisper", {}).get(f"{cond}/{lang}")
        if cell:
            xs3.append(s)
            ys3.append(cell["err"])
    if xs3:
        ax.plot(xs3, ys3, "--s", color=C["whisper"], lw=1.8, markersize=5,
                label=f"{NAME8['whisper']} (real)" if ai == 0 else None,
                markeredgecolor="white", markeredgewidth=0.6)
    # NEW v1.6: Whisper large-v3-turbo, all six levels
    xs4, ys4 = [], []
    for cond, s in RB:
        cell = turbo.get(f"{cond}/{lang}")
        if cell:
            xs4.append(s)
            ys4.append(cell["err"])
    if xs4:
        ax.plot(xs4, ys4, "--^", color=C["lg3t"], lw=2.0, markersize=5.5,
                label=f"{NAME8['lg3t']} (real)" if ai == 0 else None,
                markeredgecolor="white", markeredgewidth=0.6)
    ax.axhline(100, color="#999", lw=0.7, ls=":")
    ax.text(11, 106, "CER = 100%", ha="right", fontsize=8.5, color="#777")
    ax.axhline(10, color="#999", lw=0.7, ls="--")
    ax.set_xlabel("SNR (dB)")
    ax.set_title("Mandarin (AISHELL-1 test)" if lang == "zh"
                 else "English (LibriSpeech test-clean)", fontsize=10.5)
    ax.set_xticks([10, 5, 2.5, 0, -2.5, -5])
    ax.set_xlim(-6.5, 11.5)
    ax.set_ylim(-5, 230)
    ax.grid(alpha=0.25, lw=0.5)
axes[0].set_ylabel("Error rate (%)")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="upper center", bbox_to_anchor=(0.5, 1.12), ncol=3,
           frameon=False, fontsize=8.5)
fig.savefig(f"{FIG}/fig8_real_validation.pdf", bbox_inches="tight", dpi=300)
fig.savefig(f"{FIG}/fig8_real_validation.png", bbox_inches="tight", dpi=300)
plt.close(fig)
print("saved fig8_real_validation (v1.6: + lg-v3-turbo series)")
