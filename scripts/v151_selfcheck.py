#!/usr/bin/env python3
"""v1.5.1 self-check: extend v15_selfcheck with this round's changes.
Checks: Qwen3-vs-specialists reversal wording, Table 4 two-decimal values,
Appendix D six-level babble table, real-speech paired bootstrap numbers,
GLM three-point wording, S12 consistency, author block, abstract <=250."""
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_ROOT = _os.path.dirname(_HERE)              # repository root
_PAPER = _os.path.join(_ROOT, "paper", "latex")
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
t5 = texts["results"]
ALL = main + "".join(texts.values()) + supp

checks = []
def chk(name, cond):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)

# --- 1. Qwen3-vs-specialists contradiction fix (user point 1) ---
chk("no 'every tested babble level' claim",
    "better than both specialists at every tested babble level" not in ALL)
chk("reversal at +2.5 vs tel", "behind the telephone-band\nspecialist at $+2.5$~dB (62.3 against 60.2 percent)" in t5)
chk("reversal from 0dB both", "behind both\nspecialists from $0$~dB downward" in t5)
chk("english stays below 16k", "in English it stays\nbelow the\n16~kHz specialist at every tested level (64.1 against 86.1 percent at" in t5
    or "in English it stays below the" in t5)
chk("conclusion reversal kept", "disappearing and for one LLM system reversing" in texts["conclusions"])
chk("abstract near-knee bound kept", "near-knee regime" in main)

# --- 2. Table 4 two-decimal + threshold consistency (user point 5b) ---
chk("Table4 2.48 present", "2.48\\,(2.26,3.23)" in t5)
chk("Table4 8.82 present", "8.82\\,(8.17,9.31)" in t5)
chk("Table4 -0.06 present", "$-0.06$\\,($-0.25,0.68$)" in t5)
chk("Table4 6.79 present", "6.79\\,(4.93,7.91)" in t5)
chk("prose 2.48 crossing", "at 2.48~dB (95\\% CI 2.26 to 3.23)" in t5)
chk("gap 2.19-2.54 in prose", "2.19 to 2.54~dB" in t5)
chk("gap 8.53-8.88 in prose", "8.53 to" in t5 and "8.88~dB" in t5)
chk("en gap 4.41-4.77 in prose", "4.41 to 4.77~dB" in t5)
chk("no stale 1-decimal Table4", "2.5\\,(2.3,3.3)" not in t5 and "6.8\\,(5.0,7.9)" not in t5)
chk("abstract 2.2-2.5 consistent", "2.2--2.5~dB (Mandarin)" in main)
chk("streaming generalist fixed", "streaming generalist" not in ALL)

# --- 3. Appendix Appendix C fix (user point 5a) ---
chk("no manual Appendix prefix on refs", "Appendix~\\ref{app:" not in ALL)

# --- 4. Appendix D six-level babble table (user point 5c) ---
chk("appendix D present", "Six-level real-babble recognition ladder" in texts["appendix"])
chk("app:babble label", "\\label{app:babble}" in texts["appendix"])
chk("tab:babble referenced in results", "\\ref{app:babble}" in t5)
chk("appendix D q3 row", "Qwen3-ASR & 2.4 & 15.0 & 62.3 & 117.5 & 173.0 & 207.6 & 7.0" in texts["appendix"])
chk("appendix D cross-ref to S5/S7", "Supplementary Tables~S5 and~S7" in texts["appendix"])

# --- 5. real-speech paired bootstrap (user point 3) ---
chk("paired bootstrap in 4.4", "paired sentence-level bootstrap (1000 resamples over the 150 sentences)" in t5)
chk("oracle diff CI", "$+7.9$ points, 95\\% CI $-1.5$ to $+16.7$" in t5)
chk("glm convergence 32.6/32.7", "losing 32.6 and 32.7 percent respectively" in t5)
chk("glm diff CI", "$-0.1$, CI $-9.0$ to $+9.0$" in t5)
chk("point estimate qualified 4.4", "more fragile one in point estimate under the\nsame-engine reference" in t5)
chk("5.3 reference-sensitive", "relative-loss comparison is itself reference-sensitive" in texts["discussion"])
chk("5.3 glm converge", "the two losses converge to 32.6 and 32.7 percent" in texts["discussion"])
chk("conclusion real qualified", "in point estimate under the same-engine\nreference" in texts["conclusions"]
    or "in point estimate under the same-engine reference" in texts["conclusions"])
chk("no stale 'within-path stable' claim", "within-path\nrelative losses are stable across reference choices" not in ALL)
chk("S12 referenced in results", "Supplementary Table~S12" in t5)
chk("S12 table in supp", "tab:realpaired" in supp and "tab_s12_realpaired" in supp)
chk("S12 data row oracle", "42.0 & 24.5 & 41.6 & 69.1 & 45.8 & 33.7 & $+7.9$ ($-1.5,+16.7$)" in read("supp_tables/tab_s12_realpaired.tex"))
chk("S12 data row glm", "37.3 & 25.1 & 32.6 & 32.9 & 22.1 & 32.7 & $-0.1$ ($-9.0,+9.0$)" in read("supp_tables/tab_s12_realpaired.tex"))

# --- 6. GLM backend three-point wording (user point 4) ---
chk("abstract three-point", "three-point re-fit on a second vendor's engine" in main)
chk("abstract engine-independence caveat", "engine-independence of the coefficient is not" in main)
chk("intro three-point", "three-point re-fit on a second vendor's translation engine" in texts["intro"])
chk("4.7 same order magnitude", "reproduced on\na disjoint engine at the same order of magnitude (a three-point fit" in t5)
chk("4.7 english quarter shallower", "the English\ncoefficient about a quarter shallower" in t5)
chk("4.7 n=3 no inference", "no inferential weight at $n=3$" in t5)
chk("5.1 three-point fit", "second-backend three-point fit on a disjoint engine" in texts["discussion"])
chk("worked example three-point", "second-backend three-point fit reproduces the relation" in texts["discussion"])
chk("conclusion three-point", "a three-point re-fit on a second vendor's engine" in texts["conclusions"])
chk("conclusion not-single-artefact", "not a single-engine\nartefact, not that its coefficient is engine-independent" in texts["conclusions"])
chk("no stale 'survives re-fitting'", "survives re-fitting on a second vendor" not in ALL)
chk("no stale 'survives swapping'", "survives swapping the translation engine" not in ALL)

# --- 7. author + email (user directive) ---
chk("author + email", "Chang Tan" in main and "aquars43@foxmail.com" in main
    and "Dalian University of Technology" in main)
chk("corref syntax", "\\corref{cor1}" in main and "\\cortext[cor1]" in main)

# --- 8. supplementary consistency (user point 5d) ---
chk("S4 referenced 3x still", ALL.count("Supplementary Table~S4") >= 3)
chk("appendix now A-D", "\\section{Six-level real-babble recognition ladder}" in texts["appendix"])

# --- 9. abstract length <= 250 ---
m = re.search(r"\\begin{abstract}(.*?)\\end{abstract}", main, re.S)
words = len(re.sub(r"\\[a-zA-Z]+|[{}$&]", " ", m.group(1)).split())
chk(f"abstract {words} words (<=250)", words <= 250)

# --- 10. revision language still clean ---
chk("no revision language", "this revision" not in ALL and "previous version" not in ALL
    and "added in this revision" not in ALL)

fails = [n for n, ok in checks if not ok]
print(f"\n{len(checks) - len(fails)}/{len(checks)} checks passed")
for n in fails:
    print("FAIL:", n)
raise SystemExit(1 if fails else 0)
