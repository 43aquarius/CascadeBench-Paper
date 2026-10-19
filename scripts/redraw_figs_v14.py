#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.4 图重画: fig6 (CAC三条+CI带+温和/崩溃标记), fig4 (论文Fig5: 上面板SNR+下面板非噪声),
fig8 (真实6点曲线)
输出到 figures/"""
import os, sys, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
for fcand in ['/usr/share/fonts/truetype/chinese/NotoSansSC[wght].ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
    try: fm.fontManager.addfont(fcand)
    except Exception: pass
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Noto Sans SC']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams.update({'font.size': 9, 'axes.titlesize': 10, 'axes.labelsize': 9,
                     'legend.fontsize': 7.5, 'xtick.labelsize': 8, 'ytick.labelsize': 8})

FIG = os.path.join(ROOT, "figures")
RES = os.path.join(ROOT, "results")
X = json.load(open(f"{RES}/analysis_ext.json"))
V14 = json.load(open(f"{RES}/analysis_v14.json"))

C = {"para16k": "#1f77b4", "q31": "#d62728", "q3": "#ff7f0e", "omni": "#9467bd", "lt": "#2ca02c"}
NAME = {"q31": "Cascade: Qwen-Audio + MT", "para16k": "Cascade: Paraformer + MT",
        "q3": "Cascade: Qwen3-ASR + MT", "omni": "E2E: Omni-Flash", "lt": "E2E: LiveTranslate"}

# ================= fig6: CAC 三条 + CI 带 + 温和/崩溃 =================
cac = X["cac_v2"]
fig, ax = plt.subplots(figsize=(6.6, 4.8), constrained_layout=True)
COLLAPSE_TH = 40.0  # 崩溃条件阈值 (正文: excluding conditions above 40%)
for mk in ["q31", "para16k", "q3"]:
    d = cac[mk]
    pts = d["points"]
    xs = np.array([p["asr_err"] for p in pts]); ys = np.array([p["loss"] for p in pts])
    col = C[mk]
    b, a = np.polyfit(xs, ys, 1)
    r = d.get("pearson_r")
    slo, shi = d["slope_ci95"]
    ilo, ihi = d["intercept_ci95"]
    gx = np.linspace(0, max(115, xs.max() + 5), 60)
    ax.plot(gx, a + b * gx, color=col, lw=1.4, alpha=0.85, zorder=2)
    # 95% 联合置信带: slope CI x + intercept CI (保守楔形)
    ax.fill_between(gx, ilo + slo * gx, ihi + shi * gx, color=col, alpha=0.10, lw=0, zorder=1)
    # 温和 vs 崩溃标记
    mild = xs <= COLLAPSE_TH; colp = xs > COLLAPSE_TH
    ax.scatter(xs[mild], ys[mild], s=22, color=col, zorder=3, edgecolor="white", lw=0.5,
               label=f"{NAME[mk]} (n={len(pts)})")
    ax.scatter(xs[colp], ys[colp], s=52, color=col, marker="X", zorder=4,
               edgecolor="black", lw=0.6)
    # 标注: slope/intercept/r
    idx = ["q31", "para16k", "q3"].index(mk)
    ytxt = 0.97 - 0.115 * idx
    ax.text(0.98, ytxt, f"slope {b:.2f} (95% CI {slo:.2f}\u2013{shi:.2f}), intercept {a:+.1f}, r = {r:.3f}",
            transform=ax.transAxes, ha="right", va="top", fontsize=7.3, color=col)
ax.scatter([], [], s=22, color="#555", edgecolor="white", lw=0.5, label="Mild conditions (error \u2264 40%)")
ax.scatter([], [], s=52, color="#555", marker="X", edgecolor="black", lw=0.6, label="Collapsed conditions (error > 40%)")
ax.axvline(COLLAPSE_TH, color="#999", ls=":", lw=0.8)
ax.text(COLLAPSE_TH + 1.5, ax.get_ylim()[1] * 0.02, "40%", fontsize=7, color="#777")
ax.set_xlabel("Mean recognition error rate (%; refusals = 100% error)")
ax.set_ylabel("BLEU loss from clean (points)")
ax.set_xlim(-4, 120); ax.set_ylim(-4, 58)
ax.legend(loc="upper left", fontsize=7.3, framealpha=0.95)
ax.grid(alpha=0.2, lw=0.4)
fig.savefig(f"{FIG}/fig6_cac.pdf", dpi=300)
fig.savefig(f"{FIG}/fig6_cac.png", dpi=200)
plt.close(fig)
print("fig6 saved")

# ================= fig4 (论文Fig5): 上面板 SNR + 下面板非噪声 =================
tx = X["translation_ext"]
conds_top = ["clean", "n20", "n15", "n10", "n5", "n25", "n0", "nm5"]
lab_top = ["Clean", "20", "15", "10", "5", "2.5", "0", "-5"]
conds_bot = ["clean", "rev", "rev_mit", "nb", "opus", "pl", "clip", "tempo"]
lab_bot = ["Clean", "Reverb\n(synth.)", "Reverb\n(MIT RIR)", "Narrow-\nband", "Opus\n8 kbit/s",
           "Packet\nloss", "Clipping", "Tempo\n+15%"]
paths = [("cascade_q31", "q31"), ("cascade_para16k", "para16k"), ("cascade_q3", "q3"),
         ("e2e_omni", "omni"), ("e2e_lt", "lt")]

def get_bleu(mk, cond):
    src = tx["cascade"].get(mk, {}).get(cond, {}).get("cond") if mk in tx["cascade"] else None
    if mk == "omni": src = tx["e2e"].get("omni", {}).get(cond)
    if mk == "lt": src = tx["e2e"].get("lt", {}).get(cond)
    v = src["bleu"] if src else np.nan
    # rev_mit: 从 v14 拿 (primary 参考)
    if cond == "rev_mit":
        v14key = {"q31": "q31", "para16k": "p16", "q3": "q3"}.get(mk)
        if v14key and v14key in V14["rev_mit_vs_rev"]["cascade"]:
            v = V14["rev_mit_vs_rev"]["cascade"][v14key]["rev_mit"]["primary"]
    return v

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10.5, 6.4), constrained_layout=True,
                               gridspec_kw={"height_ratios": [1.25, 1.0]})
for ax, conds, labs, ttl in [(ax1, conds_top, lab_top, None), (ax2, conds_bot, lab_bot, None)]:
    w = 0.16; xs = np.arange(len(conds))
    for k, (_, mk) in enumerate(paths):
        vals = [get_bleu(mk, c) for c in conds]
        ax.bar(xs + (k - 2) * w, vals, w, label=NAME[mk] if ax is ax2 else None,
               color=C[mk], alpha=0.9)
    ax.axhline(55.5, color="#444", ls=":", lw=1.0)
    ax.set_xticks(xs); ax.set_xticklabels(labs)
    ax.set_ylim(0, 94 if ax is ax2 else 78)
    ax.grid(axis="y", alpha=0.2, lw=0.4)
ax1.text(7.42, 57.0, "text-translation oracle (clean transcripts) = 55.5", fontsize=7,
         ha="right", color="#444")
ax1.set_ylabel("BLEU (macro-avg, primary reference)")
ax1.set_xlabel("Babble SNR (dB)")
ax1.set_title("Babble-noise SNR ladder", fontsize=9.5)
# 图例放两面板之间右侧空白 (下面板 clean 柱右侧)
ax2.set_ylabel("BLEU (macro-avg, primary reference)")
ax2.set_xlabel("Non-noise channel and coding conditions")
ax2.set_title("Non-noise conditions (synthetic reverb vs measured MIT RIR)", fontsize=9.5)
ax2.legend(loc="upper right", fontsize=7.3, ncol=2, framealpha=0.95)
ax2.text(0.02, 57.0, "oracle = 55.5", fontsize=7, ha="left", color="#444")
fig.savefig(f"{FIG}/fig4_cascade_e2e.pdf", dpi=300)
fig.savefig(f"{FIG}/fig4_cascade_e2e.png", dpi=200)
plt.close(fig)
print("fig4 saved")

# ================= fig8: 真实 6 点曲线 =================
D3 = json.load(open(os.path.join(ROOT, "results", "d3_analysis.json")))
C6 = {"para16k": "#1f77b4", "para8k": "#17becf", "q31": "#d62728", "q3": "#ff7f0e", "whisper": "#8c564b"}
NAME6 = {"para16k": "Paraformer-RT-v2", "para8k": "Paraformer-RT-8K (zh)",
         "q31": "Qwen-Audio-3.1", "q3": "Qwen3-ASR", "whisper": "Whisper-small (non-Alibaba)"}
lad = V14["babble_ladder6"]
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.0), sharey=True, constrained_layout=True)
for ai, lang in enumerate(["zh", "en"]):
    ax = axes[ai]
    lname = "Mandarin (AISHELL-1 test)" if lang == "zh" else "English (LibriSpeech test-clean)"
    for sysk in ["para16k", "para8k", "q31", "q3", "whisper"]:
        if sysk == "para8k" and lang != "zh": continue
        if sysk == "whisper":
            pts = lad.get("whisper", {}).get(lang, {}).get("points", [])
            if len(pts) < 2: continue
            xs = [p["snr"] for p in pts]; ys = [p["err"] for p in pts]
            ax.plot(xs, ys, "--s", color=C6[sysk], lw=1.8, markersize=4.5,
                    label=f"{NAME6[sysk]} (real)" if ai == 0 else None,
                    markeredgecolor="white", markeredgewidth=0.6)
            continue
        try:
            pts = X["snr_curves_v2"][sysk][lang]
            xs = [p["snr"] for p in pts]; ys = [p["mean"] for p in pts]
            lo = [p["ci_lo"] for p in pts]; hi = [p["ci_hi"] for p in pts]
            ax.plot(xs, ys, "-", color=C6[sysk], lw=1.0, alpha=0.7,
                    label=f"{NAME6[sysk]} (synth.)" if ai == 0 else None)
            ax.fill_between(xs, lo, hi, color=C6[sysk], alpha=0.07, linewidth=0)
        except Exception: pass
        pts6 = lad.get(sysk, {}).get(lang, {}).get("points", [])
        if pts6:
            xs = [p["snr"] for p in pts6]; ys = [p["err"] for p in pts6]
            ax.plot(xs, ys, "--o", color=C6[sysk], lw=2.0, markersize=4.5,
                    label=f"{NAME6[sysk]} (real)" if ai == 0 else None,
                    markeredgecolor="white", markeredgewidth=0.6)
    ax.set_xlabel("SNR (dB)"); ax.set_title(lname)
    ax.set_xticks([10, 5, 2.5, 0, -2.5, -5])
    ax.set_xlim(-6.5, 11.5); ax.set_ylim(-5, 230)
    ax.axhline(100, color="#999", lw=0.6, ls=":")
    ax.text(11, 106, "CER = 100%", ha="right", fontsize=7, color="#777")
    ax.axhline(10, color="#999", lw=0.6, ls="--")
    ax.grid(alpha=0.25, lw=0.5)
axes[0].set_ylabel("Error rate (%)")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="upper center", bbox_to_anchor=(0.5, 1.12), ncol=3, frameon=False, fontsize=7.3)
fig.savefig(f"{FIG}/fig8_real_validation.pdf", bbox_inches="tight", dpi=300)
fig.savefig(f"{FIG}/fig8_real_validation.png", bbox_inches="tight", dpi=200)
plt.close(fig)
print("fig8 saved")
