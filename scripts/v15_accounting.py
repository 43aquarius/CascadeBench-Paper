#!/usr/bin/env python3
"""v1.5 master call accounting: verify every count against raw JSONL logs.

Conventions (inherited from v1.3 Table 2):
- successful calls: every logged ok=True API response (re-runs included)
- unique evaluations: distinct (system, condition, sentence) keys with ok=True
- local model runs (whisper-small) are NOT API calls; reported separately
"""
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_ROOT = _os.path.dirname(_HERE)              # repository root
_PAPER = _os.path.join(_ROOT, "paper", "latex")
_FIG = _os.path.join(_ROOT, "figures")
import json, os
from collections import Counter, defaultdict

R = _os.path.join(_ROOT, "results")

def load(fn):
    path = os.path.join(R, fn)
    if not os.path.exists(path):
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out

def stats(fn, key_fn=lambda d: d["key"]):
    rows = load(fn)
    ok = [d for d in rows if d.get("ok")]
    uniq = len({key_fn(d) for d in ok})
    return len(rows), len(ok), uniq

print("=" * 78)
print("A. v1.3 baseline cross-check (should reproduce Table 2 of v1.3)")
print("=" * 78)
base = {
    "Sambert TTS": ("tts_log.jsonl", 520, 520),
    "ASR para16k": ("asr_para16k.jsonl", 5174, 4752),
    "ASR para8k": ("asr_para8k.jsonl", 2376, 2376),
    "ASR q31": ("asr_q31.jsonl", 5154, 4752),
    "ASR q3": ("asr_q3.jsonl", 4752, 4752),
    "ASR omni": ("asr_omni.jsonl", 1271, 1271),
    "MT oracle+ref": ("mt_oracle.jsonl", 480, 480),
    "MT refmax": ("mt_refmax.jsonl", 480, 480),
    "MT cascade": ("mt_cascade.jsonl", 3456, 3456),
    "MT e2e omni": ("mt_e2e_omni.jsonl", 1004, 1004),
    "MT e2e LT": ("mt_e2e_lt.jsonl", 1571, 1544),
}
tot_calls = tot_unique = 0
for name, (fn, exp_calls, exp_uniq) in base.items():
    lines, ok, uniq = stats(fn)
    flag = "OK" if (ok == exp_calls and uniq == exp_uniq) else f"MISMATCH(exp {exp_calls}/{exp_uniq})"
    print(f"{name:16s} lines={lines:5d} ok={ok:5d} uniq={uniq:5d}  {flag}")
    tot_calls += ok; tot_unique += uniq
print(f"{'ORIGINAL SUM':16s} calls={tot_calls} unique={tot_unique}  (v1.3 says 26238/25363)")

ext = ["ext_asr_para16k", "ext_asr_para8k", "ext_asr_q3", "ext_asr_q31",
       "ext_mt_cascade", "ext_mt_cascade_q3main", "ext_mt_e2e_lt", "ext_mt_latency"]
ec = eu = 0
for name in ext:
    lines, ok, uniq = stats(name + ".jsonl")
    print(f"{name:24s} lines={lines:5d} ok={ok:5d} uniq={uniq:5d}")
    ec += ok; eu += uniq
for r in ("r1", "r2"):
    for s in ("q31_n0", "q3_n0", "q31_tempo", "q3_tempo"):
        lines, ok, uniq = stats(f"ext_rep_{s}_{r}.jsonl")
        ec += ok; eu += uniq
print(f"{'EXT SUM':24s} calls={ec} unique={eu}  (v1.3 says 5581/5581)")

print()
print("=" * 78)
print("B. Real-speech validation: v1.2 core + v1.4 babble expansion")
print("=" * 78)
NEW_CONDS = {"rb10", "rb25", "rbm25"}
OLD_CONDS = {"clean_r", "revr", "rb5", "rb0", "rbm5", "rn0"}
d3 = {
    "d3_asr_para16k": "asr_para16k", "d3_asr_q31": "asr_q31",
    "d3_asr_q3": "asr_q3", "d3_asr_para8k": "asr_para8k",
    "d3_mt_cascade": "mt_cascade(q31 fe)",
}
for fn in ["d3_asr_para16k", "d3_asr_q31", "d3_asr_q3", "d3_asr_para8k",
           "d3_mt_cascade", "d3_asr_whisper"]:
    rows = load(fn + ".jsonl")
    ok = [d for d in rows if d.get("ok")]
    old = [d for d in ok if d["key"].split("/")[0] in OLD_CONDS]
    new = [d for d in ok if d["key"].split("/")[0] in NEW_CONDS]
    uo = len({d["key"] for d in old}); un = len({d["key"] for d in new})
    print(f"{fn:20s} ok_total={len(ok):5d}  old_ok={len(old):5d}(uniq {uo})  new_ok={len(new):5d}(uniq {un})  failed={len(rows)-len(ok)}")
for fn in ["d3_mt_e2e_lt", "d3_mt_oracle"]:
    lines, ok, uniq = stats(fn + ".jsonl")
    print(f"{fn:20s} lines={lines} ok={ok} uniq={uniq}")

print()
print("=" * 78)
print("C. v1.4 additions: rev-mit (measured RIR on synthetic corpus) + GLM tasks")
print("=" * 78)
for fn in ["revmit_asr_p16", "revmit_asr_p8", "revmit_asr_q3", "revmit_asr_q31",
           "revmit_mt_cascade"]:
    lines, ok, uniq = stats(fn + ".jsonl")
    print(f"{fn:20s} lines={lines:5d} ok={ok:5d} uniq={uniq:5d} failed={lines-ok}")

rows = load("glm_tasks.jsonl")
kind_stat = defaultdict(lambda: [0, 0, set()])
for d in rows:
    k = d.get("kind", "?") + ":" + d["key"].split("/")[0]
    kind_stat[k][0] += 1
    if d.get("ok"):
        kind_stat[k][1] += 1
        kind_stat[k][2].add(d["key"])
for k, (n, okn, keys) in sorted(kind_stat.items()):
    print(f"glm {k:22s} lines={n:4d} ok={okn:4d} uniq_ok={len(keys):4d}")

print()
print("=" * 78)
print("D. GRAND TOTALS (successful calls / unique evaluations)")
print("=" * 78)
# original + ext from v1.3 (verified above), real validation recomputed
real_core = 4650  # v1.2: verified in v1.3 round
# new-condition successful unique counts from section B
rows = load("d3_asr_para16k.jsonl"); new_p16 = len({d["key"] for d in rows if d.get("ok") and d["key"].split("/")[0] in NEW_CONDS})
rows = load("d3_asr_q31.jsonl");    new_q31 = len({d["key"] for d in rows if d.get("ok") and d["key"].split("/")[0] in NEW_CONDS})
rows = load("d3_asr_q3.jsonl");     new_q3 = len({d["key"] for d in rows if d.get("ok") and d["key"].split("/")[0] in NEW_CONDS})
rows = load("d3_asr_para8k.jsonl"); new_p8 = len({d["key"] for d in rows if d.get("ok") and d["key"].split("/")[0] in NEW_CONDS})
rows = load("d3_mt_cascade.jsonl"); new_mt = len({d["key"] for d in rows if d.get("ok") and d["key"].split("/")[0] in NEW_CONDS})
d3_expand = new_p16 + new_q31 + new_q3 + new_p8 + new_mt
print(f"D3 babble expansion successful unique: {new_p16}+{new_q31}+{new_q3}+{new_p8}+{new_mt} = {d3_expand}")

rows = load("revmit_asr_p16.jsonl") + load("revmit_asr_p8.jsonl") + load("revmit_asr_q3.jsonl") + load("revmit_asr_q31.jsonl")
revmit_asr_ok = sum(1 for d in rows if d.get("ok"))
rows = load("revmit_mt_cascade.jsonl"); revmit_mt_ok = sum(1 for d in rows if d.get("ok"))
print(f"rev-mit: ASR ok={revmit_asr_ok}  MT ok={revmit_mt_ok}  sum={revmit_asr_ok+revmit_mt_ok}")

glm_ok = sum(1 for d in load("glm_tasks.jsonl") if d.get("ok"))
print(f"GLM successful: {glm_ok}")

orig, extn = 26238, 5581
grand = orig + extn + real_core + d3_expand + (revmit_asr_ok + revmit_mt_ok) + glm_ok
print()
print(f"GRAND TOTAL successful API responses = {orig} + {extn} + {real_core} + {d3_expand} + {revmit_asr_ok+revmit_mt_ok} + {glm_ok} = {grand}")
print(f"  (v1.4 manuscript claimed 38,494 in sec 3.7 / 41,854 in abstract+Table2)")
print(f"  -> both MISSED the {glm_ok} GLM calls; 41,854 = 36,469 + {d3_expand} + {revmit_asr_ok+revmit_mt_ok}")
whisper_rows = load("d3_asr_whisper.jsonl")
whisper_ok = sum(1 for d in whisper_rows if d.get("ok"))
print(f"Whisper-small local runs (not API calls): {whisper_ok} ok of {len(whisper_rows)}")
glm_failed = sum(1 for d in load('glm_tasks.jsonl') if not d.get('ok'))
print(f"Failed GLM attempts: {glm_failed}")
