#!/usr/bin/env python3
"""Generate LaTeX table bodies for the supplementary material (S4-S9)."""
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_ROOT = _os.path.dirname(_HERE)              # repository root
_PAPER = _os.path.join(_ROOT, "paper", "latex")
_FIG = _os.path.join(_ROOT, "figures")
import json, os

R = _os.path.join(_ROOT, "results")
OUT = _os.path.join(_PAPER, "supp_tables")
os.makedirs(OUT, exist_ok=True)

V = json.load(open(f"{R}/analysis_v15_real.json"))      # asr_real_all, babble_ladder6, real_cascade_2ref, slopes
V2 = json.load(open(f"{R}/analysis_v15_real2.json"))    # revmit, backend matrix
WD = json.load(open(f"{R}/analysis_v15_whisper_decomp.json"))
T5 = json.load(open(f"{R}/analysis_v15_table5.json"))

def cell(d):
    if not d:
        return "---"
    return f"{d['err']:.1f} ({d['ci'][0]:.0f},{d['ci'][1]:.0f})"

# ---------- Table S5: real-speech ASR, 9 conditions ----------
CONDS = [("clean_r", "Clean"), ("revr", "RevR"), ("rb10", "RB$+10$"), ("rb5", "RB$+5$"),
         ("rb25", "RB$+2.5$"), ("rb0", "RB$0$"), ("rbm25", "RB$-2.5$"), ("rbm5", "RB$-5$"),
         ("rn0", "TN$0$")]
SYS = [("q31", "Qwen-Audio"), ("q3", "Qwen3-ASR"), ("para16k", "Paraformer-v2"), ("para8k", "Paraformer-8K")]
rows = []
for key, name in SYS:
    langs = ["zh"] if key == "para8k" else ["zh", "en"]
    for lang in langs:
        cells = [cell(V["asr_real_all"][key].get(f"{c}/{lang}")) for c, _ in CONDS]
        cross = V["babble_ladder6"].get(key, {}).get(lang, {}).get("cross10", "---")
        if isinstance(cross, (int, float)):
            cross = f"{cross:.1f}"
        elif cross == "above-highest":
            cross = "$>+10$"
        lab = f"{name} {'zh' if lang=='zh' else 'en'}"
        if key == "para8k":
            lab = f"{name} zh"
        rows.append(f"{lab} & " + " & ".join(cells) + f" & {cross} \\\\")
for lang in ("zh", "en"):
    cells = [cell(V["asr_real_all"]["whisper"].get(f"{c}/{lang}")) for c, _ in CONDS]
    rows.append(f"Whisper small {'zh' if lang=='zh' else 'en'} & " + " & ".join(cells) + " & $>+5$ \\\\")
open(f"{OUT}/tab_s5_realval.tex", "w").write("\n".join(rows) + "\n")

# ---------- Table S6: real-speech MT (cascade 9 conds + LT 3 conds) ----------
cas = V["real_cascade_2ref"]
lt_cond = {"clean_r": (69.2 - 69.2, 44.1), }  # placeholder, LT numbers from v1.3 table
rows = []
for c, lab in CONDS:
    zh = cas[c]["oracle"]["zh2en"]; en = cas[c]["oracle"]["en2zh"]
    rows.append(f"{lab} & {zh:.1f} & {en:.1f} \\\\")
open(f"{OUT}/tab_s6_cascade.tex", "w").write("\n".join(rows) + "\n")

# ---------- Table S7: whisper detail ----------
rows = []
for c, lab in [("clean_r", "Clean"), ("rb5", "RB$+5$"), ("rb0", "RB$0$"), ("rbm5", "RB$-5$")]:
    for lang in ("zh", "en"):
        a = V["asr_real_all"]["whisper"].get(f"{c}/{lang}", {})
        w = WD.get(f"{c}/{lang}", {})
        tot = w.get("ins", 0) + w.get("del", 0) + w.get("sub", 0)
        rows.append(f"{lab} & {lang} & {a.get('err','-'):.1f} ({a['ci'][0]:.0f},{a['ci'][1]:.0f}) & "
                    f"{a.get('empty_pct','-')} & {w.get('ins','-')} & {w.get('del','-')} & {w.get('sub','-')} & "
                    f"{w.get('ins_frac','-'):.2f} \\\\"
                    if a else f"{lab} & {lang} & --- & --- & --- & --- & --- & --- \\\\")
open(f"{OUT}/tab_s7_whisper.tex", "w").write("\n".join(rows) + "\n")

# ---------- Table S8: rev-mit ----------
rows = []
SYS2 = [("q31", "Qwen-Audio"), ("q3", "Qwen3-ASR"), ("para16k", "Paraformer-v2"), ("para8k", "Paraformer-8K")]
for key, name in SYS2:
    rmm = V2["revmit_asr"][key]
    rv = V2["rev_asr_full"][key]
    langs = ["zh"] if key == "para8k" else ["zh", "en"]
    for lang in langs:
        rows.append(f"{name} {'zh' if lang=='zh' else 'en'} & {rv.get(lang,'-')} & {rmm.get(lang,'-')} \\\\")
open(f"{OUT}/tab_s8_revmit_asr.tex", "w").write("\n".join(rows) + "\n")

rows = []
for fe, name in [("q31", "Qwen-Audio"), ("q3", "Qwen3-ASR"), ("p16", "Paraformer-v2"), ("p8", "Paraformer-8K")]:
    rec = V2["revmit_cascade_3ref"][fe]
    rm = rec["rev_mit_sweep"]  # sweep-matched, n=144 (72 zh for 8K)
    line = f"{name} & {rm['primary']['bleu']:.1f} & {rm['oracle']['bleu']:.1f} & {rm['glm']['bleu']:.1f}"
    if "rev" in rec:
        rv = rec["rev"]
        line += f" & {rv['primary']['bleu']:.1f} & {rv['oracle']['bleu']:.1f} & {rv['glm']['bleu']:.1f} \\\\"
    else:
        line += " & --- & --- & --- \\\\"
    rows.append(line)
open(f"{OUT}/tab_s8_revmit_cascade.tex", "w").write("\n".join(rows) + "\n")

# ---------- Table S9: three-reference absolute scores ----------
NAME = {"cascade_q31": "Cascade: Qwen-Audio+MT", "cascade_para16k": "Cascade: Paraformer+MT",
        "cascade_q3": "Cascade: Qwen3-ASR+MT", "e2e_omni": "E2E: Omni-Flash",
        "e2e_lt": "E2E: LiveTranslate"}
rows = []
for key, name in NAME.items():
    rec = T5["table5_three_ref"][key]
    parts = [name]
    for ref in ("primary", "oracle", "glm"):
        parts.append(f"{rec[ref]['clean']['bleu']:.1f}")
    for ref in ("primary", "oracle", "glm"):
        parts.append(f"{rec[ref]['n0_cond']['bleu']:.1f}")
    rows.append(" & ".join(parts) + " \\\\")
open(f"{OUT}/tab_s9_threeref.tex", "w").write("\n".join(rows) + "\n")

# paired bootstrap rows
rows = []
for cmp_key, label in [("omni_vs_q31", "Omni $-$ Qwen-Audio cascade"),
                       ("omni_vs_q3", "Omni $-$ Qwen3-ASR cascade")]:
    pb = T5["paired_bootstrap_n0"][cmp_key]
    rl = T5["relloss_bootstrap_n0"][cmp_key]
    rows.append(f"{label} (absolute BLEU) & {pb['primary']['diff']:+.1f} ({pb['primary']['ci95'][0]:+.1f},{pb['primary']['ci95'][1]:+.1f}) & "
                f"{pb['oracle']['diff']:+.1f} ({pb['oracle']['ci95'][0]:+.1f},{pb['oracle']['ci95'][1]:+.1f}) & "
                f"{pb['glm']['diff']:+.1f} ({pb['glm']['ci95'][0]:+.1f},{pb['glm']['ci95'][1]:+.1f}) \\\\")
    rows.append(f"{label} (relative-loss diff.) & {rl['primary']['diff_pct']:+.1f} ({rl['primary']['ci95'][0]:+.1f},{rl['primary']['ci95'][1]:+.1f}) & "
                f"{rl['oracle']['diff_pct']:+.1f} ({rl['oracle']['ci95'][0]:+.1f},{rl['oracle']['ci95'][1]:+.1f}) & "
                f"{rl['glm']['diff_pct']:+.1f} ({rl['glm']['ci95'][0]:+.1f},{rl['glm']['ci95'][1]:+.1f}) \\\\")
open(f"{OUT}/tab_s9_paired.tex", "w").write("\n".join(rows) + "\n")

print("supplementary table bodies written to", OUT)
for f in sorted(os.listdir(OUT)):
    print(" -", f)
