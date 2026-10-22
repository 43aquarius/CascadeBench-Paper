#!/usr/bin/env python3
"""v1.7 analysis: GLM nine-condition backend re-translation (upgrade item 2).
- nine-condition backend matrix: 2 backends (gummy/qwen-mt-uni vs GLM) x 2 refs (oracle/GLM) x 9 real conds
- n alignment: q31-transcribed list is authoritative (150/cond); GLM missing entries -> hyp='' (same rule
  as gummy cascade: empty ASR output = broken cascade = empty translation)
- GLM nine-condition pass-through slopes (with clean / no clean), directly comparable to
  gummy slopes 0.429/0.721 (v1.5 slope_new9_noclean)
- per-cond paired backend delta (both under GLM ref and under oracle ref)
Run AFTER glm_translate_v17.mjs finishes all 727 tasks.
"""
import metrics as M
from sacrebleu.metrics import BLEU
_bleu_en, _bleu_zh = BLEU(tokenize="13a"), BLEU(tokenize="zh")

D3C = {json.loads(l)["id"]: json.loads(l)
       for l in open(os.path.join(_ROOT, "corpus", "d3_corpus.jsonl"))}

CONDS9 = ["clean_r", "revr", "rb10", "rb5", "rb25", "rb0", "rbm25", "rbm5", "rn0"]


def load(fn):
    out = {}
    for line in open(os.path.join(R, fn)):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        if d.get("ok"):
            out[d["key"]] = d
    return out


def bleu_d3(pairs, refmap, keep_empty=True):
    h_zh2en, r_zh2en, h_en2zh, r_en2zh = [], [], [], []
    for sid, hyp in pairs:
        rec = D3C.get(sid)
        ref = refmap.get(sid)
        if not rec or ref is None:
            continue
        if not hyp and not keep_empty:
            continue
        if rec["lang"] == "zh":
            h_zh2en.append(hyp or ""); r_zh2en.append(ref)
        else:
            h_en2zh.append(hyp or ""); r_en2zh.append(ref)
    out = {}
    for nm, (h, r, b) in {"zh2en": (h_zh2en, r_zh2en, _bleu_en),
                          "en2zh": (h_en2zh, r_en2zh, _bleu_zh)}.items():
        out[nm] = round(b.corpus_score(h, [r]).score, 2) if h else None
    vals = [v for v in out.values() if v is not None]
    out["bleu"] = round(sum(vals) / len(vals), 2) if vals else None
    out["n"] = len(h_zh2en) + len(h_en2zh)
    return out


# ---------- inputs ----------
d3mt = load("d3_mt_cascade.jsonl")            # gummy backend, key cond/sid
d3orc = {k: v["text"] for k, v in load("d3_mt_oracle.jsonl").items()}
mtreal, refreal = {}, {}
for k, d in load("glm_tasks.jsonl").items():
    if k.startswith("mtreal/"):
        _, cond, sid = k.split("/")
        mtreal[(cond, sid)] = d["text"]
    elif k.startswith("refreal/"):
        refreal[k.split("/", 1)[1]] = d["text"]

# q31 authoritative transcription list (last ok record wins)
q31last = {}
for line in open(os.path.join(R, "d3_asr_q31.jsonl")):
    d = json.loads(line)
    k = d.get("key", "")
    if not k or "/" not in k:
        continue
    cond, sid = k.split("/", 1)
    if cond in CONDS9 and d.get("ok"):
        q31last[k] = (d.get("text") or "")
nq31 = {c: sum(1 for k in q31last if k.split("/", 1)[0] == c) for c in CONDS9}

# q31 per-cond/lang mean error (x axis for slopes), same as v15 asr_err
_q31e = {}
for k, txt in q31last.items():
    cond, sid = k.split("/", 1)
    rec = D3C.get(sid)
    if rec:
        _q31e.setdefault((cond, rec["lang"]), []).append(
            M.err_rate(rec["text"], txt, rec["lang"]))
q31err = {f"{c}/{l}": round(sum(v) / len(v) * 100, 1) for (c, l), v in _q31e.items()}

RESULT = {"n_q31_by_cond": nq31,
          "n_glm_by_cond": {c: sum(1 for (cc, _) in mtreal if cc == c) for c in CONDS9}}

# ---------- 1. nine-condition backend matrix ----------
# GLM pairs: authoritative 150/cond; missing -> '' (aligns n with gummy)
def glm_pairs(cond):
    out = []
    for k in q31last:
        c, sid = k.split("/", 1)
        if c == cond:
            out.append((sid, mtreal.get((cond, sid), "")))
    return out

def gummy_pairs(cond):
    pref = cond + "/"
    return [(k.split("/")[-1], d["text"]) for k, d in d3mt.items() if k.startswith(pref)]

matrix = {}
for cond in CONDS9:
    gp, lp = gummy_pairs(cond), glm_pairs(cond)
    rec = {
        "n_gummy": len(gp), "n_glm": len(lp),
        "gummy_vs_oracle": bleu_d3(gp, d3orc),
        "gummy_vs_glmref": bleu_d3(gp, refreal),
        "glm_vs_oracle": bleu_d3(lp, d3orc),
        "glm_vs_glmref": bleu_d3(lp, refreal),
    }
    matrix[cond] = rec
RESULT["backend_matrix_9"] = matrix
print("nine-condition backend matrix (BLEU, n aligned to q31 list):")
for cond in CONDS9:
    r = matrix[cond]
    print(f"  {cond:8s} n {r['n_gummy']}/{r['n_glm']}"
          f"  gummy|orc {r['gummy_vs_oracle']['bleu']:5.2f}  gummy|glm {r['gummy_vs_glmref']['bleu']:5.2f}"
          f"  glm|orc {r['glm_vs_oracle']['bleu']:5.2f}  glm|glm {r['glm_vs_glmref']['bleu']:5.2f}")

# ---------- 2. per-backend nine-condition slopes (same fit as v15_real) ----------
def slope_fit(cas, conds, refname):
    fits = {}
    for lang, key_lang in (("zh", "zh2en"), ("en", "en2zh")):
        xs, ys = [], []
        clean_b = cas["clean_r"][refname][key_lang]
        for cond in conds:
            e = q31err.get(f"{cond}/{lang}")
            b = cas[cond][refname][key_lang]
            if e is None or b is None:
                continue
            xs.append(e)
            ys.append(max(0.0, clean_b - b))
        if len(xs) < 3:
            continue
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs)
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        b1 = sxy / sxx
        b0 = my - b1 * mx
        r = (sxy / (sxx * sum((y - my) ** 2 for y in ys)) ** 0.5)
        fits[lang] = {"slope": round(b1, 3), "intercept": round(b0, 2),
                      "r": round(r, 3), "n_points": n,
                      "x": [round(x, 1) for x in xs], "y": [round(y, 1) for y in ys]}
    return fits

# cascade BLEU ladders per backend/ref
cas_gummy_orc = {c: {"oracle": matrix[c]["gummy_vs_oracle"], "glm": matrix[c]["gummy_vs_glmref"]} for c in CONDS9}
cas_glm_glmref = {c: {"oracle": matrix[c]["glm_vs_oracle"], "glm": matrix[c]["glm_vs_glmref"]} for c in CONDS9}

RESULT["slope_gummy_9cond_oracleref_noclean"] = slope_fit(cas_gummy_orc, [c for c in CONDS9 if c != "clean_r"], "oracle")
RESULT["slope_gummy_9cond_oracleref_withclean"] = slope_fit(cas_gummy_orc, CONDS9, "oracle")
RESULT["slope_glm_9cond_glmref_noclean"] = slope_fit(cas_glm_glmref, [c for c in CONDS9 if c != "clean_r"], "glm")
RESULT["slope_glm_9cond_glmref_withclean"] = slope_fit(cas_glm_glmref, CONDS9, "glm")
RESULT["slope_glm_9cond_oracleref_noclean"] = slope_fit(cas_glm_glmref, [c for c in CONDS9 if c != "clean_r"], "oracle")
RESULT["slope_glm_9cond_glmref_noclean_prev3"] = slope_fit(cas_glm_glmref, ["rb5", "rb0", "rbm5"], "glm")

print()
print("gummy 9-cond slope (oracle ref, no clean):", {k: v["slope"] for k, v in RESULT["slope_gummy_9cond_oracleref_noclean"].items()})
print("GLM   9-cond slope (glm ref, no clean):  ", {k: v["slope"] for k, v in RESULT["slope_glm_9cond_glmref_noclean"].items()})
print("GLM   9-cond slope (oracle ref, no clean):", {k: v["slope"] for k, v in RESULT["slope_glm_9cond_oracleref_noclean"].items()})
print("GLM   prev 3-pt slope (glm ref):         ", {k: v["slope"] for k, v in RESULT["slope_glm_9cond_glmref_noclean_prev3"].items()})
print("(v1.5 reported: gummy 0.43 zh / 0.72 en [9-cond oracle]; GLM 0.34/0.55 [3-pt glm ref])")

# ---------- 3. per-cond paired backend deltas ----------
deltas = {}
for cond in CONDS9:
    d = {"glmref": round(matrix[cond]["gummy_vs_glmref"]["bleu"] - matrix[cond]["glm_vs_glmref"]["bleu"], 2),
         "oracle": round(matrix[cond]["gummy_vs_oracle"]["bleu"] - matrix[cond]["glm_vs_oracle"]["bleu"], 2)}
    # diagonal advantage (same-engine minus cross-engine)
    d["diag_gummy"] = round(matrix[cond]["gummy_vs_oracle"]["bleu"] - matrix[cond]["gummy_vs_glmref"]["bleu"], 2)
    d["diag_glm"] = round(matrix[cond]["glm_vs_glmref"]["bleu"] - matrix[cond]["glm_vs_oracle"]["bleu"], 2)
    deltas[cond] = d
RESULT["backend_deltas"] = deltas
print()
print("paired deltas (gummy - glm, +ve = gummy higher):")
for cond in CONDS9:
    print(f"  {cond:8s} glmref {deltas[cond]['glmref']:+6.2f}  oracle {deltas[cond]['oracle']:+6.2f}"
          f"  diag_gummy {deltas[cond]['diag_gummy']:+6.2f}  diag_glm {deltas[cond]['diag_glm']:+6.2f}")

# ---------- 4. empty-translation accounting ----------
empt = {"gummy": sum(1 for k, d in d3mt.items() if not (d.get("text") or "").strip() and k.split("/")[0] in CONDS9),
        "glm_filled": sum(1 for (c, s) in mtreal if c in CONDS9),
        "glm_empty_slots": sum(nq31[c] - RESULT["n_glm_by_cond"][c] for c in CONDS9)}
RESULT["empty_accounting"] = empt
print()
print("empty accounting:", empt)

out_path = os.path.join(R, "analysis_v17_glm9.json")
json.dump(RESULT, open(out_path, "w"), indent=1, ensure_ascii=False)
print("saved", out_path)
