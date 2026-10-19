#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CascadeBench v1.1 扩展分析 (revision round):
读取主日志 + 扩展日志(n25/nm5/nm10, q3-cascade, D4重复, MT延迟),
输出 analysis_ext.json, 与 analysis.py(v1.0, 冻结)互补。
Blocks:
  snr_curves_v2 / knee / slopes_v2    - 8点SNR曲线 + logistic拐点 + 新斜率
  cac_v2                              - 带截距误差传递 + bootstrap CI + LOO + 杠杆点检验 + 含拒答变体
  refusal                             - 全系统拒答/API错误表 (静默空 vs NO_WORDS)
  rep_variance                        - D4运行间方差 (3次重复)
  mt_latency                          - A8 MT延迟实测
  call_accounting                     - A15精确调用核算
  lt_vs_systems                       - A10同子集LT对比 + 配对检验
  translation_ext                     - 新条件翻译 + 双参考 + chrF + n + 有效BLEU(拒答计空)
  norm_sensitivity                    - D14归一化敏感性
  wilcoxon_zero                       - D13零差值比例
  stoi                                - D8 STOI分析
"""
import os, sys, json, math, glob, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
from metrics import (err_rate, bleu, chrf_score, bootstrap_ci, wilcoxon_test,
                     normalize_zh, normalize_en, bleu_bidir)
from scipy.optimize import curve_fit
from scipy.stats import spearmanr

CORPUS = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(ROOT, "corpus", "corpus.jsonl"))}
SWEEP = set(json.load(open(os.path.join(ROOT, "corpus", "sweep_ids.json"))))
MAIN_CONDS = ["clean","n10","n0","rev","nb","opus","pl","clip","tempo"]
SWEEP_CONDS = ["n20","n15","n5"]
EXT_CONDS = ["n25","nm5","nm10"]
ALL_CONDS = MAIN_CONDS + SWEEP_CONDS + EXT_CONDS
SNR_OF = {"n20":20,"n15":15,"n10":10,"n5":5,"n25":2.5,"n0":0,"nm5":-5,"nm10":-10}

def load_jsonl(path):
    if not os.path.exists(path): return []
    out = []
    for line in open(path, encoding="utf-8"):
        try: out.append(json.loads(line))
        except Exception: pass
    return out

def load_asr_all(model):
    """main + ext 日志合并, last-wins; NO_WORDS→空文本(100%错误)"""
    d = {}
    for f in [f"{RES}/asr_{model}.jsonl", f"{RES}/ext_asr_{model}.jsonl"]:
        for j in load_jsonl(f):
            cond, sid = j["key"].split("/", 1)
            if j.get("ok"):
                d[(cond, sid)] = j
            elif "NO_WORDS" in str(j.get("err","")):
                d[(cond, sid)] = {"key": j["key"], "ok": True, "text": "", "no_words": True, "lang": j.get("lang")}
    return d

ASR = {m: load_asr_all(m) for m in ["para16k","para8k","q31","q3","omni"]}

def sent_err(model, cond, sid):
    j = ASR[model].get((cond, sid))
    if j is None: return None
    rec = CORPUS[sid]
    return err_rate(rec["text"], j.get("text","") or "", rec["lang"])

out = {}

# ---------- 1. SNR curves v2 (8 points) ----------
print("[1/13] snr_curves_v2", flush=True)
snr2 = {}
for model in ["para16k","para8k","q31","q3"]:
    snr2[model] = {}
    for lang in ["zh","en"]:
        pts = []
        for c in SNR_OF:
            vals = [sent_err(model, c, s) for s in SWEEP
                    if CORPUS[s]["lang"] == lang and sent_err(model, c, s) is not None]
            if vals:
                m, lo, hi = bootstrap_ci(vals, n_boot=1000)
                pts.append({"snr": SNR_OF[c], "mean": round(m*100,2),
                            "ci_lo": round(lo*100,2), "ci_hi": round(hi*100,2), "n": len(vals)})
        snr2[model][lang] = sorted(pts, key=lambda p: -p["snr"])
out["snr_curves_v2"] = snr2

# ---------- 2. Knee / logistic analysis ----------
print("[2/13] knee", flush=True)
def logistic(s, L, k, s0, b):
    """descending sigmoid: err high at low SNR, floor b at high SNR"""
    return b + (L - b) / (1.0 + np.exp(k * (s - s0)))

def fit_logistic(s, y):
    L0 = min(max(y.max()*1.05, 1.0), 155.0)
    b0 = min(y.min(), 1.0)
    p0 = [L0, 0.5, float(np.median(s)), b0]
    bounds = ([max(y.max()*0.5, 1.0), 0.05, -15.0, 0.0],
              [160.0, 3.0, 20.0, max(y.min()*1.5, 0.5)])
    popt, _ = curve_fit(logistic, s, y, p0=p0, maxfev=40000, bounds=bounds)
    return popt

knee = {}
for model in ["para16k","para8k","q31","q3"]:
    knee[model] = {}
    for lang in ["zh","en"]:
        pts = snr2[model][lang]
        if len(pts) < 6: continue
        s = np.array([p["snr"] for p in pts], float)
        y = np.array([p["mean"] for p in pts], float)
        try:
            popt = fit_logistic(s, y)
            L, k, s0, b = popt
            grid = np.linspace(-15, 22, 3701)
            yy = logistic(grid, *popt)
            def snr_at(th):
                # descending curve: error>=th for s<=crossing; return the crossing (rightmost idx)
                idx = np.where(yy >= th)[0]
                return round(float(grid[idx[-1]]), 2) if len(idx) else None
            steep = float((L - b) * k / 4)  # max slope pp/dB
            # bootstrap CI over sentences: model-free elbow interpolation (robust)
            s10s = []
            for _ in range(300):
                samp = {}
                for c in SNR_OF:
                    vals = [sent_err(model, c, s_) for s_ in SWEEP
                            if CORPUS[s_]["lang"] == lang and sent_err(model, c, s_) is not None]
                    if vals:
                        samp[c] = 100*float(np.mean(np.random.choice(vals, len(vals))))
                cs = sorted(samp, key=lambda c: -SNR_OF[c])
                for i in range(len(cs)-1):
                    hi_s, lo_s = SNR_OF[cs[i]], SNR_OF[cs[i+1]]
                    hi_y, lo_y = samp[cs[i]], samp[cs[i+1]]
                    if hi_y < 10 <= lo_y:
                        t = (10 - hi_y) / (lo_y - hi_y)
                        s10s.append(hi_s + t*(lo_s - hi_s))
                        break
            ci = (round(float(np.percentile(s10s,2.5)),2), round(float(np.percentile(s10s,97.5)),2)) if len(s10s) > 100 else None
            knee[model][lang] = {
                "snr_at_10pct_err": snr_at(10.0), "snr_at_50pct_err": snr_at(50.0),
                "s10_ci95": ci,
                "logistic_max_slope_pp_per_db": round(steep, 2),
                "logistic_params": {"L": round(float(L),1), "k": round(float(k),3),
                                     "s0": round(float(s0),2), "b": round(float(b),2)},
                "elbow_snr_interp_10pct": None,
            }
            # piecewise-linear interpolated crossing (model-free)
            for i in range(len(pts)-1):
                hi_p, lo_p = pts[i], pts[i+1]
                if hi_p["mean"] < 10 <= lo_p["mean"]:
                    t = (10 - hi_p["mean"]) / (lo_p["mean"] - hi_p["mean"])
                    knee[model][lang]["elbow_snr_interp_10pct"] = round(hi_p["snr"] + t*(lo_p["snr"]-hi_p["snr"]), 2)
                    break
        except Exception as e:
            knee[model][lang] = {"error": str(e)[:100]}
out["knee"] = knee

# ---------- 3. slopes v2 ----------
print("[3/13] slopes_v2", flush=True)
slopes2 = {}
for model in ["para16k","para8k","q31","q3"]:
    for lang in ["zh","en"]:
        for rng, conds in [("20to0", [c for c in SNR_OF if SNR_OF[c] >= 0]),
                           ("20to-10", list(SNR_OF))]:
            xs, ys = [], []
            for c in conds:
                vals = [sent_err(model, c, s) for s in SWEEP
                        if CORPUS[s]["lang"] == lang and sent_err(model, c, s) is not None]
                if vals:
                    xs.append(SNR_OF[c]); ys.append(100*np.mean(vals))
            if len(xs) >= 4 and np.std(xs) > 0:
                sl = np.polyfit(xs, ys, 1)[0]
                r = np.corrcoef(xs, ys)[0,1]
                slopes2[f"{model}_{lang}_{rng}"] = {"slope_per_db": round(float(sl),2),
                                                     "r": round(float(r),3), "n_points": len(xs)}
out["slopes_v2"] = slopes2

# ---------- 4. CAC v2 ----------
print("[4/13] cac_v2", flush=True)
refmax = {j["key"]: j["text"] for j in load_jsonl(f"{RES}/mt_refmax.jsonl") if j.get("ok")}
oracle = {j["key"]: j["text"] for j in load_jsonl(f"{RES}/mt_oracle.jsonl") if j.get("ok")}

def cascade_cond_pairs(mk, cond, eff=False):
    """(sid, hyp) pairs for cascade mk@cond; eff=True 时拒答计空翻译"""
    if mk == "q3":
        recs = load_jsonl(f"{RES}/ext_mt_cascade_q3main.jsonl")
    elif cond in EXT_CONDS:
        recs = load_jsonl(f"{RES}/ext_mt_cascade.jsonl")
    else:
        recs = load_jsonl(f"{RES}/mt_cascade.jsonl")
    pairs = {}
    for j in recs:
        if not j.get("ok"): continue
        cm, ccond, sid = j["key"].split("/", 2)
        if cm != mk or ccond != cond: continue
        if j.get("empty_asr"):
            if eff: pairs[sid] = ""
            continue
        pairs[sid] = j["text"]
    return [(s, pairs[s]) for s in sorted(pairs)]

cac2 = {}
for mk in ["q31", "para16k", "q3"]:
    conds = [c for c in ALL_CONDS if c != "clean"] if mk != "q3" else \
            [c for c in MAIN_CONDS + SWEEP_CONDS if c != "clean"]
    rows = []
    base_pairs = cascade_cond_pairs(mk, "clean", eff=True)
    BASE = bleu_bidir(base_pairs, refmax, keep_empty=True)["bleu"] if base_pairs else None
    for cond in conds:
        pairs = cascade_cond_pairs(mk, cond, eff=True)
        if not pairs: continue
        errs = [sent_err(mk, cond, s) for s, _ in pairs]
        if any(e is None for e in errs): continue
        d = bleu_bidir(pairs, refmax, keep_empty=True)
        rows.append({"cond": cond, "asr_err": round(100*np.mean(errs),2),
                     "bleu": d["bleu"], "loss": round(BASE - d["bleu"],2),
                     "rel_loss": round(100*(BASE-d["bleu"])/BASE,1), "n": len(pairs)})
    if len(rows) < 5: continue
    xs = np.array([r["asr_err"] for r in rows]); ys = np.array([r["loss"] for r in rows])
    b, a = np.polyfit(xs, ys, 1)  # ys = a + b*xs
    r = np.corrcoef(xs, ys)[0,1]
    print(f"  cac {mk}: OLS done ({len(rows)} pts), bootstrapping...", flush=True)
    # sentence-level bootstrap CI (60 resamples; clean base fixed)
    boot = []
    all_pairs = {c: dict(cascade_cond_pairs(mk, c, eff=True)) for c in conds}
    sids = sorted(set().union(*[set(p) for p in all_pairs.values()]))
    for bi in range(60):
        samp = np.random.choice(sids, len(sids), replace=True)
        rws = []
        for cond in conds:
            pd = all_pairs[cond]
            chosen = [(s, pd[s]) for s in samp if s in pd]
            if not chosen: continue
            errs = [sent_err(mk, cond, s) for s, _ in chosen]
            if any(e is None for e in errs): continue
            d = bleu_bidir(chosen, refmax, keep_empty=True)
            rws.append((100*np.mean(errs), BASE - d["bleu"]))
        if len(rws) >= 5:
            bx = np.array([p[0] for p in rws]); by = np.array([p[1] for p in rws])
            if np.std(bx) > 0: boot.append(np.polyfit(bx, by, 1))
        if bi % 20 == 0: print(f"    {mk} boot {bi}/60", flush=True)
    if boot:
        bs = np.array(boot)
        slope_ci = (round(float(np.percentile(bs[:,0],2.5)),3), round(float(np.percentile(bs[:,0],97.5)),3))
        icept_ci = (round(float(np.percentile(bs[:,1],2.5)),3), round(float(np.percentile(bs[:,1],97.5)),3))
    else:
        slope_ci = icept_ci = None
    # LOO robustness
    loos = []
    for i in range(len(rows)):
        mask = np.ones(len(rows), bool); mask[i] = False
        if mask.sum() >= 4 and np.std(xs[mask]) > 0:
            loos.append(round(float(np.polyfit(xs[mask], ys[mask], 1)[0]),3))
    # leverage: drop err>40
    m2 = xs <= 40
    lev = {"slope_drop_high_lev": round(float(np.polyfit(xs[m2], ys[m2], 1)[0]),3),
           "n_points_kept": int(m2.sum())} if m2.sum() >= 4 and np.std(xs[m2])>0 else None
    cac2[mk] = {"points": rows, "slope": round(float(b),3), "intercept": round(float(a),2),
                "pearson_r": round(float(r),3), "slope_ci95": slope_ci, "intercept_ci95": icept_ci,
                "loo_slopes": loos, "loo_slope_range": (min(loos), max(loos)) if loos else None,
                "leverage_check": lev,
                "protocol": "refusal-inclusive: empty ASR -> empty translation, error=100%"}
out["cac_v2"] = cac2

# ---------- 5. Refusal / API-error table ----------
print("[5/13] refusal", flush=True)
refusal = {}
for model in ["para16k","para8k","q31","q3","omni"]:
    refusal[model] = {}
    for cond in ALL_CONDS:
        for lang in ["zh","en"]:
            if model == "para8k" and lang == "en": continue
            if model == "omni" and cond in EXT_CONDS + SWEEP_CONDS: continue
            n = ref = api_err = 0
            for s in (SWEEP if cond in SWEEP_CONDS + EXT_CONDS else CORPUS):
                if CORPUS[s]["lang"] != lang: continue
                if cond in SWEEP_CONDS + EXT_CONDS and s not in SWEEP: continue
                j = ASR[model].get((cond, s))
                if j is None: continue
                n += 1
                if j.get("no_words"): ref += 1
                elif j.get("ok") and not (j.get("text") or "").strip(): ref += 1
            if n and ref:
                refusal[model][f"{cond}/{lang}"] = {"rate": round(100*ref/n,1), "k": ref, "n": n}
out["refusal"] = refusal

# ---------- 6. Repetition variance (D4) ----------
print("[6/13] rep_variance", flush=True)
rep = {}
for model in ["q31","q3"]:
    rep[model] = {}
    for cond in ["n0","tempo"]:
        runs = []
        # run 0 = main log (sweep subset)
        v0 = [sent_err(model, cond, s) for s in SWEEP if sent_err(model, cond, s) is not None]
        runs.append(("main", 100*np.mean(v0) if v0 else None))
        # reps
        for r in [1,2]:
            d = {}
            for j in load_jsonl(f"{RES}/ext_rep_{model}_{cond}_r{r}.jsonl"):
                if j.get("ok"): d[j["key"].split("/",1)[1]] = j.get("text","") or ""
                elif "NO_WORDS" in str(j.get("err","")): d[j["key"].split("/",1)[1]] = ""
            vals = [err_rate(CORPUS[s]["text"], d.get(s,""), CORPUS[s]["lang"]) for s in SWEEP if s in d]
            runs.append((f"r{r}", round(100*np.mean(vals),2) if vals else None))
        # transcript agreement main vs r1
        dmain = {s: (ASR[model].get((cond,s)) or {}).get("text","") for s in SWEEP}
        d1 = {}
        for j in load_jsonl(f"{RES}/ext_rep_{model}_{cond}_r1.jsonl"):
            if j.get("ok") or "NO_WORDS" in str(j.get("err","")):
                d1[j["key"].split("/",1)[1]] = j.get("text","") or ""
        agree = np.mean([dmain[s] == d1.get(s,"<none>") for s in SWEEP if s in d1]) if d1 else None
        means = [v for _, v in runs if v is not None]
        rep[model][cond] = {"runs": dict(runs), "mean_of_runs": round(float(np.mean(means)),2),
                            "sd_across_runs": round(float(np.std(means, ddof=1)),3) if len(means)>1 else None,
                            "transcript_agreement_main_vs_r1": round(float(agree),3) if agree is not None else None}
out["rep_variance"] = rep

# ---------- 7. MT latency (A8) ----------
print("[7/13] mt_latency", flush=True)
lat = [j["latency_s"] for j in load_jsonl(f"{RES}/ext_mt_latency.jsonl") if j.get("ok")]
if lat:
    out["mt_latency"] = {"n": len(lat), "mean": round(float(np.mean(lat)),3),
                         "p50": round(float(np.percentile(lat,50)),3),
                         "p95": round(float(np.percentile(lat,95)),3),
                         "protocol": "120 sequential qwen-mt-uni calls, wall-clock, Oct 2026"}

# ---------- 8. Call accounting (A15) ----------
print("[8/13] call_accounting", flush=True)
acct = {}
tot_lines = tot_ok = 0
files = [("tts","tts_log.jsonl"),("asr_para16k","asr_para16k.jsonl"),("asr_para8k","asr_para8k.jsonl"),
         ("asr_q31","asr_q31.jsonl"),("asr_q3","asr_q3.jsonl"),("asr_omni","asr_omni.jsonl"),
         ("mt_oracle","mt_oracle.jsonl"),("mt_refmax","mt_refmax.jsonl"),("mt_cascade","mt_cascade.jsonl"),
         ("mt_e2e_omni","mt_e2e_omni.jsonl"),("mt_e2e_lt","mt_e2e_lt.jsonl"),
         ("ext_asr_q31","ext_asr_q31.jsonl"),("ext_asr_q3","ext_asr_q3.jsonl"),
         ("ext_asr_para16k","ext_asr_para16k.jsonl"),("ext_asr_para8k","ext_asr_para8k.jsonl"),
         ("ext_mt_cascade","ext_mt_cascade.jsonl"),("ext_mt_cascade_q3main","ext_mt_cascade_q3main.jsonl"),
         ("ext_mt_e2e_lt","ext_mt_e2e_lt.jsonl"),("ext_mt_latency","ext_mt_latency.jsonl")]
for name, f in files:
    js = load_jsonl(f"{RES}/{f}")
    if not js: continue
    okc = sum(1 for j in js if j.get("ok"))
    keys = len({j["key"] for j in js if j.get("ok")})
    acct[name] = {"lines": len(js), "ok": okc, "unique_ok": keys}
    tot_lines += len(js); tot_ok += okc
acct["TOTAL"] = {"lines": tot_lines, "ok": tot_ok}
out["call_accounting"] = acct

# ---------- 9. LT frontend vs other systems (A10) ----------
print("[9/13] lt_vs_systems", flush=True)
lt_recs = load_jsonl(f"{RES}/mt_e2e_lt.jsonl") + load_jsonl(f"{RES}/ext_mt_e2e_lt.jsonl")
lt_asr = {}
for j in lt_recs:
    if j.get("ok") and j.get("source_asr") is not None:
        c, sid = j["key"].split("/", 1)
        lt_asr[(c, sid)] = j["source_asr"]
ltv = {}
for cond in MAIN_CONDS + SWEEP_CONDS + EXT_CONDS:
    row = {}
    lvals = [err_rate(CORPUS[s]["text"], lt_asr[(cond,s)], CORPUS[s]["lang"])
             for s in SWEEP if (cond,s) in lt_asr]
    if not lvals: continue
    row["lt"] = {"mean": round(100*np.mean(lvals),1), "n": len(lvals)}
    for m in ["q31","q3","para16k"]:
        vals = [sent_err(m, cond, s) for s in SWEEP if sent_err(m, cond, s) is not None]
        if vals: row[m] = round(100*np.mean(vals),1)
    # paired wilcoxon LT vs q31 on common sids
    common = [s for s in SWEEP if (cond,s) in lt_asr and sent_err("q31",cond,s) is not None]
    if len(common) > 20:
        a = [err_rate(CORPUS[s]["text"], lt_asr[(cond,s)], CORPUS[s]["lang"]) for s in common]
        b = [sent_err("q31", cond, s) for s in common]
        try:
            row["wilcoxon_lt_vs_q31_p"] = round(wilcoxon_test(a, b), 4)
        except Exception:
            row["wilcoxon_lt_vs_q31_p"] = None
    ltv[cond] = row
out["lt_vs_systems"] = ltv

# ---------- 10. Translation ext ----------
print("[10/13] translation_ext", flush=True)
tx = {"cascade": {}, "e2e": {}}
for mk in ["q31","para16k","q3"]:
    tx["cascade"][mk] = {}
    conds = ALL_CONDS if mk != "q3" else MAIN_CONDS + SWEEP_CONDS
    for cond in ALL_CONDS if mk != "q3" else MAIN_CONDS + SWEEP_CONDS:
        for eff in [False, True]:
            pairs = cascade_cond_pairs(mk, cond, eff=eff)
            if not pairs: continue
            d = bleu_bidir(pairs, refmax, keep_empty=eff)
            d2 = bleu_bidir(pairs, oracle, keep_empty=eff)
            tag = "eff" if eff else "cond"
            tx["cascade"][mk].setdefault(cond, {})[tag] = {
                "bleu": d["bleu"], "chrf": d["chrf"], "n": len(pairs),
                "bleu_vs_oracle": d2["bleu"]}
# e2e paths on ext conds
e2e_omni = {j["key"]: j for j in load_jsonl(f"{RES}/mt_e2e_omni.jsonl") if j.get("ok")}
for name, data in [("omni", e2e_omni), ("lt", {j["key"]: j for j in lt_recs if j.get("ok")})]:
    tx["e2e"][name] = {}
    for cond in ALL_CONDS:
        pairs = []
        for k, j in data.items():
            c, sid = k.split("/", 1)
            if c == cond and j.get("text"): pairs.append((sid, j["text"]))
        if pairs:
            d = bleu_bidir(pairs, refmax)
            d2 = bleu_bidir(pairs, oracle)
            tx["e2e"][name][cond] = {"bleu": d["bleu"], "chrf": d["chrf"], "n": len(pairs),
                                     "bleu_vs_oracle": d2["bleu"]}
# oracle row
pairs = list(oracle.items())
d = bleu_bidir(pairs, refmax)
tx["oracle_mt_clean"] = {"bleu": d["bleu"], "chrf": d["chrf"], "n": len(pairs),
                          "bleu_vs_refmax_self": None}
out["translation_ext"] = tx

# ---------- 11. Normalisation sensitivity (D14) ----------
print("[11/13] norm_sensitivity", flush=True)
def raw_err(ref, hyp, lang):
    """仅大小写/标点折叠, 不做数字归一化"""
    import re, unicodedata
    def fold(t):
        t = unicodedata.normalize("NFKC", t).lower()
        t = re.sub(r"[^\w\s]", "", t, flags=re.UNICODE)
        return re.sub(r"\s+", " ", t).strip()
    a, b = fold(ref), fold(hyp or "")
    la = list(a) if lang == "zh" else a.split()
    lb = list(b) if lang == "zh" else b.split()
    if not la: return 1.0 if lb else 0.0
    # levenshtein
    prev = list(range(len(lb)+1))
    for i, ca in enumerate(la, 1):
        cur = [i]
        for j, cb in enumerate(lb, 1):
            cur.append(min(prev[j]+1, cur[-1]+1, prev[j-1]+(ca != cb)))
        prev = cur
    return prev[-1] / len(la)

norms = {}
for model in ["q31","para16k","q3"]:
    norms[model] = {}
    for cond in ["clean","n0","nb","rev"]:
        vf, vr = [], []
        for s in CORPUS:
            j = ASR[model].get((cond, s))
            if j is None: continue
            vf.append(err_rate(CORPUS[s]["text"], j.get("text",""), CORPUS[s]["lang"]))
            vr.append(raw_err(CORPUS[s]["text"], j.get("text",""), CORPUS[s]["lang"]))
        if vf:
            norms[model][cond] = {"full_norm": round(100*np.mean(vf),2),
                                   "raw": round(100*np.mean(vr),2)}
out["norm_sensitivity"] = norms

# ---------- 12. Wilcoxon zero-diff fractions (D13) ----------
print("[12/13] wilcoxon_zero", flush=True)
zd = {}
for cond in ["n0","rev"]:
    for lang in ["zh","en"]:
        a = [sent_err("q31",cond,s) for s in CORPUS if CORPUS[s]["lang"]==lang and sent_err("q31",cond,s) is not None]
        b = [sent_err("para16k",cond,s) for s in CORPUS if CORPUS[s]["lang"]==lang and sent_err("para16k",cond,s) is not None]
        common = [s for s in CORPUS if CORPUS[s]["lang"]==lang
                  and sent_err("q31",cond,s) is not None and sent_err("para16k",cond,s) is not None]
        da = [sent_err("q31",cond,s) for s in common]
        db = [sent_err("para16k",cond,s) for s in common]
        zero = sum(1 for x,y in zip(da,db) if x==y)
        zd[f"q31_vs_para16k/{cond}/{lang}"] = {"n": len(common), "zero_diff_frac": round(zero/len(common),3)}
out["wilcoxon_zero"] = zd

# ---------- 13. STOI analysis (D8) ----------
print("[13/13] stoi", flush=True)

def load_wav_local(p):
    import soundfile as sfl
    x, sr = sfl.read(p, dtype="float32")
    if x.ndim > 1: x = x.mean(axis=1)
    return x

try:
    from pystoi import stoi as stoi_fn
    import soundfile as sf_a
    AUDIO = None
    for cand in [os.path.join(ROOT, "audio")]:
        if os.path.exists(os.path.join(cand, "tts")): AUDIO = cand; break
    if AUDIO:
        st = {}
        sample = sorted(SWEEP)
        for cond in MAIN_CONDS + SWEEP_CONDS + EXT_CONDS:
            vals = []
            for sid in sample:
                p = f"{AUDIO}/perturbed/{cond}/{sid}.wav"
                if not os.path.exists(p): continue
                c = load_wav_local(p)
                cl = f"{AUDIO}/tts/{sid}.wav"
                if not os.path.exists(cl): continue
                cc = load_wav_local(cl)
                n = min(len(c), len(cc))
                vals.append(stoi_fn(cc[:n], c[:n], 16000, extended=False))
            if vals:
                errs = [sent_err("q31",cond,s) for s in sample if sent_err("q31",cond,s) is not None]
                st[cond] = {"stoi_mean": round(float(np.mean(vals)),3),
                            "q31_err": round(100*np.mean(errs),1) if errs else None}
        out["stoi"] = st
except ImportError:
    out["stoi"] = "pystoi unavailable"

# save
with open(f"{RES}/analysis_ext.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("saved analysis_ext.json")
print(json.dumps({k: (list(v.keys())[:6] if isinstance(v,dict) else str(v)[:40]) for k,v in out.items()}, indent=1, ensure_ascii=False))
