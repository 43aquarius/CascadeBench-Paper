#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.8 review fix #2: Whisper Mandarin CER traditional->simplified sensitivity.

The released Whisper scoring applies no script conversion, so traditional
characters in ~10% (small) / ~13% (turbo) of Mandarin outputs are scored as
substitutions. This script applies OpenCC t2s to every zh hypothesis before
scoring, recomputes the per-condition CER ladders and the SNR@10% crossings,
and reports (a) the share of sentences containing convertible traditional
characters before conversion, (b) the share still containing traditional
characters after conversion, (c) before/after CER side by side.

Scoring is otherwise identical to v16_whisper_curve.py (per-utterance
metrics.err_rate, mean x100, 1000-resample bootstrap CI seed 42; cross10
linear interpolation), and the 'before' columns must reproduce the released
analysis_v16_whisper_curve.json exactly (regression check).

Writes analysis_v18_whisper_t2s.json.
"""
import json, os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics as M
from opencc import OpenCC
import opencc as _occpkg

cc = OpenCC("t2s")
DICT_DIR = os.path.join(os.path.dirname(_occpkg.__file__), "dictionary")

# single-character t2s table (for traditional-character detection)
t2s_chars = {}
with open(os.path.join(DICT_DIR, "TSCharacters.txt"), encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            t2s_chars[parts[0]] = parts[1]

def n_trad(t):
    return sum(1 for ch in t if ch in t2s_chars)

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
SRC = {
    "whisper-small": os.path.join(R, "d3_asr_whisper.jsonl"),
    "whisper-large-v3-turbo": os.path.join(R, "d3_asr_whisper_lg3t.jsonl"),
}
D3C = {json.loads(l)["id"]: json.loads(l)
       for l in open(os.path.join(R, "..", "corpus", "d3_corpus.jsonl"))}
RB = {"rb10": 10, "rb5": 5, "rb25": 2.5, "rb0": 0, "rbm25": -2.5, "rbm5": -5}

def boot_ci(vals, n_boot=1000, seed=42):
    rng = random.Random(seed)
    stats = sorted(sum(rng.choices(vals, k=len(vals))) / len(vals) for _ in range(n_boot))
    return [round(stats[24], 1), round(stats[974], 1)]

def cross10(points):
    pts = sorted(points, key=lambda p: -p[0])
    if pts[0][1] >= 10:
        return "above-highest"
    for (s1, e1), (s2, e2) in zip(pts, pts[1:]):
        if e2 >= 10 > e1:
            return round(s2 + (e2 - 10) / (e2 - e1) * (s1 - s2), 1) if e2 != e1 else s2
    return "below-lowest"

# sanity: reference transcripts must be simplified
ref_trad = sum(1 for rec in D3C.values() if rec["lang"] == "zh" and n_trad(rec["text"]))
print(f"zh reference sentences containing traditional chars: {ref_trad} (expect 0)")

RESULT = {"ref_trad_sentences": ref_trad, "models": {}}

for model, path in SRC.items():
    log = {}
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        if d.get("ok") and d.get("key"):
            log[d["key"]] = d  # last ok record wins

    errs_b, errs_a, tradstats = {}, {}, {}
    for key, d in log.items():
        cond, sid = key.split("/")
        rec = D3C.get(sid)
        if rec is None or rec["lang"] != "zh":
            continue
        hyp = d.get("text") or ""
        hyp_s = cc.convert(hyp)
        errs_b.setdefault(cond, []).append((M.err_rate(rec["text"], hyp, "zh"), not hyp.strip()))
        errs_a.setdefault(cond, []).append((M.err_rate(rec["text"], hyp_s, "zh"), not hyp_s.strip()))
        st = tradstats.setdefault(cond, {"n": 0, "trad_before": 0, "trad_after": 0})
        st["n"] += 1
        if n_trad(hyp) > 0:
            st["trad_before"] += 1
        if n_trad(hyp_s) > 0:
            st["trad_after"] += 1

    ladder_b, ladder_a = {}, {}
    for cond, pairs in errs_b.items():
        vb = [p[0] * 100 for p in pairs]
        va = [p[0] * 100 for p in errs_a[cond]]
        ladder_b[cond] = {"err": round(sum(vb) / len(vb), 1), "ci": boot_ci(vb), "n": len(vb)}
        ladder_a[cond] = {"err": round(sum(va) / len(va), 1), "ci": boot_ci(va), "n": len(va)}

    pts_b = [(RB[c], ladder_b[c]["err"]) for c in RB if c in ladder_b]
    pts_a = [(RB[c], ladder_a[c]["err"]) for c in RB if c in ladder_a]

    RESULT["models"][model] = {
        "ladder_zh_before": ladder_b, "ladder_zh_after": ladder_a,
        "cross10_zh_before": cross10(pts_b) if len(pts_b) >= 2 else None,
        "cross10_zh_after": cross10(pts_a) if len(pts_a) >= 2 else None,
        "trad_sentences": {c: {"n": s["n"], "before_pct": round(100 * s["trad_before"] / s["n"], 1),
                               "after_pct": round(100 * s["trad_after"] / s["n"], 1)}
                           for c, s in sorted(tradstats.items())},
    }
    m = RESULT["models"][model]
    print(f"\n=== {model} (zh) ===")
    print(f"  {'cond':8s} {'CER before':>10s} {'CER after':>10s} {'Δ':>6s} {'trad%b':>6s} {'trad%a':>6s}")
    for cond in sorted(ladder_b, key=lambda c: (c not in RB, -RB.get(c, 99))):
        ts = m["trad_sentences"].get(cond, {})
        db, da = ladder_b[cond]["err"], ladder_a[cond]["err"]
        print(f"  {cond:8s} {db:10.1f} {da:10.1f} {da-db:6.1f} "
              f"{ts.get('before_pct','-'):>6} {ts.get('after_pct','-'):>6}")
    print(f"  cross10 before: {m['cross10_zh_before']}  after: {m['cross10_zh_after']}")
    tot = sum(s["n"] for s in tradstats.values())
    tb = sum(s["trad_before"] for s in tradstats.values())
    ta = sum(s["trad_after"] for s in tradstats.values())
    print(f"  trad sentences: {tb}/{tot} before ({100*tb/tot:.1f}%), {ta}/{tot} after ({100*ta/tot:.1f}%)")

# regression check against released turbo analysis
v16 = json.load(open(os.path.join(R, "analysis_v16_whisper_curve.json")))
turbo_b = RESULT["models"]["whisper-large-v3-turbo"]["ladder_zh_before"]
mismatch = [c for c in turbo_b
            if c in v16["ladder"] and f"{c}/zh" in v16["ladder"]
            and abs(turbo_b[c]["err"] - v16["ladder"][f"{c}/zh"]["err"]) > 0.05]
print(f"\nregression check turbo before-vs-v16: {'PASS' if not mismatch else 'MISMATCH ' + str(mismatch)}")

out = os.path.join(R, "analysis_v18_whisper_t2s.json")
json.dump(RESULT, open(out, "w"), indent=1, ensure_ascii=False)
print(f"wrote {out}")
