# -*- coding: utf-8 -*-
"""D3 真实语音抽取: AISHELL-1 test (zh) + LibriSpeech test-clean (en)
- 远程读取 HF parquet (hf-mirror, Range请求+重试)
- 时长过滤 + 说话人分散采样 (75 zh + 75 en)
- 电平归一化: 匹配合成语料 clean 的 active RMS 中位数
- 输出: d3_data/real_zh/*.wav, d3_data/real_en/*.wav, d3_corpus.jsonl
"""
import io, os, sys, json, time, glob, csv, random
import numpy as np
import soundfile as sf
import pyarrow.parquet as pq
import fsspec
from aiohttp import ClientTimeout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from perturb import active_rms, save_wav, load_wav, SR

random.seed(20261018)
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D3 = os.path.join(ROOT, "d3_data")
MIRROR = "https://hf-mirror.com"

AIS_FILES = [f"{MIRROR}/datasets/AudioLLMs/aishell_1_zh_test/resolve/main/data/test-0000{i}-of-00003.parquet" for i in range(3)]
AIS_GROUPS = [0, 8, 16]
LIB_URL = f"{MIRROR}/datasets/openslr/librispeech_asr/resolve/main/clean/test/0000.parquet"
LIB_GROUPS = [0, 4, 8, 12, 16, 20]
CACHE = f"{D3}/cache"
os.makedirs(CACHE, exist_ok=True)

N_PER_LANG = 75

def open_pf(url, tries=10):
    last = None
    for i in range(tries):
        try:
            fs = fsspec.filesystem("http", block_size=1024*1024,
                                   client_kwargs={"timeout": ClientTimeout(total=120, connect=20)})
            return pq.ParquetFile(fs.open(url, "rb"))
        except Exception as e:
            last = e; print(f"    open retry {i+1}: {str(e)[:100]}", flush=True); time.sleep(3+i*2)
    raise last

def read_group_retry(url, g, tries=6):
    last = None
    for i in range(tries):
        try:
            pf = open_pf(url, tries=3)
            return pf.read_row_group(g, columns=None)
        except Exception as e:
            last = e; print(f"    group{g} retry {i+1}: {str(e)[:100]}", flush=True); time.sleep(4+i*2)
    raise last

def cached_group(url, g, tag):
    """带磁盘缓存的行组读取: cache/{tag}.json (音频字节存 base64)"""
    import base64
    cf = f"{CACHE}/{tag}.json"
    if os.path.exists(cf):
        try:
            return json.load(open(cf))
        except Exception:
            os.remove(cf)
    tbl = read_group_retry(url, g)
    rows = []
    for i in range(tbl.num_rows):
        row = {c: tbl.column(c)[i].as_py() for c in tbl.column_names}
        rows.append(row)
    # 序列化 (bytes -> base64)
    ser = json.dumps(rows, default=lambda o: base64.b64encode(o).decode() if isinstance(o, bytes) else str(o))
    with open(cf, "w") as f:
        f.write(ser)
    return rows

def flac_bytes_to_wav(b):
    x, sr = sf.read(io.BytesIO(b), dtype="float32")
    if x.ndim > 1: x = x.mean(axis=1)
    return x, sr

# ---------- 1) 合成语料电平基准 ----------
def synth_level():
    files = sorted(glob.glob(os.path.join(ROOT, "audio", "perturbed", "clean", "*.wav")))
    sample = files[::40]  # ~24 个
    vals = [active_rms(load_wav(f)) for f in sample]
    med = float(np.median(vals))
    print(f"合成语料 clean active RMS 中位数: {med:.4f} (n={len(sample)})")
    return med

# ---------- 2) AISHELL 抽取 ----------
def extract_aishell():
    print("=== AISHELL-1 test 抽取 ===", flush=True)
    import base64
    cands = []
    for fi, url in enumerate(AIS_FILES):
        for g in AIS_GROUPS:
            tag = f"ais{fi}g{g}"
            try:
                rows = cached_group(url, g, tag)
            except Exception as e:
                print(f"  文件{fi} 组{g} 失败: {str(e)[:80]}", flush=True); continue
            n0 = len(cands)
            for i, row in enumerate(rows):
                ctx = row.get("context") or {}
                ans = row.get("answer")
                b = ctx.get("bytes") if isinstance(ctx, dict) else None
                if isinstance(b, str):
                    try: b = base64.b64decode(b)
                    except Exception: continue
                if not b: continue
                txt = (ans or "").strip()
                if not (4 <= len(txt) <= 60): continue
                cands.append({"bytes": b, "text": txt, "src": f"p{fi}g{g}r{i}"})
            print(f"  文件{fi} 组{g}: +{len(cands)-n0} 累计 {len(cands)}", flush=True)
    print(f"AISHELL 候选总数: {len(cands)}", flush=True)
    # 时长过滤 + 电平信息
    keep = []
    for c in cands:
        try:
            x, sr = flac_bytes_to_wav(c["bytes"])
        except Exception:
            continue
        dur = len(x)/sr
        if not (2.5 <= dur <= 9.0): continue
        if abs(np.max(np.abs(x))) < 1e-4: continue
        keep.append({"x": x, "sr": sr, "text": c["text"], "src": c["src"], "dur": dur})
    print(f"时长过滤后: {len(keep)}")
    return keep

# ---------- 3) LibriSpeech 抽取 ----------
def extract_libri():
    print("=== LibriSpeech test-clean 抽取 ===", flush=True)
    import base64
    cands = []
    for g in LIB_GROUPS:
        tag = f"libg{g}"
        try:
            rows = cached_group(LIB_URL, g, tag)
        except Exception as e:
            print(f"  组{g} 失败: {str(e)[:80]}", flush=True); continue
        n0 = len(cands)
        for i, row in enumerate(rows):
            au = row.get("audio") or {}
            txt = (row.get("text") or "").strip()
            spk = row.get("speaker_id")
            b = au.get("bytes") if isinstance(au, dict) else None
            if isinstance(b, str):
                try: b = base64.b64decode(b)
                except Exception: continue
            if not b: continue
            if len(txt.split()) < 6: continue
            cands.append({"bytes": b, "text": txt, "speaker": str(spk), "src": f"g{g}r{i}"})
        print(f"  组{g}: +{len(cands)-n0} 累计 {len(cands)}", flush=True)
    print(f"LibriSpeech 候选总数: {len(cands)}", flush=True)
    keep = []
    for c in cands:
        try:
            x, sr = flac_bytes_to_wav(c["bytes"])
        except Exception:
            continue
        dur = len(x)/sr
        if not (3.0 <= dur <= 12.0): continue
        keep.append({"x": x, "sr": sr, "text": c["text"], "speaker": c["speaker"], "src": c["src"], "dur": dur})
    print(f"时长过滤后: {len(keep)}")
    return keep

# ---------- 4) 采样 + 归一化 + 保存 ----------
def sent_case(t):
    """ALL CAPS → 首字母大写句式 (仅用于 MT 输入)"""
    low = t.lower().capitalize()
    return low

def finalize(keep, lang, outdir, prefix, level):
    os.makedirs(outdir, exist_ok=True)
    # 按说话人分桶轮询采样 (LibriSpeech); AISHELL 用 src 前缀近似分桶
    if all("speaker" in k for k in keep):
        groups = {}
        for k in keep: groups.setdefault(k["speaker"], []).append(k)
        keys = sorted(groups)
        random.shuffle(keys)
        picked = []
        while len(picked) < N_PER_LANG and any(groups.values()):
            for k in keys:
                if groups[k]: picked.append(groups[k].pop(random.randrange(len(groups[k]))))
                if len(picked) >= N_PER_LANG: break
    else:
        random.shuffle(keep)
        picked = keep[:N_PER_LANG]
    recs = []
    for n, k in enumerate(picked[:N_PER_LANG], 1):
        x = k["x"].astype(np.float32)
        if k["sr"] != SR:
            from librosa import resample
            x = resample(x, orig_sr=k["sr"], target_sr=SR).astype(np.float32)
        # 电平归一化到合成语料水平 (active RMS), 峰值保护
        cur = active_rms(x)
        gain = level / (cur + 1e-9)
        peak = float(np.max(np.abs(x)))
        if peak * gain > 0.985:
            gain = 0.985 / (peak + 1e-9)
        y = x * gain
        sid = f"{prefix}{n:03d}"
        save_wav(f"{outdir}/{sid}.wav", y, SR)
        recs.append({"id": sid, "lang": lang, "text": k["text"],
                     "speaker": k.get("speaker"), "src": k["src"], "dur_s": round(len(y)/SR, 2),
                     "level_gain": round(float(gain), 3)})
    return recs

if __name__ == "__main__":
    level = synth_level()
    zh_keep = extract_aishell()
    en_keep = extract_libri()
    zh_recs = finalize(zh_keep, "zh", f"{D3}/real_zh", "rz", level)
    en_recs = finalize(en_keep, "en", f"{D3}/real_en", "re", level)
    with open(f"{D3}/d3_corpus.jsonl", "w") as f:
        for r in zh_recs + en_recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # 摘要
    spk_zh = {}
    spk_en = set(r["speaker"] for r in en_recs)
    # AISHELL 说话人验证: 用 CSV 转写反查
    csv_map = {}
    with open(f"{D3}/aishell1_test.csv") as f:
        rd = csv.DictReader(f)
        for row in rd:
            txt = (row["Text:LABEL"] or "").strip()
            spk = row["Audio:FILE"].split("/")[2] if "/" in row["Audio:FILE"] else "?"
            csv_map.setdefault(txt, set()).add(spk)
    amb = 0
    for r in zh_recs:
        s = csv_map.get(r["text"], set())
        if len(s) == 1: r["speaker"] = next(iter(s)); spk_zh[r["speaker"]] = spk_zh.get(r["speaker"], 0) + 1
        else: amb += 1
    with open(f"{D3}/d3_corpus.jsonl", "w") as f:
        for r in zh_recs + en_recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n中文: {len(zh_recs)} 句, 说话人分布: {spk_zh}, 转写歧义 {amb}")
    print(f"英文: {len(en_recs)} 句, 说话人数: {len(spk_en)}")
    dz = [r["dur_s"] for r in zh_recs]; de = [r["dur_s"] for r in en_recs]
    print(f"中文时长: 中位 {np.median(dz):.1f}s 范围 {min(dz):.1f}-{max(dz):.1f}")
    print(f"英文时长: 中位 {np.median(de):.1f}s 范围 {min(de):.1f}-{max(de):.1f}")
    print("完成: d3_corpus.jsonl")
