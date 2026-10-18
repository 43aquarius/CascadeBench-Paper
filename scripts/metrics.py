# -*- coding: utf-8 -*-
"""CascadeBench 评测指标 v3: 跨系统文本归一化 + CER/WER + BLEU/chrF + 统计"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import re, json, unicodedata
import cn2an
from word2number.w2n import word_to_num

_PUNCT_ZH = "，。！？；：、""''（）《》【】…—·～「」『』\n\r\t"
_PUNCT_EN = ",.!?;:\"'()[]{}<>_/\\|@#$%^&*+=~`…\u2014\u2018\u2019\u201c\u201d"
_DOT = "\u0001"  # 小数点占位符

def _strip_punct(s):
    return "".join(ch for ch in s if ch not in _PUNCT_ZH and ch not in _PUNCT_EN)

def _to_halfwidth(s):
    return unicodedata.normalize("NFKC", s)

def _fmt_num(v):
    if isinstance(v, float) and v == int(v): return str(int(v))
    return str(v)

# ============ 中文 ============
_ZH_D = "零一二三四五六七八九"
_DIGIT_MAP = {c: str(i) for i, c in enumerate(_ZH_D)}

def _cn_num(seg):
    seg2 = seg.replace("两", "二")
    # 逐位读法保留前导零: 零七三一 → 0731
    if len(seg2) >= 2 and all(c in _ZH_D for c in seg2):
        return "".join(_DIGIT_MAP[c] for c in seg2)
    try:
        return _fmt_num(cn2an.cn2an(seg2, mode="smart"))
    except Exception:
        return seg

def _zh_time_repl(m):
    h, mm, has_fen = m.group(1), m.group(2), m.group(3)
    return f"{_cn_num(h)}点{_cn_num(mm) if mm else ''}{has_fen}"

def _zh_norm_numbers(t):
    t = re.sub(r"(\d{1,2}):(\d{2})", r"\1点\2", t)          # 10:20 → 10点20
    t = t.replace("百分之", "")                               # 70% ≡ 百分之七十
    t = re.sub(rf"([{_ZH_D}十]{{1,4}})点([{_ZH_D}十]{{2,4}})(分?)", _zh_time_repl, t)
    t = re.sub(rf"([{_ZH_D}十]{{1,4}})点(?![{_ZH_D}])", lambda m: _cn_num(m.group(1))+"点", t)
    t = re.sub(rf"[{_ZH_D}]{{2,}}", lambda m: "".join(_DIGIT_MAP[c] for c in m.group(0)), t)
    t = re.sub(r"[零一二两三四五六七八九十百千万亿]+(?:点[零一二三四五六七八九]+)?",
               lambda m: _cn_num(m.group(0)), t)
    def _unit(m):
        v, u = float(m.group(1).replace(_DOT, ".")), m.group(2)
        mul = {"万亿": 1e12, "亿": 1e8, "百万": 1e6, "万": 1e4, "千": 1e3}[u]
        return _fmt_num(v * mul)
    t = re.sub(rf"(\d+(?:[{_DOT}.]\d+)?)(万亿|百万|亿|万|千)", _unit, t)
    t = re.sub(r"(\d+点\d+)分(?!钟)", r"\1", t)
    return t

def normalize_zh(text, num_norm=True):
    t = _to_halfwidth(text).lower()
    t = re.sub(r"(\d)\.(\d)", rf"\1{_DOT}\2", t)  # 保护小数点
    t = _strip_punct(t)
    if num_norm:
        t = _zh_norm_numbers(t)
    t = re.sub(rf"[^0-9a-z\u4e00-\u9fff]+", "", t)
    return t

# ============ 英文 ============
_EN_ONES = "zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen"
_EN_TENS = "twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety"
_EN_SCALE = "hundred|thousand|million|billion|trillion"
_EN_ORD = "first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth|thirteenth|fourteenth|fifteenth|sixteenth|seventeenth|eighteenth|nineteenth|twentieth|thirtieth|fortieth|fiftieth|sixtieth|seventieth|eightieth|ninetieth"
_EN_NUM_WORDS = set(_EN_ONES.split("|") + _EN_TENS.split("|") + _EN_SCALE.split("|"))
_EN_TENS_SET = set(_EN_TENS.split("|"))
_EN_SCALE_SET = set(_EN_SCALE.split("|"))
_EN_ONES_SET = set(_EN_ONES.split("|"))

def _val(w):
    try:
        return word_to_num(w)
    except Exception:
        return None

def _w2n_safe(seg):
    try:
        return _fmt_num(word_to_num(re.sub(r"\s+", " ", seg.strip().lower())))
    except Exception:
        return None

def _grammatical(run):
    """判断英文数词串是否为合法语法数字(而非逐位/时间读法)"""
    if "zero" in run: return False
    for a, b in zip(run, run[1:]):
        va, vb = _val(a), _val(b)
        if va is None or vb is None: return False
        if va <= 19 and vb <= 19: return False          # seven three one
        if va <= 19 and b in _EN_TENS_SET: return False  # nine forty
    return True

def _convert_run(run):
    """把数词串转换为数字字符串"""
    run = [r.lower() for r in run]
    # 单独的scale词不转换(留给单位规则: 18 billion)
    if len(run) == 1 and run[0] in _EN_SCALE_SET:
        return None
    # 小数: L point R (R可带scale尾缀)
    if "point" in run:
        pi = run.index("point")
        left, right = run[:pi], run[pi+1:]
        scale_mul = 1
        if right and right[-1] in _EN_SCALE_SET:
            scale_word = right[-1]
            scale_mul = {"thousand":1e3,"million":1e6,"billion":1e9,"trillion":1e12}[scale_word]
            right = right[:-1]
        if left and right:
            base = _w2n_safe(" ".join(left) + " point " + " ".join(right))
            if base is not None:
                return _fmt_num(float(base) * scale_mul)
        return None
    if _grammatical(run):
        whole = _w2n_safe(" ".join(run))
        if whole is not None:
            return whole
    # 时间/逐位读法: H + M (eleven thirty three → 1133)
    if len(run) >= 2:
        h = _val(run[0])
        rest = run[1:]
        if h is not None and h <= 12:
            if _grammatical(rest) and not any(w in _EN_SCALE_SET for w in rest):
                m = _w2n_safe(" ".join(rest))
                if m is not None and float(m) < 60:
                    return f"{_fmt_num(h)}{_fmt_num(float(m))}"
        # 逐词拼接 (twelve zero eight → 1208)
        parts = [_val(r) for r in run]
        if all(p is not None for p in parts):
            return "".join(_fmt_num(p) for p in parts)
    return None

def _en_norm_numbers(t):
    t = re.sub(r"(?<=[a-z])-(?=[a-z])", " ", t)
    t = re.sub(r"\band a half\b", " point five", t)
    # 冠词数: a hundred → one hundred
    t = re.sub(r"\ba (hundred|thousand|million|billion|trillion)\b", r"one \1", t, flags=re.IGNORECASE)
    t = re.sub(rf"\b({_EN_ORD})\b", "<num>", t, flags=re.IGNORECASE)
    t = re.sub(r"\b\d+(?:st|nd|rd|th)\b", "<num>", t, flags=re.IGNORECASE)
    tokens = t.split()
    out, i = [], 0
    while i < len(tokens):
        w = re.sub(r"[^a-z]", "", tokens[i].lower())
        if w in _EN_NUM_WORDS or w == "point":
            j, run = i, []
            while j < len(tokens):
                wj = re.sub(r"[^a-z]", "", tokens[j].lower())
                if wj in _EN_NUM_WORDS or wj in ("and", "point"):
                    if wj != "and": run.append(wj)  # 追加清洗后的token
                    j += 1
                else: break
            conv = _convert_run(run) if run else None
            if conv is not None:
                out.append(conv)
            else:
                out.extend(run)
            i = j
        else:
            out.append(tokens[i]); i += 1
    t = " ".join(out)
    def _unit(m):
        v, u = float(m.group(1)), m.group(2)
        mul = {"trillion": 1e12, "billion": 1e9, "million": 1e6, "thousand": 1e3}[u]
        return _fmt_num(v * mul)
    t = re.sub(r"(\d+(?:\.\d+)?)\s*(trillion|billion|million|thousand)\b", _unit, t)
    t = re.sub(r"(\d{1,2}):(\d{2})", r"\1\2", t)
    return t

def normalize_en(text, num_norm=True):
    t = _to_halfwidth(text).lower()
    t = t.replace("’", "").replace("'", "")
    if num_norm:
        t = _en_norm_numbers(t)
    t = _strip_punct(t)
    t = t.replace("<num>", " <num> ")
    t = re.sub(r"\s+", " ", t).strip()
    return t

# ============ CER / WER ============
def edit_distance(ref, hyp):
    n, m = len(ref), len(hyp)
    if n == 0: return m
    prev = list(range(m+1))
    for i in range(1, n+1):
        cur = [i] + [0]*m
        for j in range(1, m+1):
            cost = 0 if ref[i-1] == hyp[j-1] else 1
            cur[j] = min(prev[j]+1, cur[j-1]+1, prev[j-1]+cost)
        prev = cur
    return prev[m]

def cer(ref, hyp, num_norm=True):
    r, h = normalize_zh(ref, num_norm), normalize_zh(hyp, num_norm)
    if not r: return 0.0 if not h else 1.0
    return edit_distance(r, h) / len(r)

def wer(ref, hyp, num_norm=True):
    r, h = normalize_en(ref, num_norm).split(), normalize_en(hyp, num_norm).split()
    if not r: return 0.0 if not h else 1.0
    return edit_distance(r, h) / len(r)

def err_rate(ref, hyp, lang, num_norm=True):
    return cer(ref, hyp, num_norm) if lang == "zh" else wer(ref, hyp, num_norm)

# ============ BLEU / chrF ============
from sacrebleu.metrics import BLEU, CHRF
_bleu_en = BLEU(tokenize="13a")
_bleu_zh = BLEU(tokenize="zh")
_chrf = CHRF()

_CORPUS = None
def _get_corpus():
    global _CORPUS
    if _CORPUS is None:
        _CORPUS = {json.loads(l)["id"]: json.loads(l)
                   for l in open(os.path.join(ROOT, "corpus", "corpus.jsonl"))}
    return _CORPUS
CORPUS = _get_corpus()

def bleu(hyps, refs, target_lang="en"):
    """hyps: list[str], refs: list[str] 对齐; 返回corpus BLEU"""
    b = _bleu_zh if target_lang == "zh" else _bleu_en
    try:
        return round(b.corpus_score(list(hyps), [list(refs)]).score, 2)
    except Exception:
        return 0.0

def bleu_bidir(pairs, refmap, keep_empty=False):
    """双语对称语料的BLEU: 按目标语言分向计算后宏平均
    pairs: [(sid, hyp_text)], refmap: {sid: reference_text}
    keep_empty=True 时空翻译(拒答)计入语料(有效BLEU口径)"""
    corpus = _get_corpus()
    h_zh2en, r_zh2en, h_en2zh, r_en2zh = [], [], [], []
    for sid, hyp in pairs:
        rec = corpus.get(sid)
        ref = refmap.get(sid)
        if not rec or not ref: continue
        if not hyp and not keep_empty: continue
        if rec["lang"] == "zh":
            h_zh2en.append(hyp or ""); r_zh2en.append(ref)
        else:
            h_en2zh.append(hyp or ""); r_en2zh.append(ref)
    b1 = bleu(h_zh2en, r_zh2en, "en") if h_zh2en else None
    b2 = bleu(h_en2zh, r_en2zh, "zh") if h_en2zh else None
    vals = [v for v in (b1, b2) if v is not None]
    c1 = chrf_score(h_zh2en, r_zh2en) if h_zh2en else None
    c2 = chrf_score(h_en2zh, r_en2zh) if h_en2zh else None
    cvals = [v for v in (c1, c2) if v is not None]
    return {"bleu_zh2en": b1, "bleu_en2zh": b2,
            "bleu": round(sum(vals)/len(vals), 2) if vals else None,
            "chrf_zh2en": c1, "chrf_en2zh": c2,
            "chrf": round(sum(cvals)/len(cvals), 2) if cvals else None,
            "n": len(h_zh2en)+len(h_en2zh)}

def chrf_score(hyps, refs):
    try:
        return round(_chrf.corpus_score(list(hyps), [list(refs)]).score, 2)
    except Exception:
        return 0.0

# ============ 统计 ============
def bootstrap_ci(values, stat_fn=None, n_boot=1000, alpha=0.05, seed=42):
    import random as _r
    if not values: return (float("nan"),)*3
    rng = _r.Random(seed)
    stat_fn = stat_fn or (lambda v: sum(v)/len(v))
    stats = sorted(stat_fn([values[rng.randrange(len(values))] for _ in range(len(values))]) for _ in range(n_boot))
    return stat_fn(values), stats[int(alpha/2*n_boot)], stats[min(int((1-alpha/2)*n_boot), n_boot-1)]

def wilcoxon_test(x, y):
    from scipy.stats import wilcoxon
    if sum(1 for a,b in zip(x,y) if a != b) < 5:
        return float("nan"), float("nan")
    try:
        stat, p = wilcoxon(x, y)
        return stat, p
    except Exception:
        return float("nan"), float("nan")

if __name__ == "__main__":
    print("=== zh tests ===")
    zh_tests = [
        ("今天全国大部分地区晴朗，气温二十六度。", "今天全国大部分地区晴朗，气温26度。", 0.0),
        ("会议将于三月十五日召开。", "会议将于3月15日召开。", 0.0),
        ("二零二五年一月一日", "2025年1月1日", 0.0),
        ("同比增长百分之五点二", "同比增长5.2%", 0.0),
        ("火车十点二十发车。", "火车10点20分发车。", 0.0),
        ("共筹得善款两千六百万元", "共筹得善款2600万元", 0.0),
        ("两万三千亿元", "2.3万亿元", 0.0),
        ("预约编号零七三一。", "预约编号0731。", 0.0),
        ("于十一点三十三分安全着陆", "于11点33分安全着陆", 0.0),
        ("早上七点零六分从南站发车", "早上7点06分从南站发车", 0.0),
        ("统一的思想", "统一的思想", 0.0),
        ("电池续航提升两成", "电池续航提升两成", 0.0),
        ("百分之七十的受访者", "70%的受访者", 0.0),
        ("增长百分之三点五", "增长3.5%", 0.0),
    ]
    ok = 0
    for ref, hyp, exp in zh_tests:
        c = cer(ref, hyp)
        good = abs(c-exp) < 1e-9; ok += good
        print(f"[{'OK' if good else 'FAIL'}] CER={c:.3f} | {normalize_zh(ref)[:30]} VS {normalize_zh(hyp)[:30]}")
    print("=== en tests ===")
    en_tests = [
        ("He turns thirty next week.", "He turns 30 next week.", 0.0),
        ("It costs twenty dollars.", "It costs twenty dollars.", 0.0),
        ("the twentieth century", "the 20th century", 0.0),
        ("four and a half hours", "4.5 hours", 0.0),
        ("Room twelve zero eight", "Room 1208", 0.0),
        ("three thousand acres", "3,000 acres", 0.0),
        ("eighteen billion", "18 billion", 0.0),
        ("The train departs at nine forty.", "The train departs at 9:40.", 0.0),
        ("Class begins at eight thirty.", "Class begins at 8:30.", 0.0),
        ("two point three trillion yuan", "2.3 trillion yuan", 0.0),
        ("sixty five thousand", "65,000", 0.0),
        ("five hundred milliliters", "500 milliliters", 0.0),
        ("The code is seven three one.", "The code is 731.", 0.0),
        ("his first date ten years ago", "his 1st date ten years ago", 0.0),
        ("landed safely at eleven thirty three", "landed safely at 11:33", 0.0),
        ("two thousand twenty five", "2025", 0.0),
        ("Flight CA one three two five departs", "Flight CA 1325 departs", 0.0),
        ("starts with seven seven three zero", "starts with 7730", 0.0),
        ("nineteen zero five", "1905", 0.0),
        ("a hundred years", "100 years", 0.0),
        ("sixteen and a half hours", "16.5 hours", 0.0),
        ("twenty five basis points", "25 basis points", 0.0),
        ("magnitude eight earthquake", "magnitude 8 earthquake", 0.0),
        ("raised twenty six million", "raised 26 million", 0.0),
    ]
    for ref, hyp, exp in en_tests:
        w = wer(ref, hyp)
        good = abs(w-exp) < 1e-9; ok += good
        print(f"[{'OK' if good else 'FAIL'}] WER={w:.3f} | {normalize_en(ref)[:34]} VS {normalize_en(hyp)[:34]}")
    print(f"\nTOTAL: {ok}/{len(zh_tests)+len(en_tests)} passed")
    print("BLEU identical:", bleu("the cat sat on the mat", ["the cat sat on the mat"], "en"))
    print("chrF:", chrf_score("the cat sat on the mat", ["the cat sat on the mat"]))
