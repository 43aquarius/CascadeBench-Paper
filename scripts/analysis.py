# -*- coding: utf-8 -*-
"""CascadeBench 分析模块: 主结果计算 + 统计检验 → analysis_results.json"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import json, os, sys, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metrics import (err_rate, bleu, chrf_score, bootstrap_ci, wilcoxon_test,
                     normalize_zh, normalize_en, bleu_bidir)

RES = os.path.join(ROOT, "results")
CORPUS = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(ROOT, "corpus", "corpus.jsonl"))}
SWEEP = set(json.load(open(os.path.join(ROOT, "corpus", "sweep_ids.json"))))
MAIN_CONDS = ["clean","n10","n0","rev","nb","opus","pl","clip","tempo"]
SWEEP_CONDS = ["n20","n15","n5"]
COND_LABELS = {"clean":"Clean","n20":"Babble 20dB","n15":"Babble 15dB","n10":"Babble 10dB","n5":"Babble 5dB",
               "n0":"Babble 0dB","rev":"Reverb","nb":"Narrowband","opus":"Codec","pl":"PacketLoss","clip":"Clipping","tempo":"Tempo"}
MODEL_LABELS = {"para16k":"Paraformer-RT-v2","para8k":"Paraformer-RT-8K","q31":"Qwen-Audio-3.1","q3":"Qwen3-ASR","omni":"Qwen3.8-Omni"}
ASR_MODELS = ["para16k","para8k","q31","q3","omni"]

def load_jsonl(path):
    if not os.path.exists(path): return []
    out = []
    for line in open(path):
        try: out.append(json.loads(line))
        except Exception: pass
    return out

def load_asr(model):
    """{(cond,sid): record}; ASR_RESPONSE_HAVE_NO_WORDS 视为空转写(完全失败)"""
    d = {}
    for j in load_jsonl(f"{RES}/asr_{model}.jsonl"):
        cond, sid = j["key"].split("/", 1)
        if j.get("ok"):
            d[(cond, sid)] = j
        elif "HAVE_NO_WORDS" in str(j.get("err","")):
            d[(cond, sid)] = {"key": j["key"], "ok": True, "text": "", "no_words": True,
                              "latency_s": j.get("latency_s"), "lang": j.get("lang"), "ref": j.get("ref")}
    return d

def sentence_errors(model, conds=None, lang=None, subset=None):
    """返回 {(cond,sid): error_rate}"""
    data = load_asr(model)
    out = {}
    for (cond, sid), j in data.items():
        if conds and cond not in conds: continue
        rec = CORPUS.get(sid)
        if not rec: continue
        if lang and rec["lang"] != lang: continue
        if subset and sid not in subset: continue
        out[(cond, sid)] = err_rate(rec["text"], j["text"], rec["lang"])
    return out

def agg(vals):
    if not vals: return {"mean": float("nan"), "ci_lo": float("nan"), "ci_hi": float("nan"), "n": 0}
    m, lo, hi = bootstrap_ci(vals, n_boot=1000)
    return {"mean": round(m*100, 2), "ci_lo": round(lo*100, 2), "ci_hi": round(hi*100, 2), "n": len(vals)}

def main_asr_results():
    """主网格: 模型×条件×语言的错误率"""
    results = {}
    for model in ASR_MODELS:
        results[model] = {}
        all_errs = sentence_errors(model, MAIN_CONDS)
        for cond in MAIN_CONDS:
            results[model][cond] = {}
            for lang in ["zh", "en"]:
                errs = [v for (c, s), v in all_errs.items() if c == cond and CORPUS[s]["lang"] == lang]
                if errs: results[model][cond][lang] = agg(errs)
            both = [v for (c, s), v in all_errs.items() if c == cond]
            if both: results[model][cond]["all"] = agg(both)
    return results

def snr_curves():
    """SNR梯度曲线: n20/n15/n10/n5/n0 × 模型 × 语言"""
    snr_conds = ["n20","n15","n10","n5","n0"]
    snr_db = {"n20":20,"n15":15,"n10":10,"n5":5,"n0":0}
    out = {}
    for model in ["para16k","q31","q3"]:
        errs = sentence_errors(model, snr_conds, subset=SWEEP)
        out[model] = {}
        for lang in ["zh","en"]:
            series = []
            for c in snr_conds:
                vals = [v for (cc, s), v in errs.items() if cc == c and CORPUS[s]["lang"] == lang]
                series.append({"snr": snr_db[c], **agg(vals)})
            out[model][lang] = series
    return out

def degradation_slopes():
    """每个模型×语言的 CER~SNR 线性回归斜率 (Theil-Sen近似: 用普通OLS+bootstrap CI)"""
    snr_conds = ["n20","n15","n10","n5","n0"]
    snr_db = {"n20":20,"n15":15,"n10":10,"n5":5,"n0":0}
    out = {}
    for model in ["para16k","q31","q3"]:
        errs = sentence_errors(model, snr_conds, subset=SWEEP)
        for lang in ["zh","en"]:
            xs, ys = [], []
            for (c, s), v in errs.items():
                if CORPUS[s]["lang"] != lang: continue
                xs.append(snr_db[c]); ys.append(v*100)
            if len(xs) < 10: continue
            xs, ys = np.array(xs), np.array(ys)
            slope = np.polyfit(xs, ys, 1)[0]
            # bootstrap slope
            rng = np.random.RandomState(42)
            slopes = []
            for _ in range(1000):
                idx = rng.randrange(len(xs)) if len(xs) == 1 else rng.randint(0, len(xs), len(xs))
                try: slopes.append(np.polyfit(xs[idx], ys[idx], 1)[0])
                except Exception: pass
            slopes.sort()
            key = f"{model}_{lang}"
            out[key] = {"slope_per_db": round(slope, 3),
                        "ci_lo": round(slopes[50], 3), "ci_hi": round(slopes[949], 3)}
    return out

def pairwise_tests():
    """同条件下模型配对Wilcoxon检验 (主网格, 按语言)"""
    tests = {}
    pairs = [("q31","para16k"), ("q3","para16k"), ("q31","q3"), ("q31","omni"), ("para16k","omni")]
    for cond in MAIN_CONDS:
        for lang in ["zh","en"]:
            for m1, m2 in pairs:
                e1 = {k: v for k, v in sentence_errors(m1, [cond], lang).items()}
                e2 = {k: v for k, v in sentence_errors(m2, [cond], lang).items()}
                common = sorted(set(e1) & set(e2))
                if len(common) < 10: continue
                x = [e1[k] for k in common]; y = [e2[k] for k in common]
                stat, p = wilcoxon_test(x, y)
                tests[f"{cond}_{lang}_{m1}_vs_{m2}"] = {
                    "W": float(stat) if stat == stat else None, "p": round(p, 5) if p == p else None,
                    "n": len(common), "mean1": round(np.mean(x)*100,2), "mean2": round(np.mean(y)*100,2)}
    return tests

def latency_stats():
    out = {}
    for model in ASR_MODELS:
        lats = [j["latency_s"] for j in load_jsonl(f"{RES}/asr_{model}.jsonl") if j.get("ok") and j.get("latency_s")]
        if lats:
            lats = sorted(lats)
            out[model] = {"mean": round(np.mean(lats),2), "p50": round(np.percentile(lats,50),2),
                          "p90": round(np.percentile(lats,90),2), "p95": round(np.percentile(lats,95),2),
                          "n": len(lats)}
    return out

def lt_internal_asr():
    """LiveTranslate内置前端ASR (gummy-realtime) 的错误率, 作为第6个ASR系统"""
    out = {}
    for cond in MAIN_CONDS + SWEEP_CONDS:
        errs = []
        for line in open(f"{RES}/mt_e2e_lt.jsonl"):
            j = json.loads(line)
            if not j.get("ok") or not j.get("source_asr"): continue
            c, sid = j["key"].split("/", 1)
            if c != cond: continue
            rec = CORPUS.get(sid)
            if not rec: continue
            errs.append(err_rate(rec["text"], j["source_asr"], rec["lang"]))
        if errs:
            out.setdefault(cond, {})["all"] = agg(errs)
    return out

def translation_results_dual():
    """双参考敏感性: BLEU同时对 refmax 与 oracle 两套参考计算"""
    refmax = {j["key"]: j["text"] for j in load_jsonl(f"{RES}/mt_refmax.jsonl") if j.get("ok")}
    oracle = {j["key"]: j["text"] for j in load_jsonl(f"{RES}/mt_oracle.jsonl") if j.get("ok")}
    res = translation_results()
    # 重新计算 vs oracle
    cascade = load_jsonl(f"{RES}/mt_cascade.jsonl")
    e2e_omni = {j["key"]: j for j in load_jsonl(f"{RES}/mt_e2e_omni.jsonl") if j.get("ok")}
    e2e_lt = {j["key"]: j for j in load_jsonl(f"{RES}/mt_e2e_lt.jsonl") if j.get("ok")}
    ALL = MAIN_CONDS + SWEEP_CONDS
    res["vs_oracle"] = {"cascade": {}, "e2e": {}}
    for mk in ["q31", "para16k"]:
        res["vs_oracle"]["cascade"][mk] = {}
        for cond in ALL:
            pairs = []
            for j in cascade:
                if not j.get("ok") or j.get("empty_asr"): continue
                cm, ccond, sid = j["key"].split("/", 2)
                if cm != mk or ccond != cond: continue
                pairs.append((sid, j["text"]))
            if pairs: res["vs_oracle"]["cascade"][mk][cond] = bleu_bidir(pairs, oracle)
    for name, data in [("omni", e2e_omni), ("lt", e2e_lt)]:
        res["vs_oracle"]["e2e"][name] = {}
        for cond in ALL:
            pairs = []
            for k, j in data.items():
                ccond, sid = k.split("/", 1)
                if ccond != cond or not j.get("text"): continue
                pairs.append((sid, j["text"]))
            if pairs: res["vs_oracle"]["e2e"][name][cond] = bleu_bidir(pairs, oracle)
    return res

def translation_results():
    """级联 vs E2E 翻译质量 (双向BLEU/chrF宏平均, 参考为qwen3.8-max独立译文)"""
    refmax = {j["key"]: j["text"] for j in load_jsonl(f"{RES}/mt_refmax.jsonl") if j.get("ok")}
    oracle = {j["key"]: j["text"] for j in load_jsonl(f"{RES}/mt_oracle.jsonl") if j.get("ok")}
    cascade = load_jsonl(f"{RES}/mt_cascade.jsonl")
    e2e_omni = {j["key"]: j for j in load_jsonl(f"{RES}/mt_e2e_omni.jsonl") if j.get("ok")}
    e2e_lt = {j["key"]: j for j in load_jsonl(f"{RES}/mt_e2e_lt.jsonl") if j.get("ok")}
    asr_err = {m: sentence_errors(m) for m in ["q31", "para16k"]}

    out = {"cascade": {}, "e2e": {}, "cac": {}}
    ALL = MAIN_CONDS + SWEEP_CONDS
    for mk in ["q31", "para16k"]:
        out["cascade"][mk] = {}
        for cond in ALL:
            pairs, errs = [], []
            for j in cascade:
                if not j.get("ok") or j.get("empty_asr"): continue
                cm, ccond, sid = j["key"].split("/", 2)
                if cm != mk or ccond != cond: continue
                pairs.append((sid, j["text"]))
                e = asr_err[mk].get((cond, sid))
                if e is not None: errs.append(e)
            if pairs:
                d = bleu_bidir(pairs, refmax)
                d["mean_asr_err"] = round(np.mean(errs)*100, 2) if errs else None
                out["cascade"][mk][cond] = d
    for name, data in [("omni", e2e_omni), ("lt", e2e_lt)]:
        out["e2e"][name] = {}
        for cond in ALL:
            pairs = []
            for k, j in data.items():
                ccond, sid = k.split("/", 1)
                if ccond != cond or not j.get("text"): continue
                pairs.append((sid, j["text"]))
            if pairs:
                out["e2e"][name][cond] = bleu_bidir(pairs, refmax)
    out["oracle"] = {}
    pairs = [(sid, txt) for sid, txt in oracle.items()]
    if pairs:
        out["oracle"]["mt_clean_text"] = bleu_bidir(pairs, refmax)
    for mk in ["q31", "para16k"]:
        xs, ys = [], []
        for cond in ALL:
            cdata = out["cascade"][mk].get(cond)
            if not cdata or cdata.get("mean_asr_err") is None: continue
            base = out["oracle"]["mt_clean_text"].get("bleu")
            if base is None or cdata.get("bleu") is None: continue
            xs.append(cdata["mean_asr_err"])
            ys.append(base - cdata["bleu"])
        if len(xs) >= 5:
            xs, ys = np.array(xs), np.array(ys)
            if np.std(xs) > 0 and np.std(ys) > 0:
                slope = np.polyfit(xs, ys, 1)[0]
                r = np.corrcoef(xs, ys)[0, 1]
                out["cac"][mk] = {"slope_bleu_per_asr_pct": round(float(slope), 3),
                                  "pearson_r": round(float(r), 3), "n_conditions": len(xs)}
    return out

def domain_breakdown():
    """D4(数字专名) vs 其他领域的错误率对比 (q31, para16k, clean+nb+n0)"""
    out = {}
    for model in ["para16k","q31","q3"]:
        errs = sentence_errors(model, ["clean","nb","n0"])
        for cond in ["clean","nb","n0"]:
            d4 = [v for (c,s),v in errs.items() if c==cond and CORPUS[s]["domain"]=="D4"]
            rest = [v for (c,s),v in errs.items() if c==cond and CORPUS[s]["domain"]!="D4"]
            if d4 and rest:
                out[f"{model}_{cond}"] = {"D4": agg(d4), "others": agg(rest)}
    return out

def stratified_breakdown():
    """两个主力系统的分领域(D1-D4)错误率: clean/n0/nb 条件"""
    out = {}
    for model in ["para16k","q31"]:
        errs = sentence_errors(model, ["clean","nb","n0"])
        for cond in ["clean","nb","n0"]:
            for dom in ["D1","D2","D3","D4"]:
                vals = [v for (c,s),v in errs.items() if c==cond and CORPUS[s]["domain"]==dom]
                if vals:
                    out[f"{model}_{cond}_{dom}"] = round(float(np.mean(vals)) * 100, 2)
    return out

if __name__ == "__main__":
    results = {
        "asr_main": main_asr_results(),
        "asr_lt_internal": lt_internal_asr(),
        "snr_curves": snr_curves(),
        "slopes": degradation_slopes(),
        "pairwise": pairwise_tests(),
        "latency": latency_stats(),
        "translation": translation_results_dual(),
        "domain": domain_breakdown(),
        "stratified": stratified_breakdown(),
    }
    with open(f"{RES}/analysis_results.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    # 摘要打印
    print("=== 主网格错误率 (all, %) ===")
    print(f"{'model':<16}", *[f"{c:<10}" for c in MAIN_CONDS])
    for model in ASR_MODELS:
        row = [f"{results['asr_main'][model][c]['all']['mean']:.1f}" if 'all' in results['asr_main'][model][c] else "-" for c in MAIN_CONDS]
        print(f"{MODEL_LABELS.get(model, model):<16}", *[f"{v:<10}" for v in row])
    print("\n=== SNR斜率 (%/dB) ===")
    for k, v in results["slopes"].items(): print(f"  {k}: {v['slope_per_db']}")
    print("\n=== 延迟(s) ===")
    for k, v in results["latency"].items(): print(f"  {k}: mean={v['mean']} p95={v['p95']}")
    if results["translation"].get("cascade"):
        print("\n=== 级联BLEU (vs refmax) ===")
        for mk in ["q31","para16k"]:
            row = results["translation"]["cascade"].get(mk, {})
            print(f"  {mk}: " + " ".join(f"{c}={d['bleu']:.1f}" for c, d in sorted(row.items())))
    for name in ["omni","lt"]:
        if results["translation"].get("e2e", {}).get(name):
            row = results["translation"]["e2e"][name]
            print(f"=== E2E-{name} BLEU ===\n  " + " ".join(f"{c}={d['bleu']:.1f}" for c, d in sorted(row.items())))
    print("\nSaved to analysis_results.json")
