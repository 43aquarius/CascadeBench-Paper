#!/usr/bin/env python3
"""v1.5 analysis part 4: whisper-small error decomposition (ins/del/sub) + summary."""
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_ROOT = _os.path.dirname(_HERE)              # repository root
_PAPER = _os.path.join(_ROOT, "paper", "latex")
_FIG = _os.path.join(_ROOT, "figures")
import json, os, sys

ROOT = _ROOT
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import metrics as M

R = os.path.join(ROOT, "results")
D3C = {json.loads(l)["id"]: json.loads(l)
       for l in open(_os.path.join(_ROOT, "corpus", "d3_corpus.jsonl"))}

def norm(text, lang):
    return (M.normalize_zh(text) if lang == "zh" else M.normalize_en(text)).split() \
        if lang == "en" else list(M.normalize_zh(text))

def ops(ref_seq, hyp_seq):
    """Levenshtein op counts: returns (ins, del, sub)."""
    n, m = len(ref_seq), len(hyp_seq)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            dp[i][j] = min(dp[i-1][j] + 1,          # deletion
                           dp[i][j-1] + 1,          # insertion
                           dp[i-1][j-1] + (ref_seq[i-1] != hyp_seq[j-1]))
    # backtrack for op counts
    i, j = n, m
    ins = dele = sub = 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and ref_seq[i-1] == hyp_seq[j-1]:
            i -= 1; j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] + 1:
            sub += 1; i -= 1; j -= 1
        elif j > 0 and dp[i][j] == dp[i][j-1] + 1:
            ins += 1; j -= 1
        else:
            dele += 1; i -= 1
    return ins, dele, sub

out = {}
for line in open(os.path.join(R, "d3_asr_whisper.jsonl")):
    d = json.loads(line)
    if not d.get("ok"):
        continue
    cond, sid = d["key"].split("/")
    rec = D3C.get(sid)
    if not rec:
        continue
    lang = rec["lang"]
    rs = norm(rec["text"], lang)
    hs = norm(d.get("text") or "", lang)
    i_, d_, s_ = ops(rs, hs)
    cell = out.setdefault(f"{cond}/{lang}", {"ins": 0, "del": 0, "sub": 0, "n": 0, "empty": 0})
    cell["ins"] += i_; cell["del"] += d_; cell["sub"] += s_; cell["n"] += 1
    if not (d.get("text") or "").strip():
        cell["empty"] += 1

for k, v in out.items():
    tot = v["ins"] + v["del"] + v["sub"]
    v["ins_frac"] = round(v["ins"] / tot, 3) if tot else 0.0
    v["del_frac"] = round(v["del"] / tot, 3) if tot else 0.0
    v["empty_pct"] = round(100 * v["empty"] / v["n"], 1)

json.dump(out, open(os.path.join(R, "analysis_v15_whisper_decomp.json"), "w"),
          indent=1, ensure_ascii=False)
print("whisper decomposition (ins/del/sub, ins_frac):")
for k in sorted(out):
    v = out[k]
    print(f"  {k:10s} ins {v['ins']:6d}  del {v['del']:6d}  sub {v['sub']:6d}"
          f"  ins_frac {v['ins_frac']:5.2f}  empty {v['empty_pct']:4.1f}%  n {v['n']}")

# reference: Ali systems at rbm5 (from v1.3 supplement) for context
print()
print("Ali q31 rbm5 zh ins_frac was 0.45, q3 0.56, para8k 0.016 (v1.3 numbers)")
