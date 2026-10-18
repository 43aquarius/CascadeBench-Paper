# -*- coding: utf-8 -*-
"""CascadeBench ASR实验运行器
用法: python3 run_asr.py <model_key>
model_key: para16k | para8k | q31 | q3 | omni
- 全部模型跑主网格9条件; sweep子集跑n20/n15/n5
- para8k 用 perturbed_8k 目录 (8kHz输入)
- omni 只跑144句sweep子集 (配额与时间考虑)
- JSONL断点续跑, 429自动退避
"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apis import asr_paraformer, asr_q31, asr_q3, omni_audio, load_done, append_jsonl

BASE = os.path.join(ROOT, "audio")
RES = os.path.join(ROOT, "results")
MODEL_KEY = sys.argv[1]

corpus = [json.loads(l) for l in open(os.path.join(ROOT, "corpus", "corpus.jsonl"))]
sweep_ids = set(json.load(open(os.path.join(ROOT, "corpus", "sweep_ids.json"))))
LOG = f"{RES}/asr_{MODEL_KEY}.jsonl"
done = load_done(LOG)
MAIN_CONDS = ["clean","n10","n0","rev","nb","opus","pl","clip","tempo"]
SWEEP_CONDS = ["n20","n15","n5"]

ASR_PROMPT_ZH = "Please transcribe this speech verbatim in its original language. Output only the transcript."
E2E_PROMPT = {"zh": "Please translate this Chinese speech into English. Output only the English translation.",
              "en": "Please translate this English speech into Chinese. Output only the Chinese translation."}

def call_model(wav_path, rec):
    lang = rec["lang"]
    if MODEL_KEY == "para16k":
        return asr_paraformer("paraformer-realtime-v2", wav_path, sample_rate=16000)
    if MODEL_KEY == "para8k":
        return asr_paraformer("paraformer-realtime-8k-v2", wav_path, sample_rate=8000)
    if MODEL_KEY == "q31":
        return asr_q31(wav_path)
    if MODEL_KEY == "q3":
        return asr_q3(wav_path)
    if MODEL_KEY == "omni":
        return omni_audio(wav_path, ASR_PROMPT_ZH)
    raise ValueError(MODEL_KEY)

def wav_dir(cond):
    return f"{BASE}/perturbed_8k/{cond}" if MODEL_KEY == "para8k" else f"{BASE}/perturbed/{cond}"

def build_jobs():
    jobs = []
    subset = (MODEL_KEY == "omni")
    zh_only = (MODEL_KEY == "para8k")  # 电话带专用模型仅支持中文
    # 条件主序: 先clean全量(供验证), 再其余
    for cond in MAIN_CONDS:
        for rec in corpus:
            if subset and rec["id"] not in sweep_ids: continue
            if zh_only and rec["lang"] != "zh": continue
            jobs.append((cond, rec))
    for cond in SWEEP_CONDS:
        for rec in corpus:
            if rec["id"] not in sweep_ids: continue
            if zh_only and rec["lang"] != "zh": continue
            jobs.append((cond, rec))
    return jobs

jobs = build_jobs()
todo = [(c, r) for c, r in jobs if f"{c}/{r['id']}" not in done]
print(f"[{MODEL_KEY}] total jobs={len(jobs)}, todo={len(todo)}", flush=True)

ok = fail = 0
t_start = time.time()
for cond, rec in todo:
    key = f"{cond}/{rec['id']}"
    wav = f"{wav_dir(cond)}/{rec['id']}.wav"
    if not os.path.exists(wav):
        append_jsonl(LOG, {"key": key, "ok": False, "err": "no_wav"})
        fail += 1; continue
    t0 = time.time()
    try:
        r = call_model(wav, rec)
        append_jsonl(LOG, {"key": key, "ok": True, "text": r["text"],
                           "latency_s": round(time.time()-t0, 3),
                           "api_latency_s": r.get("latency_s"),
                           "usage": r.get("usage", {}), "ref": rec["text"], "lang": rec["lang"]})
        ok += 1
    except Exception as e:
        append_jsonl(LOG, {"key": key, "ok": False, "err": str(e)[:200]})
        fail += 1
        if "AllocationQuota" in str(e) or "free quota" in str(e).lower():
            print(f"[{MODEL_KEY}] QUOTA EXHAUSTED, stopping", flush=True)
            break
    n = ok + fail
    if n % 100 == 0:
        el = time.time() - t_start
        print(f"[{MODEL_KEY}] {n}/{len(todo)} ok={ok} fail={fail} elapsed={el/60:.1f}min eta={el/n*(len(todo)-n)/60:.1f}min", flush=True)

print(f"[{MODEL_KEY}] DONE ok={ok} fail={fail} in {(time.time()-t_start)/60:.1f}min", flush=True)
