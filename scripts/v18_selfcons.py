#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.8 review fix #3: GLM reference self-consistency + noise-calibrated Monte Carlo.

- 5 versions of the 150-sentence GLM reference translation
  (r1 = released refreal in glm_tasks.jsonl, r2-r5 = reruns in glm_selfcons.jsonl,
   identical batch protocol, gateway default sampling, no seed control)
- corpus-level pairwise BLEU(g_i, g_j), 10 pairs, per direction (zh2en: 13a,
  en2zh: zh) -> mean/sd  = two-sided generation noise sigma_pair
  (this is exactly the noise shape of a Table 6 GLM|GLM cell: one sampled
  version plays candidate, the other plays reference)
- corpus-level BLEU(g_i, oracle fixed ref) for the 5 versions -> sd = one-sided
  noise sigma_single (noise of a GLM|oracle cell, mt side only)
- Monte Carlo (2000 draws): perturb the nine-condition cells with the measured
  sigma, refit slopes -> slope CIs for GLM|GLM and GLM|oracle, and the
  vendor-minus-GLM gap CI
- ensemble: per-cell BLEU averaged over the 5 reference versions -> noise-reduced
  slope refit (the 'average over repeated generations' variant)

Run AFTER glm_selfcons.mjs completed all 600 reruns.
Writes analysis_v18_selfcons.json.
"""
import json, os, sys, random, statistics, itertools

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sacrebleu.metrics import BLEU
_bleu_en, _bleu_zh = BLEU(tokenize="13a"), BLEU(tokenize="zh")

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
A17 = json.load(open(os.path.join(R, "analysis_v17_glm9.json")))
MTREAL_LOG = os.path.join(R, "glm_tasks.jsonl")
SELFCONS_LOG = os.path.join(R, "glm_selfcons.jsonl")
ORACLE_LOG = os.path.join(R, "d3_mt_oracle.jsonl")
N_MC = 2000
CONDS9 = ["clean_r", "revr", "rb10", "rb5", "rb25", "rb0", "rbm25", "rbm5", "rn0"]

# ---------- load the five reference versions ----------
r1 = {}
for line in open(MTREAL_LOG):
    d = json.loads(line)
    if d.get("ok") and d.get("key", "").startswith("refreal/") and d.get("kind") == "reference":
        r1[d["key"].split("/", 1)[1]] = d["text"]  # last record wins (v17 convention)
versions = {"r1": r1}
for rnd in (2, 3, 4, 5):
    v = {}
    for line in open(SELFCONS_LOG):
        d = json.loads(line)
        if d.get("ok") and d.get("key", "").startswith(f"sc{rnd}/"):
            v[d["key"].split("/", 1)[1]] = d["text"]
    versions[f"r{rnd}"] = v
for name, v in versions.items():
    assert len(v) == 150, f"{name} has {len(v)} sentences"
sids = sorted(r1)
zh_sids = [s for s in sids if s.startswith("rz")]
en_sids = [s for s in sids if s.startswith("re")]
assert len(zh_sids) == 75 and len(en_sids) == 75

oracle = {}
for line in open(ORACLE_LOG):
    d = json.loads(line)
    if d.get("ok"):
        oracle[d["key"]] = d["text"]
assert len(oracle) == 150

def cbleu(va, vb, direction):
    """corpus BLEU of version va (candidate) vs vb (reference), one direction."""
    ds = zh_sids if direction == "zh2en" else en_sids
    b = _bleu_en if direction == "zh2en" else _bleu_zh
    return round(b.corpus_score([va[s] for s in ds], [[vb[s] for s in ds]]).score, 2)

DIRS = ("zh2en", "en2zh")

# ---------- 1. pairwise self-consistency (two-sided) ----------
pairwise = {}
for d in DIRS:
    pv = {f"{a}-{b}": cbleu(versions[a], versions[b], d)
          for a, b in itertools.combinations(versions, 2)}
    vs = list(pv.values())
    pairwise[d] = {"pairs": pv, "n_pairs": len(vs), "mean": round(statistics.mean(vs), 2),
                   "sd": round(statistics.stdev(vs), 3), "min": min(vs), "max": max(vs)}
# macro average (Table 6 cell metric) noise, measured on the same 10 pairs
macro_pv = {k: round((pairwise["zh2en"]["pairs"][k] + pairwise["en2zh"]["pairs"][k]) / 2, 2)
            for k in pairwise["zh2en"]["pairs"]}
mvs = list(macro_pv.values())
pairwise["macro"] = {"pairs": macro_pv, "n_pairs": len(mvs), "mean": round(statistics.mean(mvs), 2),
                     "sd": round(statistics.stdev(mvs), 3), "min": min(mvs), "max": max(mvs)}

# ---------- 2. one-sided noise vs fixed oracle reference ----------
one_sided = {}
for d in DIRS:
    sv = {n: cbleu(versions[n], oracle, d) for n in versions}
    vs = list(sv.values())
    one_sided[d] = {"scores": sv, "mean": round(statistics.mean(vs), 2),
                    "sd": round(statistics.stdev(vs), 3)}
macro_sv = {n: round((one_sided["zh2en"]["scores"][n] + one_sided["en2zh"]["scores"][n]) / 2, 2)
            for n in versions}
svs = list(macro_sv.values())
one_sided["macro"] = {"scores": macro_sv, "mean": round(statistics.mean(svs), 2),
                      "sd": round(statistics.stdev(svs), 3)}

# ---------- 3. Monte Carlo with measured sigma ----------
def ols(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / sxx

def q(vals, p):
    s = sorted(vals)
    return round(s[int(p * (len(s) - 1))], 3)

matrix = A17["backend_matrix_9"]
conds8 = [c for c in CONDS9 if c != "clean_r"]
rng = random.Random(42)

def mc_row(cellkey, sigmas, slopename):
    """perturb the 9 cells (incl. clean baseline) of one Table-6 row, refit slopes."""
    out = {}
    for lang, kl in (("zh", "zh2en"), ("en", "en2zh")):
        sigma = sigmas[kl]["sd"]
        x8 = A17[slopename][lang]["x"]
        clean_b = matrix["clean_r"][cellkey][kl]
        slopes = []
        for _ in range(N_MC):
            cb = clean_b + rng.gauss(0, sigma)
            ys = [max(0.0, cb - (matrix[c][cellkey][kl] + rng.gauss(0, sigma)))
                  for c in conds8]
            slopes.append(ols(x8, ys))
        out[lang] = {"point": A17[slopename][lang]["slope"],
                     "ci95": [q(slopes, 0.025), q(slopes, 0.975)],
                     "mc_mean": round(statistics.mean(slopes), 3)}
    return out

mc = {
    "glm_vs_glmref": mc_row("glm_vs_glmref", pairwise, "slope_glm_9cond_glmref_noclean"),
    "glm_vs_oracle": mc_row("glm_vs_oracle", one_sided, "slope_glm_9cond_oracleref_noclean"),
}

# vendor (gummy|oracle, deterministic backend) minus GLM|GLM gap
gap = {}
for lang, kl in (("zh", "zh2en"), ("en", "en2zh")):
    sigma = pairwise[kl]["sd"]
    gummy_s = A17["slope_gummy_9cond_oracleref_noclean"][lang]["slope"]
    x8 = A17["slope_glm_9cond_glmref_noclean"][lang]["x"]
    clean_b = matrix["clean_r"]["glm_vs_glmref"][kl]
    gaps, pos = [], 0
    for _ in range(N_MC):
        cb = clean_b + rng.gauss(0, sigma)
        ys = [max(0.0, cb - (matrix[c]["glm_vs_glmref"][kl] + rng.gauss(0, sigma)))
              for c in conds8]
        g = gummy_s - ols(x8, ys)
        gaps.append(g)
        if g > 0:
            pos += 1
    gap[lang] = {"point": round(gummy_s - A17["slope_glm_9cond_glmref_noclean"][lang]["slope"], 3),
                 "ci95": [q(gaps, 0.025), q(gaps, 0.975)],
                 "frac_positive": round(pos / N_MC, 3)}
mc["gap_vendor_minus_glm_glmref"] = gap

# ---------- 4. ensemble over the 5 reference versions ----------
# reload mtreal (last-ok convention) exactly like v17_glm9conds.py
mtreal = {}
for line in open(MTREAL_LOG):
    d = json.loads(line)
    if d.get("ok") and d.get("key", "").startswith("mtreal/"):
        _, cond, sid = d["key"].split("/")
        mtreal[(cond, sid)] = d["text"]
q31last = {}
for line in open(os.path.join(R, "d3_asr_q31.jsonl")):
    d = json.loads(line)
    k = d.get("key", "")
    if k and "/" in k:
        cond, sid = k.split("/", 1)
        if cond in CONDS9 and d.get("ok"):
            q31last[k] = (d.get("text") or "")

def cell_bleu_ens(cond, refver, direction):
    """corpus BLEU of mtreal(cond) vs one reference version, one direction."""
    ds = zh_sids if direction == "zh2en" else en_sids
    h, r = [], []
    for k in q31last:
        c, sid = k.split("/", 1)
        if c == cond and sid in refver and (sid.startswith("rz") if direction == "zh2en" else sid.startswith("re")):
            h.append(mtreal.get((cond, sid), ""))
            r.append(refver[sid])
    if not h:
        return None
    b = _bleu_en if direction == "zh2en" else _bleu_zh
    return b.corpus_score(h, [r]).score

ens = {}
for lang, kl in (("zh", "zh2en"), ("en", "en2zh")):
    per_cond_mean = {}
    for cond in CONDS9:
        vals = [cell_bleu_ens(cond, versions[n], kl) for n in versions]
        per_cond_mean[cond] = round(statistics.mean(vals), 2)
    clean_b = per_cond_mean["clean_r"]
    xs = A17["slope_glm_9cond_glmref_noclean"][lang]["x"]
    ys = [max(0.0, clean_b - per_cond_mean[c]) for c in conds8]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b1 = sxy / sxx
    r = (sxy / (sxx * sum((y - my) ** 2 for y in ys)) ** 0.5)
    ens[lang] = {"per_cond_bleu_ref5mean": per_cond_mean, "slope": round(b1, 3),
                 "r": round(r, 3)}

RESULT = {
    "n_versions": 5, "n_sentences": 150,
    "protocol": "batch 8-sent/call, gateway default sampling, thinking disabled, no seed control",
    "pairwise_selfcons": pairwise,
    "one_sided_vs_oracle": one_sided,
    "mc": mc,
    "ensemble_ref_mean": ens,
}

out = os.path.join(R, "analysis_v18_selfcons.json")
json.dump(RESULT, open(out, "w"), indent=1, ensure_ascii=False)

print("=== pairwise corpus self-consistency BLEU (10 pairs) ===")
for d in DIRS + ("macro",):
    p = pairwise[d]
    print(f"  {d:6s}: mean {p['mean']:6.2f}  sd {p['sd']:5.3f}  range [{p['min']}, {p['max']}]")
print("=== one-sided vs fixed oracle ref (5 versions) ===")
for d in DIRS + ("macro",):
    s = one_sided[d]
    print(f"  {d:6s}: mean {s['mean']:6.2f}  sd {s['sd']:5.3f}")
print("=== MC slope CIs (measured sigma) ===")
for row in ("glm_vs_glmref", "glm_vs_oracle"):
    for lang in ("zh", "en"):
        c = mc[row][lang]
        print(f"  {row} {lang}: point {c['point']}  CI95 [{c['ci95'][0]}, {c['ci95'][1]}]")
for lang in ("zh", "en"):
    g = gap[lang]
    print(f"  vendor-GLM gap {lang}: point {g['point']}  CI95 [{g['ci95'][0]}, {g['ci95'][1]}]  P(gap>0)={g['frac_positive']}")
print("=== ensemble (5-reference-mean) slopes ===")
for lang in ("zh", "en"):
    print(f"  {lang}: slope {ens[lang]['slope']}  r {ens[lang]['r']}  (r1-only was {A17['slope_glm_9cond_glmref_noclean'][lang]['slope']})")
print(f"\nwrote {out}")
