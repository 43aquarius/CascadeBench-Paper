#!/usr/bin/env python3
"""v1.5 analysis part 2: real-speech validation numbers.
- 9-condition ladder for q31 ASR + cascade (2 refs), slope refit (old-6 vs new-9)
- GLM backend matrix (2 backends x 2 refs x 4 conditions) + per-backend slopes
- rev-mit verification (synthetic corpus + measured MIT RIR)
- whisper-small: errors, CIs, empty rates, insertion/deletion decomposition
- 6-level real babble ladder + cross10 for all systems (G-table)
"""
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

def boot_ci(vals, n_boot=1000, seed=42):
    rng = random.Random(seed)
    stats = sorted(sum(rng.choices(vals, k=len(vals))) / len(vals) for _ in range(n_boot))
    return [round(stats[24], 1), round(stats[974], 1)]

def asr_err(logfn, prefix_pat):
    """per condition per lang: mean err, ci, n, empty rate"""
    log = load(logfn)
    res = {}
    for key, d in log.items():
        parts = key.split("/")
        cond, sid = parts[0], parts[-1]
        rec = D3C.get(sid)
        if rec is None:
            continue
        lang = rec["lang"]
        e = M.err_rate(rec["text"], d.get("text") or "", lang)
        res.setdefault((cond, lang), []).append((e, not (d.get("text") or "").strip()))
    out = {}
    for (cond, lang), pairs in res.items():
        errs = [p[0] for p in pairs]
        out[f"{cond}/{lang}"] = {
            "err": round(sum(errs) / len(errs) * 100, 1),
            "ci": boot_ci([e * 100 for e in errs]),
            "n": len(errs),
            "empty_pct": round(100 * sum(1 for _, em in pairs if em) / len(pairs), 1)}
    return out

def bleu_d3(pairs, refmap, keep_empty=True):
    """pairs: [(sid, hyp)]; refmap sid->ref text; macro avg by direction."""
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

# ================= 1. ASR ladders (all systems) =================
SYS_FILES = {"q31": "d3_asr_q31.jsonl", "q3": "d3_asr_q3.jsonl",
             "para16k": "d3_asr_para16k.jsonl", "para8k": "d3_asr_para8k.jsonl",
             "whisper": "d3_asr_whisper.jsonl"}
ladder = {}
for sysname, fn in SYS_FILES.items():
    ladder[sysname] = asr_err(fn, None)
RESULT["asr_real_all"] = ladder

# cross10 on 6-level real babble
def cross10(points):
    """points: [(snr, err)] sorted desc by snr; linear interp crossing of 10%"""
    pts = sorted(points, key=lambda p: -p[0])
    if pts[0][1] >= 10:
        return "above-highest"
    for (s1, e1), (s2, e2) in zip(pts, pts[1:]):
        if e2 >= 10 > e1:
            return round(s2 + (e2 - 10) / (e2 - e1) * (s1 - s2), 1) if e2 != e1 else s2
    return "below-lowest"

RB = {"rb10": 10, "rb5": 5, "rb25": 2.5, "rb0": 0, "rbm25": -2.5, "rbm5": -5}
l6 = {}
for sysname in SYS_FILES:
    l6[sysname] = {}
    for lang in ("zh", "en"):
        pts = []
        for cond, snr in RB.items():
            cell = ladder[sysname].get(f"{cond}/{lang}")
            if cell:
                pts.append((snr, cell["err"]))
        if len(pts) >= 2:
            l6[sysname][lang] = {"points": [{"snr": s, "err": e} for s, e in pts],
                                 "cross10": cross10(pts)}
RESULT["babble_ladder6"] = l6
print("cross10:", {s: {l: v["cross10"] for l, v in d.items()} for s, d in l6.items()})

# ================= 2. q31 cascade BLEU ladder (2 refs) =================
d3mt = load("d3_mt_cascade.jsonl")           # key: cond/sid, q31 frontend, gummy backend
d3orc = {k: v["text"] for k, v in load("d3_mt_oracle.jsonl").items()}
refreal = {}
for k, d in load("glm_tasks.jsonl").items():
    if k.startswith("refreal/"):
        refreal[k.split("/", 1)[1]] = d["text"]
CONDS9 = ["clean_r", "revr", "rb10", "rb5", "rb25", "rb0", "rbm25", "rbm5", "rn0"]

def cascade_pairs_d3(cond):
    pref = cond + "/"
    return [(k.split("/")[-1], d["text"]) for k, d in d3mt.items() if k.startswith(pref)]

cas = {}
for cond in CONDS9:
    rec = {}
    for rname, refmap in (("oracle", d3orc), ("glm", refreal)):
        b = bleu_d3(cascade_pairs_d3(cond), refmap, keep_empty=True)
        rec[rname] = b
    cas[cond] = rec
RESULT["real_cascade_2ref"] = cas
print()
print("real cascade BLEU (oracle/glm):")
for cond in CONDS9:
    print(f"  {cond:8s} oracle {cas[cond]['oracle']['bleu']:5.2f} (zh {cas[cond]['oracle']['zh2en']}, en {cas[cond]['oracle']['en2zh']})"
          f"   glm {cas[cond]['glm']['bleu']:5.2f}")

# ================= 3. slope refit =================
q31 = ladder["q31"]
def slope_fit(conds, refname="oracle"):
    fits = {}
    for lang, key_lang in (("zh", "zh2en"), ("en", "en2zh")):
        xs, ys = [], []
        clean_b = cas["clean_r"][refname][key_lang]
        for cond in conds:
            e = q31.get(f"{cond}/{lang}", {}).get("err")
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
        r = (sxy / (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5)
        fits[lang] = {"slope": round(b1, 3), "intercept": round(b0, 2),
                      "r": round(r, 3), "n_points": n,
                      "x": [round(x, 1) for x in xs], "y": [round(y, 1) for y in ys]}
    return fits

OLD6 = ["clean_r", "revr", "rb5", "rb0", "rbm5", "rn0"]
NEW9 = CONDS9
RESULT["slope_old6_withclean"] = slope_fit(OLD6)
RESULT["slope_old6_noclean"] = slope_fit([c for c in OLD6 if c != "clean_r"])
RESULT["slope_new9_withclean"] = slope_fit(NEW9)
RESULT["slope_new9_noclean"] = slope_fit([c for c in NEW9 if c != "clean_r"])
print()
print("slope old6 with clean:", {k: v["slope"] for k, v in RESULT["slope_old6_withclean"].items()})
print("slope old6 no clean:  ", {k: v["slope"] for k, v in RESULT["slope_old6_noclean"].items()})
print("slope new9 with clean:", {k: v["slope"] for k, v in RESULT["slope_new9_withclean"].items()})
print("slope new9 no clean:  ", {k: v["slope"] for k, v in RESULT["slope_new9_noclean"].items()})
print("(v1.3 reported 0.41 zh / 0.73 en on the old 6 conditions)")

json.dump(RESULT, open(os.path.join(R, "analysis_v15_real.json"), "w"),
          indent=1, ensure_ascii=False)
print()
print("saved analysis_v15_real.json (part 1 of 2)")
