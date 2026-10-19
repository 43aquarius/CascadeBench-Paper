#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""升级项c: rev_mit (MIT实测RIR混响, 主网格480句) 的 ASR + MT 实验
用法: python3 run_revmit.py <stage>
  stage: asr_q31 | asr_q3 | asr_p16 | asr_p8 | mt
断点续跑; TIME_BUDGET 环境变量控制本次秒数(默认 520s)"""
import os, sys, json, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DASHSCOPE_API_KEY", open(os.path.join(ROOT, "apikey.txt")).read().strip())
from apis import (asr_paraformer, asr_q31, asr_q3, mt_uni,
                  load_done, append_jsonl)

BASE = os.path.join(ROOT, "audio")
RES = os.path.join(ROOT, "results")
STAGE = sys.argv[1]
BUDGET = float(os.environ.get("TIME_BUDGET", "520"))
T0 = time.time()

corpus = [json.loads(l) for l in open(os.path.join(ROOT, "corpus", "corpus.jsonl"))]
CORP = {r["id"]: r for r in corpus}

def tgt_lang(rec): return "en" if rec["lang"] == "zh" else "zh"

# ---------- ASR ----------
def run_asr(mk):
    LOG = f"{RES}/revmit_asr_{mk}.jsonl"; done = load_done(LOG)
    if mk == "p8":
        jobs = [r for r in corpus if r["lang"] == "zh"]
    else:
        jobs = corpus
    todo = [r for r in jobs if f"rev_mit/{r['id']}" not in done]
    print(f"[revmit asr {mk}] todo={len(todo)}", flush=True)
    ok = fail = 0
    for rec in todo:
        if time.time() - T0 > BUDGET:
            print(f"BUDGET STOP at {ok+fail}/{len(todo)}", flush=True); return
        key = f"rev_mit/{rec['id']}"
        if mk == "p8":
            wav = f"{BASE}/perturbed_8k/rev_mit/{rec['id']}.wav"
        else:
            wav = f"{BASE}/perturbed/rev_mit/{rec['id']}.wav"
        if not os.path.exists(wav):
            append_jsonl(LOG, {"key": key, "ok": False, "err": "no_wav"}); continue
        try:
            if mk == "q31": r = asr_q31(wav)
            elif mk == "q3": r = asr_q3(wav)
            elif mk == "p16": r = asr_paraformer("paraformer-realtime-v2", wav, sample_rate=16000)
            elif mk == "p8": r = asr_paraformer("paraformer-realtime-8k-v2", wav, sample_rate=8000)
            txt = (r.get("text") or "").strip()
            append_jsonl(LOG, {"key": key, "ok": True, "text": txt,
                               "lang": rec["lang"], "usage": r.get("usage", {}),
                               "latency_s": r.get("latency_s")})
            ok += 1
        except Exception as e:
            append_jsonl(LOG, {"key": key, "ok": False, "err": str(e)[:150]}); fail += 1
        if (ok + fail) % 25 == 0:
            print(f"  {ok+fail}/{len(todo)} (ok {ok})", flush=True)
    print(f"[revmit asr {mk}] DONE ok={ok} fail={fail}", flush=True)

# ---------- MT (级联: 翻译各ASR的rev_mit转写) ----------
def run_mt():
    LOG = f"{RES}/revmit_mt_cascade.jsonl"; done = load_done(LOG)
    asr = {}
    for mk in ["q31", "q3", "p16", "p8"]:
        p = f"{RES}/revmit_asr_{mk}.jsonl"
        if not os.path.exists(p): continue
        d = {}
        for line in open(p):
            j = json.loads(line)
            if j.get("ok"): d[j["key"]] = j.get("text", "")
        asr[mk] = d
        print(f"loaded asr {mk}: {len(d)}", flush=True)
    todo = []
    for mk, d in asr.items():
        for rec in corpus:
            key = f"rev_mit/{rec['id']}"
            if key not in d: continue
            mkey = f"{mk}/{key}"
            if mkey in done: continue
            todo.append((mk, rec, d[key]))
    print(f"[revmit mt] todo={len(todo)}", flush=True)
    ok = fail = 0
    for mk, rec, src in todo:
        if time.time() - T0 > BUDGET:
            print(f"BUDGET STOP at {ok+fail}/{len(todo)}", flush=True); return
        mkey = f"{mk}/rev_mit/{rec['id']}"
        try:
            if not src.strip():
                append_jsonl(LOG, {"key": mkey, "ok": True, "text": "", "src": src,
                                   "lang": rec["lang"], "asr": mk, "usage": {}})
                ok += 1
            else:
                r = mt_uni(src, rec["lang"], tgt_lang(rec))
                append_jsonl(LOG, {"key": mkey, "ok": True, "text": r["text"], "src": src,
                                   "lang": rec["lang"], "asr": mk, "usage": r.get("usage", {})})
                ok += 1
        except Exception as e:
            append_jsonl(LOG, {"key": mkey, "ok": False, "err": str(e)[:150], "asr": mk}); fail += 1
        time.sleep(0.15)
        if (ok + fail) % 50 == 0:
            print(f"  {ok+fail}/{len(todo)} (ok {ok})", flush=True)
    print(f"[revmit mt] DONE ok={ok} fail={fail}", flush=True)

if STAGE.startswith("asr_"):
    run_asr(STAGE.split("_", 1)[1])
elif STAGE == "mt":
    run_mt()
else:
    raise SystemExit(f"unknown stage {STAGE}")
