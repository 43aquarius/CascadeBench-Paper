#!/usr/bin/env python3
"""v1.7 rendering-noise analysis: reproduce the generation-noise numbers in Sec. 4.7.

Outputs (all reported in the paper):
- sentence-level self-BLEU over 19 doubly-rendered sentences (16 batch-protocol
  consistency pairs from /tmp/batchcheck.json + 3 in-run retry duplicates in
  glm_tasks.jsonl): mean, IQR
- corpus-level clean-vs-rev gap from analysis_v17_glm9.json (near-identical ASR
  inputs): the empirical rendering-noise floor
- Monte Carlo re-fit of both backends' slopes under N(0, sigma) cell noise:
  share of draws with a positive provider-minus-GLM gap and its interval
"""
import json, os, random, statistics as st
from collections import defaultdict
from sacrebleu.metrics import BLEU

R = "/tmp/my-project/research/results"
_bleu_en = BLEU(tokenize="13a")
_bleu_zh = BLEU(tokenize="zh")

def dir_bleu(key, a, b):
    """zh->en renderings (rz ids) scored with 13a; en->zh (re ids) with zh."""
    b_ = _bleu_en if key.split("/")[-1].startswith("rz") else _bleu_zh
    return (b_.sentence_score(b, [a]).score + b_.sentence_score(a, [b]).score) / 2

# ---- 1. doubly-rendered pairs ----
pairs = []
for d in json.load(open("/tmp/batchcheck.json")):
    if d.get("old") and d.get("new"):
        pairs.append((d["key"], d["old"], d["new"]))
by_key = defaultdict(list)
for line in open(os.path.join(R, "glm_tasks.jsonl")):
    d = json.loads(line)
    if d.get("ok") and d.get("text"):
        by_key[d["key"]].append(d["text"])
for k, v in by_key.items():
    if len(v) >= 2:
        pairs.append((k, v[0], v[-1]))

sym = [dir_bleu(k, a, b) for k, a, b in pairs]
sym.sort()
n = len(sym)
print(f"doubly-rendered pairs: n={n}")
print(f"sentence-level self-BLEU: mean={st.mean(sym):.0f} "
      f"IQR=[{sym[n//4]:.0f},{sym[3*n//4]:.0f}] range=[{sym[0]:.0f},{sym[-1]:.0f}]")

# ---- 2. clean-vs-rev corpus gap ----
A = json.load(open(os.path.join(R, "analysis_v17_glm9.json")))
M = A["backend_matrix_9"]
gap = M["clean_r"]["glm_vs_glmref"]["bleu"] - M["revr"]["glm_vs_glmref"]["bleu"]
print(f"clean-vs-rev cell gap (glm|glm): {gap:.1f} BLEU  -> floor ~5 BLEU")

random.seed(7)
SIGMA = 5.0
def refit(xs, ys):
    n = len(xs); mx, my = sum(xs)/n, sum(ys)/n
    sxx = sum((x-mx)**2 for x in xs)
    return sum((x-mx)*(y-my) for x, y in zip(xs, ys)) / sxx

for lang in ("zh", "en"):
    fg = A["slope_gummy_9cond_oracleref_noclean"][lang]
    fl = A["slope_glm_9cond_glmref_noclean"][lang]
    diffs = []
    for _ in range(2000):
        ng = [random.gauss(0, SIGMA) for _ in fg["y"]]
        nl = [random.gauss(0, SIGMA) for _ in fl["y"]]
        cg = random.gauss(0, SIGMA); cl = random.gauss(0, SIGMA)
        sg = refit(fg["x"], [y + cg + ny for y, ny in zip(fg["y"], ng)])
        sl = refit(fl["x"], [y + cl + ny for y, ny in zip(fl["y"], nl)])
        diffs.append(sg - sl)
    diffs.sort()
    pos = sum(1 for d in diffs if d > 0) / len(diffs)
    print(f"{lang}: provider-GLM gap {fg['slope']-fl['slope']:.2f} "
          f"MC95=[{diffs[int(0.025*len(diffs))]:.2f},{diffs[int(0.975*len(diffs))]:.2f}] "
          f"P(gap>0)={pos:.2f}")
