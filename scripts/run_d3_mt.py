# -*- coding: utf-8 -*-
"""D3 翻译实验运行器
用法: python3 run_d3_mt.py <phase> [shard nshard]
phase: cascade - qwen-mt-uni 翻译 q31 ASR 输出 (级联路径) 900
       oracle  - qwen-mt-uni 翻译真实转写文本 (oracle上界) 150
       e2e_lt  - livetranslate 音频直译 (clean_r/revr/rb0 全部150句 = 450)
       lt_probe- LT 配额探测 (6 调用)
"""
import json, os, sys, time, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apis import mt_uni, livetranslate, load_done, append_jsonl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "audio", "d3")
RES = os.path.join(ROOT, "results")
CORPUS = [json.loads(l) for l in open(os.path.join(ROOT, "corpus", "d3_corpus.jsonl"))]
CONDS = ["clean_r", "revr", "rb5", "rb0", "rbm5", "rn0"]
LT_CONDS = ["clean_r", "revr", "rb0"]

PHASE = sys.argv[1]
SHARD, NSHARD = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 1)

def tgt_lang(rec): return "en" if rec["lang"] == "zh" else "zh"

def sent_case(t):
    return t.lower().capitalize() if t else t

def sharded(key):
    return (zlib.crc32(key.encode()) & 0xffffffff) % NSHARD == SHARD

def run_cascade():
    """依赖 d3_asr_q31.jsonl"""
    LOG = f"{RES}/d3_mt_cascade.jsonl"; done = load_done(LOG)
    asr = {}
    for line in open(f"{RES}/d3_asr_q31.jsonl"):
        j = json.loads(line)
        if j.get("ok"): asr[j["key"]] = j["text"]
    recmap = {r["id"]: r for r in CORPUS}
    ok = fail = 0
    jobs = []
    for cond in CONDS:
        for rec in CORPUS:
            key = f"{cond}/{rec['id']}"
            if key in done or key not in asr: continue
            jobs.append((key, rec, asr[key]))
    print(f"cascade 待跑: {len(jobs)} (q31已就绪 {len(asr)})", flush=True)
    for key, rec, hyp in jobs:
        if not sharded(key): continue
        src = "zh" if rec["lang"] == "zh" else "en"
        text = hyp if rec["lang"] == "zh" else hyp  # ASR 假设原样入MT
        if not text.strip():
            # ASR 拒答/空输出 → 级联断裂, 译文为空 (有效数据点)
            append_jsonl(LOG, {"key": key, "ok": True, "text": "", "src": "",
                               "lang": rec["lang"], "cascade_broken": True})
            ok += 1
            continue
        try:
            r = mt_uni(text, src, tgt_lang(rec))
            append_jsonl(LOG, {"key": key, "ok": True, "text": r["text"], "src": text,
                               "lang": rec["lang"], "usage": r.get("usage", {})})
            ok += 1
        except Exception as e:
            append_jsonl(LOG, {"key": key, "ok": False, "err": str(e)[:150], "lang": rec["lang"]})
            fail += 1
        time.sleep(0.2)
        if (ok + fail) % 50 == 0: print(f"cascade {ok+fail}/{len(jobs)}", flush=True)
    print(f"cascade DONE ok={ok} fail={fail}")

def run_oracle():
    LOG = f"{RES}/d3_mt_oracle.jsonl"; done = load_done(LOG)
    ok = fail = 0
    for rec in CORPUS:
        key = rec["id"]
        if key in done: continue
        src_text = rec["text"] if rec["lang"] == "zh" else sent_case(rec["text"])
        try:
            r = mt_uni(src_text, rec["lang"], tgt_lang(rec))
            append_jsonl(LOG, {"key": key, "ok": True, "text": r["text"], "src": src_text,
                               "lang": rec["lang"], "usage": r.get("usage", {})})
            ok += 1
        except Exception as e:
            append_jsonl(LOG, {"key": key, "ok": False, "err": str(e)[:150]}); fail += 1
        time.sleep(0.2)
    print(f"oracle DONE ok={ok} fail={fail}")

def run_e2e_lt():
    LOG = f"{RES}/d3_mt_e2e_lt.jsonl"; done = load_done(LOG)
    ok = fail = 0
    jobs = []
    for cond in LT_CONDS:
        for rec in CORPUS:
            key = f"{cond}/{rec['id']}"
            if key in done: continue
            jobs.append((key, rec))
    print(f"e2e_lt 待跑: {len(jobs)}", flush=True)
    for key, rec in jobs:
        if not sharded(key): continue
        wav = f"{BASE}/{key.split('/')[0]}/{rec['id']}.wav"
        try:
            r = livetranslate(wav, tgt_lang(rec))
            append_jsonl(LOG, {"key": key, "ok": True, "text": r["translation"],
                               "source_asr": r["source"], "latency_s": r["latency_s"], "lang": rec["lang"]})
            ok += 1
        except Exception as e:
            append_jsonl(LOG, {"key": key, "ok": False, "err": str(e)[:150], "lang": rec["lang"]})
            fail += 1
            # LT 配额/连接错误率高时提前止损
            if fail >= 25 and ok == 0:
                print("e2e_lt 全失败, 中止"); break
        time.sleep(0.4)
        if (ok + fail) % 25 == 0: print(f"e2e_lt {ok+fail}/{len(jobs)} ok={ok}", flush=True)
    print(f"e2e_lt DONE ok={ok} fail={fail}")

def run_lt_probe():
    rec = CORPUS[0]
    for cond in CONDS:
        wav = f"{BASE}/{cond}/{rec['id']}.wav"
        try:
            r = livetranslate(wav, tgt_lang(rec))
            print(f"  {cond}: OK latency={r['latency_s']} src={r['source'][:40]}")
        except Exception as e:
            print(f"  {cond}: FAIL {str(e)[:120]}")
        time.sleep(1)

if __name__ == "__main__":
    {"cascade": run_cascade, "oracle": run_oracle, "e2e_lt": run_e2e_lt,
     "lt_probe": run_lt_probe}[PHASE]()
