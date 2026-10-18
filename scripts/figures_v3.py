#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CascadeBench v1.2 figure: fig8 real-speech validation curves
synthetic 8-pt SNR curves (thin solid) vs real-babble 3-pt curves (thick dashed)."""
import os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
for fcand in ['/usr/share/fonts/truetype/chinese/NotoSansSC[wght].ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
    try: fm.fontManager.addfont(fcand)
    except Exception: pass
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Noto Sans SC', 'WenQuanYi Zen Hei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams.update({'font.size': 9, 'axes.titlesize': 10, 'axes.labelsize': 9,
                     'legend.fontsize': 7.5, 'xtick.labelsize': 8, 'ytick.labelsize': 8})

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D3D = os.path.join(ROOT, "corpus")
FIG = os.path.join(ROOT, "figures")
X = json.load(open(os.path.join(ROOT, "results", "analysis_ext.json")))
D3 = json.load(open(os.path.join(ROOT, "results", "d3_analysis.json")))
os.makedirs(FIG, exist_ok=True)

C = {"para16k": "#1f77b4", "para8k": "#17becf", "q31": "#d62728", "q3": "#ff7f0e"}
NAME = {"para16k": "Paraformer-RT-v2", "para8k": "Paraformer-RT-8K (zh)",
        "q31": "Qwen-Audio-3.1", "q3": "Qwen3-ASR"}

fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9), sharey=True, constrained_layout=True)
for ai, lang in enumerate(["zh", "en"]):
    ax = axes[ai]
    lname = "Mandarin (AISHELL-1 test)" if lang == "zh" else "English (LibriSpeech test-clean)"
    for sysk in ["para16k", "para8k", "q31", "q3"]:
        if sysk == "para8k" and lang != "zh":
            continue
        # synthetic curve
        try:
            pts = X["snr_curves_v2"][sysk][lang]
            xs = [p["snr"] for p in pts]; ys = [p["mean"] for p in pts]
            lo = [p["ci_lo"] for p in pts]; hi = [p["ci_hi"] for p in pts]
            ax.plot(xs, ys, "-", color=C[sysk], lw=1.1, alpha=0.75,
                    label=f"{NAME[sysk]} (synth.)" if ai == 0 else None)
            ax.fill_between(xs, lo, hi, color=C[sysk], alpha=0.08, linewidth=0)
        except Exception:
            pass
        # real 3-pt curve
        try:
            means = D3["real_babble_slopes"][f"{sysk}_{lang}"]["means_5_0_m5"]
            ax.plot([5, 0, -5], means, "--o", color=C[sysk], lw=2.0, markersize=5.5,
                    label=f"{NAME[sysk]} (real)" if ai == 0 else None,
                    markeredgecolor="white", markeredgewidth=0.7)
        except Exception:
            pass
    ax.set_xlabel("SNR (dB)")
    ax.set_title(lname)
    ax.set_xticks([20, 10, 5, 0, -5, -10])
    ax.set_xlim(-11, 21)
    ax.set_ylim(-5, 230)
    ax.axhline(100, color="#999", lw=0.6, ls=":")
    ax.text(20, 104, "CER = 100%", ha="right", fontsize=7, color="#777")
    ax.grid(alpha=0.25, lw=0.5)
axes[0].set_ylabel("Error rate (%)")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="upper center", bbox_to_anchor=(0.5, 1.13), ncol=4, frameon=False)
fig.savefig(f"{FIG}/fig8_real_validation.pdf", bbox_inches="tight", dpi=300)
fig.savefig(f"{FIG}/fig8_real_validation.png", bbox_inches="tight", dpi=300)
plt.close(fig)
print("saved fig8_real_validation")
