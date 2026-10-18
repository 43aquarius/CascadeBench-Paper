# -*- coding: utf-8 -*-
"""D3 真实语音 ASR 运行器
用法: python3 run_d3_asr.py <model_key> [shard_id n_shard]
model_key: para16k | para8k | q31 | q3
- 150句真实语音 × 6条件 (clean_r/revr/rb5/rb0/rbm5/rn0)
- para8k 仅中文 (d3_8k 目录)
- JSONL断点续跑, 429自动退避
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apis import asr_paraformer, asr_q31, asr_q3, load_done, append_jsonl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "audio", "d3")
BASE8 = os.path.join(ROOT, "audio", "d3_8k")
RES = os.path.join(ROOT, "results")
CORPUS = [json.loads(l) for l in open(os.path.join(ROOT, "corpus", "d3_corpus.jsonl"))]
CONDS = ["clean_r", "revr", "rb5", "rb0", "rbm5", "rn0"]

MODEL_KEY = sys.argv[1]
SHARD, NSHARD = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 1)
LOG = f"{RES}/d3_asr_{MODEL_KEY}.jsonl"
done = load_done(LOG)

def call_model(wav_path, rec):
    if MODEL_KEY == "para16k":
        return asr_paraformer("paraformer-realtime-v2", wav_path, sample_rate=16000)
    if MODEL_KEY == "para8k":
        return asr_paraformer("paraformer-realtime-8k-v2", wav_path, sample_rate=8000)
    if MODEL_KEY == "q31":
        return asr_q31(wav_path)
    if MODEL_KEY == "q3":
        return asr_q3(wav_path)
    raise ValueError(MODEL_KEY)

def sharded(key):
    import zlib
    return (zlib.crc32(key.encode()) & 0xffffffff) % NSHARD == SHARD

ok = fail = skip = 0
t0 = time.time()
for cond in CONDS:
    for rec in CORPUS:
        if MODEL_KEY == "para8k" and rec["lang"] != "zh":
            continue
        key = f"{cond}/{rec['id']}"
        if key in done: skip += 1; continue
        if not sharded(key): continue
        if MODEL_KEY == "para8k":
            wav = f"{BASE8}/{cond}/{rec['id']}.wav"
        else:
            wav = f"{BASE}/{cond}/{rec['id']}.wav"
        if not os.path.exists(wav):
            append_jsonl(LOG, {"key": key, "ok": False, "err": "no_wav"})
            fail += 1; continue
        try:
            r = call_model(wav, rec)
            append_jsonl(LOG, {"key": key, "ok": True, "text": r["text"],
                               "latency_s": r.get("latency_s"), "lang": rec["lang"],
                               "usage": r.get("usage")})
            ok += 1
        except Exception as e:
            msg = str(e)
            if "NO_WORDS" in msg:
                # 模型明确拒答(无词输出): 记为有效空转写, 与主实验口径一致
                append_jsonl(LOG, {"key": key, "ok": True, "text": "", "refusal": True,
                                   "lang": rec["lang"]})
                ok += 1
            else:
                append_jsonl(LOG, {"key": key, "ok": False, "err": msg[:160], "lang": rec["lang"]})
                fail += 1
        if (ok + fail) % 25 == 0:
            print(f"[{MODEL_KEY} s{SHARD}] ok={ok} fail={fail} skip={skip} elapsed={time.time()-t0:.0f}s", flush=True)
        if fail >= 40 and ok == 0:
            print(f"[{MODEL_KEY} s{SHARD}] 连续失败过多, 退出"); break
print(f"[{MODEL_KEY} s{SHARD}] 完成 ok={ok} fail={fail} skip={skip} {time.time()-t0:.0f}s")
