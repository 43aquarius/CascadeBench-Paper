#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CascadeBench v1.4 综合分析: 升级项 a/b/c/d/e 的全部数字
a. Whisper (非阿里ASR) vs 4阿里系统 (真实语音4条件)
b. GLM 第三参考 (合成480三参考 / 真实150双参考) 下的级联BLEU与相对损失
c. rev_mit (MIT实测RIR) vs rev (合成极端DRR): 6系统CER/WER + 级联BLEU
d. 6点真实babble阶梯膝点校验
e. GLM MT vs Gummy MT (q31前端, 真实语音): clean→0dB相对损失 + 4条件曲线
输出: research/results/analysis_v14.json"""
import os, sys, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metrics import err_rate, cer, wer, normalize_zh, normalize_en
from sacrebleu.metrics import BLEU

RES = os.path.join(ROOT, "results")
CORP_SYNTH = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(ROOT, "corpus", "corpus.jsonl"))}
CORP_REAL = {r["id"]: r for r in (json.loads(l) for l in open(os.path.join(ROOT, "corpus", "d3_corpus.jsonl")))}
OUT = {}

_bleu_en = BLEU(tokenize="13a")
_bleu_zh = BLEU(tokenize="zh")

def load_jsonl_map(path, keyfield="key"):
    out = {}
    if not os.path.exists(path): return out
    for line in open(path):
        try:
            j = json.loads(line)
            if j.get("ok"): out[j[keyfield]] = j
        except Exception: pass
    return out

def bleu_bidir_score(pairs, ref_of, keep_empty=False):
    """pairs: list of (hyp, rec); 按语言分别 corpus BLEU, 返回 macro"""
    per_lang = {"zh": [], "en": []}
    for hyp, rec in pairs:
        r = ref_of(rec)
        if r is None: continue
        if not keep_empty and not (hyp or "").strip(): continue
        per_lang[rec["lang"]].append((hyp or "", r))
    scores = []
    detail = {}
    for lang, ps in per_lang.items():
        if not ps: continue
        bl = _bleu_en if lang == "zh" else _bleu_zh  # 目标语言: zh句→en译文
        s = bl.corpus_score([h for h, _ in ps], [[r for _, r in ps]]).score
        detail[lang] = round(s, 2)
        scores.append(s)
    return {"bleu": round(float(np.mean(scores)), 2) if scores else None, "detail": detail, "n": sum(len(v) for v in per_lang.values())}

def boot_ci_mean(vals, n=1000, seed=7):
    rng = np.random.RandomState(seed)
    vals = np.asarray(vals, dtype=float)
    if len(vals) == 0: return (None, None)
    bs = [np.mean(rng.choice(vals, len(vals))) for _ in range(n)]
    return (round(float(np.percentile(bs, 2.5)), 1), round(float(np.percentile(bs, 97.5)), 1))

# ============ 数据加载 ============
# ASR (真实)
asr_real = {mk: load_jsonl_map(f"{RES}/d3_asr_{mk}.jsonl") for mk in ["q31", "q3", "para16k", "para8k"]}
asr_whisper = load_jsonl_map(f"{RES}/d3_asr_whisper.jsonl")
# ASR (合成 rev_mit)
asr_revmit = {mk: load_jsonl_map(f"{RES}/revmit_asr_{mk}.jsonl") for mk in ["q31", "q3", "p16", "p8"]}
# MT (真实)
mt_real_gummy = load_jsonl_map(f"{RES}/d3_mt_cascade.jsonl")     # q31前端, key=cond/id
mt_oracle_real = load_jsonl_map(f"{RES}/d3_mt_oracle.jsonl", "key")  # key=id
# MT (合成)
mt_synth = {mk: load_jsonl_map(f"{RES}/revmit_mt_cascade.jsonl") for mk in []}
revmit_mt = {}
for line in open(f"{RES}/revmit_mt_cascade.jsonl"):
    j = json.loads(line)
    if j.get("ok"): revmit_mt[j["key"]] = j  # key = mk/rev_mit/id
# 合成主网格已有结果 (rev 条件) 从 analysis_ext.json 读
AX = json.load(open(f"{RES}/analysis_ext.json"))
# GLM
glm = {}
for line in open(f"{RES}/glm_tasks.jsonl"):
    j = json.loads(line)
    if j.get("ok"):
        kind, rest = j["key"].split("/", 1)
        glm.setdefault(kind, {})[rest] = j
# 参考 (合成)
ref_synth_primary = load_jsonl_map(f"{RES}/mt_refmax.jsonl", "key")  # Qwen3.8-Max
ref_synth_oracle = load_jsonl_map(f"{RES}/mt_oracle.jsonl", "key")   # Gummy

REFSYS = {"q31": "Qwen-Audio", "q3": "Qwen3-ASR", "para16k": "Paraformer-16k", "para8k": "Paraformer-8k", "whisper": "Whisper-small"}

# ============ A. Whisper vs 阿里系统 (真实语音 4 条件) ============
print("=== A. Whisper vs Ali systems (real speech) ===", flush=True)
CONDS_A = ["clean_r", "rb5", "rb0", "rbm5"]
whis_tbl = {}
for mk, data in [("whisper", asr_whisper), ("q31", asr_real["q31"]), ("q3", asr_real["q3"]),
                 ("para16k", asr_real["para16k"]), ("para8k", asr_real["para8k"])]:
    whis_tbl[mk] = {}
    for cond in CONDS_A:
        per = {"zh": [], "en": []}
        empty = {"zh": 0, "en": 0}
        for sid, rec in CORP_REAL.items():
            if mk == "para8k" and rec["lang"] != "zh": continue
            j = data.get(f"{cond}/{sid}")
            if j is None: continue
            hyp = (j.get("text") or "").strip()
            if not hyp:
                per[rec["lang"]].append(1.0); empty[rec["lang"]] += 1
            else:
                per[rec["lang"]].append(err_rate(rec["text"], hyp, rec["lang"]))
        e = {}
        for lang, vals in per.items():
            if not vals: continue
            e[lang] = {"err": round(float(np.mean(vals)) * 100, 1),
                       "ci": boot_ci_mean([v * 100 for v in vals]),
                       "n": len(vals), "empty": empty[lang]}
        whis_tbl[mk][cond] = e
OUT["whisper_vs_ali"] = whis_tbl
for mk in whis_tbl:
    r = whis_tbl[mk]
    print(f"  {mk}: clean zh {r['clean_r'].get('zh',{}).get('err')} en {r['clean_r'].get('en',{}).get('err')} | rb0 zh {r['rb0'].get('zh',{}).get('err')} en {r['rb0'].get('en',{}).get('err')}")

# ============ B. GLM 第三参考 ============
print("=== B. GLM third reference ===", flush=True)
# B1. 合成主网格: 三参考下 clean + n0 的级联 BLEU (q31/q3/p16k 用已有 mt_cascade)
mt_synth_cascade = {}  # mk -> {cond/id: text}
for fname in ["mt_cascade.jsonl", "ext_mt_cascade.jsonl", "ext_mt_cascade_q3main.jsonl"]:
    for line in open(f"{RES}/{fname}"):
        j = json.loads(line)
        if not j.get("ok"): continue
        mk, rest = j["key"].split("/", 1)  # mk/cond/id
        mt_synth_cascade.setdefault(mk, {})[rest] = j.get("text", "")

def synth_refs(rec):
    sid = rec["id"]
    return {
        "primary": (ref_synth_primary.get(sid) or {}).get("text"),
        "oracle": (ref_synth_oracle.get(sid) or {}).get("text"),
        "glm": (glm.get("refsynth", {}).get(sid) or {}).get("text"),
    }

three_ref_synth = {}
for mk in ["q31", "q3", "para16k"]:
    three_ref_synth[mk] = {}
    d = mt_synth_cascade.get(mk, {})
    if not d:
        # 主网格 cascade MT 可能在单文件带 asr 字段
        continue
    for cond in ["clean", "n0"]:
        for refname in ["primary", "oracle", "glm"]:
            pairs = [(d.get(f"{cond}/{sid}", ""), rec) for sid, rec in CORP_SYNTH.items()
                     if f"{cond}/{sid}" in d or True]
            pairs = [(h, r) for h, r in pairs if f"{cond}/{r['id']}" in d]
            def ref_of(rec, rn=refname):
                return synth_refs(rec)[rn]
            sc = bleu_bidir_score(pairs, ref_of, keep_empty=True)
            three_ref_synth[mk][f"{cond}_{refname}"] = sc
OUT["three_ref_synth"] = three_ref_synth
for mk, v in three_ref_synth.items():
    print(f"  synth {mk}: clean P/O/G = {v.get('clean_primary',{}).get('bleu')}/{v.get('clean_oracle',{}).get('bleu')}/{v.get('clean_glm',{}).get('bleu')}"
          f" | n0 P/O/G = {v.get('n0_primary',{}).get('bleu')}/{v.get('n0_oracle',{}).get('bleu')}/{v.get('n0_glm',{}).get('bleu')}")

# B2. 真实语音: 双参考 (oracle Gummy / glm) 下 q31 级联 clean_r + rb0
real_refs = {}
for sid, rec in CORP_REAL.items():
    real_refs[sid] = {
        "oracle": (mt_oracle_real.get(sid) or {}).get("text"),
        "glm": (glm.get("refreal", {}).get(sid) or {}).get("text"),
    }
two_ref_real = {}
for refname in ["oracle", "glm"]:
    for cond in ["clean_r", "rb5", "rb0", "rbm5"]:
        pairs = []
        for sid, rec in CORP_REAL.items():
            j = mt_real_gummy.get(f"{cond}/{sid}")
            if j is None: continue
            pairs.append(((j.get("text") or ""), rec))
        def ref_of(rec, rn=refname):
            return real_refs[rec["id"]][rn]
        sc = bleu_bidir_score(pairs, ref_of, keep_empty=True)
        two_ref_real[f"{cond}_{refname}"] = sc
OUT["two_ref_real_q31cascade"] = two_ref_real
for k in ["clean_r_oracle", "clean_r_glm", "rb0_oracle", "rb0_glm"]:
    print(f"  real q31-cascade {k}: {two_ref_real.get(k,{}).get('bleu')} (n={two_ref_real.get(k,{}).get('n')})")

# ============ C. rev_mit vs rev (合成) ============
print("=== C. rev_mit vs rev ===", flush=True)
rev_cmp = {"asr": {}, "cascade": {}}
for mk in ["q31", "q3", "p16", "p8"]:
    key_map = {"q31": "q31", "q3": "q3", "p16": "para16k", "p8": "para8k"}
    ali_key = key_map[mk]
    # rev (合成, 已有日志)
    d_rev = load_jsonl_map(f"{RES}/asr_{ali_key}.jsonl")
    per = {"zh": [], "en": []}
    for sid, rec in CORP_SYNTH.items():
        if mk == "p8" and rec["lang"] != "zh": continue
        j = d_rev.get(f"rev/{sid}")
        if j is None: continue
        hyp = (j.get("text") or "").strip()
        per[rec["lang"]].append(1.0 if not hyp else err_rate(rec["text"], hyp, rec["lang"]))
    # rev_mit
    per2 = {"zh": [], "en": []}
    for sid, rec in CORP_SYNTH.items():
        if mk == "p8" and rec["lang"] != "zh": continue
        j = asr_revmit[mk].get(f"rev_mit/{sid}")
        if j is None: continue
        hyp = (j.get("text") or "").strip()
        per2[rec["lang"]].append(1.0 if not hyp else err_rate(rec["text"], hyp, rec["lang"]))
    e1 = {l: round(float(np.mean(v)) * 100, 1) for l, v in per.items() if v}
    e2 = {l: round(float(np.mean(v)) * 100, 1) for l, v in per2.items() if v}
    rev_cmp["asr"][mk] = {"rev": e1, "rev_mit": e2}
    print(f"  {mk}: rev {e1} -> rev_mit {e2}")
# 级联 BLEU: rev_mit (Gummy MT) vs rev (analysis_ext) — 三参考
for mk in ["q31", "q3", "p16"]:
    d_mit = {}
    for k, j in revmit_mt.items():
        parts = k.split("/", 1)  # mk/rev_mit/id
        if parts[0] != mk: continue
        d_mit[parts[1]] = j.get("text", "")
    ent = {}
    for refname in ["primary", "oracle", "glm"]:
        pairs = [(d_mit.get(f"rev_mit/{sid}", ""), rec) for sid, rec in CORP_SYNTH.items()]
        def ref_of(rec, rn=refname):
            return synth_refs(rec)[rn]
        sc = bleu_bidir_score(pairs, ref_of, keep_empty=True)
        ent[refname] = sc["bleu"]
    # 合成 rev 的对应值从 analysis_ext 读
    ext = AX["translation_ext"]["cascade"].get({"q31": "q31", "q3": "q3", "p16": "para16k"}[mk], {}).get("rev", {}).get("cond", {})
    rev_cmp["cascade"][mk] = {"rev_mit": ent, "rev_primary_bleu": ext.get("bleu"), "rev_oracle_bleu": ext.get("bleu_vs_oracle")}
    print(f"  cascade {mk}: rev_mit P/O/G = {ent} | old rev P={ext.get('bleu')} O={ext.get('bleu_vs_oracle')}")
OUT["rev_mit_vs_rev"] = rev_cmp

# ============ D. 6点 babble 阶梯膝点校验 ============
print("=== D. 6-level babble ladder ===", flush=True)
LADDER = [("rb10", 10), ("rb5", 5), ("rb25", 2.5), ("rb0", 0), ("rbm25", -2.5), ("rbm5", -5)]
ladder = {}
for mk, data in [("q31", asr_real["q31"]), ("q3", asr_real["q3"]), ("para16k", asr_real["para16k"]), ("para8k", asr_real["para8k"]), ("whisper", asr_whisper)]:
    ladder[mk] = {}
    for lang in ["zh", "en"]:
        if mk == "para8k" and lang != "zh": continue
        pts = []
        for cond, snr in LADDER:
            vals = []
            for sid, rec in CORP_REAL.items():
                if rec["lang"] != lang: continue
                if mk == "whisper" and cond not in CONDS_A: continue
                j = data.get(f"{cond}/{sid}")
                if j is None: continue
                hyp = (j.get("text") or "").strip()
                vals.append(1.0 if not hyp else err_rate(rec["text"], hyp, rec["lang"]))
            if vals:
                pts.append({"snr": snr, "err": round(float(np.mean(vals)) * 100, 1)})
        # 10% 交叉点 (线性插值, 从高SNR到低SNR)
        cross = None
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            if a["err"] <= 10 < b["err"]:
                t = (10 - a["err"]) / (b["err"] - a["err"] + 1e-9)
                cross = round(a["snr"] + t * (b["snr"] - a["snr"]), 1)
                break
        if pts and pts[0]["err"] > 10: cross = "above-highest"
        ladder[mk][lang] = {"points": pts, "cross10": cross}
        print(f"  {mk} {lang}: cross10={cross} pts={[(p['snr'],p['err']) for p in pts]}")
OUT["babble_ladder6"] = ladder

# ============ E. GLM MT vs Gummy MT (q31 前端, 真实) ============
print("=== E. GLM MT backend vs Gummy (q31 frontend, real) ===", flush=True)
mt_cmp = {}
for backend, getter in [("gummy", lambda cond, sid: (mt_real_gummy.get(f"{cond}/{sid}") or {}).get("text", "")),
                        ("glm", lambda cond, sid: (glm.get("mtreal", {}).get(f"{cond}/{sid}") or {}).get("text", None))]:
    mt_cmp[backend] = {}
    for refname in ["oracle", "glm"]:
        for cond in CONDS_A:
            pairs = []
            for sid, rec in CORP_REAL.items():
                t = getter(cond, sid)
                if t is None: continue
                pairs.append((t, rec))
            def ref_of(rec, rn=refname):
                return real_refs[rec["id"]][rn]
            sc = bleu_bidir_score(pairs, ref_of, keep_empty=True)
            mt_cmp[backend][f"{cond}_{refname}"] = sc
OUT["mt_backend_cmp_real"] = mt_cmp
for b in ["gummy", "glm"]:
    v = mt_cmp[b]
    print(f"  {b}: clean_r O/G = {v.get('clean_r_oracle',{}).get('bleu')}/{v.get('clean_r_glm',{}).get('bleu')}"
          f" | rb0 O/G = {v.get('rb0_oracle',{}).get('bleu')}/{v.get('rb0_glm',{}).get('bleu')}")

json.dump(OUT, open(f"{RES}/analysis_v14.json", "w"), ensure_ascii=False, indent=1)
print("\nsaved analysis_v14.json")
