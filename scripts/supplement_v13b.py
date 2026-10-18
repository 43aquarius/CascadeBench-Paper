#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.3 快速补充: (a) Table5 条件口径 CI; (b) 数字归一化 BLEU 敏感性; (c) 合成观测分段斜率"""
import os, sys, json
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from metrics import normalize_zh, normalize_en
from sacrebleu.metrics import BLEU

CORPUS = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(ROOT, "corpus", "corpus.jsonl"))}
_bleu_en = BLEU(tokenize="13a"); _bleu_zh = BLEU(tokenize="zh")

def load_jsonl(path):
    out = []
    if not os.path.exists(path): return out
    for line in open(path, encoding="utf-8"):
        try: out.append(json.loads(line))
        except Exception: pass
    return out

refmax = {j["key"]: j["text"] for j in load_jsonl(f"{RES}/mt_refmax.jsonl") if j.get("ok")}

def cascade_pairs(mk, cond, conditional=False):
    if mk == "q3":
        recs = load_jsonl(f"{RES}/ext_mt_cascade_q3main.jsonl")
    elif cond in ("n25","nm5","nm10"):
        recs = load_jsonl(f"{RES}/ext_mt_cascade.jsonl")
    else:
        recs = load_jsonl(f"{RES}/mt_cascade.jsonl")
    pairs = {}
    for j in recs:
        if not j.get("ok"): continue
        cm, ccond, sid = j["key"].split("/", 2)
        if cm != mk or ccond != cond: continue
        if j.get("empty_asr"):
            if not conditional: pairs[sid] = ""
            continue
        pairs[sid] = j["text"]
    return [(s, pairs[s]) for s in sorted(pairs)]

def numnorm(text, lang):
    return normalize_zh(text) if lang == "zh" else normalize_en(text)

def corpus_bleu_bidir(pairs, refmap, norm_fn=None):
    h = {"zh": [], "en": []}; r = {"zh": [], "en": []}
    for sid, hyp in pairs:
        rec = CORPUS.get(sid); ref = refmap.get(sid)
        if rec is None or ref is None: continue
        hv = norm_fn(hyp) if norm_fn else hyp
        rv = norm_fn(ref) if norm_fn else ref
        h[rec["lang"]].append(hv); r[rec["lang"]].append(rv)
    bs = {}
    for lang, hyps in h.items():
        if not hyps: continue
        b = _bleu_en if lang == "zh" else _bleu_zh
        bs[lang] = round(b.corpus_score(hyps, [r[lang]]).score, 2)
    return {"bleu": round(float(np.mean(list(bs.values()))), 2) if bs else None,
            "by_dir": bs, "n": sum(len(v) for v in h.values())}

def boot_ci(pairs, refmap, n_boot=300, seed=11, norm_fn=None):
    rng = np.random.RandomState(seed)
    vals = []
    for _ in range(n_boot):
        samp = [pairs[i] for i in rng.choice(len(pairs), len(pairs), replace=True)]
        v = corpus_bleu_bidir(samp, refmap, norm_fn)["bleu"]
        if v is not None: vals.append(v)
    vals.sort()
    return [round(vals[int(0.025*len(vals))],1), round(vals[int(0.975*len(vals))],1)] if len(vals)>50 else None

out = {}
# (a) 条件口径 n0 CI (para16k + q31)
print("(a) conditional-protocol n0")
for mk in ["q31", "para16k"]:
    p = cascade_pairs(mk, "n0", conditional=True)
    v = corpus_bleu_bidir(p, refmax)
    ci = boot_ci(p, refmax)
    out[f"cond_n0_{mk}"] = {"bleu": v["bleu"], "ci95": ci, "n": v["n"]}
    print(f"  {mk}: bleu={v['bleu']} ci={ci} n={v['n']}")

# (b) 数字归一化 BLEU (真实语音 clean: 解释 69 vs 100)
print("(b) numeral-normalised BLEU on real speech")
D3_CORPUS = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(ROOT, "corpus", "d3_corpus.jsonl"))}
d3_oracle = {j["key"]: j["text"] for j in load_jsonl(f"{RES}/d3_mt_oracle.jsonl") if j.get("ok")}
def d3_bleu(pairs, refmap, norm_fn=None):
    h = {"zh": [], "en": []}; r = {"zh": [], "en": []}
    for sid, hyp in pairs:
        rec = D3_CORPUS.get(sid); ref = refmap.get(sid)
        if rec is None or ref is None: continue
        hv = norm_fn(hyp, rec["lang"]) if norm_fn else hyp
        rv = norm_fn(ref, rec["lang"]) if norm_fn else ref
        h[rec["lang"]].append(hv); r[rec["lang"]].append(rv)
    bs = {}
    for lang, hyps in h.items():
        if not hyps: continue
        b = _bleu_en if lang == "zh" else _bleu_zh
        bs[lang] = round(b.corpus_score(hyps, [r[lang]]).score, 2)
    return round(float(np.mean(list(bs.values()))), 2) if bs else None

def d3_pairs_cascade(cond):
    pairs = {}
    for j in load_jsonl(f"{RES}/d3_mt_cascade.jsonl"):
        if not j.get("ok"): continue
        ccond, sid = j["key"].split("/", 1)
        if ccond == cond: pairs[sid] = j["text"]
    return [(s, pairs[s]) for s in sorted(pairs)]

def d3_pairs_lt(cond):
    pairs = {}
    for j in load_jsonl(f"{RES}/d3_mt_e2e_lt.jsonl"):
        if not j.get("ok"): continue
        ccond, sid = j["key"].split("/", 1)
        if ccond == cond: pairs[sid] = j["text"]
    return [(s, pairs[s]) for s in sorted(pairs)]

for cond in ["clean_r"]:
    pc = d3_pairs_cascade(cond)
    raw = d3_bleu(pc, d3_oracle)
    nn = d3_bleu(pc, d3_oracle, numnorm)
    pl = d3_pairs_lt(cond)
    raw_l = d3_bleu(pl, d3_oracle); nn_l = d3_bleu(pl, d3_oracle, numnorm)
    out[f"numnorm_{cond}"] = {"cascade_raw": raw, "cascade_numnorm": nn,
                              "lt_raw": raw_l, "lt_numnorm": nn_l}
    print(f"  cascade: raw={raw} numnorm={nn} | lt: raw={raw_l} numnorm={nn_l}")

# 逐句差距来源: cascade clean 输入 (ASR) 与人工转写的字差
import collections
d3_asr = {}
for j in load_jsonl(f"{RES}/d3_asr_q31.jsonl"):
    if j.get("ok"):
        cond, sid = j["key"].split("/", 1)
        if cond == "clean_r": d3_asr[sid] = j.get("text","") or ""
diffs = collections.Counter()
for sid, rec in D3_CORPUS.items():
    if sid not in d3_asr: continue
    a = normalize_zh(d3_asr[sid]) if rec["lang"]=="zh" else normalize_en(d3_asr[sid])
    b = normalize_zh(rec["text"]) if rec["lang"]=="zh" else normalize_en(rec["text"])
    if a != b: diffs["changed"] += 1
    else: diffs["identical"] += 1
print(f"  q31 clean ASR vs human transcript: {dict(diffs)}")
out["asr_vs_human_clean"] = dict(diffs)

# (c) 合成观测分段斜率 (从 snr_curves_v2)
ext = json.load(open(f"{RES}/analysis_ext.json"))
seg = {}
for model in ["para16k","para8k","q31","q3"]:
    for lang in ["zh","en"]:
        try:
            pts = ext["snr_curves_v2"][model][lang]
        except Exception: continue
        if not pts: continue
        row = {}
        for i in range(len(pts)-1):
            hi, lo = pts[i], pts[i+1]
            db = hi["snr"] - lo["snr"]
            row[f"{hi['snr']}to{lo['snr']}"] = round((lo["mean"]-hi["mean"])/db, 1)
        seg[f"{model}_{lang}"] = row
out["synthetic_segment_slopes"] = seg
print("(c) synthetic observed segment slopes (pp/dB):")
for k, v in seg.items(): print(f"  {k}: {v}")

with open(f"{RES}/supplement_v13b.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("saved supplement_v13b.json")
