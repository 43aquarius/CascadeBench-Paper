# -*- coding: utf-8 -*-
"""TTS批量合成: 480语料句 + 40 babble噪声源句 → research/audio/tts/*.wav"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apis import tts_sambert, load_done, append_jsonl
import soundfile as sf

BASE = os.path.join(ROOT, "audio")
os.makedirs(f"{BASE}/tts", exist_ok=True)
LOG = os.path.join(ROOT, "results", "tts_log.jsonl")

jobs = []
for line in open(os.path.join(ROOT, "corpus", "corpus.jsonl")):
    rec = json.loads(line)
    jobs.append((rec["id"], rec["voice"], rec["text"]))
for line in open(os.path.join(ROOT, "corpus", "babble_sources.jsonl")):
    rec = json.loads(line)
    jobs.append((rec["id"], rec["voice"], rec["text"]))

done = load_done(LOG)
done_ids = {d for d in done}
print(f"total {len(jobs)}, done {len([j for j in jobs if j[0] in done_ids])}")

ok = fail = 0
for sid, voice, text in jobs:
    if sid in done_ids: continue
    t0 = time.time()
    try:
        data = tts_sambert(voice, text)
        path = f"{BASE}/tts/{sid}.wav"
        with open(path, "wb") as f:
            f.write(data)
        # 校验
        info = sf.info(path)
        append_jsonl(LOG, {"key": sid, "voice": voice, "ok": True,
                           "dur_s": round(info.duration,2), "latency": round(time.time()-t0,2)})
        ok += 1
    except Exception as e:
        append_jsonl(LOG, {"key": sid, "voice": voice, "ok": False, "err": str(e)[:150]})
        fail += 1
        print("FAIL", sid, str(e)[:80])
    if (ok+fail) % 50 == 0:
        print(f"progress: {ok+fail}/{len(jobs)} (ok={ok} fail={fail})", flush=True)
    time.sleep(0.3)

print(f"TTS DONE: ok={ok} fail={fail}")
