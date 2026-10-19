#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.4: fig1 微调 — 字号 10、拥挤框加宽、三参考表述、增加留白"""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
for fcand in ['/usr/share/fonts/truetype/chinese/NotoSansSC[wght].ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
    try: fm.fontManager.addfont(fcand)
    except Exception: pass
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Noto Sans SC']
plt.rcParams.update({'font.size': 10})

from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
fig, ax = plt.subplots(figsize=(11.0, 4.8), constrained_layout=True)
ax.set_xlim(0, 105); ax.set_ylim(0, 42); ax.axis("off")
def box(x, y, w, h, text, fc="#eef3fb", ec="#3565a8", fs=10):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.7", fc=fc, ec=ec, lw=1.2))
    ax.text(x+w/2, y+h/2, text, ha="center", va="center", fontsize=fs, linespacing=1.25)
def arrow(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12, color="#555", lw=1.2))
box(1, 30, 17, 8.5, "480-sentence\nbilingual corpus\n(zh/en, 4 domains)", fc="#eefbe9", ec="#3d8b3d")
box(22, 30, 17, 8.5, "Neural TTS\n4 test voices +\n6 babble voices", fc="#eefbe9", ec="#3d8b3d")
box(43, 30, 21, 8.5, "Degradation grid\n8 conditions + 8-level\nSNR sweep (20 to -10 dB)", fc="#fff6e0", ec="#c98a00")
box(68, 33, 17, 5.5, "Recognition systems\n(3 product classes)")
box(68, 25.5, 17, 5.5, "LiveTranslate\ninternal frontend")
box(89.5, 30, 14.5, 8.5, "Text translation\n(qwen-mt-uni)\ncascade stage", fc="#f3eefa", ec="#7d4ba8")
box(68, 3, 17, 7.5, "End-to-end paths\nomni / LiveTranslate", fc="#f3eefa", ec="#7d4ba8")
box(89.5, 12, 14.5, 8.5, "Three-reference\nscoring\nBLEU / chrF", fc="#fdeeee", ec="#b04040")
box(68, 13.5, 17, 7.5, "Error analysis\nCER / WER, refusals,\nthresholds, STOI")
arrow(18, 34.2, 22, 34.2); arrow(39, 34.2, 43, 34.2)
arrow(64, 35.8, 68, 35.8); arrow(64, 32, 68, 28.2)
arrow(85, 35.8, 89.5, 33.5); arrow(85, 28.2, 89.5, 31.5)
arrow(76.5, 25.5, 76.5, 10.5); arrow(85, 6.7, 89.5, 14)
arrow(85, 17.2, 89.5, 17.7)
ax.set_title("CascadeBench evaluation pipeline", fontsize=13, pad=3)
FIG = os.path.join(ROOT, "figures")
fig.savefig(f"{FIG}/fig1_architecture.pdf", dpi=300)
fig.savefig(f"{FIG}/fig1_architecture.png", dpi=200)
print("fig1 saved")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

