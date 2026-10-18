#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CascadeBench v1.3 补充重算：审稿意见 R1-R12 相关的全部新数字。
输出: /home/z/my-project/work_v13/run_root/results/supplement_v13.json + 控制台摘要
模块:
  S1  Table 5 bootstrap CI + omni 共同子集 (R9)
  S2  风格归一化 BLEU 敏感性: 合成 + 真实 (R1)
  S3  幻觉区插入/删除/替换拆分: 合成 nm5/nm10 + 真实 rbm5 (R2)
  S4  真实 babble 分段观测斜率 (R2/R5)
  S5  真实 E2E vs 级联: within-system 相对损失 + 逐句配对差 (R1)
  S6  CAC 条件层 bootstrap CI (R4)
  S7  logistic 膝点位置 s0 (R5)
  S8  q31 vs q3 级联 12 共享条件最大差 (R8)
  S9  ESTOI 全条件 (R6)
"""
import os, sys, json, random
import numpy as np
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from metrics import err_rate, normalize_zh, normalize_en, bleu, chrf_score
from sacrebleu.metrics import BLEU, CHRF

CORPUS = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(ROOT, "corpus", "corpus.jsonl"))}
SWEEP = set(json.load(open(os.path.join(ROOT, "corpus", "sweep_ids.json"))))
D3_CORPUS = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(ROOT, "corpus", "d3_corpus.jsonl"))}
SNR_OF = {"n20":20,"n15":15,"n10":10,"n5":5,"n25":2.5,"n0":0,"nm5":-5,"nm10":-10}
MAIN_CONDS = ["clean","n10","n0","rev","nb","opus","pl","clip","tempo"]

_bleu_en = BLEU(tokenize="13a"); _bleu_zh = BLEU(tokenize="zh")
_chrf = CHRF()

def load_jsonl(path):
    out = []
    if not os.path.exists(path): return out
    for line in open(path, encoding="utf-8"):
        try: out.append(json.loads(line))
        except Exception: pass
    return out

def load_asr_all(model):
    d = {}
    for f in [f"{RES}/asr_{model}.jsonl", f"{RES}/ext_asr_{model}.jsonl"]:
        for j in load_jsonl(f):
            cond, sid = j["key"].split("/", 1)
            if j.get("ok"): d[(cond, sid)] = j
            elif "NO_WORDS" in str(j.get("err","")):
                d[(cond, sid)] = {"key": j["key"], "ok": True, "text": "", "no_words": True, "lang": j.get("lang")}
    return d

ASR = {m: load_asr_all(m) for m in ["para16k","para8k","q31","q3","omni"]}
out = {}

# ============================================================
# 通用: 双语 corpus BLEU (自实现, 不依赖合成 corpus), 支持归一化钩子
# ============================================================
def corpus_bleu_bidir(pairs, refmap, corpus, norm_fn=None):
    """pairs: [(sid, hyp)] ; corpus: {sid: rec with lang}; 返回宏平均 BLEU 与分向"""
    h = {"zh": [], "en": []}; r = {"zh": [], "en": []}
    for sid, hyp in pairs:
        rec = corpus.get(sid); ref = refmap.get(sid)
        if rec is None or ref is None: continue
        hv = norm_fn(hyp) if norm_fn else hyp
        rv = norm_fn(ref) if norm_fn else ref
        if hv is None or rv is None: continue
        h[rec["lang"]].append(hv); r[rec["lang"]].append(rv)
    bs = {}
    for lang, hyps in h.items():
        if not hyps: continue
        b = _bleu_en if lang == "zh" else _bleu_zh   # zh源->en译 用13a; en源->zh译 用zh
        bs[lang] = round(b.corpus_score(hyps, [r[lang]]).score, 2)
    macro = round(float(np.mean(list(bs.values()))), 2) if bs else None
    return {"bleu": macro, "by_dir": bs, "n": sum(len(v) for v in h.values())}

def bootstrap_bleu_ci(pairs, refmap, corpus, n_boot=500, seed=42, norm_fn=None):
    rng = np.random.RandomState(seed)
    idx = list(range(len(pairs)))
    vals = []
    for _ in range(n_boot):
        samp = [pairs[i] for i in rng.choice(idx, len(idx), replace=True)]
        v = corpus_bleu_bidir(samp, refmap, corpus, norm_fn)["bleu"]
        if v is not None: vals.append(v)
    vals.sort()
    if len(vals) < 50: return None
    return [round(vals[int(0.025*len(vals))],1), round(vals[int(0.975*len(vals))],1)]

# ============================================================
# S1: Table 5 bootstrap CI + omni 共同子集
# ============================================================
print("[S1] Table 5 CI + omni common subset", flush=True)
refmax = {j["key"]: j["text"] for j in load_jsonl(f"{RES}/mt_refmax.jsonl") if j.get("ok")}

def cascade_pairs(mk, cond):
    """级联 mk@cond 的 (sid, hyp); 拒答计空串(有效口径)"""
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
        pairs[sid] = "" if j.get("empty_asr") else j["text"]
    return [(s, pairs[s]) for s in sorted(pairs)]

def e2e_pairs(kind, cond):
    """omni / lt 的 (sid, hyp)"""
    fn = f"{RES}/mt_e2e_omni.jsonl" if kind == "omni" else f"{RES}/mt_e2e_lt.jsonl"
    pairs = {}
    for j in load_jsonl(fn):
        if not j.get("ok"): continue
        ccond, sid = j["key"].split("/", 1)
        if ccond != cond: continue
        pairs[sid] = j["text"]
    return [(s, pairs[s]) for s in sorted(pairs)]

s1 = {}
for cond in ["clean", "n0"]:
    row = {}
    for mk in ["q31", "para16k", "q3"]:
        p = cascade_pairs(mk, cond)
        row[f"cascade_{mk}"] = {"bleu": corpus_bleu_bidir(p, refmax, CORPUS)["bleu"], "n": len(p),
                                "ci95": bootstrap_bleu_ci(p, refmax, CORPUS, n_boot=300)}
    for kind in ["omni", "lt"]:
        p = e2e_pairs(kind, cond)
        row[f"e2e_{kind}"] = {"bleu": corpus_bleu_bidir(p, refmax, CORPUS)["bleu"], "n": len(p),
                              "ci95": bootstrap_bleu_ci(p, refmax, CORPUS, n_boot=300)}
    # omni 共同子集: 在 omni 覆盖的 sid 上重算所有系统
    omni_sids = set(s for s, _ in e2e_pairs("omni", cond))
    common = {}
    for mk in ["q31", "para16k", "q3"]:
        p = [(s, h) for s, h in cascade_pairs(mk, cond) if s in omni_sids]
        common[f"cascade_{mk}"] = {"bleu": corpus_bleu_bidir(p, refmax, CORPUS)["bleu"], "n": len(p)}
    pl = [(s, h) for s, h in e2e_pairs("lt", cond) if s in omni_sids]
    if pl: common["e2e_lt"] = {"bleu": corpus_bleu_bidir(pl, refmax, CORPUS)["bleu"], "n": len(pl)}
    po = e2e_pairs("omni", cond)
    common["e2e_omni"] = {"bleu": corpus_bleu_bidir(po, refmax, CORPUS)["bleu"], "n": len(po)}
    # omni vs q31-cascade 配对 bootstrap (同子集)
    cq = dict(cascade_pairs("q31", cond))
    oq = dict(e2e_pairs("omni", cond))
    shared = sorted(set(cq) & set(oq))
    diffs = None
    if shared:
        rng = np.random.RandomState(7)
        bs = []
        for _ in range(300):
            samp = list(rng.choice(shared, len(shared), replace=True))
            bo = corpus_bleu_bidir([(s, oq[s]) for s in samp], refmax, CORPUS)["bleu"]
            bc = corpus_bleu_bidir([(s, cq[s]) for s in samp], refmax, CORPUS)["bleu"]
            if bo is not None and bc is not None: bs.append(bo - bc)
        bs.sort()
        diffs = [round(bs[int(0.025*len(bs))],1), round(bs[int(0.975*len(bs))],1)] if len(bs) > 50 else None
    row["omni_common_subset"] = common
    row["omni_minus_q31cascade_ci95"] = diffs
    s1[cond] = row
out["table5_ci"] = s1
for cond in s1:
    print(f"  {cond}: " + " | ".join(f"{k}={v['bleu']}(n={v['n']})" for k, v in s1[cond].items()
          if isinstance(v, dict) and "bleu" in v))
    print(f"    omni-q31cascade diff CI: {s1[cond]['omni_minus_q31cascade_ci95']}")

# ============================================================
# S2: 风格归一化 BLEU 敏感性 (标点剥离)
# ============================================================
print("[S2] style-normalised BLEU sensitivity", flush=True)
import re
_PUNCT = "，。！？；：、""''（）《》【】…—·～「」『』\n\r\t,.!?;:()[]{}<>_/\\|@#$%^&*+=~`\u2014\u2018\u2019\u201c\u201d"
def strip_style(text):
    """剥离标点但保留空格 (英文词边界必须保留)"""
    if text is None: return None
    t = "".join(ch for ch in text if ch not in _PUNCT)
    t = " ".join(t.split())
    return t if t.strip() else None

s2 = {"synthetic": {}, "real": {}}
for mk in ["q31", "q3", "para16k"]:
    p = cascade_pairs(mk, "clean")
    s2["synthetic"][f"cascade_{mk}"] = {
        "bleu_raw": corpus_bleu_bidir(p, refmax, CORPUS)["bleu"],
        "bleu_stripped": corpus_bleu_bidir(p, refmax, CORPUS, norm_fn=strip_style)["bleu"]}
for kind in ["omni", "lt"]:
    p = e2e_pairs(kind, "clean")
    s2["synthetic"][f"e2e_{kind}"] = {
        "bleu_raw": corpus_bleu_bidir(p, refmax, CORPUS)["bleu"],
        "bleu_stripped": corpus_bleu_bidir(p, refmax, CORPUS, norm_fn=strip_style)["bleu"]}
po = [(j["key"], j["text"]) for j in load_jsonl(f"{RES}/mt_oracle.jsonl") if j.get("ok")]
s2["synthetic"]["oracle_mt_vs_refmax"] = {
    "bleu_raw": corpus_bleu_bidir(po, refmax, CORPUS)["bleu"],
    "bleu_stripped": corpus_bleu_bidir(po, refmax, CORPUS, norm_fn=strip_style)["bleu"]}
# 真实: 参考 = d3 oracle (人工转写 -> 同一 MT 引擎)
d3_oracle = {j["key"]: j["text"] for j in load_jsonl(f"{RES}/d3_mt_oracle.jsonl") if j.get("ok")}
d3_refmap = {}
for sid, rec in D3_CORPUS.items():
    if sid in d3_oracle: d3_refmap[sid] = d3_oracle[sid]

def d3_pairs_cascade(cond):
    pairs = {}
    for j in load_jsonl(f"{RES}/d3_mt_cascade.jsonl"):
        if not j.get("ok"): continue
        ccond, sid = j["key"].split("/", 1)
        if ccond != cond: continue
        pairs[sid] = j["text"]
    return [(s, pairs[s]) for s in sorted(pairs)]

def d3_pairs_lt(cond):
    pairs = {}
    for j in load_jsonl(f"{RES}/d3_mt_e2e_lt.jsonl"):
        if not j.get("ok"): continue
        ccond, sid = j["key"].split("/", 1)
        if ccond != cond: continue
        pairs[sid] = j["text"]
    return [(s, pairs[s]) for s in sorted(pairs)]

for cond in ["clean_r", "revr", "rb0"]:
    pc = d3_pairs_cascade(cond)
    row = {"cascade_q31": {
        "bleu_raw": corpus_bleu_bidir(pc, d3_refmap, D3_CORPUS)["bleu"],
        "bleu_stripped": corpus_bleu_bidir(pc, d3_refmap, D3_CORPUS, norm_fn=strip_style)["bleu"]}}
    pl = d3_pairs_lt(cond)
    if pl:
        row["e2e_lt"] = {
            "bleu_raw": corpus_bleu_bidir(pl, d3_refmap, D3_CORPUS)["bleu"],
            "bleu_stripped": corpus_bleu_bidir(pl, d3_refmap, D3_CORPUS, norm_fn=strip_style)["bleu"]}
    s2["real"][cond] = row
out["style_sensitivity"] = s2
for grp in s2:
    for k, v in s2[grp].items():
        if isinstance(v, dict) and "bleu_raw" in v:
            print(f"  {grp} {k}: raw={v['bleu_raw']} stripped={v['bleu_stripped']}")

# ============================================================
# S3: 幻觉拆分 (插入/删除/替换)
# ============================================================
print("[S3] hallucination decomposition", flush=True)
def lev_ops(ref, hyp, unit="zh"):
    r = list(ref) if unit == "zh" else ref.split()
    h = list(hyp) if unit == "zh" else hyp.split()
    m, n = len(r), len(h)
    dp = [[0]*(n+1) for _ in range(m+1)]
    for i in range(m+1): dp[i][0] = i
    for j in range(n+1): dp[0][j] = j
    for i in range(1, m+1):
        for j in range(1, n+1):
            dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+(r[i-1] != h[j-1]))
    i, j = m, n; ins = dels = subs = 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] + (r[i-1] != h[j-1]):
            if r[i-1] != h[j-1]: subs += 1
            i -= 1; j -= 1
        elif j > 0 and dp[i][j] == dp[i][j-1] + 1:
            ins += 1; j -= 1
        else:
            dels += 1; i -= 1
    return ins, dels, subs

def norm_for_err(text, lang):
    return normalize_zh(text) if lang == "zh" else normalize_en(text)

s3 = {"synthetic": {}, "real": {}}
for model in ["para16k", "q31", "q3"]:
    for cond in ["nm5", "nm10"]:
        for lang in ["zh", "en"]:
            tot = Counter()
            for sid in SWEEP:
                rec = CORPUS[sid]
                if rec["lang"] != lang: continue
                j = ASR[model].get((cond, sid))
                if j is None: continue
                ref = norm_for_err(rec["text"], lang); hyp = norm_for_err(j.get("text","") or "", lang)
                i_, d_, s_ = lev_ops(ref, hyp, "zh" if lang == "zh" else "en")
                tot["ins"] += i_; tot["del"] += d_; tot["sub"] += s_
            if tot["ins"]+tot["del"]+tot["sub"] > 0:
                tot_err = tot["ins"]+tot["del"]+tot["sub"]
                s3["synthetic"][f"{model}_{cond}_{lang}"] = {
                    "ins": tot["ins"], "del": tot["del"], "sub": tot["sub"],
                    "ins_frac": round(tot["ins"]/tot_err, 3),
                    "ins_minus_del_ratio": round((tot["ins"]-tot["del"])/max(tot["ins"]+tot["del"],1), 3)}
D3_ASR = {}
for model in ["para16k", "q31", "q3", "para8k"]:
    D3_ASR[model] = {}
    for j in load_jsonl(f"{RES}/d3_asr_{model}.jsonl"):
        if j.get("ok"):
            cond, sid = j["key"].split("/", 1)
            D3_ASR[model][(cond, sid)] = j
for model in ["para16k", "q31", "q3", "para8k"]:
    for lang in ["zh", "en"]:
        if model == "para8k" and lang != "zh": continue
        tot = Counter(); n_ut = 0
        for sid, rec in D3_CORPUS.items():
            if rec["lang"] != lang: continue
            j = D3_ASR[model].get(("rbm5", sid))
            if j is None: continue
            ref = norm_for_err(rec["text"], lang); hyp = norm_for_err(j.get("text","") or "", lang)
            i_, d_, s_ = lev_ops(ref, hyp, "zh" if lang == "zh" else "en")
            tot["ins"] += i_; tot["del"] += d_; tot["sub"] += s_; n_ut += 1
        if sum(tot.values()) > 0:
            tot_err = tot["ins"]+tot["del"]+tot["sub"]
            s3["real"][f"{model}_rbm5_{lang}"] = {
                "ins": tot["ins"], "del": tot["del"], "sub": tot["sub"],
                "ins_frac": round(tot["ins"]/tot_err, 3), "n": n_ut}
out["hallucination_decomp"] = s3
for grp in ["synthetic", "real"]:
    for k, v in s3[grp].items():
        print(f"  {grp} {k}: ins={v['ins']} del={v['del']} sub={v['sub']} ins_frac={v['ins_frac']}")

# ============================================================
# S4: 真实 babble 分段观测斜率
# ============================================================
print("[S4] real babble segment slopes", flush=True)
def d3_cond_err(model, cond, lang):
    errs = []
    for sid, rec in D3_CORPUS.items():
        if rec["lang"] != lang: continue
        j = D3_ASR[model].get((cond, sid))
        if j is None: continue
        errs.append(err_rate(rec["text"], j.get("text","") or "", lang))
    return 100*np.mean(errs) if errs else None

s4 = {}
for model in ["para16k", "q31", "q3", "para8k"]:
    for lang in ["zh", "en"]:
        if model == "para8k" and lang != "zh": continue
        e5, e0, em5 = (d3_cond_err(model, c, lang) for c in ["rb5","rb0","rbm5"])
        if None in (e5, e0, em5): continue
        s4[f"{model}_{lang}"] = {"err_5": round(e5,1), "err_0": round(e0,1), "err_m5": round(em5,1),
                                 "seg_5to0": round((e0-e5)/5, 2), "seg_0tom5": round((em5-e0)/5, 2)}
out["real_segment_slopes"] = s4
for k, v in s4.items():
    print(f"  {k}: 5->0 {v['seg_5to0']} pp/dB, 0->-5 {v['seg_0tom5']} pp/dB")

# ============================================================
# S5: 真实 E2E vs 级联 within-system 损失
# ============================================================
print("[S5] real E2E vs cascade within-system loss", flush=True)
s5 = {}
for cond in ["clean_r", "revr", "rb0"]:
    pc = d3_pairs_cascade(cond); pl = d3_pairs_lt(cond)
    bc = corpus_bleu_bidir(pc, d3_refmap, D3_CORPUS)["bleu"]
    bl = corpus_bleu_bidir(pl, d3_refmap, D3_CORPUS)["bleu"] if pl else None
    s5[cond] = {"cascade_bleu": bc, "e2e_lt_bleu": bl,
                "gap": round(bc-bl,1) if bl is not None else None}
if s5["clean_r"]["cascade_bleu"] and s5["rb0"]["cascade_bleu"]:
    s5["cascade_rel_loss_rb0"] = round(100*(1 - s5["rb0"]["cascade_bleu"]/s5["clean_r"]["cascade_bleu"]), 1)
if s5["clean_r"]["e2e_lt_bleu"] and s5["rb0"]["e2e_lt_bleu"]:
    s5["e2e_rel_loss_rb0"] = round(100*(1 - s5["rb0"]["e2e_lt_bleu"]/s5["clean_r"]["e2e_lt_bleu"]), 1)
out["real_e2e_vs_cascade"] = s5
print("  ", json.dumps(s5, ensure_ascii=False))

# ============================================================
# S6: CAC 条件层 bootstrap
# ============================================================
print("[S6] CAC condition-level bootstrap", flush=True)
ext = json.load(open(f"{RES}/analysis_ext.json"))
s6 = {}
rng = np.random.RandomState(123)
for mk in ["q31", "para16k", "q3"]:
    rows = ext["cac_v2"][mk]["points"]
    xs = np.array([r["asr_err"] for r in rows]); ys = np.array([r["loss"] for r in rows])
    sl = []
    for _ in range(2000):
        idx = rng.choice(len(rows), len(rows), replace=True)
        if np.std(xs[idx]) == 0: continue
        sl.append(np.polyfit(xs[idx], ys[idx], 1)[0])
    sl.sort()
    s6[f"synthetic_{mk}"] = {"n_cond": len(rows), "slope": round(float(np.polyfit(xs, ys, 1)[0]), 3),
        "cond_boot_ci95": [round(float(sl[int(0.025*len(sl))]),3), round(float(sl[int(0.975*len(sl))]),3)],
        "cond_boot_median": round(float(sl[len(sl)//2]),3)}
d3a = json.load(open(os.path.join(RES, "d3_analysis.json")))
for lang in ["zh", "en"]:
    cl = d3a["cac_condition_level"][lang]
    xs = np.array(cl["x_cer_pct"]); ys = np.array(cl["y_bleu_loss"])
    sl = []
    for _ in range(2000):
        idx = rng.choice(len(xs), len(xs), replace=True)
        if np.std(xs[idx]) == 0: continue
        sl.append(np.polyfit(xs[idx], ys[idx], 1)[0])
    sl.sort()
    s6[f"real_{lang}"] = {"n_cond": len(xs), "slope": round(float(np.polyfit(xs, ys, 1)[0]), 3),
        "cond_boot_ci95": [round(float(sl[int(0.025*len(sl))]),3), round(float(sl[int(0.975*len(sl))]),3)],
        "cond_boot_median": round(float(sl[len(sl)//2]),3)}
out["cac_cond_bootstrap"] = s6
for k, v in s6.items(): print(f"  {k}: slope={v['slope']} cond-CI={v['cond_boot_ci95']}")

# ============================================================
# S7: logistic s0 位置
# ============================================================
print("[S7] logistic knee position", flush=True)
s7 = {}
for model in ["para16k","para8k","q31","q3"]:
    for lang in ["zh","en"]:
        try:
            lp = ext["knee"][model][lang]["logistic_params"]
            s7[f"{model}_{lang}"] = {"s0": lp["s0"], "k": lp["k"]}
        except Exception: pass
out["logistic_knee_position"] = s7
print("  ", json.dumps(s7, ensure_ascii=False))

# ============================================================
# S8: q31 vs q3 级联 12 共享条件差
# ============================================================
print("[S8] q31 vs q3 cascade max gap", flush=True)
s8 = {}
for cond in [c for c in MAIN_CONDS + ["n20","n15","n5"] if c != "clean"]:
    pq = dict(cascade_pairs("q31", cond)); p3 = dict(cascade_pairs("q3", cond))
    shared = sorted(set(pq) & set(p3))
    if not shared: continue
    bq = corpus_bleu_bidir([(s, pq[s]) for s in shared], refmax, CORPUS)["bleu"]
    b3 = corpus_bleu_bidir([(s, p3[s]) for s in shared], refmax, CORPUS)["bleu"]
    s8[cond] = {"q31": bq, "q3": b3, "gap": round(bq-b3, 2), "n": len(shared)}
gaps = [v["gap"] for v in s8.values() if isinstance(v, dict) and "gap" in v]
s8["_summary"] = {"max_abs_gap": round(max(abs(g) for g in gaps), 2),
                  "mean_abs_gap": round(float(np.mean([abs(g) for g in gaps])), 2)}
out["q31_vs_q3_cascade"] = s8
print(f"  max |gap| = {s8['_summary']['max_abs_gap']} BLEU over {len(gaps)} conds")

# ============================================================
# S9: ESTOI 全条件 (sweep 子集)
# ============================================================
print("[S9] ESTOI", flush=True)
try:
    from pystoi import stoi as stoi_fn
    import soundfile as sf
    AUDIO = os.path.join(ROOT, "audio")
    def load_wav(p):
        x, _ = sf.read(p)
        if x.ndim > 1: x = x.mean(axis=1)
        return x
    sample = sorted(SWEEP)[:36]
    s9 = {}
    for cond in ["clean","n20","n15","n10","n5","n25","n0","nm5","nm10","rev","nb","opus","pl","clip","tempo"]:
        vals = []
        for sid in sample:
            p = None
            for cand in [f"{AUDIO}/perturbed/{cond}/{sid}.wav", f"{AUDIO}/{cond}/{sid}.wav", f"{AUDIO}/main/{cond}/{sid}.wav"]:
                if os.path.exists(cand): p = cand; break
            if p is None: continue
            c = load_wav(p); cl = load_wav(f"{AUDIO}/tts/{sid}.wav")
            n = min(len(c), len(cl))
            vals.append(stoi_fn(cl[:n], c[:n], 16000, extended=True))
        if vals: s9[cond] = round(float(np.mean(vals)), 3)
    out["estoi"] = s9
    print("  ", json.dumps(s9, ensure_ascii=False))
except Exception as e:
    out["estoi"] = f"unavailable: {e}"
    print("  ESTOI failed:", e)

with open(f"{RES}/supplement_v13.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("\nsaved supplement_v13.json")
