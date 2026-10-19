#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""升级项a: Whisper large-v3-turbo (开源非阿里ASR) 在真实语音9条件上推理
断点续传, 分块运行; 输出格式与 d3_asr_q31.jsonl 一致"""
import os, sys, json, time, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
AUDIO = os.path.join(ROOT, "audio", "d3")
OUT = os.path.join(ROOT, "results", "d3_asr_whisper.jsonl")
CORPUS = {r["id"]: r for r in (json.loads(l) for l in open(os.path.join(ROOT, "corpus", "d3_corpus.jsonl")))}
CONDS = ["clean_r", "rb5", "rb0", "rbm5"]

def load_done():
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            try:
                j = json.loads(line)
                if j.get("ok") and j.get("key"): done.add(j["key"])
            except Exception: pass
    return done

def append(obj):
    with open(OUT, "a") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n"); f.flush()

MAXN = int(sys.argv[1]) if len(sys.argv) > 1 else 10**9  # 本次最多处理N句
TEST = os.environ.get("WSP_TEST") == "1"

from faster_whisper import WhisperModel
import wave as wavlib
t0 = time.time()
model = WhisperModel("Systran/faster-whisper-small", device="cpu",
                     compute_type="int8", cpu_threads=2, num_workers=1)
print(f"model loaded in {time.time()-t0:.0f}s", flush=True)

INIT_PROMPT = {"zh": "以下是普通话的句子，简体白话文。",
               "en": ""}

def read_pcm16k(path):
    w = wavlib.open(path)
    assert w.getframerate() == 16000 and w.getnchannels() == 1, "need 16k mono"
    import numpy as np
    raw = w.readframes(w.getnframes()); w.close()
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

done = load_done()
todo = [(c, i) for c in CONDS for i in sorted(CORPUS) if f"{c}/{i}" not in done]
print(f"done={len(done)} todo={len(todo)}", flush=True)

n_run = 0; t_infer = 0.0
for c, sid in todo:
    if n_run >= MAXN: break
    wav = f"{AUDIO}/{c}/{sid}.wav"
    if not os.path.exists(wav):
        append({"key": f"{c}/{sid}", "ok": False, "err": "missing_audio"}); continue
    lang = CORPUS[sid]["lang"]
    ts = time.time()
    try:
        audio = read_pcm16k(wav)
        segments, info = model.transcribe(audio, language=lang, beam_size=1,
                                          vad_filter=False, condition_on_previous_text=False,
                                          initial_prompt=INIT_PROMPT.get(lang) or None)
        txt = "".join(s.text for s in segments).strip()
        dt = time.time() - ts; t_infer += dt; n_run += 1
        append({"key": f"{c}/{sid}", "ok": True, "text": txt,
                "latency_s": round(dt, 2), "lang": lang, "model": "whisper-small"})
    except Exception as e:
        append({"key": f"{c}/{sid}", "ok": False, "err": str(e)[:200]})
    if n_run % 20 == 0 and n_run:
        print(f"  {n_run} done, avg {t_infer/n_run:.1f}s/utt", flush=True)
    if TEST and n_run >= 5: break

print(f"RUN DONE: {n_run} utts, avg {t_infer/max(n_run,1):.1f}s/utt, remaining {len(todo)-n_run}", flush=True)
