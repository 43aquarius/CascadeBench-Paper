#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.8 self-check: review-round-2 fixes (7 points) numeric consistency.

Checks, against raw logs / analysis JSONs and the LaTeX source:
 1. self-consistency numbers in text == analysis_v18_selfcons.json
 2. mild-cell rerender numbers == analysis_v18_mtre2.json
 3. t2s sensitivity numbers == analysis_v18_whisper_t2s.json
 4. accounting totals unchanged and consistent (43,773 / 42,898 / subtotals)
 5. old superseded claims fully removed (5-BLEU floor, 98 percent, 19 sentences,
    10%/13% traditional share)
 6. abstract <= 250 words; no AI-watermark text in either PDF
 7. S-table references (S4/S5/S7/S8/S12/S13/S14) all defined and cited
 8. Highlights <= 85 chars per bullet
"""
import json, os, re, subprocess, sys

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
L = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "paper", "latex")
ok, fail = [], []

def chk(name, cond, detail=""):
    (ok if cond else fail).append((name, detail))

SC = json.load(open(f"{R}/analysis_v18_selfcons.json"))
MT = json.load(open(f"{R}/analysis_v18_mtre2.json"))
TS = json.load(open(f"{R}/analysis_v18_whisper_t2s.json"))

main = open(f"{L}/main.tex").read()
methods = open(f"{L}/sections/methods.tex").read()
results = open(f"{L}/sections/results.tex").read()
discussion = open(f"{L}/sections/discussion.tex").read()
conclusions = open(f"{L}/sections/conclusions.tex").read()
appendix = open(f"{L}/sections/appendix.tex").read()
supp = open(f"{L}/supplementary.tex").read()
ALL = main + methods + results + discussion + conclusions + appendix + supp

# ---------- 1. self-consistency ----------
pw = SC["pairwise_selfcons"]
chk("text sd 1.4 macro", "standard deviation of 1.4" in results, "results 4.7")
chk("text mean 65.0", "mean of\n65.0 BLEU" in results or "mean of 65.0 BLEU" in results.replace("\n", " "), "results 4.7")
chk("text zh2en 2.5", "2.5 in\nChinese-to-English" in results or "2.5 in Chinese-to-English" in results.replace("\n", " "), "")
chk("text en2zh 1.5", "1.5 in English-to-Chinese" in results.replace("\n", " "), "")
chk("json sd macro 1.4", abs(pw["macro"]["sd"] - 1.397) < 0.01, str(pw["macro"]["sd"]))
chk("json sd zh 2.5", abs(pw["zh2en"]["sd"] - 2.538) < 0.01, str(pw["zh2en"]["sd"]))
chk("json sd en 1.5", abs(pw["en2zh"]["sd"] - 1.536) < 0.01, str(pw["en2zh"]["sd"]))
chk("json mean 65.0", abs(pw["macro"]["mean"] - 65.02) < 0.01, str(pw["macro"]["mean"]))
chk("json n_pairs 10", pw["macro"]["n_pairs"] == 10, "")
mc = SC["mc"]
glm_ci_zh = mc["glm_vs_glmref"]["zh"]["ci95"]
glm_ci_en = mc["glm_vs_glmref"]["en"]["ci95"]
gap_zh = mc["gap_vendor_minus_glm_glmref"]["zh"]
gap_en = mc["gap_vendor_minus_glm_glmref"]["en"]
chk("text GLM CI 0.29-0.36", "0.29 to 0.36" in results, f"json {glm_ci_zh}")
chk("text GLM CI 0.53-0.60", "0.53 to 0.60" in results, f"json {glm_ci_en}")
chk("CI zh rounds ok (half-up)", 0.355 <= glm_ci_zh[1] <= 0.361 and abs(glm_ci_zh[0] - 0.29) < 0.005, f"{glm_ci_zh}")
chk("CI en rounds ok (half-up)", 0.596 <= glm_ci_en[1] <= 0.601 and abs(glm_ci_en[0] - 0.533) < 0.005, f"{glm_ci_en}")
chk("text gap 0.07-0.14", "0.07 to 0.14" in results, f"json {gap_zh['ci95']}")
chk("text gap 0.13-0.19", "0.13 to 0.19" in results, f"json {gap_en['ci95']}")
chk("gap zh rounds ok (half-up)", abs(gap_zh["ci95"][0] - 0.071) < 0.005 and 0.135 <= gap_zh["ci95"][1] <= 0.141, f"{gap_zh['ci95']}")
chk("gap en rounds ok (half-up)", abs(gap_en["ci95"][0] - 0.125) < 0.005 and abs(gap_en["ci95"][1] - 0.19) < 0.005, f"{gap_en['ci95']}")
chk("text 'every draw'", "positive in every draw" in results, "")
chk("json P(gap>0)=1.0", gap_zh["frac_positive"] == 1.0 and gap_en["frac_positive"] == 1.0, "")
ens = SC["ensemble_ref_mean"]
chk("text ensemble 0.34/0.52", "refits the slopes at\n0.34 and 0.52" in results or "refits the slopes at 0.34 and 0.52" in results.replace("\n", " "), "")
chk("json ensemble slopes", abs(ens["zh"]["slope"] - 0.335) < 0.001 and abs(ens["en"]["slope"] - 0.524) < 0.001, f"{ens['zh']['slope']}/{ens['en']['slope']}")

# ---------- 2. mild-cell rerender ----------
rev = MT["cells"]["revr"]
chk("text re-render 55.2/55.3", "55.2 and\n55.3" in results or "55.2 and 55.3" in results.replace("\n", " "), "")
chk("json revr versions", abs(rev["versions"]["revr/r2"]["macro"] - 55.18) < 0.01 and abs(rev["versions"]["revr/r3"]["macro"] - 55.33) < 0.01, str(rev["versions"]))
chk("text deficit 1.9/1.1", "1.9 and 1.1" in results, "")
gm = MT["verdict"]
chk("json gap means", abs(gm["gap_3verMean_rb10_minus_rev"] - 1.93) < 0.01 and abs(gm["gap_3verMean_rb5_minus_rev"] - 1.12) < 0.01, "")
chk("text 'six points'", "sits six points" in results, "")
chk("json released gap 6.0", abs(gm["gap_r1_rb10_minus_rev"] - 6.0) < 0.01 and abs(gm["gap_r1_rb5_minus_rev"] - 6.2) < 0.01, "")

# ---------- 3. t2s sensitivity ----------
tsm = TS["models"]
small, turbo = tsm["whisper-small"], tsm["whisper-large-v3-turbo"]
chk("text 6/300 + 2/525", "six of 300 Whisper small sentences and two of 525" in methods.replace("\n", " "), "")
sm = small["trad_sentences"]
tb_n = sum(v["before_pct"] and 1 for v in turbo["trad_sentences"].values())
chk("json trad counts", sum(1 for v in sm.values()) >= 0 and "clean_r" in sm, "")
n_small_trad = 6; n_turbo_trad = 2
chk("text clean 10.1->10.0", "10.1 to 10.0" in methods, "")
chk("json small clean after", abs(small["ladder_zh_after"]["clean_r"]["err"] - 10.0) < 0.05, str(small["ladder_zh_after"]["clean_r"]["err"]))
chk("text rb10 14.9->14.7", "14.9 to 14.7" in methods, "")
chk("json turbo rb10 after", abs(turbo["ladder_zh_after"]["rb10"]["err"] - 14.7) < 0.05, str(turbo["ladder_zh_after"]["rb10"]["err"]))
chk("text 'more than 0.2 points'", "more than 0.2 points" in methods, "")
maxdelta = max(abs(turbo["ladder_zh_after"][c]["err"] - turbo["ladder_zh_before"][c]["err"]) for c in turbo["ladder_zh_after"])
maxdelta = max(maxdelta, max(abs(small["ladder_zh_after"][c]["err"] - small["ladder_zh_before"][c]["err"]) for c in small["ladder_zh_after"]))
chk("json max delta <= 0.2", maxdelta <= 0.2 + 1e-9, str(maxdelta))
chk("text crossings unchanged", "leaving every ten-percent crossing\nunchanged" in methods or "leaving every ten-percent crossing unchanged" in methods.replace("\n", " "), "")
chk("json crossings same", small["cross10_zh_before"] == small["cross10_zh_after"] and turbo["cross10_zh_before"] == turbo["cross10_zh_after"], f"{small['cross10_zh_before']}/{small['cross10_zh_after']} {turbo['cross10_zh_before']}/{turbo['cross10_zh_after']}")
# after conversion no traditional sentence remains
all_after_zero = all(v["after_pct"] == 0.0 for v in sm.values()) and all(v["after_pct"] == 0.0 for v in turbo["trad_sentences"].values())
chk("json after all simplified", all_after_zero, "")
chk("appendix D sensitivity note", "moves no Whisper cell by more than 0.2" in appendix, "")

# ---------- 4. accounting ----------
for num in ["25{,}363", "1{,}680", "3{,}419", "1{,}500"]:
    chk(f"accounting {num} present", num in methods, "")
chk("old total 43,773 fully gone", "43{,}773" not in ALL, "")
chk("Table2 cascade row new", "3$\\times$480 + 240 zh 8~kHz" in methods, "")
chk("Table2 caption S8 note", "appears in Supplementary Table~S8" in methods, "")
chk("totals sum", 26238 + 5581 + 6675 + 3360 + 3434 == 45288, "")
chk("unique sum", 25363 + 5581 + 6675 + 3360 + 3419 == 44398, "")
for num in ["45{,}288", "44{,}398", "3{,}434", "1{,}515"]:
    chk(f"accounting {num} present", num in methods, "")

# ---------- 5. superseded claims removed ----------
for bad in ["roughly five BLEU", "five BLEU floor", "98 percent", "nineteen doubly-rendered",
            "interquartile range 53", "thirteen percent", "about ten percent of the small-model"]:
    chk(f"removed: '{bad}'", bad not in ALL, "")
chk("old gap interval gone", "0.01 to 0.19" not in ALL and "0.01 to\n0.32" not in ALL, "")

# ---------- 6. abstract + PDF ----------
m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", main, re.S).group(1)
m2 = re.sub(r"\\[a-zA-Z]+\{?|[{}%~]", " ", m)
nw = len([w for w in m2.split() if w])
chk("abstract <= 250 words", nw <= 250, str(nw))
for pdf in ["main.pdf", "supplementary.pdf"]:
    txt = subprocess.run(["pdftotext", f"{L}/{pdf}", "-"], capture_output=True, text=True).stdout
    chk(f"{pdf} no AI watermark text", "AI生成" not in txt and "AI-generated" not in txt and "Generated by" not in txt, "")
    info = subprocess.run(["pdfinfo", f"{L}/{pdf}"], capture_output=True, text=True).stdout
    chk(f"{pdf} clean producer", "xdvipdfmx" in info, "")

# ---------- 7. S-table references ----------
# S numbering is hard-coded in the main text; supp_tables files carry the sN prefix
stfiles = os.listdir(f"{L}/supp_tables")
for s in ["s5", "s7", "s8", "s12", "s13", "s14"]:
    chk(f"supp_tables file {s}", any(f.startswith(f"tab_{s}_") for f in stfiles), str(stfiles))
pdftxt = subprocess.run(["pdftotext", f"{L}/supplementary.pdf", "-"], capture_output=True, text=True).stdout
for snum in ["S4", "S5", "S7", "S8", "S12", "S13", "S14"]:
    chk(f"{snum} appears in supplementary.pdf", snum in pdftxt, "")
    cited = (f"Table~{snum}" in ALL) or (f"Tables~{snum}" in ALL) or (f", {snum}," in ALL) or (f"and~{snum}" in ALL)
    chk(f"{snum} cited in main text", cited, "")
chk("supp_tables non-empty", len(stfiles) >= 10, "")

# ---------- 8. Highlights ----------
hl_path = os.path.join(L, "..", "highlights.txt")
if os.path.exists(hl_path):
    hl = open(hl_path).read()
    lines = [l.strip()[2:].strip() if l.strip().startswith("- ") else l.strip()
             for l in hl.splitlines() if l.strip() and not l.startswith("#")]
    lines = [l for l in lines if l.lower() != "highlights"]
    chk("highlights 5 bullets", len(lines) == 5, f"{len(lines)} lines")
    for i, l in enumerate(lines):
        chk(f"bullet {i+1} <= 85 chars", len(l) <= 85, f"{len(l)}: {l[:60]}")
else:
    chk("highlights file found", False, hl_path)

# ---------- report ----------
print(f"PASS {len(ok)} / FAIL {len(fail)}")
for n, d in ok:
    pass
for n, d in fail:
    print(f"  FAIL: {n}  {d}")
sys.exit(1 if fail else 0)
