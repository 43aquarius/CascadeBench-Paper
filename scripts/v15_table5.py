#!/usr/bin/env python3
"""v1.5 analysis part 1: Table 5 under three references (primary/oracle/GLM)
+ paired bootstrap omni vs LLM-frontend cascades at 0 dB, synthetic sweep subset.

Conventions (must reproduce v1.3 Table 5 first, then extend with GLM column):
- subset: 144-sentence sweep (sweep_ids.json)
- cascades at n0: conditional on non-empty frontend output (empty hyp dropped)
- omni: its quota-limited coverage; LT: its session coverage
- rel loss per reference = (clean_bleu_ref - n0_bleu_ref) / clean_bleu_ref
"""
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_ROOT = _os.path.dirname(_HERE)              # repository root
_PAPER = _os.path.join(_ROOT, "paper", "latex")
_FIG = _os.path.join(_ROOT, "figures")
import json, os, sys, random

ROOT = _ROOT
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import metrics as M  # normalize/err_rate/BLEU objects live here

R = os.path.join(ROOT, "results")
SWEEP = set(json.load(open(os.path.join(ROOT, "corpus", "sweep_ids.json"))))

def load(fn):
    out = {}
    for line in open(os.path.join(R, fn)):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        if not d.get("ok"):
            continue
        out[d["key"]] = d
    return out

# ---- references on clean transcripts (synthetic corpus, all 480) ----
refmax = load("mt_refmax.jsonl")            # primary: Qwen3.8-Max
oracle = load("mt_oracle.jsonl")            # oracle: qwen-mt-uni (cascade engine)
glmref = {}
for k, d in load("glm_tasks.jsonl").items():
    if d.get("kind") == "reference" and k.startswith("refsynth/"):
        glmref[k.split("/", 1)[1]] = d      # GLM reference translations
REFS = {"primary": {k: v["text"] for k, v in refmax.items()},
        "oracle":  {k: v["text"] for k, v in oracle.items()},
        "glm":     {k: v["text"] for k, v in glmref.items()}}
for name, r in REFS.items():
    assert len(r) == 480, (name, len(r))

# ---- translation path logs ----
mt_cascade = load("mt_cascade.jsonl")               # keys: fe/cond/sid  (fe q31, para16k)
mt_q3 = load("ext_mt_cascade_q3main.jsonl")         # keys: q3/cond/sid
mt_omni = load("mt_e2e_omni.jsonl")                 # keys: cond/sid
mt_lt = load("mt_e2e_lt.jsonl")                     # keys: cond/sid

def cascade_pairs(fe, cond):
    src = mt_q3 if fe == "q3" else mt_cascade
    pref = f"{fe}/{cond}/"
    pairs = [(k.split("/")[-1], d["text"]) for k, d in src.items()
             if k.startswith(pref) and k.split("/")[-1] in SWEEP]
    return pairs

def e2e_pairs(log, cond):
    pref = f"{cond}/"
    return [(k.split("/")[-1], d["text"]) for k, d in log.items()
            if k.startswith(pref) and k.split("/")[-1] in SWEEP]

def bleu_bidir_fast(pairs, refmap, keep_empty=False):
    """macro-averaged BLEU only (no chrF) - chrf was the bottleneck."""
    corpus = M.CORPUS
    h_zh2en, r_zh2en, h_en2zh, r_en2zh = [], [], [], []
    for sid, hyp in pairs:
        rec = corpus.get(sid)
        ref = refmap.get(sid)
        if not rec or not ref:
            continue
        if not hyp and not keep_empty:
            continue
        if rec["lang"] == "zh":
            h_zh2en.append(hyp or ""); r_zh2en.append(ref)
        else:
            h_en2zh.append(hyp or ""); r_en2zh.append(ref)
    vals = []
    if h_zh2en:
        vals.append(M.bleu(h_zh2en, r_zh2en, "en"))
    if h_en2zh:
        vals.append(M.bleu(h_en2zh, r_en2zh, "zh"))
    return {"bleu": round(sum(vals) / len(vals), 2) if vals else None,
            "n": len(h_zh2en) + len(h_en2zh)}

def score(pairs, refname, conditional=True):
    refmap = REFS[refname]
    if conditional:
        pairs = [(s, h) for s, h in pairs if h.strip()]
    return bleu_bidir_fast(pairs, refmap, keep_empty=not conditional)

PATHS = {
    "cascade_q31":    ("q31", lambda c: cascade_pairs("q31", c)),
    "cascade_para16k": ("para16k", lambda c: cascade_pairs("para16k", c)),
    "cascade_q3":     ("q3", lambda c: cascade_pairs("q3", c)),
    "e2e_omni":       ("omni", lambda c: e2e_pairs(mt_omni, c)),
    "e2e_lt":         ("lt", lambda c: e2e_pairs(mt_lt, c)),
}

print("=" * 70)
print("TABLE 5 (v1.5): clean & n0 BLEU under three references, sweep subset")
print("=" * 70)
out = {}
for name, (label, get) in PATHS.items():
    rec = {}
    for ref in ("primary", "oracle", "glm"):
        cl = score(get("clean"), ref, conditional=True)
        n0c = score(get("n0"), ref, conditional=True)     # conditional
        n0i = score(get("n0"), ref, conditional=False)    # refusal-inclusive
        rl = (cl["bleu"] - n0c["bleu"]) / cl["bleu"] * 100 if cl["bleu"] else None
        rec[ref] = {"clean": cl, "n0_cond": n0c, "n0_incl": n0i,
                    "rel_loss_pct": round(rl, 1)}
    out[name] = rec
    p, o, g = rec["primary"], rec["oracle"], rec["glm"]
    print(f"{name:16s} clean(p/o/g) {p['clean']['bleu']:5.1f}/{o['clean']['bleu']:5.1f}/{g['clean']['bleu']:5.1f}"
          f"  n0 {p['n0_cond']['bleu']:5.1f}/{o['n0_cond']['bleu']:5.1f}/{g['n0_cond']['bleu']:5.1f}"
          f"  n0incl {p['n0_incl']['bleu']:5.1f}"
          f"  relloss {p['rel_loss_pct']:4.1f}/{o['rel_loss_pct']:4.1f}/{g['rel_loss_pct']:4.1f}"
          f"  n {p['clean']['n']}/{p['n0_cond']['n']}")

print()
print("v1.3 expected: q31 53.9/44.1/oracle68.3/18% | p16 51.5/15.8/17.4/69% |"
      " q3 53.2/43.0/66.7/19% | omni 68.1/45.5/34.4/33% | lt 59.8/50.4/44.9/16%")

# ---- paired bootstrap: omni vs cascades on common subset at n0, 3 refs ----
print()
print("=" * 70)
print("PAIRED BOOTSTRAP at n0 (common subset), omni - cascade BLEU diff, 3 refs")
print("=" * 70)

def corpus_bleu_on(sids, hyp_a, refmap_a):
    """BLEU of path a on given sid multiset (with ref of same name)."""
    pairs = [(s, hyp_a[s]) for s in sids if s in hyp_a]
    return bleu_bidir_fast(pairs, refmap_a, keep_empty=True)

def paired_boot(hyp_a, hyp_b, refname, n_boot=300, seed=42):
    """hyp_a, hyp_b: dict sid->text on the SAME sid set; returns diff CI."""
    common = sorted(set(hyp_a) & set(hyp_b))
    refmap = REFS[refname]
    rng = random.Random(seed)
    diffs = []
    for _ in range(n_boot):
        sids = [common[rng.randrange(len(common))] for _ in range(len(common))]
        ba = corpus_bleu_on(sids, hyp_a, refmap)
        bb = corpus_bleu_on(sids, hyp_b, refmap)
        diffs.append(ba["bleu"] - bb["bleu"])
    diffs.sort()
    point = bleu_bidir_fast([(s, hyp_a[s]) for s in common], refmap, keep_empty=True)["bleu"] - \
            bleu_bidir_fast([(s, hyp_b[s]) for s in common], refmap, keep_empty=True)["bleu"]
    lo, hi = diffs[int(0.025 * n_boot)], diffs[int(0.975 * n_boot) - 1]
    return {"n": len(common), "diff": round(point, 2), "ci95": [round(lo, 1), round(hi, 1)]}

def hyp_map(fe, cond, conditional=True):
    src = mt_q3 if fe == "q3" else mt_cascade
    pref = f"{fe}/{cond}/"
    out = {}
    for k, d in src.items():
        sid = k.split("/")[-1]
        if k.startswith(pref) and sid in SWEEP:
            if conditional and not d["text"].strip():
                continue
            out[sid] = d["text"]
    return out

def hyp_map_e2e(log, cond):
    pref = f"{cond}/"
    return {k.split("/")[-1]: d["text"] for k, d in log.items()
            if k.startswith(pref) and k.split("/")[-1] in SWEEP}

omni_n0 = hyp_map_e2e(mt_omni, "n0")
pb_out = {}
for fe in ("q31", "q3"):
    cas = hyp_map(fe, "n0")
    common = sorted(set(omni_n0) & set(cas))
    rec = {"n_common": len(common)}
    for ref in ("primary", "oracle", "glm"):
        rec[ref] = paired_boot(omni_n0, cas, ref)
    pb_out[f"omni_vs_{fe}"] = rec
    print(f"omni vs {fe} (n={len(common)}):", {r: rec[r] for r in ('primary','oracle','glm')})

json.dump({"table5_three_ref": out, "paired_bootstrap_n0": pb_out},
          open(os.path.join(R, "analysis_v15_table5.json"), "w"), indent=1, ensure_ascii=False)
print()
print("saved analysis_v15_table5.json")

# ---- paired bootstrap of RELATIVE-LOSS difference (omni - cascade) ----
# resample common sids; per path rel loss = (clean_bleu - n0_bleu)/clean_bleu
print()
print("=" * 70)
print("PAIRED BOOTSTRAP of RELATIVE-LOSS difference at n0 (omni - cascade)")
print("=" * 70)

def relloss_boot(hyp_a_clean, hyp_a_n0, hyp_b_clean, hyp_b_n0, refname, n_boot=300, seed=42):
    common = sorted(set(hyp_a_clean) & set(hyp_a_n0) & set(hyp_b_clean) & set(hyp_b_n0))
    refmap = REFS[refname]
    rng = random.Random(seed)
    diffs = []
    for _ in range(n_boot):
        sids = [common[rng.randrange(len(common))] for _ in range(len(common))]
        ca = bleu_bidir_fast([(s, hyp_a_clean[s]) for s in sids], refmap, keep_empty=True)["bleu"]
        na = bleu_bidir_fast([(s, hyp_a_n0[s]) for s in sids], refmap, keep_empty=True)["bleu"]
        cb = bleu_bidir_fast([(s, hyp_b_clean[s]) for s in sids], refmap, keep_empty=True)["bleu"]
        nb = bleu_bidir_fast([(s, hyp_b_n0[s]) for s in sids], refmap, keep_empty=True)["bleu"]
        if ca <= 0 or cb <= 0:
            continue
        diffs.append((ca - na) / ca * 100 - (cb - nb) / cb * 100)
    diffs.sort()
    ca = bleu_bidir_fast([(s, hyp_a_clean[s]) for s in common], refmap, keep_empty=True)["bleu"]
    na = bleu_bidir_fast([(s, hyp_a_n0[s]) for s in common], refmap, keep_empty=True)["bleu"]
    cb = bleu_bidir_fast([(s, hyp_b_clean[s]) for s in common], refmap, keep_empty=True)["bleu"]
    nb = bleu_bidir_fast([(s, hyp_b_n0[s]) for s in common], refmap, keep_empty=True)["bleu"]
    point = (ca - na) / ca * 100 - (cb - nb) / cb * 100
    lo, hi = diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs)) - 1]
    return {"n": len(common), "diff_pct": round(point, 1),
            "ci95": [round(lo, 1), round(hi, 1)]}

omni_clean = hyp_map_e2e(mt_omni, "clean")
rl_out = {}
for fe in ("q31", "q3"):
    cas_n0 = hyp_map(fe, "n0")
    cas_cl = hyp_map(fe, "clean")
    rec = {}
    for ref in ("primary", "oracle", "glm"):
        rec[ref] = relloss_boot(omni_clean, omni_n0, cas_cl, cas_n0, ref)
    rl_out[f"omni_vs_{fe}"] = rec
    print(f"rel-loss diff omni-{fe}:", rec)

d5 = json.load(open(os.path.join(R, "analysis_v15_table5.json")))
d5["relloss_bootstrap_n0"] = rl_out
json.dump(d5, open(os.path.join(R, "analysis_v15_table5.json"), "w"), indent=1, ensure_ascii=False)
print("updated analysis_v15_table5.json")
