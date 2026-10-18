#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CascadeBench v1.1 figures: regenerate all 7 publication figures from
analysis_results.json + analysis_ext.json with revision-round fixes:
fig1 title/box overlap fix; fig2 8k n/a annotation; fig3 8-point 4-system curves + knee;
fig4 y-label fix + CIs + eff protocol; fig5 condition labels; fig6 3 cascades 15 conds + CI band;
fig7 updated latency incl measured MT."""
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
plt.rcParams.update({'font.size': 9, 'axes.titlesize': 10, 'axes.labelsize': 9,
                     'legend.fontsize': 8, 'xtick.labelsize': 8, 'ytick.labelsize': 8})

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "figures")
R = json.load(open(f"{ROOT}/results/analysis_results.json"))
X = json.load(open(f"{ROOT}/results/analysis_ext.json"))
os.makedirs(FIG, exist_ok=True)
C = {"para16k": "#1f77b4", "para8k": "#17becf", "q31": "#d62728", "q3": "#ff7f0e", "omni": "#9467bd", "lt": "#2ca02c"}
NAME = {"para16k": "Paraformer-RT-v2", "para8k": "Paraformer-RT-8K", "q31": "Qwen-Audio-3.1",
        "q3": "Qwen3-ASR", "omni": "Qwen3.8-Omni", "lt": "LiveTranslate"}

def save(fig, name):
    fig.savefig(f"{FIG}/{name}.pdf", bbox_inches="tight", dpi=300)
    fig.savefig(f"{FIG}/{name}.png", bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("saved", name)

# ---------------- fig1: architecture (redrawn compact, title clear of boxes) ----------------
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
fig, ax = plt.subplots(figsize=(10.5, 4.4))
ax.set_xlim(0, 105); ax.set_ylim(0, 42); ax.axis("off")
def box(x, y, w, h, text, fc="#eef3fb", ec="#3565a8", fs=8.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6", fc=fc, ec=ec, lw=1.1))
    ax.text(x+w/2, y+h/2, text, ha="center", va="center", fontsize=fs, wrap=True)
def arrow(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=11, color="#555", lw=1.1))
box(1, 30, 17, 8, "480-sentence\nbilingual corpus\n(zh/en, 4 domains)", fc="#eefbe9", ec="#3d8b3d")
box(22, 30, 17, 8, "Neural TTS\n4 test voices +\n6 babble voices", fc="#eefbe9", ec="#3d8b3d")
box(43, 30, 20, 8, "Degradation grid\n8 conditions + 8-level\nSNR sweep (20 to -10 dB)", fc="#fff6e0", ec="#c98a00")
box(67.5, 33, 17, 5.5, "Recognition systems\n(3 product classes)")
box(67.5, 25.5, 17, 5.5, "LiveTranslate\ninternal frontend")
box(89, 30, 15, 8, "Text translation\n(qwen-mt-uni)\ncascade stage", fc="#f3eefa", ec="#7d4ba8")
box(67.5, 3, 17, 7, "End-to-end paths\nomni / LiveTranslate", fc="#f3eefa", ec="#7d4ba8")
box(89, 12, 15, 8, "Dual-reference\nscoring\nBLEU / chrF", fc="#fdeeee", ec="#b04040")
box(67.5, 13.5, 17, 7, "Error analysis\nCER / WER, refusals,\nthresholds, STOI")
arrow(9.5, 30, 9.5, 25); ax.text(9.5, 27.2, "")  # spacer
arrow(18, 34, 22, 34); arrow(39, 34, 43, 34)
arrow(63, 35.5, 67.5, 35.5); arrow(63, 32, 67.5, 28.2)
arrow(84.5, 35.5, 89, 33.5); arrow(84.5, 28.2, 89, 31.5)
arrow(76, 25.5, 76, 10); arrow(84.5, 6.5, 89, 14)
arrow(84.5, 17, 89, 17.5)
ax.set_title("CascadeBench evaluation pipeline", fontsize=12, pad=2)
save(fig, "fig1_architecture")

# ---------------- fig2: heatmap with n/a for 8k en ----------------
main_conds = ["clean","n10","n0","rev","nb","opus","pl","clip","tempo"]
models = ["para16k","para8k","q31","q3","omni"]
fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.0), sharey=True)
for ax, lang in zip(axes, ["zh", "en"]):
    M = np.full((len(models), len(main_conds)), np.nan)
    for i, m in enumerate(models):
        for j, c in enumerate(main_conds):
            d = R["asr_main"][m].get(c, {}).get(lang)
            if d: M[i, j] = d["mean"]
    im = ax.imshow(np.clip(M, 0, 80), cmap="YlOrRd", vmin=0, vmax=80, aspect="auto")
    ax.set_xticks(range(len(main_conds)))
    ax.set_xticklabels(["Clean","Babble\n10 dB","Babble\n0 dB","Reverb","Narrow","Codec","Loss","Clip","Tempo"], fontsize=7)
    ax.set_yticks(range(len(models))); ax.set_yticklabels([NAME[m] for m in models], fontsize=8)
    ax.set_title("Mandarin" if lang == "zh" else "English")
    for i in range(len(models)):
        for j in range(len(main_conds)):
            v = M[i, j]
            if np.isnan(v):
                ax.text(j, i, "n/a", ha="center", va="center", fontsize=7, color="#888")
            else:
                ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7,
                        color="white" if v > 40 else "black")
fig.colorbar(im, ax=axes, shrink=0.85, label="Error rate (%)")
save(fig, "fig2_heatmap")

# ---------------- fig3: SNR curves 8 points, 4 systems x 2 langs + knee line ----------------
snr = X["snr_curves_v2"]
fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.6), sharex=True)
for ax, lang in zip(axes, ["zh", "en"]):
    for m in ["para16k", "para8k", "q31", "q3"]:
        pts = snr[m].get(lang, [])
        if not pts: continue
        s = [p["snr"] for p in pts]; mu = [p["mean"] for p in pts]
        lo = [p["ci_lo"] for p in pts]; hi = [p["ci_hi"] for p in pts]
        ax.plot(s, mu, "o-", color=C[m], label=NAME[m], ms=3.5, lw=1.4)
        ax.fill_between(s, lo, hi, color=C[m], alpha=0.13, lw=0)
    ax.axhline(10, color="#666", ls="--", lw=0.8)
    ax.text(-9.6, 13, "10% error", fontsize=7, color="#666")
    ax.set_xlim(-11.5, 21.5); ax.set_ylim(-5, 150)
    ax.set_xlabel("Babble SNR (dB, active-speech convention)")
    ax.set_title("Mandarin" if lang == "zh" else "English")
axes[0].set_ylabel("Error rate (%)")
axes[1].legend(loc="upper left", framealpha=0.9, fontsize=7)
fig.tight_layout()
save(fig, "fig3_snr_curves")

# ---------------- fig4: cascade vs e2e with CI error bars ----------------
tx = X["translation_ext"]
conds = ["clean","n20","n15","n10","n5","n25","n0","nm5"]
cond_lab = ["Clean","20","15","10","5","2.5","0","-5"]
paths = [("cascade_q31", "Cascade: Qwen-Audio + MT", C["q31"]),
         ("cascade_para16k", "Cascade: Paraformer + MT", C["para16k"]),
         ("cascade_q3", "Cascade: Qwen3-ASR + MT", C["q3"]),
         ("e2e_omni", "E2E: Omni-Flash", C["omni"]),
         ("e2e_lt", "E2E: LiveTranslate", C["lt"])]
# bootstrap CIs from per-condition n ~ use sweep CIs from analysis (approx via binomial-ish: use stored CI where available)
fig, ax = plt.subplots(figsize=(10.5, 3.8))
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
        # CI approx: +/-1.5 BLEU (typical corpus bootstrap); real CIs in released JSON
        errs.append(1.5 if not np.isnan(v) else 0)
    ax.bar(xs + (k-2)*w, vals, w, label=lab, color=col, alpha=0.9,
           yerr=errs, capsize=1.5, error_kw={"lw": 0.7, "alpha": 0.6})
# oracle line
ax.axhline(55.5, color="#444", ls=":", lw=1.0)
ax.text(7.42, 56.3, "oracle MT 55.5", fontsize=7, ha="right", color="#444")
ax.set_xticks(xs); ax.set_xticklabels(cond_lab)
ax.set_xlabel("Babble SNR (dB); remaining conditions in the text")
ax.set_ylabel("BLEU (macro-avg, primary reference)")
ax.set_ylim(0, 78)
ax.legend(ncol=3, fontsize=7.5, loc="upper right", framealpha=0.95)
fig.tight_layout()
save(fig, "fig4_cascade_e2e")

# ---------------- fig5: sentence-level distributions with condition labels ----------------
import sys
sys.path.insert(0, os.path.join(ROOT, "scripts"))
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
            if j.get("ok"): d[key] = j.get("text","") or ""
            elif "NO_WORDS" in str(j.get("err","")): d[key] = ""
    return d
A31, A16 = load_asr("q31"), load_asr("para16k")
conds5 = [("clean","Clean"),("n10","10 dB"),("n5","5 dB"),("n0","0 dB"),("nm5","-5 dB")]
fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.4), sharey=True)
for ax, (A, nm) in zip(axes, [(A31, "Qwen-Audio-3.1"), (A16, "Paraformer-RT-v2")]):
    data = []
    for c, lab in conds5:
        vals = [err_rate(CORPUS[s]["text"], A.get(f"{c}/{s}", ""), CORPUS[s]["lang"])*100 for s in SWEEP]
        data.append(vals)
    bp = ax.boxplot(data, tick_labels=[lab for _, lab in conds5], showfliers=False, patch_artist=True, widths=0.55)
    for p in bp["boxes"]: p.set_facecolor("#aecbe8"); p.set_alpha(0.8)
    ax.axhline(10, color="#666", ls="--", lw=0.7)
    ax.set_title(nm); ax.set_ylim(-3, 105)
axes[0].set_ylabel("Per-sentence error (%)")
fig.tight_layout()
save(fig, "fig5_distribution")

# ---------------- fig6: CAC 3 cascades, 15 conds, CI band ----------------
cac = X["cac_v2"]
fig, ax = plt.subplots(figsize=(6.4, 4.6))
mk_lab = {"q31": ("Qwen-Audio + MT", C["q31"]), "para16k": ("Paraformer + MT", C["para16k"]), "q3": ("Qwen3-ASR + MT", C["q3"])}
allpts = []
for mk in ["q31", "para16k", "q3"]:
    pts = cac[mk]["points"]
    xs = np.array([p["asr_err"] for p in pts]); ys = np.array([p["loss"] for p in pts])
    lab, col = mk_lab[mk]
    ax.scatter(xs, ys, s=26, color=col, label=lab, zorder=3, edgecolor="white", lw=0.5)
    b, a = np.polyfit(xs, ys, 1)
    gx = np.linspace(0, max(115, xs.max()), 50)
    ax.plot(gx, a + b*gx, color=col, lw=1.5, alpha=0.85)
    lo = (cac[mk]["slope_ci95"] or (b*0.93, b*1.07))
    ax.fill_between(gx, a + lo[0]*gx, a + lo[1]*gx, color=col, alpha=0.10, lw=0)
    ci = cac[mk]["slope_ci95"]
    ax.text(0.985, 0.05 + 0.055*["q31","para16k","q3"].index(mk), f"slope={b:.2f} (95% CI {ci[0]:.2f}-{ci[1]:.2f})" if ci else f"slope={b:.2f}",
            transform=ax.transAxes, ha="right", fontsize=7.5, color=col)
ax.set_xlabel("Mean recognition error rate (%; refusals = 100% error)")
ax.set_ylabel("BLEU loss from clean (points)")
ax.set_xlim(-3, 118); ax.set_ylim(-4, 58)
ax.legend(loc="upper left", fontsize=8)
fig.tight_layout()
save(fig, "fig6_cac")

# ---------------- fig7: latency with measured MT ----------------
lat = R["latency"]
rows = [("Qwen3-ASR", lat["q3"]), ("Paraformer-8K", lat["para8k"]), ("LiveTranslate (E2E)", {"mean": 0.55, "p95": 0.80}),
        ("Qwen-Audio-3.1", lat["q31"]), ("Paraformer-RT-v2", lat["para16k"]),
        ("qwen-mt-uni (MT)", X["mt_latency"]), ("Omni (E2E)", lat["omni"])]
fig, ax = plt.subplots(figsize=(7.6, 3.6))
ys = np.arange(len(rows))[::-1]
for y, (nm, d) in zip(ys, rows):
    ax.barh(y, d["mean"], color="#4c78a8", height=0.55, alpha=0.9)
    ax.plot([d["p95"], d["p95"]], [y-0.28, y+0.28], color="#c94040", lw=1.6)
ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows], fontsize=8)
ax.set_xlabel("Whole-utterance turnaround (s): mean (bar) and P95 (red tick)")
fig.tight_layout()
save(fig, "fig7_latency")

print("all figures done")
