#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.6 analysis: Whisper large-v3-turbo full six-level real-babble curve.

Upgrade item 1: where does a non-vendor open-weights ASR's knee sit on the real
babble ladder? Identical methodology to v15_real.py (per-utterance
metrics.err_rate, mean x100, 1000-resample bootstrap CI seed 42; cross10 linear
interpolation of the ten-percent crossing) plus the v15_whisper.py
insertion/deletion decomposition.

Reads results/d3_asr_whisper_lg3t.jsonl and results/analysis_v15_real.json;
writes results/analysis_v16_whisper_curve.json.
"""
import json, os, sys, random

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
import metrics as M

R = os.path.join(ROOT, "results")
SRC = os.path.join(R, "d3_asr_whisper_lg3t.jsonl")
D3C = {json.loads(l)["id"]: json.loads(l)
       for l in open(os.path.join(ROOT, "corpus", "d3_corpus.jsonl"))}

RB = {"rb10": 10, "rb5": 5, "rb25": 2.5, "rb0": 0, "rbm25": -2.5, "rbm5": -5}
LEVELS = ["rb10", "rb5", "rb25", "rb0", "rbm25", "rbm5"]


def boot_ci(vals, n_boot=1000, seed=42):
    rng = random.Random(seed)
    stats = sorted(sum(rng.choices(vals, k=len(vals))) / len(vals) for _ in range(n_boot))
    return [round(stats[24], 1), round(stats[974], 1)]


def norm(text, lang):
    if lang == "zh":
        return list(M.normalize_zh(text))
    return (M.normalize_en(text) or "").split()


def ops(ref_seq, hyp_seq):
    """Levenshtein op counts (ins, del, sub) via full DP + backtrack."""
    n, m = len(ref_seq), len(hyp_seq)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            dp[i][j] = min(dp[i-1][j] + 1,
                           dp[i][j-1] + 1,
                           dp[i-1][j-1] + (ref_seq[i-1] != hyp_seq[j-1]))
    i, j = n, m
    ins = dele = sub = 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and ref_seq[i-1] == hyp_seq[j-1]:
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] + 1:
            sub += 1
            i -= 1
            j -= 1
        elif j > 0 and dp[i][j] == dp[i][j-1] + 1:
            ins += 1
            j -= 1
        else:
            dele += 1
            i -= 1
    return ins, dele, sub


def cross10(points):
    pts = sorted(points, key=lambda p: -p[0])
    if pts[0][1] >= 10:
        return "above-highest"
    for (s1, e1), (s2, e2) in zip(pts, pts[1:]):
        if e2 >= 10 > e1:
            return round(s2 + (e2 - 10) / (e2 - e1) * (s1 - s2), 1) if e2 != e1 else s2
    return "below-lowest"


# ---------- 1. load turbo log ----------
log = {}
for line in open(SRC):
    line = line.strip()
    if not line:
        continue
    d = json.loads(line)
    if d.get("ok") and d.get("key"):
        log[d["key"]] = d

errs, decomp = {}, {}
for key, d in log.items():
    cond, sid = key.split("/")
    rec = D3C.get(sid)
    if rec is None:
        continue
    lang = rec["lang"]
    e = M.err_rate(rec["text"], d.get("text") or "", lang)
    errs.setdefault((cond, lang), []).append((e, not (d.get("text") or "").strip()))
    i_, dl_, s_ = ops(norm(rec["text"], lang), norm(d.get("text") or "", lang))
    c = decomp.setdefault((cond, lang), {"ins": 0, "del": 0, "sub": 0, "n": 0, "empty": 0})
    c["ins"] += i_
    c["del"] += dl_
    c["sub"] += s_
    c["n"] += 1
    if not (d.get("text") or "").strip():
        c["empty"] += 1

ladder = {}
for (cond, lang), pairs in errs.items():
    vals = [p[0] * 100 for p in pairs]
    ladder[f"{cond}/{lang}"] = {
        "err": round(sum(vals) / len(vals), 1),
        "ci": boot_ci(vals),
        "n": len(vals),
        "empty_pct": round(100 * sum(1 for _, em in pairs if em) / len(pairs), 1)}

RESULT = {"model": "whisper-large-v3-turbo (int8, CPU, beam 1)",
          "source_log": "results/d3_asr_whisper_lg3t.jsonl",
          "n_ok": len(log), "ladder": ladder}

l6 = {}
for lang in ("zh", "en"):
    pts = [(snr, ladder[f"{c}/{lang}"]["err"]) for c, snr in RB.items()
           if f"{c}/{lang}" in ladder]
    l6[lang] = {"points": [{"snr": s, "err": e} for s, e in pts],
                "cross10": cross10(pts) if len(pts) >= 2 else None}
RESULT["babble_cross10"] = l6

D = {}
for (cond, lang), v in decomp.items():
    tot = v["ins"] + v["del"] + v["sub"]
    D[f"{cond}/{lang}"] = {
        "ins": v["ins"], "del": v["del"], "sub": v["sub"], "n": v["n"],
        "ins_frac": round(v["ins"] / tot, 3) if tot else 0.0,
        "del_frac": round(v["del"] / tot, 3) if tot else 0.0,
        "empty_pct": round(100 * v["empty"] / v["n"], 1)}
RESULT["decomp"] = D

# ---------- 2. vendor + whisper-small side-by-side ----------
A = json.load(open(os.path.join(R, "analysis_v15_real.json")))
vend = A["asr_real_all"]
names = {"q31": "Qwen-Audio", "q3": "Qwen3-ASR", "para16k": "16kHz-spec",
         "para8k": "tel-spec", "whisper": "whisper-small", "lg3t": "lg-v3-turbo"}

print(f"turbo records ok: {len(log)}")
for lang in ("zh", "en"):
    print(f"\n=== {lang}: six-level real babble, error % ===")
    print(f"{'SNR':>6} |" + "|".join(f"{names[s]:>13}" for s in
          ["lg3t", "q31", "q3", "para16k", "para8k", "whisper"]) + "|")
    for cond in LEVELS:
        row = f"{RB[cond]:>6} |"
        for s in ["lg3t", "q31", "q3", "para16k", "para8k", "whisper"]:
            cell = (ladder if s == "lg3t" else vend[s]).get(f"{cond}/{lang}")
            row += f"{cell['err']:>13.1f}|" if cell else f"{'—':>13}|"
        print(row)
    print(f"cross10 (turbo): {l6[lang]['cross10']}")
    for s in ["q31", "q3", "para16k", "para8k"]:
        cc = A.get("babble_ladder6", {}).get(s, {}).get(lang, {}).get("cross10")
        print(f"cross10 ({names[s]}): {cc}")

print("\n=== clean_r anchor ===")
for lang in ("zh", "en"):
    t = ladder.get(f"clean_r/{lang}")
    w = vend["whisper"].get(f"clean_r/{lang}")
    print(f"{lang}: turbo={t['err'] if t else '—'} whisper-small={w['err'] if w else '—'}")

json.dump(RESULT, open(os.path.join(R, "analysis_v16_whisper_curve.json"), "w"),
          indent=1, ensure_ascii=False)
print("\nwrote analysis_v16_whisper_curve.json")
