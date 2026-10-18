# -*- coding: utf-8 -*-
"""CascadeBench 出版级图表: 300dpi PNG + PDF, Okabe-Ito色盲友好配色"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

RES = os.path.join(ROOT, "results")
FIG = os.path.join(ROOT, "figures")
os.makedirs(FIG, exist_ok=True)
A = json.load(open(f"{RES}/analysis_results.json"))

# Okabe-Ito 色盲安全色板
OI = {"orange": "#E69F00", "sky": "#56B4E9", "green": "#009E73", "yellow": "#F0E442",
      "blue": "#0072B2", "verm": "#D55E00", "purple": "#CC79A7", "black": "#000000"}
MCOLOR = {"para16k": OI["verm"], "para8k": OI["orange"], "q31": OI["blue"],
          "q3": OI["sky"], "omni": OI["green"]}
MLABEL = {"para16k": "Paraformer-RT-v2", "para8k": "Paraformer-RT-8K",
          "q31": "Qwen-Audio-3.1", "q3": "Qwen3-ASR-Flash", "omni": "Qwen3.8-Omni"}
MODELS = ["para16k", "para8k", "q31", "q3", "omni"]
MAIN_CONDS = ["clean","n10","n0","rev","nb","opus","pl","clip","tempo"]
COND_LBL = {"clean": "Clean", "n10": "Babble\n10 dB", "n0": "Babble\n0 dB", "rev": "Reverb",
            "nb": "Narrow-\nband", "opus": "Codec\n8 kbps", "pl": "Packet\nLoss",
            "clip": "Clip", "tempo": "Tempo\n1.15x"}
COND_LBL1L = {"clean": "Clean", "n10": "Babble10", "n0": "Babble0", "rev": "Reverb",
              "nb": "Narrowband", "opus": "Codec", "pl": "PktLoss", "clip": "Clipping", "tempo": "Tempo"}
SNR_CONDS = ["n20","n15","n10","n5","n0"]

plt.rcParams.update({
    "font.size": 8.5, "axes.titlesize": 9.5, "axes.labelsize": 8.5,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 7.5,
    "font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
})

def save(fig, name):
    fig.savefig(f"{FIG}/{name}.png")
    fig.savefig(f"{FIG}/{name}.pdf")
    plt.close(fig)
    print("saved", name)

# ============ Fig 1: 系统架构图 ============
def fig1_architecture():
    fig, ax = plt.subplots(figsize=(7.4, 3.7))
    ax.set_xlim(0, 100); ax.set_ylim(0, 44); ax.axis("off")

    def box(x, y, w, h, text, fc, fs=7.0):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.35",
                     facecolor=fc, edgecolor="#555555", linewidth=0.9))
        ax.text(x+w/2, y+h/2, text, ha="center", va="center", fontsize=fs, linespacing=1.45)

    def arrow(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                     mutation_scale=10, color="#555555", linewidth=1.0))

    # 布局: 每个盒子最宽行<=14字符
    box(1.5, 27, 13, 10, "Corpus\n480 sentences\nzh 240 / en 240", "#E8F1F8")
    box(17.5, 27, 13, 10, "TTS\nSambert voices\n2 per language", "#E8F1F8")
    box(33.5, 27, 15, 10, "Degradation\n8 conditions\n+ SNR sweep", "#FDF3DC")
    box(52, 35.5, 17, 6.5, "Specialised ASR\nParaformer-RT-v2", "#FBE3D6")
    box(52, 27, 17, 6.5, "LLM-ASR\nQwen-Audio-3.1", "#D6E9F5")
    box(52, 18, 17, 6.5, "Omni LLM\nQwen3.8-Omni", "#DFF0E4")
    box(73, 30, 12, 8, "Text MT\nqwen-mt-uni\n(cascade)", "#EDE3F2")
    box(73, 17, 12, 8, "E2E ST\nLiveTranslate\n(direct)", "#EDE3F2")
    box(88.5, 22, 10, 11, "Metrics\nCER / WER\nBLEU / chrF\nLatency", "#F2F2F2")

    arrow(14.5, 32, 17.5, 32); arrow(30.5, 32, 33.5, 32)
    arrow(48.5, 35, 52, 38); arrow(48.5, 32, 52, 30.2); arrow(48.5, 29, 52, 21.2)
    arrow(69, 38.5, 73, 35); arrow(69, 30.2, 73, 33.5)
    arrow(69, 21.2, 73, 21)
    arrow(85, 34, 88.5, 30); arrow(85, 21, 88.5, 26)
    ax.text(50, 12.5, "Cascade: ASR $\\rightarrow$ MT          End-to-end: audio $\\rightarrow$ translation",
            ha="center", fontsize=7.6, style="italic", color="#333333")
    ax.text(50, 42.3, "CascadeBench: evaluation pipeline", ha="center", fontsize=10, weight="bold")
    save(fig, "fig1_architecture")

# ============ Fig 2: 热力图 (模型×条件, zh/en) ============
def fig2_heatmap():
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), gridspec_kw={"wspace": 0.42})
    models = [m for m in MODELS]
    for k, (ax, lang, title) in enumerate([(axes[0], "zh", "Chinese (CER, %)"), (axes[1], "en", "English (WER, %)")]):
        mat = np.full((len(models), len(MAIN_CONDS)), np.nan)
        for i, m in enumerate(models):
            for j, c in enumerate(MAIN_CONDS):
                d = A["asr_main"].get(m, {}).get(c, {}).get(lang)
                if d: mat[i, j] = d["mean"]
        im = ax.imshow(mat, cmap="YlOrRd", aspect="auto", vmin=0, vmax=80)
        ax.set_xticks(range(len(MAIN_CONDS)))
        ax.set_xticklabels([COND_LBL1L[c] for c in MAIN_CONDS], rotation=40, ha="right")
        ax.set_yticks(range(len(models)))
        ax.set_yticklabels([MLABEL[m] for m in models] if k == 0 else [""]*len(models))
        for i in range(len(models)):
            for j in range(len(MAIN_CONDS)):
                if not np.isnan(mat[i, j]):
                    v = mat[i, j]
                    ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7,
                            color="white" if v > 45 else "black")
        ax.set_title(title)
        for s in ax.spines.values(): s.set_visible(False)
    cb = fig.colorbar(im, ax=axes, shrink=0.85, pad=0.02)
    cb.set_label("Error rate (%)")
    save(fig, "fig2_heatmap")

# ============ Fig 3: SNR退化曲线 ============
def fig3_snr_curves():
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.7))
    for ax, lang in [(axes[0], "zh"), (axes[1], "en")]:
        for m in ["para16k", "q3", "q31"]:
            series = A["snr_curves"].get(m, {}).get(lang, [])
            if not series: continue
            xs = [p["snr"] for p in series]
            ys = [p["mean"] for p in series]
            lo = [p["ci_lo"] for p in series]
            hi = [p["ci_hi"] for p in series]
            ax.plot(xs, ys, "o-", color=MCOLOR[m], label=MLABEL[m], markersize=4, linewidth=1.4)
            ax.fill_between(xs, lo, hi, color=MCOLOR[m], alpha=0.15, linewidth=0)
        ax.set_xlabel("SNR (dB)")
        ax.set_ylabel("CER (%)" if lang == "zh" else "WER (%)")
        ax.set_title("Chinese" if lang == "zh" else "English")
        ax.set_xticks([20, 15, 10, 5, 0])
        ax.legend(frameon=False)
        ax.grid(alpha=0.25, linewidth=0.5)
    save(fig, "fig3_snr_curves")

# ============ Fig 4: 级联 vs E2E BLEU ============
def fig4_cascade_e2e():
    conds = MAIN_CONDS
    series = [
        ("Oracle MT (clean text)", None, OI["black"], "//"),
        ("Cascade: Paraformer + MT", ("cascade", "para16k"), MCOLOR["para16k"], None),
        ("Cascade: Qwen-Audio + MT", ("cascade", "q31"), MCOLOR["q31"], None),
        ("E2E: Omni-Flash", ("e2e", "omni"), MCOLOR["omni"], None),
        ("E2E: LiveTranslate", ("e2e", "lt"), MCOLOR["para8k"], None),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    W = 0.16
    xs = np.arange(len(conds))
    for k, (label, path, color, hatch) in enumerate(series):
        ys = []
        for c in conds:
            if path is None:
                v = A["translation"]["oracle"]["mt_clean_text"].get("bleu")
            else:
                grp = A["translation"][path[0]].get(path[1], {}).get(c, {})
                v = grp.get("bleu")
            ys.append(v if v is not None else np.nan)
        ax.bar(xs + (k-2)*W, ys, W, label=label, color=color, hatch=hatch,
               edgecolor="white", linewidth=0.4)
    ax.set_xticks(xs); ax.set_xticklabels([COND_LBL[c] for c in conds], fontsize=7.5)
    ax.set_ylabel("BLEU (macro-avg., vs. independent reference)")
    ax.legend(frameon=False, ncol=2, fontsize=7)
    ax.grid(axis="y", alpha=0.25, linewidth=0.5)
    ax.set_axisbelow(True)
    save(fig, "fig4_cascade_e2e")

# ============ Fig 5: 句级误差分布 (violin/box) ============
def fig5_distribution():
    import metrics as M
    from analysis import load_asr, sentence_errors
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.7), sharey=True)
    show = ["q31", "para16k"]
    conds_show = ["clean", "n10", "n0", "nb", "rev"]
    for ax, lang in [(axes[0], "zh"), (axes[1], "en")]:
        data, labels, colors = [], [], []
        for m in show:
            errs = sentence_errors(m, conds_show, lang=lang)
            for c in conds_show:
                vals = [v*100 for (cc, s), v in errs.items() if cc == c]
                if vals:
                    data.append(vals); labels.append(c); colors.append(MCOLOR[m])
        positions = []
        labels_all = []
        pos = 0
        for m_i, m in enumerate(show):
            for c in conds_show:
                positions.append(pos); labels_all.append(f"{COND_LBL1L[c]}")
                pos += 1
            pos += 0.8
        bp = ax.boxplot(data, positions=positions, widths=0.72, showfliers=False,
                        patch_artist=True, medianprops=dict(color="black", linewidth=1))
        for patch, c in zip(bp["boxes"], colors):
            patch.set_facecolor(c); patch.set_alpha(0.65); patch.set_linewidth(0.6)
        ax.set_xticks(positions)
        ax.set_xticklabels([l if i < len(conds_show) else "" for i, l in enumerate(labels_all)],
                           fontsize=6.8, rotation=35, ha="right")
        mid = (positions[len(conds_show)-1] + positions[len(conds_show)]) / 2
        ax.axvline(mid, color="#bbbbbb", linewidth=0.7, linestyle=":")
        # 模型图例
        from matplotlib.patches import Patch
        ax.legend(handles=[Patch(facecolor=MCOLOR[m], alpha=0.65, label=MLABEL[m]) for m in show],
                  frameon=False, fontsize=7)
        ax.set_title("Chinese" if lang == "zh" else "English")
        ax.grid(axis="y", alpha=0.25, linewidth=0.5)
    axes[0].set_ylabel("Sentence error rate (%)")
    save(fig, "fig5_distribution")

# ============ Fig 6: CAC 回归散点 ============
def fig6_cac():
    fig, ax = plt.subplots(figsize=(3.4, 2.8))
    mk_colors = {"q31": MCOLOR["q31"], "para16k": MCOLOR["para16k"]}
    all_conds = MAIN_CONDS + ["n20","n15","n5"]
    base = A["translation"]["oracle"]["mt_clean_text"]["bleu"]
    for mk in ["q31", "para16k"]:
        xs, ys = [], []
        for c in all_conds:
            d = A["translation"]["cascade"].get(mk, {}).get(c)
            if not d or d.get("bleu") is None or d.get("mean_asr_err") is None: continue
            xs.append(d["mean_asr_err"]); ys.append(base - d["bleu"])
        ax.scatter(xs, ys, s=22, color=mk_colors[mk], label=MLABEL[mk], alpha=0.85, linewidth=0)
        if len(xs) >= 3:
            k, b = np.polyfit(xs, ys, 1)
            xr = np.linspace(0, max(xs)*1.05, 20)
            ax.plot(xr, k*xr+b, "--", color=mk_colors[mk], linewidth=1.2)
            r = A["translation"]["cac"].get(mk, {})
            ax.annotate(f"slope={k:.2f}, r={r.get('pearson_r', 0):.3f}",
                        (0.97, 0.05 if mk == "q31" else 0.14), xycoords="axes fraction",
                        ha="right", fontsize=7, color=mk_colors[mk])
    ax.set_xlabel("Mean ASR error rate (%)")
    ax.set_ylabel("BLEU drop from oracle (pts)")
    ax.legend(frameon=False, loc="upper left")
    ax.grid(alpha=0.25, linewidth=0.5)
    save(fig, "fig6_cac")

# ============ Fig 7: 延迟 ============
def fig7_latency():
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    names, means, p95s, colors = [], [], [], []
    for m in MODELS:
        d = A["latency"].get(m)
        if not d: continue
        names.append(MLABEL[m]); means.append(d["mean"]); p95s.append(d["p95"]); colors.append(MCOLOR[m])
    ys = np.arange(len(names))
    ax.barh(ys, means, 0.55, color=colors, alpha=0.8, label="Mean")
    ax.scatter(p95s, ys, marker="|", color="black", s=60, label="P95", linewidth=1.2)
    ax.set_yticks(ys); ax.set_yticklabels(names, fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlabel("API round-trip latency (s)")
    ax.set_xlim(0, max(p95s)*1.18)
    ax.legend(frameon=False, fontsize=7)
    ax.grid(axis="x", alpha=0.25, linewidth=0.5)
    save(fig, "fig7_latency")

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "1"): fig1_architecture()
    if which in ("all", "2"): fig2_heatmap()
    if which in ("all", "3"): fig3_snr_curves()
    if which in ("all", "4"): fig4_cascade_e2e()
    if which in ("all", "5"): fig5_distribution()
    if which in ("all", "6"): fig6_cac()
    if which in ("all", "7"): fig7_latency()
