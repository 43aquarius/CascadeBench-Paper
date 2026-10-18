# -*- coding: utf-8 -*-
"""D3 真实语音验证分析
1. 各系统×条件 CER/WER (真实 ground truth) + 拒答率
2. 真实 vs 合成配对对比 (clean/rev/噪声匹配条件)
3. 真实 babble SNR 斜率
4. 级联翻译: BLEU (oracle 参考) + CAC 线性律检验
5. E2E LT vs 级联 (同子集)
输出: d3_analysis.json
"""
import json, os, sys, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metrics import err_rate, cer, wer, normalize_zh, normalize_en

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D3D = os.path.join(ROOT, "corpus")
RES = os.path.join(ROOT, "results")
CORPUS = [json.loads(l) for l in open(os.path.join(ROOT, "corpus", "d3_corpus.jsonl"))]
RECMAP = {r["id"]: r for r in CORPUS}
CONDS = ["clean_r", "revr", "rb5", "rb0", "rbm5", "rn0"]
SYSCONF = {"q31": "LLM (Qwen-Audio-3.1)", "q3": "LLM (Qwen3-ASR)",
           "para16k": "Streaming (Paraformer-16k)", "para8k": "Streaming (Paraformer-8k)"}

def load_asr(key):
    out = {}
    for line in open(f"{RES}/d3_asr_{key}.jsonl"):
        j = json.loads(line)
        if j.get("ok"):
            out[j["key"]] = j
    return out

def load_mt(fname):
    out = {}
    for line in open(f"{RES}/{fname}"):
        j = json.loads(line)
        if j.get("ok"):
            out[j["key"]] = j
    return out

def boot_ci(vals, n=2000, seed=7):
    rng = np.random.RandomState(seed)
    vals = np.asarray(vals, dtype=float)
    if len(vals) == 0: return (None, None)
    bs = [np.mean(rng.choice(vals, len(vals))) for _ in range(n)]
    return (round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4))

results = {"n_utts": {"zh": sum(1 for r in CORPUS if r["lang"]=="zh"),
                       "en": sum(1 for r in CORPUS if r["lang"]=="en")}}

# ---------- 1) ASR: CER/WER + 拒答 ----------
print("=== 1) ASR 识别错误率 (真实语音) ===")
asr_data = {k: load_asr(k) for k in SYSCONF}
asr_table = {}
for sysk, conftxt in SYSCONF.items():
    asr_table[sysk] = {}
    for cond in CONDS:
        per_lang = {"zh": [], "en": []}
        refuse = {"zh": 0, "en": 0}; n_ref = {"zh": 0, "en": 0}
        for rec in CORPUS:
            lang = rec["lang"]
            if sysk == "para8k" and lang != "zh": continue
            j = asr_data[sysk].get(f"{cond}/{rec['id']}")
            if j is None: continue
            hyp = j.get("text") or ""
            if j.get("refusal") or not hyp.strip():
                per_lang[lang].append(1.0); refuse[lang] += 1
            else:
                per_lang[lang].append(err_rate(rec["text"], hyp, lang))
            n_ref[lang] += 1
        entry = {}
        for lang in ["zh", "en"]:
            if per_lang[lang]:
                ci = boot_ci(per_lang[lang])
                entry[lang] = {"mean": round(float(np.mean(per_lang[lang])), 4), "ci95": ci,
                               "n": len(per_lang[lang]),
                               "refusal_rate": round(refuse[lang]/max(1,n_ref[lang]), 4)}
        asr_table[sysk][cond] = entry
        zh_m = entry.get("zh", {}).get("mean"); en_m = entry.get("en", {}).get("mean")
        print(f"  {sysk:8s} {cond:8s} zh={zh_m if zh_m is None else round(zh_m*100,1)}% en={en_m if en_m is None else round(en_m*100,1)}%")
results["asr_table"] = asr_table

# ---------- 2) 真实 babble SNR 斜率 ----------
print("=== 2) 真实 babble SNR 斜率 (%/dB) ===")
snr_pts = {"rb5": 5, "rb0": 0, "rbm5": -5}
slopes = {}
for sysk in SYSCONF:
    for lang in ["zh", "en"]:
        means = []
        for cond in ["rb5", "rb0", "rbm5"]:
            e = asr_table[sysk][cond].get(lang)
            if e: means.append(e["mean"] * 100)
        if len(means) == 3:
            snrs = [5, 0, -5]
            k, b = np.polyfit(snrs, means, 1)
            # bootstrap CI
            rng = np.random.RandomState(3)
            per_cond_errs = []
            for cond in ["rb5", "rb0", "rbm5"]:
                errs = []
                for rec in CORPUS:
                    if rec["lang"] != lang: continue
                    if sysk == "para8k" and lang != "zh": continue
                    j = asr_data[sysk].get(f"{cond}/{rec['id']}")
                    if j is None: continue
                    hyp = j.get("text") or ""
                    errs.append(1.0 if (j.get("refusal") or not hyp.strip()) else err_rate(rec["text"], hyp, lang))
                per_cond_errs.append(errs)
            bs = []
            for _ in range(2000):
                m = [np.mean(rng.choice(e, len(e))) * 100 for e in per_cond_errs]
                bs.append(np.polyfit(snrs, m, 1)[0])
            slopes[f"{sysk}_{lang}"] = {"slope_pp_per_db": round(float(k), 3),
                                        "ci95": (round(float(np.percentile(bs,2.5)),3), round(float(np.percentile(bs,97.5)),3)),
                                        "means_5_0_m5": [round(m,2) for m in means]}
            print(f"  {sysk:8s} {lang}: slope={k:.2f}%/dB  means(5/0/-5)={[round(m,1) for m in means]}")
results["real_babble_slopes"] = slopes

# ---------- 3) 与合成语料配对对比 ----------
print("=== 3) 真实 vs 合成 (匹配条件) ===")
# 合成: asr_main[sys][cond][lang] = {mean(百分数), ci_lo, ci_hi, n}
syn = json.load(open(os.path.join(RES, "analysis_results.json")))
syn_ext = json.load(open(os.path.join(RES, "analysis_ext.json")))
def find_syn(sysk, cond, lang):
    try:
        return syn["asr_main"][sysk][cond][lang]["mean"]  # 百分数
    except Exception:
        return None

def find_syn_snr(sysk, snr, lang):
    """从 snr_curves_v2 取指定 SNR 点 (百分数)"""
    try:
        for pt in syn_ext["snr_curves_v2"][sysk][lang]:
            if pt["snr"] == snr: return pt["mean"]
    except Exception: pass
    return None

# 匹配映射: 真实条件 -> (合成主网格条件 或 SNR点)
MATCH = {"clean_r": ("cond", "clean"), "revr": ("cond", "rev"),
         "rb5": ("snr", 5), "rb0": ("snr", 0), "rbm5": ("snr", -5)}
comparison = {}
for sysk in SYSCONF:
    comparison[sysk] = {}
    for rcond, (mtype, mval) in MATCH.items():
        for lang in ["zh", "en"]:
            r_e = asr_table[sysk].get(rcond, {}).get(lang, {})
            s_v = find_syn(sysk, mval, lang) if mtype == "cond" else find_syn_snr(sysk, mval, lang)
            if r_e and s_v is not None:
                comparison[sysk][f"{rcond}_{lang}"] = {
                    "real_pct": round(r_e["mean"]*100, 2), "synthetic_pct": round(float(s_v), 2)}
for sysk, d in comparison.items():
    print(f"  {sysk}: {d}")
results["real_vs_synthetic"] = comparison

# ---------- 3b) 真实膝点插值 (10% 错误率对应 SNR) ----------
def knee_interp(means, snrs=(5, 0, -5), thr=10.0):
    """在 3 点曲线中插值出错误率=thr 的 SNR; 若全部低于thr返回>5标记"""
    m5, m0, mm5 = means
    if m5 >= thr:
        return 5.0 + (m5 - thr) / max(m5 - m0, 1e-9) * (-5) * -1 if m5 > m0 else None  # 超出范围
    if m5 < thr <= m0:
        # 在 [5,0] 之间线性插值
        return 5 - (thr - m5) / max(m0 - m5, 1e-9) * 5
    if m0 < thr <= mm5:
        return 0 - (thr - m0) / max(mm5 - m0, 1e-9) * 5
    return None  # 全程未达阈值

print("=== 3b) 真实膝点 (10%错误率SNR, dB) 与合成对比 ===")
knees_real = {}
for sysk in SYSCONF:
    knees_real[sysk] = {}
    for lang in ["zh", "en"]:
        if sysk == "para8k" and lang != "zh": continue
        e5 = asr_table[sysk]["rb5"].get(lang, {}).get("mean")
        e0 = asr_table[sysk]["rb0"].get(lang, {}).get("mean")
        em5 = asr_table[sysk]["rbm5"].get(lang, {}).get("mean")
        if not all(v is not None for v in (e5, e0, em5)): continue
        kr = knee_interp([e5*100, e0*100, em5*100])
        # 合成膝点 (从 analysis_ext.knee)
        try:
            ks = syn_ext["knee"][sysk][lang]["snr_at_10pct_err"]
        except Exception:
            ks = None
        knees_real[sysk][lang] = {"real_snr_at_10pct": round(kr, 2) if kr is not None else None,
                                   "synthetic_snr_at_10pct": ks}
        print(f"  {sysk:8s} {lang}: 真实={kr if kr is None else round(kr,2)}dB 合成={ks}dB")
results["knee_real_vs_syn"] = knees_real

# ---------- 3c) 幻觉率 (CER>100%) ----------
print("=== 3c) 幻觉率 (错误率>100% 的句占比) ===")
halluc = {}
for sysk in SYSCONF:
    halluc[sysk] = {}
    for cond in ["rb0", "rbm5", "rn0"]:
        for lang in ["zh", "en"]:
            if sysk == "para8k" and lang != "zh": continue
            errs = []
            for rec in CORPUS:
                if rec["lang"] != lang: continue
                j = asr_data[sysk].get(f"{cond}/{rec['id']}")
                if j is None: continue
                hyp = j.get("text") or ""
                if j.get("refusal") or not hyp.strip(): continue
                errs.append(err_rate(rec["text"], hyp, lang))
            if errs:
                halluc[sysk][f"{cond}_{lang}"] = {
                    "rate_pct_gt100": round(float(np.mean([e > 1.0 for e in errs])), 3),
                    "n": len(errs)}
results["hallucination"] = halluc
for sysk, d in halluc.items():
    for k, v in d.items():
        if v["rate_pct_gt100"] > 0: print(f"  {sysk} {k}: {v['rate_pct_gt100']*100:.0f}% ({v['n']}句中)")

# ---------- 4) 级联翻译 BLEU + CAC ----------
print("=== 4) 级联翻译 (真实语音, oracle=真实转写直译) ===")
from sacrebleu.metrics import BLEU
_bleu_en = BLEU(tokenize="13a")
_bleu_zh = BLEU(tokenize="zh")

oracle = load_mt("d3_mt_oracle.jsonl")   # key=id
cascade = load_mt("d3_mt_cascade.jsonl") # key=cond/id

def ref_of(rec): return oracle[rec["id"]]["text"]

cascade_table = {}
for cond in CONDS:
    per_lang = {"zh": [], "en": []}
    for rec in CORPUS:
        key = f"{cond}/{rec['id']}"
        c = cascade.get(key); o = oracle.get(rec["id"])
        if not c or not o: continue
        hyp = c.get("text") or ""
        per_lang[rec["lang"]].append((hyp, ref_of(rec)))
    entry = {}
    for lang, pairs in per_lang.items():
        if not pairs: continue
        # 方向按目标语言: zh语句->英文译文用13a; en语句->中文译文用zh
        bl = _bleu_en if lang == "zh" else _bleu_zh
        bleu = bl.corpus_score([h for h, _ in pairs], [[r for _, r in pairs]])
        entry[lang] = {"bleu": round(bleu.score, 2)}
    cascade_table[cond] = entry
    print(f"  {cond}: zh BLEU={entry.get('zh',{}).get('bleu')} en BLEU={entry.get('en',{}).get('bleu')}")
results["cascade_bleu"] = cascade_table

# oracle 自身基线
ob = {}
for lang in ["zh", "en"]:
    pairs = [(oracle[r["id"]]["text"],) for r in CORPUS if r["lang"] == lang and r["id"] in oracle]
    refs = [ref_of(r) for r in CORPUS if r["lang"] == lang and r["id"] in oracle]
    bl = _bleu_en if lang == "zh" else _bleu_zh
    s = bl.corpus_score([p[0] for p in pairs], [[x] for x in refs])
    ob[lang] = round(s.score, 2)
results["oracle_self_bleu"] = ob  # 应该接近0或无意义——oracle就是参考本身; 此处改为: refmax不存在, oracle=参考生成器
print(f"  (oracle 即参考生成器, 自评无意义: {ob})")

# CAC: 级联BLEU损失 vs ASR错误率 (逐句)
print("=== 5) CAC 线性律 (真实语音, 逐句) ===")
cac = {}
for lang in ["zh", "en"]:
    xs, ys = [], []  # x=句级ASR错误率, y=句级BLEU损失(相对oracle=0)
    for cond in CONDS:
        for rec in CORPUS:
            if rec["lang"] != lang: continue
            a = asr_data["q31"].get(f"{cond}/{rec['id']}")
            c = cascade.get(f"{cond}/{rec['id']}")
            o = oracle.get(rec["id"])
            if not (a and c and o): continue
            hyp_asr = a.get("text") or ""
            if a.get("refusal") or not hyp_asr.strip():
                xerr = 1.0
            else:
                xerr = err_rate(rec["text"], hyp_asr, lang)
            # 句级 BLEU 损失用 sacrebleu 句子级
            hyp_mt = c.get("text") or ""
            if not hyp_mt.strip():
                yb = 0.0
            else:
                bl = (_bleu_en if lang == "zh" else _bleu_zh).sentence_score(hyp_mt, [o["text"]])
                yb = bl.score / 100.0
            xs.append(xerr); ys.append(yb)
    xs, ys = np.array(xs), np.array(ys)
    # 线性拟合 y = a + b*x  (BLEU分数 vs 错误率)
    k, b = np.polyfit(xs, ys, 1)
    r = np.corrcoef(xs, ys)[0, 1]
    # bootstrap CI for slope
    rng = np.random.RandomState(11)
    bs = []
    for _ in range(2000):
        idx = rng.choice(len(xs), len(xs))
        try: bs.append(np.polyfit(xs[idx], ys[idx], 1)[0])
        except Exception: pass
    cac[lang] = {"n": len(xs), "slope": round(float(k), 3),
                 "ci95": (round(float(np.percentile(bs,2.5)),3), round(float(np.percentile(bs,97.5)),3)),
                 "intercept": round(float(b), 3), "pearson_r": round(float(r), 3)}
    print(f"  {lang}: n={len(xs)} slope={k:.3f} r={r:.3f} intercept={b:.3f}")
results["cac_real"] = cac

# ---------- 5b) 条件级 CAC (与主实验同口径: 逐条件均值点回归) ----------
print("=== 5b) 条件级 CAC (BLEU损失 vs ASR错误率, 6条件) ===")
cac_cond = {}
for lang in ["zh", "en"]:
    xs, ys = [], []
    for cond in CONDS:
        # x: q31 平均错误率(排除拒答句以隔离识别错误本身? 主实验用全部含拒答计100%——含拒答)
        errs = []
        for rec in CORPUS:
            if rec["lang"] != lang: continue
            a = asr_data["q31"].get(f"{cond}/{rec['id']}")
            if a is None: continue
            hyp = a.get("text") or ""
            errs.append(1.0 if (a.get("refusal") or not hyp.strip()) else err_rate(rec["text"], hyp, lang))
        if not errs: continue
        x = float(np.mean(errs)) * 100
        y = cascade_table[cond].get(lang, {}).get("bleu")
        base = cascade_table["clean_r"].get(lang, {}).get("bleu")
        if y is None or base is None: continue
        xs.append(x); ys.append(base - y)  # BLEU 损失
    if len(xs) >= 4:
        k, b = np.polyfit(xs, ys, 1)
        r = np.corrcoef(xs, ys)[0, 1]
        cac_cond[lang] = {"n_conditions": len(xs), "slope_bleu_loss_per_cer_pct": round(float(k), 3),
                          "pearson_r": round(float(r), 3), "intercept": round(float(b), 3),
                          "x_cer_pct": [round(v,1) for v in xs], "y_bleu_loss": [round(v,1) for v in ys]}
        print(f"  {lang}: slope={k:.3f} r={r:.3f} (合成参考: 0.47-0.66)")
results["cac_condition_level"] = cac_cond

# ---------- 6) E2E LT vs 级联 (同子集) ----------
print("=== 6) E2E (LT) vs 级联 同子集 ===")
lt = load_mt("d3_mt_e2e_lt.jsonl")
lt_conds = [c for c in ["clean_r", "revr", "rb0"] if any(k.startswith(c+"/") for k in lt)]
e2e_cmp = {}
for cond in lt_conds:
    for lang in ["zh", "en"]:
        hyps_lt, hyps_c, refs = [], [], []
        for rec in CORPUS:
            if rec["lang"] != lang: continue
            l = lt.get(f"{cond}/{rec['id']}"); c = cascade.get(f"{cond}/{rec['id']}"); o = oracle.get(rec["id"])
            if not (l and c and o): continue
            hyps_lt.append(l.get("text") or "")
            hyps_c.append(c.get("text") or "")
            refs.append(o["text"])
        if len(refs) < 5: continue
        bl = _bleu_en if lang == "zh" else _bleu_zh
        s_lt = bl.corpus_score(hyps_lt, [refs]).score
        s_c = bl.corpus_score(hyps_c, [refs]).score
        e2e_cmp[f"{cond}_{lang}"] = {"e2e_lt": round(s_lt, 2), "cascade_q31": round(s_c, 2),
                                     "n": len(refs)}
        print(f"  {cond} {lang}: LT={s_lt:.1f} 级联={s_c:.1f} (n={len(refs)})")
results["e2e_vs_cascade"] = e2e_cmp

# ---------- 7) 声学测量合并 ----------
try:
    ac = json.load(open(os.path.join(RES, "d3_audio_report.json")))
    results["acoustic"] = {"rir_selected": ac.get("rir"), "mit_survey_stats": ac.get("mit_survey_stats"),
                            "stoi_mean": ac.get("stoi_mean")}
except Exception as e:
    print("声学报告缺失:", e)

# ---------- 8) 汇总 ----------
with open(os.path.join(RES, "d3_analysis.json"), "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=1)
print("\n已写入 d3_analysis.json")
