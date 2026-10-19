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

# ---------------- fig4: cascade vs e2e, 4 paths, oracle dashed line ----------------
tx = X["translation_ext"]
conds = ["clean", "n20", "n15", "n10", "n5", "n25", "n0", "nm5"]
cond_lab = ["Clean", "20", "15", "10", "5", "2.5", "0", "-5"]
paths = [("q31", "Cascade: Qwen-Audio + MT", C["q31"], "cascade"),
         ("para16k", "Cascade: Paraformer + MT", C["para16k"], "cascade"),
         ("omni", "E2E: Omni-Flash", C["omni"], "e2e"),
         ("lt", "E2E: LiveTranslate", C["lt"], "e2e")]
fig, ax = plt.subplots(figsize=(8.4, 3.6))
w = 0.19
xs = np.arange(len(conds))
for k, (key, lab, col, kind) in enumerate(paths):
    vals = []
    for c in conds:
        if kind == "cascade":
            d = tx["cascade"].get(key, {}).get(c, {}).get("cond") or tx["cascade"].get(key, {}).get(c, {}).get("eff")
        else:
            d = tx["e2e"].get(key, {}).get(c)
        vals.append(d["bleu"] if d else np.nan)
    ax.bar(xs + (k-1.5)*w, vals, w, label=lab, color=col, alpha=0.9)
ax.axhline(55.5, color="#444", ls="--", lw=1.2)
ax.text(7.45, 56.6, "text-translation oracle 55.5", fontsize=9, ha="right", color="#444")
ax.set_xticks(xs); ax.set_xticklabels(cond_lab)
ax.set_xlabel("Babble SNR (dB); other conditions tabulated in the text")
ax.set_ylabel("BLEU (primary reference)")
ax.set_ylim(0, 78)
ax.legend(ncol=2, fontsize=9, loc="upper right", framealpha=0.95)
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
fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.3), sharey=True)
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
    ax.set_title(nm, fontsize=10.5); ax.set_ylim(-3, 105)
axes[0].set_ylabel("Per-sentence error (%)")
fig.tight_layout()
save(fig, "fig5_distribution")

# ---------------- fig6: CAC 3 cascades, n= in legend, enlarged ----------------
cac = X["cac_v2"]
fig, ax = plt.subplots(figsize=(5.4, 4.3))
mk_lab = {"q31": ("Qwen-Audio + MT", C["q31"]),
          "para16k": ("Paraformer + MT", C["para16k"]),
          "q3": ("Qwen3-ASR + MT", C["q3"])}
for i, mk in enumerate(["q31", "para16k", "q3"]):
    pts = cac[mk]["points"]
    xs = np.array([p["asr_err"] for p in pts]); ys = np.array([p["loss"] for p in pts])
    lab, col = mk_lab[mk]
    ax.scatter(xs, ys, s=30, color=col, label=f"{lab} (n={len(pts)})", zorder=3,
               edgecolor="white", lw=0.5)
    b, a = np.polyfit(xs, ys, 1)
    gx = np.linspace(0, max(115, xs.max()), 50)
    ax.plot(gx, a + b*gx, color=col, lw=1.6, alpha=0.85)
    lo = cac[mk].get("slope_ci95") or (b*0.93, b*1.07)
    ax.fill_between(gx, a + lo[0]*gx, a + lo[1]*gx, color=col, alpha=0.10, lw=0)
    ci = cac[mk].get("slope_ci95")
    txt = f"slope={b:.2f}" + (f" (95% CI {ci[0]:.2f}\u2013{ci[1]:.2f})" if ci else "")
    ax.text(0.985, 0.06 + 0.06*i, txt, transform=ax.transAxes, ha="right",
            fontsize=9, color=col)
ax.set_xlabel("Mean recognition error rate (%; refusals = 100% error)")
ax.set_ylabel("BLEU loss from clean (points)")
ax.set_xlim(-3, 118); ax.set_ylim(-4, 58)
ax.legend(loc="upper left", fontsize=9.5, framealpha=0.95)
save(fig, "fig6_cac")

# ---------------- fig8: synthetic 8-pt curves vs real 6-level babble + whisper ----------------
snr = X["snr_curves_v2"]
lad = V15["asr_real_all"]
RB = [("rb10", 10), ("rb5", 5), ("rb25", 2.5), ("rb0", 0), ("rbm25", -2.5), ("rbm5", -5)]
NAME = {"para16k": "Paraformer-RT-v2", "para8k": "Paraformer-RT-8K (zh)",
        "q31": "Qwen-Audio-3.1", "q3": "Qwen3-ASR"}
fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.6), sharey=True)
for ax, lang in zip(axes, ["zh", "en"]):
    for sysname in ["para16k", "q31", "q3"]:
        col = C[sysname]
        pts = snr.get(sysname, {}).get(lang, [])
        if pts:
            ax.plot([p["snr"] for p in pts], [p["mean"] for p in pts], color=col, lw=1.1,
                    alpha=0.55, zorder=2)
    for sysname in ["para16k", "q31", "q3"]:
        col = C[sysname]
        xs, ys = [], []
        for cond, s in RB:
            cell = lad.get(sysname, {}).get(f"{cond}/{lang}")
            if cell:
                xs.append(s); ys.append(cell["err"])
        if xs:
            ax.plot(xs, ys, color=col, lw=2.0, ls="--", marker="o", ms=4.5, zorder=4,
                    label=NAME[sysname] if lang == "zh" else None)
    # whisper: 4 real points
    xs, ys = [], []
    for cond, s in [("rb5", 5), ("rb0", 0), ("rbm5", -5)]:
        cell = lad.get("whisper", {}).get(f"{cond}/{lang}")
        if cell:
            xs.append(s); ys.append(cell["err"])
    if xs:
        ax.plot(xs, ys, color=C["whisper"], lw=1.8, ls=":", marker="s", ms=5, zorder=4,
                label="Whisper small (local)" if lang == "zh" else None)
    ax.axhline(100, color="#999", ls="-.", lw=0.8)
    ax.set_xlabel("SNR (dB)")
    ax.set_title("Mandarin (AISHELL-1)" if lang == "zh" else "English (LibriSpeech)", fontsize=10.5)
    ax.set_xlim(-11, 22); ax.set_ylim(-5, 210)
axes[0].set_ylabel("Error rate (%)")
axes[0].legend(fontsize=8.5, loc="upper left", framealpha=0.95)
fig.tight_layout()
save(fig, "fig8_real_validation")
print("all v1.5 figures done")
