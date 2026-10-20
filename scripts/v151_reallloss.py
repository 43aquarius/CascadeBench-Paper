#!/usr/bin/env python3
"""P3 (用户意见第3条): 真实语音 E2E vs 级联 相对损失的参考敏感性与配对 bootstrap
- 路径 A: LiveTranslate E2E (clean_r -> rb0)
- 路径 B: 级联 Qwen-Audio + gummy (clean_r -> rb0)
- 参考: oracle (gummy 译人工转写, 同引擎) / glm (GLM 译人工转写, 家族不相交)
- 口径: 与 d3_analysis.py §6 完全一致 (全句子集, 含空译文, 双向 corpus BLEU 宏平均)
- 配对 bootstrap: 句级重采样 1000 次 (methods §3.8 口径), seed=42,
  每次重采样内重算两条路径的 (clean-rb0)/clean 相对损失, 差值分布取 2.5/97.5 分位
输出: results/analysis_v151_reallloss.json
"""
import json, os, sys, random

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
import metrics as M

RES = os.path.join(_ROOT, "results")
D3D = os.path.join(_ROOT, "corpus")
OUT = os.path.join(RES, "analysis_v151_reallloss.json")

# ---------- 语料 ----------
CORPUS = {r["id"]: r for r in (json.loads(l) for l in open(f"{D3D}/d3_corpus.jsonl"))}

def load_mt(fname):
    out = {}
    for line in open(os.path.join(RES, fname)):
        j = json.loads(line)
        if j.get("ok"):
            out[j["key"]] = j
    return out

# ---------- 参考 ----------
oracle = {k: d["text"] for k, d in load_mt("d3_mt_oracle.jsonl").items()}          # 同引擎
glm_tasks = load_mt("glm_tasks.jsonl")
glmref = {k.split("/", 1)[1]: d["text"] for k, d in glm_tasks.items()
          if d.get("kind") == "reference" and k.startswith("refreal/")}            # 家族不相交
REFS = {"oracle": oracle, "glm": glmref}
assert len(oracle) == 150 and len(glmref) == 150, (len(oracle), len(glmref))

# ---------- 路径日志 ----------
lt = load_mt("d3_mt_e2e_lt.jsonl")
cas = load_mt("d3_mt_cascade.jsonl")

def hyp_map(log, cond):
    pref = f"{cond}/"
    return {k.split("/", 1)[1]: (d.get("text") or "") for k, d in log.items()
            if k.startswith(pref)}

lt_cl, lt_n0 = hyp_map(lt, "clean_r"), hyp_map(lt, "rb0")
ca_cl, ca_n0 = hyp_map(cas, "clean_r"), hyp_map(cas, "rb0")

# ---------- 共同子集: 四个假设 + 两个参考都存在的句子 ----------
common = sorted(set(lt_cl) & set(lt_n0) & set(ca_cl) & set(ca_n0) & set(oracle) & set(glmref))
n_zh = sum(1 for s in common if CORPUS[s]["lang"] == "zh")
n_en = len(common) - n_zh
print(f"common subset: n={len(common)} (zh {n_zh}, en {n_en})")

def bleu_bidir(sids, hyps, refmap):
    """双向 corpus BLEU 宏平均 (与 d3_analysis §6 / v15_table5 bleu_bidir_fast 同口径, 含空译文)"""
    h_zh2en, r_zh2en, h_en2zh, r_en2zh = [], [], [], []
    for s in sids:
        rec = CORPUS[s]
        hyp = hyps[s]
        ref = refmap[s]
        if rec["lang"] == "zh":
            h_zh2en.append(hyp); r_zh2en.append(ref)
        else:
            h_en2zh.append(hyp); r_en2zh.append(ref)
    vals = []
    if h_zh2en:
        vals.append(M.bleu(h_zh2en, r_zh2en, "en"))
    if h_en2zh:
        vals.append(M.bleu(h_en2zh, r_en2zh, "zh"))
    return round(sum(vals) / len(vals), 2) if vals else None

def relloss(sids, hyp_cl, hyp_n0, refmap):
    c = bleu_bidir(sids, hyp_cl, refmap)
    n = bleu_bidir(sids, hyp_n0, refmap)
    rl = (c - n) / c * 100 if c else None
    return c, n, rl

# ---------- 点估计 (两参考) ----------
point = {}
for refname, refmap in REFS.items():
    lt_c, lt_n, lt_rl = relloss(common, lt_cl, lt_n0, refmap)
    ca_c, ca_n, ca_rl = relloss(common, ca_cl, ca_n0, refmap)
    point[refname] = {
        "lt_clean": lt_c, "lt_rb0": lt_n, "lt_relloss_pct": round(lt_rl, 1),
        "cas_clean": ca_c, "cas_rb0": ca_n, "cas_relloss_pct": round(ca_rl, 1),
        "diff_pct": round(lt_rl - ca_rl, 1),
    }
    print(f"[{refname:6s}] LT {lt_c:.1f}->{lt_n:.1f} relloss {lt_rl:5.1f}% | "
          f"cascade {ca_c:.1f}->{ca_n:.1f} relloss {ca_rl:5.1f}% | diff {lt_rl-ca_rl:+.1f}")

# ---------- 配对 bootstrap (差值 = LT相对损失 - 级联相对损失) ----------
def paired_boot(refname, n_boot=1000, seed=42):
    refmap = REFS[refname]
    rng = random.Random(seed)
    diffs = []
    for _ in range(n_boot):
        sids = [common[rng.randrange(len(common))] for _ in range(len(common))]
        _, _, a = relloss(sids, lt_cl, lt_n0, refmap)
        _, _, b = relloss(sids, ca_cl, ca_n0, refmap)
        if a is None or b is None:
            continue
        diffs.append(a - b)
    diffs.sort()
    lo = diffs[int(0.025 * len(diffs))]
    hi = diffs[int(0.975 * len(diffs)) - 1]
    return {"n_boot": len(diffs), "diff_ci95": [round(lo, 1), round(hi, 1)],
            "crosses_zero": (lo < 0 < hi)}

boot = {}
for refname in REFS:
    boot[refname] = paired_boot(refname)
    b = boot[refname]
    print(f"[{refname:6s}] paired bootstrap diff CI95 = [{b['diff_ci95'][0]:+.1f}, {b['diff_ci95'][1]:+.1f}]"
          f"  crosses_zero={b['crosses_zero']}")

json.dump({"common_n": len(common), "n_zh": n_zh, "n_en": n_en,
           "point_estimates": point, "paired_bootstrap": boot},
          open(OUT, "w"), indent=1, ensure_ascii=False)
print("\nwritten:", OUT)
