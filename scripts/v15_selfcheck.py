#!/usr/bin/env python3
"""v1.5 self-check: verify every key number and phrase appears consistently."""
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_ROOT = _os.path.dirname(_HERE)              # repository root
_PAPER = _os.path.join(_ROOT, "paper", "latex")
_FIG = _os.path.join(_ROOT, "figures")
import re, os

P = _PAPER
def read(f):
    p = os.path.join(P, f)
    if not os.path.exists(p) and not p.endswith(".tex"):
        p += ".tex"
    return open(p, encoding="utf-8").read()

main = read("main.tex")
texts = {f: read(f"sections/{f}") for f in
         ["intro", "related", "methods", "results", "discussion", "conclusions", "appendix"]}
supp = read("supplementary.tex")
ALL = main + supp + "".join(texts.values())

checks = []
def chk(name, cond):
    checks.append((name, bool(cond)))

# --- 1. unified call accounting ---
chk("43,046 in abstract", "43{,}046" in main)
chk("43,046 in data statement", main.count("43{,}046") >= 2)
chk("43,046 in methods", texts["methods"].count("43{,}046") >= 1)
chk("no stale 36,469", "36{,}469" not in ALL)
chk("subtotals sum", 26238 + 5581 + 6675 + 3360 + 1192 == 43046)
chk("6,675 present", "6{,}675" in texts["methods"])
chk("3,360 present", "3{,}360" in texts["methods"])
chk("1,192 present", "1{,}192" in texts["methods"])
chk("2,025 present", "2{,}025" in texts["methods"])
chk("3,874 failed present", "3{,}874" in texts["methods"])
chk("3,333 + 541 split", "3{,}333" in texts["methods"] and "541" in texts["methods"])
chk("whisper local count", "1{,}650 Whisper transcriptions" in texts["methods"])
chk("unique total 42,171", "42{,}171" in texts["methods"])

# --- 2. Table 5 three references ---
t5 = texts["results"]
for s in ["15.8\\,(12.3,19.1) & 69\\% & 80\\% & 73\\%",
          "44.1\\,(40.1,48.3) & 18\\% & 24\\% & 17\\%",
          "43.0\\,(38.7,47.9) & 19\\% & 29\\% & 23\\%",
          "45.5\\,(38.2,50.5) & 33\\% & 29\\% & 30\\%",
          "50.4\\,(41.8,51.4) & 16\\% & 21\\% & 17\\%"]:
    chk(f"Table5 row {s[:12]}", s in t5)

# --- 3. omni scoping + oracle swap ---
chk("omni scoped in results", "most fragile of the end-to-end paths" in t5)
chk("oracle swap in results", "29.0 against 29.5" in t5)
chk("oracle swap in dual section", "swap adjacent positions" in t5)
chk("oracle swap in abstract", "sub-point same-engine inversion" in main)
chk("oracle swap in conclusions", "sub-point inversion" in texts["conclusions"])
chk("relloss paired CI q31", "+11.7 points, 95\\% CI $-5.6$ to $+25.8$" in t5)
chk("relloss paired CI q3", "$+4.4$, CI $-9.2$ to $+18.4$" in t5)
chk("absolute paired CI primary", "$-11.3$ to $+5.5$ primary" in t5)
chk("absolute paired CI glm", "$-10.0$ to $+6.3$ GLM" in t5)
chk("latency omni scoped", "most fragile of\nthe end-to-end paths" in t5 or "most fragile of the" in t5)

# --- 4. real-speech section numbers ---
chk("cross10 q31 2.8/2.3", "crosses ten percent Mandarin error at 2.8~dB (English 2.3~dB)" in t5)
chk("cross10 q3 7.0/3.6", "7.0~dB (English 3.6~dB)" in t5)
chk("specialists above +10", "already exceed\nten percent Mandarin error at $+10$~dB" in t5)
chk("slope 0.43/0.72 in results", "pass-through of 0.43 (Mandarin, $r = 0.994$) and 0.72 (English" in t5)
chk("slope 0.43/0.72 in conclusions", "slopes of 0.43 (Mandarin) and 0.72 (English)" in texts["conclusions"])
chk("no stale 0.41 slope", "slopes of 0.41" not in ALL and "pass-through of 0.41" not in ALL)
chk("whisper 78.7 vs 19.3", "78.7 percent Mandarin\nagainst 19.3 percent English" in t5)
chk("whisper ins 244:83", "244 to 83" in t5)
chk("whisper empty 25.3", "25.3 percent at $-5$~dB" in t5)
chk("rev-mit p8 18.2->3.4", "from 18.2 to 3.4 percent" in t5)
chk("rev-mit cascade gain", "0.5 to 1.4 BLEU" in t5)
chk("rev-mit 53.8 vs 52.4", "53.8 against 52.4" in t5)

# --- 5. backend section ---
tb = t5
chk("backend matrix rows", all(x in tb for x in
    ["69.1 & 66.2 & 45.8 & 7.3", "32.9 & 31.2 & 22.1 & 4.9",
     "36.8 & 36.0 & 26.3 & 6.7", "60.2 & 55.9 & 39.9 & 7.6"]))
chk("backend slopes", "slopes of 0.34 (Mandarin) and 0.55 (English)" in tb)
chk("backend engine slopes same conds", "0.38 and\n0.72 for the provider engine" in tb)
chk("backend relloss 33.7/33.9", "33.7 against\n33.9 percent" in tb)
chk("backend not vendor-independent", "does not constitute a\nvendor-independent cascade" in tb)

# --- 6. reference protocol wording ---
chk("no dual-reference", "dual-reference" not in ALL.lower().replace("three-reference", ""))
chk("no reference-invariant", "reference-invariant" not in ALL)
chk("three references in methods", "three reference sets" in texts["methods"])
chk("GLM family-disjoint stated", "family-disjoint from every system under test" in ALL)
chk("fig6 caption n=14,14,11", "$n=14$, 14, and 11" in t5)
chk("fig6 clean excluded", "excluded from the fit" in t5)
chk("fig4 dashed line", "dashed line is the" in t5)
chk("fig8 six levels", "six SNR levels" in t5)

# --- 7. revision language ---
chk("no 'added in this revision'", "added in this revision" not in ALL)
chk("no 'this revision'", "this revision" not in ALL)
chk("no 'previous version'", "previous version" not in ALL)

# --- 8. refs fixed ---
bib = open(os.path.join(P, "refs.bib"), encoding="utf-8").read()
chk("pino20 correct", "Pino, Juan" in bib and "10.21437/Interspeech.2020-2938" in bib)
chk("funasr authors fixed", "Gao, Zhifu and Li, Zerui and Wang, Jiaming" in bib
    and "Ming Lei" not in bib)
chk("funasr doi", "10.21437/Interspeech.2023-1428" in bib)
chk("glm refs added", "2508.06471" in bib and "glm2026api" in bib and "qwenmtcard" in bib)
chk("no park2020robust", "park2020robust" not in bib)
chk("no version-specific GLM claim", "GLM-4.6" not in open(_os.path.join(_PAPER, "sections", "methods.tex")).read() + open(_os.path.join(_PAPER, "sections", "results.tex")).read())

# --- 9. supplementary consistency ---
chk("S4 referenced 3x", ALL.count("Supplementary Table~S4") >= 3)
chk("supplementary has S5 ladder", "Cross-10" in supp or "Cross-10\\%" in supp)
chk("supp whisper table", "repetition-loop hallucination" in supp)
chk("appendix trimmed (A-C only)", "Complete pairwise significance" not in texts["appendix"]
    and "Real-speech validation" not in texts["appendix"])

# --- 10. abstract length ---
m = re.search(r"\\begin{abstract}(.*?)\\end{abstract}", main, re.S)
words = len(re.sub(r"\\[a-zA-Z]+|[{}$~]", " ", m.group(1)).split())
chk(f"abstract ~{words} words (<=260)", words <= 260)

# --- 11. author ---
chk("author filled", "Chang Tan" in main and "Dalian University of Technology" in main)

fails = [n for n, ok in checks if not ok]
print(f"{len(checks) - len(fails)}/{len(checks)} checks passed")
for n in fails:
    print("FAIL:", n)
