#!/usr/bin/env python3
"""v1.5 analysis part 3: GLM backend matrix + rev-mit verification + whisper decomposition."""
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_ROOT = _os.path.dirname(_HERE)              # repository root
_PAPER = _os.path.join(_ROOT, "paper", "latex")
_FIG = _os.path.join(_ROOT, "figures")
import json, os, sys, random

ROOT = _ROOT
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import metrics as M
from sacrebleu.metrics import BLEU
_bleu_en, _bleu_zh = BLEU(tokenize="13a"), BLEU(tokenize="zh")

R = os.path.join(ROOT, "results")
D3C = {json.loads(l)["id"]: json.loads(l)
       for l in open(_os.path.join(_ROOT, "corpus", "d3_corpus.jsonl"))}
SWEEP = set(json.load(open(os.path.join(ROOT, "corpus", "sweep_ids.json"))))
CORP = M.CORPUS

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

RESULT = {}

# ================= 4. GLM backend matrix (real speech, q31 frontend) =================
d3mt = load("d3_mt_cascade.jsonl")            # gummy backend, key cond/sid
mtreal = {}                                    # glm backend
for k, d in load("glm_tasks.jsonl").items():
    if k.startswith("mtreal/"):
        _, cond, sid = k.split("/")
        mtreal[(cond, sid)] = d["text"]
d3orc = {k: v["text"] for k, v in load("d3_mt_oracle.jsonl").items()}
refreal = {}
for k, d in load("glm_tasks.jsonl").items():
    if k.startswith("refreal/"):
        refreal[k.split("/", 1)[1]] = d["text"]

CONDS4 = ["clean_r", "rb5", "rb0", "rbm5"]
matrix = {}
for cond in CONDS4:
    gummy_pairs = [(k.split("/")[-1], d["text"]) for k, d in d3mt.items()
                   if k.startswith(cond + "/")]
    glm_pairs = [(sid, mtreal[(cond, sid)]) for (c, sid) in mtreal if c == cond]
    rec = {
        "gummy_vs_oracle": bleu_d3(gummy_pairs, d3orc),
        "gummy_vs_glmref": bleu_d3(gummy_pairs, refreal),
        "glm_vs_oracle": bleu_d3(glm_pairs, d3orc),
        "glm_vs_glmref": bleu_d3(glm_pairs, refreal),
    }
    matrix[cond] = rec
RESULT["backend_matrix"] = matrix
print("backend matrix (BLEU):")
for cond in CONDS4:
    r = matrix[cond]
    print(f"  {cond:8s} gummy|orc {r['gummy_vs_oracle']['bleu']:5.2f}  gummy|glm {r['gummy_vs_glmref']['bleu']:5.2f}"
          f"  glm|orc {r['glm_vs_oracle']['bleu']:5.2f}  glm|glm {r['glm_vs_glmref']['bleu']:5.2f}"
          f"  n {r['gummy_vs_oracle']['n']}/{r['glm_vs_oracle']['n']}")

# per-backend slopes on 3 non-clean points (+clean anchor), per lang
def backend_slope(pairs_by_cond, refmap, q31err):
    fits = {}
    for lang, key_lang in (("zh", "zh2en"), ("en", "en2zh")):
        cb = bleu_d3(pairs_by_cond["clean_r"], refmap)[key_lang]
        xs, ys = [], []
        for cond in ("rb5", "rb0", "rbm5"):
            e = q31err[(cond, lang)]
            b = bleu_d3(pairs_by_cond[cond], refmap)[key_lang]
            xs.append(e)
            ys.append(max(0.0, cb - b))
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        b1 = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
        r = (sum((x - mx) * (y - my) for x, y in zip(xs, ys)) /
             (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5)
        fits[lang] = {"slope": round(b1, 3), "r": round(r, 3), "n": n,
                      "x": xs, "y": [round(v, 1) for v in ys]}
    return fits

# q31 err per cond/lang
_q31 = load("d3_asr_q31.jsonl")
q31err = {}
for k, d in _q31.items():
    cond, sid = k.split("/")
    rec = D3C.get(sid)
    if rec:
        q31err.setdefault((cond, rec["lang"]), []).append(
            M.err_rate(rec["text"], d.get("text") or "", rec["lang"]))
q31err = {k: round(sum(v) / len(v) * 100, 1) for k, v in q31err.items()}

gummy_pairs_by_cond = {c: [(k.split("/")[-1], d["text"]) for k, d in d3mt.items() if k.startswith(c + "/")]
                     for c in CONDS4}
glm_pairs_by_cond = {c: [(sid, mtreal[(c, sid)]) for (cc, sid) in mtreal if cc == c]
                     for c in CONDS4}

RESULT["slope_gummy_backend_oracleref"] = backend_slope(gummy_pairs_by_cond, d3orc, q31err)
RESULT["slope_glm_backend_glmref"] = backend_slope(glm_pairs_by_cond, refreal, q31err)
print()
print("gummy backend slope (oracle ref):", {k: v["slope"] for k, v in RESULT["slope_gummy_backend_oracleref"].items()})
print("glm   backend slope (glm ref):  ", {k: v["slope"] for k, v in RESULT["slope_glm_backend_glmref"].items()})

# ================= 5. rev-mit verification (synthetic corpus + MIT RIR) =================
print()
RM_SYS = {"q31": "revmit_asr_q31.jsonl", "q3": "revmit_asr_q3.jsonl",
          "para16k": "revmit_asr_p16.jsonl", "para8k": "revmit_asr_p8.jsonl"}
revmit_asr = {}
for name, fn in RM_SYS.items():
    per_lang = {"zh": [], "en": []}
    for k, d in load(fn).items():
        sid = k.split("/")[-1]
        rec = CORP.get(sid)
        if rec:
            per_lang[rec["lang"]].append(M.err_rate(rec["text"], d.get("text") or "", rec["lang"]))
    revmit_asr[name] = {lang: round(sum(v) / len(v) * 100, 1) for lang, v in per_lang.items() if v}
RESULT["revmit_asr"] = revmit_asr
print("rev-mit ASR err:", revmit_asr)
print("(analysis_v14 claims: q31 0.2/1.1, q3 0.2/0.5, p16 0.7/3.7, p8 3.4)")

# synthetic rev condition (main grid, full 480) for comparison
rev_asr = {}
for name, fn in {"q31": "asr_q31.jsonl", "q3": "asr_q3.jsonl",
                 "para16k": "asr_para16k.jsonl", "para8k": "asr_para8k.jsonl"}.items():
    per_lang = {"zh": [], "en": []}
    for k, d in load(fn).items():
        parts = k.split("/")
        if parts[0] != "rev":
            continue
        sid = parts[-1]
        rec = CORP.get(sid)
        if rec:
            per_lang[rec["lang"]].append(M.err_rate(rec["text"], d.get("text") or "", rec["lang"]))
    rev_asr[name] = {lang: round(sum(v) / len(v) * 100, 1) for lang, v in per_lang.items() if v}
RESULT["rev_asr_full"] = rev_asr
print("synthetic rev ASR err (full 480):", rev_asr)

# rev-mit cascade BLEU under 3 references (full 480)
refmax = {k: v["text"] for k, v in load("mt_refmax.jsonl").items()}
oracle = {k: v["text"] for k, v in load("mt_oracle.jsonl").items()}
glmref = {}
for k, d in load("glm_tasks.jsonl").items():
    if k.startswith("refsynth/") and d.get("kind") == "reference":
        glmref[k.split("/", 1)[1]] = d["text"]

rmc = load("revmit_mt_cascade.jsonl")   # key: fe/rev_mit/sid
rmt = load("mt_cascade.jsonl")          # key: fe/cond/sid (q31, para16k frontends)
rmt_q3 = load("ext_mt_cascade_q3main.jsonl")  # key: q3/cond/sid

def cascade_src(fe):
    return rmt_q3 if fe == "q3" else rmt

def bleu_synth(pairs, refmap, keep_empty=True):
    h_zh2en, r_zh2en, h_en2zh, r_en2zh = [], [], [], []
    for sid, hyp in pairs:
        rec = CORP.get(sid)
        ref = refmap.get(sid)
        if not rec or ref is None:
            continue
        if not hyp and not keep_empty:
            continue
        if rec["lang"] == "zh":
            h_zh2en.append(hyp or ""); r_zh2en.append(ref)
        else:
            h_en2zh.append(hyp or ""); r_en2zh.append(ref)
    vals = []
    detail = {}
    for nm, (h, r, b) in {"zh2en": (h_zh2en, r_zh2en, _bleu_en),
                          "en2zh": (h_en2zh, r_en2zh, _bleu_zh)}.items():
        v = round(b.corpus_score(h, [r]).score, 2) if h else None
        detail[nm] = v
        if v is not None:
            vals.append(v)
    return {"bleu": round(sum(vals) / len(vals), 2) if vals else None, **detail,
            "n": len(h_zh2en) + len(h_en2zh)}

revmit_cas = {}
for fe in ("q31", "q3", "p16", "p8"):
    pref = f"{fe}/rev_mit/"
    pairs_all = [(k.split("/")[-1], d["text"]) for k, d in rmc.items() if k.startswith(pref)]
    pairs_sw = [(s, h) for s, h in pairs_all if s in SWEEP]
    rec = {"n_full": len(pairs_all), "n_sweep": len(pairs_sw)}
    for tag, pairs in (("rev_mit", pairs_all), ("rev_mit_sweep", pairs_sw)):
        rec[tag] = {"primary": bleu_synth(pairs, refmax), "oracle": bleu_synth(pairs, oracle),
                    "glm": bleu_synth(pairs, glmref)}
    if fe != "p8":  # main grid has no p8 cascade
        fe_main = "para16k" if fe == "p16" else fe
        prev = f"{fe_main}/rev/"
        rpairs = [(k.split("/")[-1], d["text"]) for k, d in cascade_src(fe_main).items() if k.startswith(prev)]
        rec["rev"] = {"primary": bleu_synth(rpairs, refmax), "oracle": bleu_synth(rpairs, oracle),
                       "glm": bleu_synth(rpairs, glmref)}
    revmit_cas[fe] = rec
RESULT["revmit_cascade_3ref"] = revmit_cas
print()
print("rev-mit cascade BLEU (primary/oracle/glm):")
for fe, rec in revmit_cas.items():
    rm = rec["rev_mit_sweep"]; rms = rec["rev_mit"]
    line = f"  {fe:5s} rev_mit(sweep,n={rec['n_sweep']}) {rm['primary']['bleu']:5.2f}/{rm['oracle']['bleu']:5.2f}/{rm['glm']['bleu']:5.2f}"
    line += f"  rev_mit(full,n={rec['n_full']}) {rms['primary']['bleu']:5.2f}/{rms['oracle']['bleu']:5.2f}/{rms['glm']['bleu']:5.2f}"
    if "rev" in rec:
        rv = rec["rev"]
        line += f"  rev(n={rv['primary']['n']}) {rv['primary']['bleu']:5.2f}/{rv['oracle']['bleu']:5.2f}/{rv['glm']['bleu']:5.2f}"
    print(line)
print("(analysis_v14 claims q31 rev_mit full 55.04/90.91/52.57, rev 52.42/89.75/-)")

json.dump(RESULT, open(os.path.join(R, "analysis_v15_real2.json"), "w"),
          indent=1, ensure_ascii=False)
print()
print("saved analysis_v15_real2.json")
