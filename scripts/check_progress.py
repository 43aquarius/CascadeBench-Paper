# -*- coding: utf-8 -*-
"""实验进度监控: 输出各实验完成度与待办任务列表"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import json, os

RES = os.path.join(ROOT, "results")

def count_ok(path):
    if not os.path.exists(path): return 0
    n = 0
    for line in open(path):
        try:
            j = json.loads(line)
            if j.get("ok"): n += 1
        except Exception: pass
    return n

TARGETS = {
    "asr_para16k": ("asr_para16k.jsonl", 4752),
    "asr_para8k":  ("asr_para8k.jsonl", 2376),
    "asr_q31":     ("asr_q31.jsonl", 4752),
    "asr_q3":      ("asr_q3.jsonl", 4752),
    "asr_omni":    ("asr_omni.jsonl", 1728),
    "mt_oracle":   ("mt_oracle.jsonl", 480),
    "mt_refmax":   ("mt_refmax.jsonl", 480),
    "mt_cascade":  ("mt_cascade.jsonl", 3456),
    "mt_e2e_omni": ("mt_e2e_omni.jsonl", 1728),
    "mt_e2e_lt":   ("mt_e2e_lt.jsonl", 1728),
}

all_done = True
for name, (fn, target) in TARGETS.items():
    n = count_ok(f"{RES}/{fn}")
    pct = 100*n/target
    status = "DONE" if n >= target else ("RUN" if n > 0 else "TODO")
    if n < target: all_done = False
    print(f"{name}: {n}/{target} ({pct:.0f}%) [{status}]")

# 失败统计
print("\n失败数(需重试):")
for name, (fn, target) in TARGETS.items():
    p = f"{RES}/{fn}"
    if not os.path.exists(p): continue
    fails = sum(1 for line in open(p) if '"ok": false' in line)
    if fails: print(f"  {name}: {fails} fails")
print("\nALL_DONE" if all_done else "\nPENDING")
