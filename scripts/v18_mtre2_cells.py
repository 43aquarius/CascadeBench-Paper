#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.8 review fix #3b: cell-level GLM generation noise on the three mild cells.

The released Table 6 GLM|GLM row shows reverberation (49.7) below +10/+5 dB
(55.7/55.9) despite lower recognition error -- the v1.7 text attributed this
to generation noise based on an indirect ~5-BLEU floor estimate. This script
re-renders the GLM candidate translations of the three mild cells (revr, rb5,
rb10) two extra times each (glm_mtre2.jsonl) and measures the actual cell
noise directly:

- per cell: corpus BLEU vs the same released GLM reference (refreal r1),
  for each of the 3 candidate versions (r1 = released mtreal, r2/r3 = reruns)
  -> per-version macro and per-direction scores, spread across versions
- verdict: is the Rev-vs-(+10/+5) gap within or beyond the measured cell noise?
- also: 3-version-mean cells (noise-reduced) for the three conditions

Protocol identical to v17 (n aligned to q31 authoritative list, ASR-empty
slots carry empty translation, last-ok-wins for duplicated records).
Writes analysis_v18_mtre2.json.
"""
import json, os, sys, statistics

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sacrebleu.metrics import BLEU
_bleu_en, _bleu_zh = BLEU(tokenize="13a"), BLEU(tokenize="zh")

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
CONDS = ["revr", "rb5", "rb10"]

# q31 authoritative list (last ok wins, same as v17)
q31last = {}
for line in open(os.path.join(R, "d3_asr_q31.jsonl")):
    d = json.loads(line)
    k = d.get("key", "")
    if k and "/" in k:
        cond, sid = k.split("/", 1)
        if cond in CONDS and d.get("ok"):
            q31last[k] = (d.get("text") or "")

# GLM reference (r1, released)
ref = {}
for line in open(os.path.join(R, "glm_tasks.jsonl")):
    d = json.loads(line)
    if d.get("ok") and d.get("key", "").startswith("refreal/") and d.get("kind") == "reference":
        ref[d["key"].split("/", 1)[1]] = d["text"]  # last wins

# candidate versions per condition: r1 = released mtreal, r2/r3 = reruns
cand = {(c, 1) if False else f"{c}/r1": {} for c in CONDS}
cands = {f"{c}/r1": {} for c in CONDS}
for line in open(os.path.join(R, "glm_tasks.jsonl")):
    d = json.loads(line)
    k = d.get("key", "")
    if d.get("ok") and k.startswith("mtreal/"):
        _, cond, sid = k.split("/")
        if cond in CONDS:
            cands[f"{cond}/r1"][sid] = d["text"]  # last wins
for line in open(os.path.join(R, "glm_mtre2.jsonl")):
    d = json.loads(line)
    k = d.get("key", "")
    if d.get("ok") and k.startswith("mtre2/"):
        _, rnd, cond, sid = k.split("/")
        cands.setdefault(f"{cond}/r{rnd}", {})[sid] = d["text"]  # last wins

def cell_bleu(cond, vermap, direction):
    ds = [s for k in q31last
          for s in [k.split("/", 1)[1]]
          if k.split("/", 1)[0] == cond
          and ((s.startswith("rz") and direction == "zh2en") or (s.startswith("re") and direction == "en2zh"))]
    h = [vermap.get(s, "") for s in ds]
    r = [ref[s] for s in ds]
    b = _bleu_en if direction == "zh2en" else _bleu_zh
    return round(b.corpus_score(h, [r]).score, 2)

RESULT = {"cells": {}, "protocol": "3 candidate versions per cell (released r1 + 2 reruns), scored vs the same released GLM reference"}
for cond in CONDS:
    vers = sorted([v for v in cands if v.startswith(cond + "/")])
    per_ver = {}
    for v in vers:
        vm = cands[v]
        z = cell_bleu(cond, vm, "zh2en")
        e = cell_bleu(cond, vm, "en2zh")
        per_ver[v] = {"zh2en": z, "en2zh": e, "macro": round((z + e) / 2, 2)}
    macros = [per_ver[v]["macro"] for v in vers]
    RESULT["cells"][cond] = {
        "n_versions": len(vers),
        "versions": per_ver,
        "macro_mean": round(statistics.mean(macros), 2),
        "macro_sd": round(statistics.stdev(macros), 3) if len(macros) > 1 else None,
        "macro_range": [min(macros), max(macros)],
        "released_macro": per_ver.get(f"{cond}/r1", {}).get("macro"),
    }
    c = RESULT["cells"][cond]
    print(f"=== {cond}: released {c['released_macro']} | versions {macros} "
          f"| mean {c['macro_mean']} sd {c['macro_sd']} range {c['macro_range']}")

# verdict: Rev gap vs cell noise
rev = RESULT["cells"]["revr"]
rb10 = RESULT["cells"]["rb10"]
rb5 = RESULT["cells"]["rb5"]
gap_r1 = round(rb10["released_macro"] - rev["released_macro"], 2)
gap_r1b = round(rb5["released_macro"] - rev["released_macro"], 2)
all_sd = [rev["macro_sd"], rb10["macro_sd"], rb5["macro_sd"]]
max_sd = max(all_sd)
gap_means = round(rb10["macro_mean"] - rev["macro_mean"], 2)
gap_means_b = round(rb5["macro_mean"] - rev["macro_mean"], 2)
RESULT["verdict"] = {
    "gap_r1_rb10_minus_rev": gap_r1, "gap_r1_rb5_minus_rev": gap_r1b,
    "gap_3verMean_rb10_minus_rev": gap_means, "gap_3verMean_rb5_minus_rev": gap_means_b,
    "max_cell_sd": max_sd,
    "conclusion": "Rev deficit exceeds measured cell noise" if (gap_means > 2 * max_sd and gap_means_b > 2 * max_sd)
                  else ("Rev deficit within measured cell noise" if max(gap_means, gap_means_b) <= 2 * max_sd else "mixed"),
}
print(f"\nreleased gap: +10dB - Rev = {gap_r1}, +5dB - Rev = {gap_r1b}")
print(f"3-version-mean gap: +10dB - Rev = {gap_means}, +5dB - Rev = {gap_means_b}")
print(f"max cell-level sd: {max_sd}  -> verdict: {RESULT['verdict']['conclusion']}")

out = os.path.join(R, "analysis_v18_mtre2.json")
json.dump(RESULT, open(out, "w"), indent=1, ensure_ascii=False)
print(f"wrote {out}")
