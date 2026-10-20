#!/usr/bin/env python3
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_ROOT = _os.path.dirname(_HERE)              # repository root
_PAPER = _os.path.join(_ROOT, "paper", "latex")
_FIG = _os.path.join(_ROOT, "figures")
# -*- coding: utf-8 -*-
"""v1.5 figures: fig1 (three-reference), fig4 (cascade vs e2e, 4 paths),
fig5 (distributions, enlarged), fig6 (CAC with n= + enlarged), fig8 (6-level real babble + whisper).
Font policy: base 10-10.5pt on reduced canvas so print-size text stays >= 8pt effective."""
import os, json, sys
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
plt.rcParams.update({'font.size': 10, 'axes.titlesize': 11, 'axes.labelsize': 10.5,
                     'legend.fontsize': 9.5, 'xtick.labelsize': 9.5, 'ytick.labelsize': 9.5})

ROOT = _ROOT
FIG = _FIG
X = json.load(open(f"{ROOT}/results/analysis_ext.json"))
V15 = json.load(open(f"{ROOT}/results/analysis_v15_real.json"))
V15B = json.load(open(f"{ROOT}/results/analysis_v15_real2.json"))
C = {"para16k": "#1f77b4", "para8k": "#17becf", "q31": "#d62728", "q3": "#ff7f0e",
     "omni": "#9467bd", "lt": "#2ca02c", "whisper": "#7f7f7f"}

def save(fig, name):
    fig.savefig(f"{FIG}/{name}.pdf", bbox_inches="tight", dpi=300)
    fig.savefig(f"{FIG}/{name}.png", bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("saved", name)

# ---------------- fig1: architecture (three references) ----------------
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
fig, ax = plt.subplots(figsize=(8.4, 3.9))
ax.set_xlim(0, 105); ax.set_ylim(0, 42); ax.axis("off")
def box(x, y, w, h, text, fc="#eef3fb", ec="#3565a8", fs=10):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6", fc=fc, ec=ec, lw=1.2))
    ax.text(x+w/2, y+h/2, text, ha="center", va="center", fontsize=fs)
def arrow(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12, color="#555", lw=1.2))
box(1, 30, 17, 8, "480-sentence\nbilingual corpus\n(zh/en, 4 domains)", fc="#eefbe9", ec="#3d8b3d")
box(22, 30, 17, 8, "Neural TTS\n4 test voices +\n6 babble voices", fc="#eefbe9", ec="#3d8b3d")
box(43, 30, 21, 8, "Degradation grid\n8 conditions + 8-level\nSNR sweep (20 to -10 dB)\n+ measured-RIR reverb", fc="#fff6e0", ec="#c98a00")
box(67.5, 33, 17, 5.5, "Recognition systems\n(3 product classes)")
box(67.5, 25.5, 17, 5.5, "LiveTranslate\ninternal frontend")
box(89, 30, 15, 8, "Text translation\n(qwen-mt-uni)\ncascade stage", fc="#f3eefa", ec="#7d4ba8")
box(67.5, 3, 17, 7, "End-to-end paths\nomni / LiveTranslate", fc="#f3eefa", ec="#7d4ba8")
box(89, 12, 15, 8, "Three-reference\nscoring (2 vendors)\nBLEU / chrF", fc="#fdeeee", ec="#b04040")
box(67.5, 13.5, 17, 7, "Error analysis\nCER / WER, refusals,\nthresholds, STOI", fc="#fdeeee", ec="#b04040")
arrow(18, 34, 22, 34); arrow(39, 34, 43, 34)
arrow(64, 35.5, 67.5, 35.5); arrow(64, 32, 67.5, 28.2)
arrow(84.5, 35.5, 89, 33.5); arrow(84.5, 28.2, 89, 31.5)
arrow(76, 25.5, 76, 10); arrow(84.5, 6.5, 89, 14)
arrow(84.5, 17, 89, 17.5)
ax.set_title("CascadeBench evaluation pipeline", fontsize=12.5, pad=2)
save(fig, "fig1_architecture")

# ---------------- fig4 (paper Fig. 5): two panels - SNR ladder + non-noise ----------------
tx = X["translation_ext"]
conds_top = ["clean", "n20", "n15", "n10", "n5", "n25", "n0", "nm5"]
lab_top = ["Clean", "20", "15", "10", "5", "2.5", "0", "-5"]
conds_bot = ["clean", "rev", "rev_mit", "nb", "opus", "pl", "clip", "tempo"]
lab_bot = ["Clean", "Reverb\n(synth.)", "Reverb\n(MIT RIR)", "Narrow-\nband", "Opus\n8 kbit/s",
           "Packet\nloss", "Clipping", "Tempo\n+15%"]
NAME5 = {"q31": "Cascade: Qwen-Audio + MT", "para16k": "Cascade: Paraformer + MT",
         "q3": "Cascade: Qwen3-ASR + MT", "omni": "E2E: Omni-Flash", "lt": "E2E: LiveTranslate"}
paths5 = [("q31", "cascade"), ("para16k", "cascade"), ("q3", "cascade"),
          ("omni", "e2e"), ("lt", "e2e")]
FE_V14KEY = {"q31": "q31", "para16k": "p16", "q3": "q3"}

def get_bleu(mk, kind, cond):
    if cond == "rev_mit":
        fe = FE_V14KEY.get(mk)
        if fe is None:
            return np.nan
        return V15B["revmit_cascade_3ref"][fe]["rev_mit_sweep"]["primary"]["bleu"]
    if kind == "cascade":
        d = tx["cascade"].get(mk, {}).get(cond, {}).get("cond") or tx["cascade"].get(mk, {}).get(cond, {}).get("eff")
    else:
        d = tx["e2e"].get(mk, {}).get(cond)
    return d["bleu"] if d else np.nan

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(5.9, 4.4), constrained_layout=True,
                               gridspec_kw={"height_ratios": [1.25, 1.0]})
for ax, conds, labs in [(ax1, conds_top, lab_top), (ax2, conds_bot, lab_bot)]:
    w = 0.16
    xs = np.arange(len(conds))
    for k, (mk, kind) in enumerate(paths5):
        vals = [get_bleu(mk, kind, c) for c in conds]
        ax.bar(xs + (k - 2) * w, vals, w, label=NAME5[mk] if ax is ax2 else None,
               color=C[mk], alpha=0.9)
    ax.axhline(55.5, color="#444", ls="--", lw=1.1)
    ax.set_xticks(xs); ax.set_xticklabels(labs, fontsize=9.5)
    ax.set_ylim(0, 94 if ax is ax2 else 78)
    ax.grid(axis="y", alpha=0.2, lw=0.4)
ax1.set_ylabel("BLEU (primary reference)")
ax1.set_xlabel("Babble SNR (dB)")
ax1.set_title("Babble-noise SNR ladder", fontsize=10.5)
ax2.set_ylabel("BLEU (primary reference)")
ax2.set_xlabel("Non-noise channel and coding conditions")
ax2.set_title("Non-noise conditions (synthetic reverb vs measured MIT RIR)", fontsize=10.5)
ax2.legend(loc="upper right", fontsize=9.5, ncol=2, framealpha=0.95)
save(fig, "fig4_cascade_e2e")

# ---------------- fig5: sentence-level distributions, enlarged ----------------
sys.path.insert(0, f"{ROOT}/scripts")
from metrics import err_rate
CORPUS = {json.loads(l)["id"]: json.loads(l) for l in open(f"{ROOT}/corpus/corpus.jsonl")}
SWEEP = json.load(open(f"{ROOT}/corpus/sweep_ids.json"))
def load_asr(model):
    d = {}
    for f in [f"{ROOT}/results/asr_{model}.jsonl", f"{ROOT}/results/ext_asr_{model}.jsonl"]:
        if not os.path.exists(f): continue
        for line in open(f):
            j = json.loads(line)
            key = j["key"]; cond, sid = key.split("/", 1)
            if j.get("ok"): d[key] = j.get("text", "") or ""
            elif "NO_WORDS" in str(j.get("err", "")): d[key] = ""
    return d
A31, A16 = load_asr("q31"), load_asr("para16k")
conds5 = [("clean", "Clean"), ("n10", "10 dB"), ("n5", "5 dB"), ("n0", "0 dB"), ("nm5", "-5 dB")]
fig, axes = plt.subplots(1, 2, figsize=(5.9, 2.35), sharey=True)
for ax, (A, nm) in zip(axes, [(A31, "Qwen-Audio-3.1"), (A16, "Paraformer-RT-v2")]):
    data = [[err_rate(CORPUS[s]["text"], A.get(f"{c}/{s}", ""), CORPUS[s]["lang"])*100
             for s in SWEEP] for c, _ in conds5]
    bp = ax.boxplot(data, tick_labels=[lab for _, lab in conds5], showfliers=False,
                    patch_artist=True, widths=0.55)
    for p in bp["boxes"]:
        p.set_facecolor("#aecbe8"); p.set_alpha(0.8)
    for med in bp["medians"]:
        med.set_color("#b04040"); med.set_linewidth(1.6)
    ax.axhline(10, color="#666", ls="--", lw=0.9)
    ax.set_title(nm, fontsize=11); ax.set_ylim(-3, 105)
axes[0].set_ylabel("Per-sentence error (%)")
fig.tight_layout()
save(fig, "fig5_distribution")

# ---------------- fig6 (paper Fig. 6): CAC, mild/collapsed markers, enlarged ----------------
cac = X["cac_v2"]
fig, ax = plt.subplots(figsize=(4.5, 3.6), constrained_layout=True)
COLLAPSE_TH = 40.0
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
    ax.plot(gx, a + b * gx, color=col, lw=1.5, alpha=0.85, zorder=2)
    ax.fill_between(gx, ilo + slo * gx, ihi + shi * gx, color=col, alpha=0.10, lw=0, zorder=1)
    mild = xs <= COLLAPSE_TH; colp = xs > COLLAPSE_TH
    ax.scatter(xs[mild], ys[mild], s=28, color=col, zorder=3, edgecolor="white", lw=0.5,
               label=f"{NAME5[mk].replace('Cascade: ', '')} (n={len(pts)})")
    ax.scatter(xs[colp], ys[colp], s=64, color=col, marker="X", zorder=4,
               edgecolor="black", lw=0.6)
    idx = ["q31", "para16k", "q3"].index(mk)
    ytxt = 0.97 - 0.115 * idx
    ax.text(0.98, ytxt, f"slope {b:.2f} [{slo:.2f}, {shi:.2f}], r = {r:.3f}",
            transform=ax.transAxes, ha="right", va="top", fontsize=9.5, color=col)
ax.scatter([], [], s=28, color="#555", edgecolor="white", lw=0.5, label="Mild (error \u2264 40%)")
ax.scatter([], [], s=64, color="#555", marker="X", edgecolor="black", lw=0.6, label="Collapsed (error > 40%)")
ax.axvline(COLLAPSE_TH, color="#999", ls=":", lw=0.9)
ax.text(COLLAPSE_TH + 1.5, ax.get_ylim()[1] * 0.02, "40%", fontsize=9.5, color="#777")
ax.set_xlabel("Mean recognition error rate (%; refusals = 100% error)")
ax.set_ylabel("BLEU loss from clean (points)")
ax.set_xlim(-4, 120); ax.set_ylim(-4, 58)
ax.legend(loc="upper left", fontsize=9.5, framealpha=0.95)
ax.grid(alpha=0.2, lw=0.4)
save(fig, "fig6_cac")

# ---------------- fig8 (paper Fig. 4): synthetic 8-pt curves vs real 6-level babble + whisper ----------------
snr = X["snr_curves_v2"]
lad = V15["asr_real_all"]
RB = [("rb10", 10), ("rb5", 5), ("rb25", 2.5), ("rb0", 0), ("rbm25", -2.5), ("rbm5", -5)]
NAME8 = {"para16k": "Paraformer-RT-v2", "para8k": "Paraformer-RT-8K (zh)",
         "q31": "Qwen-Audio-3.1", "q3": "Qwen3-ASR", "whisper": "Whisper small (local)"}
fig, axes = plt.subplots(1, 2, figsize=(6.0, 3.05), sharey=True, constrained_layout=True)
for ai, lang in enumerate(["zh", "en"]):
    ax = axes[ai]
    for sysk in ["para16k", "para8k", "q31", "q3"]:
        if sysk == "para8k" and lang != "zh":
            continue
        col = C[sysk]
        pts = snr.get(sysk, {}).get(lang, [])
        if pts:
            xs = [p["snr"] for p in pts]; ys = [p["mean"] for p in pts]
            lo = [p["ci_lo"] for p in pts]; hi = [p["ci_hi"] for p in pts]
            ax.plot(xs, ys, "-", color=col, lw=1.0, alpha=0.7,
                    label=f"{NAME8[sysk]} (synth.)" if ai == 0 else None)
            ax.fill_between(xs, lo, hi, color=col, alpha=0.07, linewidth=0)
        xs2, ys2 = [], []
        for cond, s in RB:
            cell = lad.get(sysk, {}).get(f"{cond}/{lang}")
            if cell:
                xs2.append(s); ys2.append(cell["err"])
        if xs2:
            ax.plot(xs2, ys2, "--o", color=col, lw=2.0, markersize=4.5,
                    label=f"{NAME8[sysk]} (real)" if ai == 0 else None,
                    markeredgecolor="white", markeredgewidth=0.6)
    xs3, ys3 = [], []
    for cond, s in [("rb5", 5), ("rb0", 0), ("rbm5", -5)]:
        cell = lad.get("whisper", {}).get(f"{cond}/{lang}")
        if cell:
            xs3.append(s); ys3.append(cell["err"])
    if xs3:
        ax.plot(xs3, ys3, "--s", color=C["whisper"], lw=1.8, markersize=5,
                label=f"{NAME8['whisper']} (real)" if ai == 0 else None,
                markeredgecolor="white", markeredgewidth=0.6)
    ax.axhline(100, color="#999", lw=0.7, ls=":")
    ax.text(11, 106, "CER = 100%", ha="right", fontsize=9.5, color="#777")
    ax.axhline(10, color="#999", lw=0.7, ls="--")
    ax.set_xlabel("SNR (dB)")
    ax.set_title("Mandarin (AISHELL-1 test)" if lang == "zh" else "English (LibriSpeech test-clean)", fontsize=11)
    ax.set_xticks([10, 5, 2.5, 0, -2.5, -5])
    ax.set_xlim(-6.5, 11.5); ax.set_ylim(-5, 230)
    ax.grid(alpha=0.25, lw=0.5)
axes[0].set_ylabel("Error rate (%)")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="upper center", bbox_to_anchor=(0.5, 1.24), ncol=2, frameon=False, fontsize=9.5)
save(fig, "fig8_real_validation")
print("all v1.5 figures done")
