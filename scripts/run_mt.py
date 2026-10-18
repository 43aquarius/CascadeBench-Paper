# -*- coding: utf-8 -*-
"""CascadeBench 翻译实验运行器
用法: python3 run_mt.py <phase>
phase: oracle   - qwen-mt-uni 翻译干净参考文本 (级联上界), 480句
       refmax   - qwen3.8-max 翻译干净参考文本 (独立参考), 480句
       cascade  - qwen-mt-uni 翻译 ASR输出 (q31+para16k × 144子集 × 12条件)
       e2e_omni - omni-flash 音频直译 (144子集 × 12条件)
       e2e_lt   - livetranslate 音频直译 (144子集 × 12条件)
"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apis import mt_uni, gen_text, omni_audio, livetranslate, load_done, append_jsonl

BASE = os.path.join(ROOT, "audio")
RES = os.path.join(ROOT, "results")
PHASE = sys.argv[1]
corpus = [json.loads(l) for l in open(os.path.join(ROOT, "corpus", "corpus.jsonl"))]
sweep_ids = set(json.load(open(os.path.join(ROOT, "corpus", "sweep_ids.json"))))
MAIN_CONDS = ["clean","n10","n0","rev","nb","opus","pl","clip","tempo"]
SWEEP_CONDS = ["n20","n15","n5"]
ALL_CONDS = MAIN_CONDS + SWEEP_CONDS

E2E_PROMPT = {"zh": "Please translate this Chinese speech into English. Output only the English translation.",
              "en": "Please translate this English speech into Chinese. Output only the Chinese translation."}

def tgt_lang(rec): return "en" if rec["lang"] == "zh" else "zh"
def src_lang(rec): return rec["lang"]

def run_oracle():
    LOG = f"{RES}/mt_oracle.jsonl"; done = load_done(LOG)
    ok = fail = 0
    for rec in corpus:
        key = rec["id"]
        if key in done: continue
        try:
            r = mt_uni(rec["text"], src_lang(rec), tgt_lang(rec))
            append_jsonl(LOG, {"key": key, "ok": True, "text": r["text"], "src": rec["text"],
                               "lang": rec["lang"], "usage": r.get("usage", {})})
            ok += 1
        except Exception as e:
            append_jsonl(LOG, {"key": key, "ok": False, "err": str(e)[:150]}); fail += 1
        time.sleep(0.25)
        if (ok+fail) % 100 == 0: print(f"oracle {ok+fail}/480", flush=True)
    print(f"oracle DONE ok={ok} fail={fail}")

def run_refmax():
    LOG = f"{RES}/mt_refmax.jsonl"; done = load_done(LOG)
    ok = fail = 0
    for rec in corpus:
        key = rec["id"]
        if key in done: continue
        src, tgt = rec["lang"], tgt_lang(rec)
        tname = "English" if tgt == "en" else "Chinese"
        sname = "Chinese" if src == "zh" else "English"
        prompt = f"Translate the following {sname} sentence into {tname}. Output only the translation, nothing else.\n{rec['text']}"
        try:
            r = gen_text("qwen3.8-max", prompt, temperature=0.2, max_tokens=400)
            append_jsonl(LOG, {"key": key, "ok": True, "text": r["text"].strip(), "src": rec["text"], "lang": src})
            ok += 1
        except Exception as e:
            append_jsonl(LOG, {"key": key, "ok": False, "err": str(e)[:150]}); fail += 1
        time.sleep(0.4)
        if (ok+fail) % 100 == 0: print(f"refmax {ok+fail}/480", flush=True)
    print(f"refmax DONE ok={ok} fail={fail}")

def load_asr_outputs():
    """{model: {cond/sid: text}}"""
    out = {}
    for mk in ["q31", "para16k"]:
        d = {}
        for line in open(f"{RES}/asr_{mk}.jsonl"):
            j = json.loads(line)
            if j.get("ok"): d[j["key"]] = j["text"]
            elif "HAVE_NO_WORDS" in str(j.get("err","")): d[j["key"]] = ""
        out[mk] = d
    return out

def run_cascade():
    LOG = f"{RES}/mt_cascade.jsonl"; done = load_done(LOG)
    asr = load_asr_outputs()
    ok = fail = skip = 0
    for mk in ["q31", "para16k"]:
        for rec in corpus:
            if rec["id"] not in sweep_ids: continue
            for cond in ALL_CONDS:
                key = f"{mk}/{cond}/{rec['id']}"
                if key in done: continue
                asr_key = f"{cond}/{rec['id']}"
                asr_text = asr[mk].get(asr_key)
                if asr_text is None: skip += 1; continue
                if not asr_text.strip():
                    append_jsonl(LOG, {"key": key, "ok": True, "text": "", "empty_asr": True, "lang": rec["lang"]}); continue
                try:
                    r = mt_uni(asr_text, src_lang(rec), tgt_lang(rec))
                    append_jsonl(LOG, {"key": key, "ok": True, "text": r["text"], "asr_text": asr_text, "lang": rec["lang"]})
                    ok += 1
                except Exception as e:
                    append_jsonl(LOG, {"key": key, "ok": False, "err": str(e)[:150]}); fail += 1
                time.sleep(0.25)
                if (ok+fail) % 200 == 0: print(f"cascade {ok+fail} (skip={skip})", flush=True)
    print(f"cascade DONE ok={ok} fail={fail} skip={skip}")

def run_e2e_omni():
    LOG = f"{RES}/mt_e2e_omni.jsonl"; done = load_done(LOG)
    ok = fail = 0
    for rec in corpus:
        if rec["id"] not in sweep_ids: continue
        for cond in ALL_CONDS:
            key = f"{cond}/{rec['id']}"
            if key in done: continue
            wav = f"{BASE}/perturbed/{cond}/{rec['id']}.wav"
            if not os.path.exists(wav): continue
            t0 = time.time()
            try:
                r = omni_audio(wav, E2E_PROMPT[rec["lang"]])
                append_jsonl(LOG, {"key": key, "ok": True, "text": r["text"], "latency_s": round(time.time()-t0,3), "lang": rec["lang"]})
                ok += 1
            except Exception as e:
                append_jsonl(LOG, {"key": key, "ok": False, "err": str(e)[:150]}); fail += 1
            time.sleep(0.3)
            if (ok+fail) % 100 == 0: print(f"e2e_omni {ok+fail}", flush=True)
    print(f"e2e_omni DONE ok={ok} fail={fail}")

def run_e2e_lt():
    LOG = f"{RES}/mt_e2e_lt.jsonl"; done = load_done(LOG)
    ok = fail = 0
    # 条件优先: 主网格9条件全覆盖后, 再补SNR扫描
    for cond in MAIN_CONDS + SWEEP_CONDS:
        for rec in corpus:
            if rec["id"] not in sweep_ids: continue
            key = f"{cond}/{rec['id']}"
            if key in done: continue
            wav = f"{BASE}/perturbed/{cond}/{rec['id']}.wav"
            if not os.path.exists(wav): continue
            try:
                r = livetranslate(wav, tgt_lang(rec))
                append_jsonl(LOG, {"key": key, "ok": True, "text": r["translation"], "source_asr": r["source"], "latency_s": r["latency_s"], "lang": rec["lang"]})
                ok += 1
            except Exception as e:
                append_jsonl(LOG, {"key": key, "ok": False, "err": str(e)[:150]}); fail += 1
                if "AllocationQuota" in str(e): print("LT QUOTA EXHAUSTED"); break
            time.sleep(0.3)
            if (ok+fail) % 100 == 0: print(f"e2e_lt {ok+fail}", flush=True)
    print(f"e2e_lt DONE ok={ok} fail={fail}")

if PHASE == "oracle": run_oracle()
elif PHASE == "refmax": run_refmax()
elif PHASE == "cascade": run_cascade()
elif PHASE == "e2e_omni": run_e2e_omni()
elif PHASE == "e2e_lt": run_e2e_lt()
else: raise ValueError(PHASE)
