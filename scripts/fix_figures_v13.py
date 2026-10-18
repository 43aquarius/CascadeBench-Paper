#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.3 figure fixes (review item 10): fig1 remove dangling arrow + larger fonts;
fig4_cascade_e2e larger legend for print size. Only regenerates these two."""
import os, json
import numpy as np
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
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Noto Sans SC', 'WenQuanYi Zen Hei']
plt.rcParams['axes.unicode_minus'] = False

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "figures")
X = json.load(open(f"{ROOT}/results/analysis_ext.json"))
C = {"para16k": "#1f77b4", "para8k": "#17becf", "q31": "#d62728", "q3": "#ff7f0e", "omni": "#9467bd", "lt": "#2ca02c"}

def save(fig, name):
    fig.savefig(f"{FIG}/{name}.pdf", bbox_inches="tight", dpi=300)
    fig.savefig(f"{FIG}/{name}.png", bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("saved", name)

# ---------------- fig1: architecture (dangling arrow removed, fonts enlarged) ----------------
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
fig, ax = plt.subplots(figsize=(10.5, 4.4))
ax.set_xlim(0, 105); ax.set_ylim(0, 42); ax.axis("off")
def box(x, y, w, h, text, fc="#eef3fb", ec="#3565a8", fs=9.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6", fc=fc, ec=ec, lw=1.2))
    ax.text(x+w/2, y+h/2, text, ha="center", va="center", fontsize=fs, wrap=True)
def arrow(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12, color="#555", lw=1.2))
box(1, 30, 17, 8, "480-sentence\nbilingual corpus\n(zh/en, 4 domains)", fc="#eefbe9", ec="#3d8b3d")
box(22, 30, 17, 8, "Neural TTS\n4 test voices +\n6 babble voices", fc="#eefbe9", ec="#3d8b3d")
box(43, 30, 20, 8, "Degradation grid\n8 conditions + 8-level\nSNR sweep (20 to -10 dB)", fc="#fff6e0", ec="#c98a00")
box(67.5, 33, 17, 5.5, "Recognition systems\n(3 product classes)")
box(67.5, 25.5, 17, 5.5, "LiveTranslate\ninternal frontend")
box(89, 30, 15, 8, "Text translation\n(qwen-mt-uni)\ncascade stage", fc="#f3eefa", ec="#7d4ba8")
box(67.5, 3, 17, 7, "End-to-end paths\nomni / LiveTranslate", fc="#f3eefa", ec="#7d4ba8")
box(89, 12, 15, 8, "Dual-reference\nscoring\nBLEU / chrF", fc="#fdeeee", ec="#b04040")
box(67.5, 13.5, 17, 7, "Error analysis\nCER / WER, refusals,\nthresholds, STOI")
arrow(18, 34, 22, 34); arrow(39, 34, 43, 34)
arrow(63, 35.5, 67.5, 35.5); arrow(63, 32, 67.5, 28.2)
arrow(84.5, 35.5, 89, 33.5); arrow(84.5, 28.2, 89, 31.5)
arrow(76, 25.5, 76, 10); arrow(84.5, 6.5, 89, 14)
arrow(84.5, 17, 89, 17.5)
ax.set_title("CascadeBench evaluation pipeline", fontsize=13, pad=2)
save(fig, "fig1_architecture")

# ---------------- fig4: cascade vs e2e, larger legend ----------------
tx = X["translation_ext"]
conds = ["clean","n20","n15","n10","n5","n25","n0","nm5"]
cond_lab = ["Clean","20","15","10","5","2.5","0","-5"]
paths = [("cascade_q31", "Cascade: Qwen-Audio + MT", C["q31"]),
         ("cascade_para16k", "Cascade: Paraformer + MT", C["para16k"]),
         ("cascade_q3", "Cascade: Qwen3-ASR + MT", C["q3"]),
         ("e2e_omni", "E2E: Omni-Flash", C["omni"]),
         ("e2e_lt", "E2E: LiveTranslate", C["lt"])]
fig, ax = plt.subplots(figsize=(10.5, 3.9))
w = 0.16
xs = np.arange(len(conds))
for k, (key, lab, col) in enumerate(paths):
    vals, errs = [], []
    for c in conds:
        if key.startswith("cascade_"):
            mk = key.split("_", 1)[1]
            d = tx["cascade"].get(mk, {}).get(c, {}).get("cond") or tx["cascade"].get(mk, {}).get(c, {}).get("eff")
            v = d["bleu"] if d else np.nan
        else:
            name = key.split("_", 1)[1]
            d = tx["e2e"].get(name, {}).get(c)
            v = d["bleu"] if d else np.nan
        vals.append(v)
        errs.append(1.5 if not np.isnan(v) else 0)
    ax.bar(xs + (k-2)*w, vals, w, label=lab, color=col, alpha=0.9,
           yerr=errs, capsize=1.5, error_kw={"lw": 0.7, "alpha": 0.6})
ax.axhline(55.5, color="#444", ls=":", lw=1.0)
ax.text(7.42, 56.3, "oracle MT 55.5", fontsize=8, ha="right", color="#444")
ax.set_xticks(xs); ax.set_xticklabels(cond_lab, fontsize=9)
ax.set_xlabel("Babble SNR (dB); remaining conditions in the text", fontsize=10)
ax.set_ylabel("BLEU (macro-avg, primary reference)", fontsize=10)
ax.set_ylim(0, 78)
ax.tick_params(axis="y", labelsize=9)
ax.legend(ncol=3, fontsize=9, loc="upper right", framealpha=0.95)
fig.tight_layout()
save(fig, "fig4_cascade_e2e")
print("done")
