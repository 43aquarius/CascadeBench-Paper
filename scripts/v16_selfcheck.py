#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.6 self-check: upgrade item 1 (Whisper large-v3-turbo full ladder).
Checks: turbo cells in Appendix D match analysis_v16_whisper_curve.json;
S13 exists and is referenced; methods accounting (1,650 = 600 + 1,050,
API total unchanged 43,046); abstract <= 250 words with the finding;
key numbers present in 4.4; cover letter / conclusions / discussion updated;
old 'knee cannot be localised' phrasing gone; released log + scripts present."""
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_ROOT = _os.path.dirname(_HERE)
_PAPER = _os.path.join(_ROOT, "paper", "latex")
import re, os, json

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
s13 = read("supp_tables/tab_s13_whisper_turbo")
appd = texts["appendix"]
res = texts["results"]
meth = texts["methods"]
ALL = main + "".join(texts.values()) + supp

J = json.load(open(os.path.join(_ROOT, "results", "analysis_v16_whisper_curve.json")))
lad = J["ladder"]

checks = []
def chk(name, cond):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)

# 1. Appendix D turbo rows match the analysis JSON
zh = lad["rb10/zh"]["err"], lad["rb5/zh"]["err"], lad["rb25/zh"]["err"], \
     lad["rb0/zh"]["err"], lad["rbm25/zh"]["err"], lad["rbm5/zh"]["err"]
en = lad["rb10/en"]["err"], lad["rb5/en"]["err"], lad["rb25/en"]["err"], \
     lad["rb0/en"]["err"], lad["rbm25/en"]["err"], lad["rbm5/en"]["err"]
row_zh = (f"Whisper large-v3-turbo & {zh[0]:.1f} & {zh[1]:.1f} & {zh[2]:.1f} & "
          f"{zh[3]:.1f} & {zh[4]:.1f} & {zh[5]:.1f} & $>+10$ \\\\")
row_en = (f"Whisper large-v3-turbo & {en[0]:.1f} & {en[1]:.1f} & {en[2]:.1f} & "
          f"{en[3]:.1f} & {en[4]:.1f} & {en[5]:.1f} & 4.4 \\\\")
chk("Appendix D turbo zh row matches JSON", row_zh in appd)
chk("Appendix D turbo en row matches JSON (cross 4.4)", row_en in appd)

# 2. cross10 values from JSON
chk("JSON cross10 zh = above-highest", J["babble_cross10"]["zh"]["cross10"] == "above-highest")
chk("JSON cross10 en = 4.4", J["babble_cross10"]["en"]["cross10"] == 4.4)

# 3. S13 present + referenced
chk("S13 table file has 14 rows", len(s13.strip().split("\n")) == 14)
chk("S13 referenced in 4.4", "Supplementary Table~S13" in res)
chk("S13 referenced in Appendix D", "S13" in appd)
chk("S13 section in supplementary", "Whisper large-v3-turbo: complete real-babble ladder" in supp)

# 4. S13 cells match JSON (spot: rbm25 zh err/ins/del/sub/ins_frac)
d = J["decomp"]["rbm25/zh"]
c = J["ladder"]["rbm25/zh"]
lo, hi = c["ci"]
s13_row = f"RB$-2.5$ & zh & {c['err']:.1f} ({lo:.0f},{hi:.0f}) & {d['empty_pct']:.1f} & {d['ins']} & {d['del']} & {d['sub']} & {d['ins_frac']:.2f} \\\\"
chk("S13 rbm25/zh row matches JSON", s13_row in s13)

# 5. Methods accounting
chk("methods prose 1,650 + split", "1{,}650 Whisper transcriptions" in meth
    and "600 with Whisper small" in meth and "1{,}050" in meth)
chk("Table 2 local row 1,650", "1{,}650 transcriptions" in meth)
chk("Table 2 caption split", "600 Whisper small and 1{,}050 Whisper large-v3-turbo" in meth)
chk("API total unchanged 43,046", "43{,}046" in meth and "Total successful responses} & 43{,}046" in meth)
chk("systems table turbo row", "Whisper large-v3-turbo (open weights) & local" in meth)

# 6. Abstract
m = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', main, re.S)
def wc(t):
    t = re.sub(r'\\[a-zA-Z]+|[{}$~]', ' ', t)
    return len([w for w in t.split() if any(ch.isalnum() for ch in w)])
chk("abstract <= 250 words", wc(m.group(1)) <= 250)
chk("abstract carries turbo finding", "open-weights\nrecogniser on the same ladder" in m.group(1)
    or "open-weights recogniser on the same ladder" in re.sub(r'\s+', ' ', m.group(1)))

# 7. 4.4 key numbers
for num in ["5.9", "2.5", "14.9", "105.3", "7.0", "2.8", "4.4", "0.08", "0.27",
            "0.38", "70.7", "120.3", "64.1", "86.6", "93.1", "207.6", "29.3"]:
    chk(f"4.4/discussion carries {num}", num in res or num in texts["discussion"])
chk("zero-empty claim in 4.4", "zero in every condition" in res)

# 8. Fig caption
chk("fig caption green turbo series", "green dashed series with triangle markers" in res
    and "Whisper large-v3-turbo model on all six levels" in res)

# 9. Old phrasing gone
chk("no 'knee cannot be localised' left",
    "cannot be localised" not in ALL and "cannot\nlocalise its own knee" not in ALL
    and "cannot localise its own knee" not in re.sub(r'\s+', ' ', ALL))

# 10. Discussion / conclusions / intro updated
chk("discussion limitation updated", "encoder--decoder models rather than audio-LLMs" in texts["discussion"])
chk("conclusions knee finding", "specialist band" in texts["conclusions"] and
    "not a generic property" in texts["conclusions"])
chk("intro two recognisers", "open-weights locally\nexecuted recognisers" in texts["intro"]
    or "open-weights locally executed recognisers" in re.sub(r'\s+', ' ', texts["intro"]))

# 11. References
refs = open(os.path.join(P, "refs.bib"), encoding="utf-8").read()
chk("whisperturbo2024 in bib + cited", "whisperturbo2024" in refs
    and "whisperturbo2024" in meth)

# 12. Released artifacts
chk("turbo log released", os.path.exists(os.path.join(_ROOT, "results", "d3_asr_whisper_lg3t.jsonl")))
chk("runner + analysis scripts released",
    os.path.exists(os.path.join(_ROOT, "scripts", "run_whisper_lg3t.py"))
    and os.path.exists(os.path.join(_ROOT, "scripts", "v16_whisper_curve.py")))
n_log = sum(1 for l in open(os.path.join(_ROOT, "results", "d3_asr_whisper_lg3t.jsonl"))
            if json.loads(l).get("ok"))
chk("log has 1,050 ok records", n_log == 1050)

# 13. Cover letter + no revision language
cl = open(os.path.join(_ROOT, "paper", "CoverLetter_v1.6.txt"), encoding="utf-8").read()
chk("cover letter updated", "large-v3-turbo" in cl and "provider-specific" in cl)
chk("no revision-process language",
    not re.search(r'\b(we revised|as requested|reviewer #|in response to the review)\b',
                  ALL, re.I))

n_fail = sum(1 for _, ok in checks if not ok)
print(f"\n{len(checks) - n_fail}/{len(checks)} checks passed")
raise SystemExit(1 if n_fail else 0)
