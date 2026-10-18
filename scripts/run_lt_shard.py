# -*- coding: utf-8 -*-
"""LT分片并行运行器: python3 run_lt_shard.py <shard_id> <num_shards>"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apis import livetranslate, load_done, append_jsonl

SHARD, NSHARD = int(sys.argv[1]), int(sys.argv[2])
BASE = os.path.join(ROOT, "audio")
RES = os.path.join(ROOT, "results")
corpus = [json.loads(l) for l in open(os.path.join(ROOT, "corpus", "corpus.jsonl"))]
sweep_ids = set(json.load(open(os.path.join(ROOT, "corpus", "sweep_ids.json"))))
ALL_CONDS = ["clean","n10","n0","rev","nb","opus","pl","clip","tempo","n20","n15","n5"]
LOG = f"{RES}/mt_e2e_lt.jsonl"

def tgt_lang(rec): return "en" if rec["lang"] == "zh" else "zh"

done = load_done(LOG)
ok = fail = 0
for rec in corpus:
    if rec["id"] not in sweep_ids: continue
    for cond in ALL_CONDS:
        key = f"{cond}/{rec['id']}"
        if key in done: continue
        # 分片: 按key哈希
        if hash(key) % NSHARD != SHARD: continue
        wav = f"{BASE}/perturbed/{cond}/{rec['id']}.wav"
        if not os.path.exists(wav): continue
        try:
            r = livetranslate(wav, tgt_lang(rec))
            append_jsonl(LOG, {"key": key, "ok": True, "text": r["translation"],
                               "source_asr": r["source"], "latency_s": r["latency_s"], "lang": rec["lang"]})
            ok += 1
        except Exception as e:
            append_jsonl(LOG, {"key": key, "ok": False, "err": str(e)[:150]})
            fail += 1
        time.sleep(0.3)
print(f"[shard {SHARD}/{NSHARD}] ok={ok} fail={fail}")
