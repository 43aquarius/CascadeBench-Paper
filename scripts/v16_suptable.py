#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit supp_tables/tab_s13_whisper_turbo.tex rows from
results/analysis_v16_whisper_curve.json (error + CI + empty + ins/del/sub +
ins_frac per condition/lang, ordered clean then six babble levels desc)."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # repo root
J = json.load(open(os.path.join(ROOT, "results", "analysis_v16_whisper_curve.json")))
lad, dec = J["ladder"], J["decomp"]

ORDER = [("clean_r", "Clean"), ("rb10", "RB$+10$"), ("rb5", "RB$+5$"),
         ("rb25", "RB$+2.5$"), ("rb0", "RB$0$"), ("rbm25", "RB$-2.5$"),
         ("rbm5", "RB$-5$")]

rows = []
for cond, label in ORDER:
    for lang in ("zh", "en"):
        k = f"{cond}/{lang}"
        cell, d = lad[k], dec[k]
        lo, hi = cell["ci"]
        rows.append(f"{label} & {lang} & {cell['err']:.1f} ({lo:.0f},{hi:.0f}) & "
                    f"{d['empty_pct']:.1f} & {d['ins']} & {d['del']} & {d['sub']} & "
                    f"{d['ins_frac']:.2f} \\\\")

out = os.path.join(ROOT, "paper", "latex", "supp_tables", "tab_s13_whisper_turbo.tex")
with open(out, "w") as f:
    f.write("\n".join(rows) + "\n")
print(f"wrote {out} ({len(rows)} rows)")
for r in rows:
    print(r)
