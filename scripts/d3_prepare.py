# -*- coding: utf-8 -*-
"""D3 音频制备: 真实语音 × {clean, 真实RIR, 真实babble×3SNR, 真实交通噪声}
- MIT IR Survey: 测 T60/DRR, 选 3 个 T60≈0.5s 房间
- 真实 babble: 40 个真实语音声源 (20 AISHELL + 20 LibriSpeech), 与合成 babble 同算法
- 交通噪声: ESC-50 train 类别
- 全部 CRC32 种子, 可复现
输出: research/audio/d3/{cond}/*.wav + d3_8k/ + d3_audio_report.json
"""
import io, os, sys, json, glob, zipfile, zlib, random
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly, fftconvolve

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from perturb import active_rms, save_wav, load_wav, mix_at_snr, build_babble, SR

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D3D = os.path.join(ROOT, "d3_data")
OUT = os.path.join(ROOT, "audio", "d3")
CORPUS = [json.loads(l) for l in open(f"{D3}/d3_corpus.jsonl")]

def seed_of(key):
    return zlib.crc32(key.encode()) & 0xffffffff

# ---------- 1) MIT IR 处理 ----------
def load_mit_irs():
    import pyarrow.parquet as pq
    tbl = pq.read_table(f"{D3}/mit_ir.parquet")
    irs = []
    for i in range(tbl.num_rows):
        row = {c: tbl.column(c)[i].as_py() for c in tbl.column_names}
        au = row["audio"]
        b = au["bytes"] if isinstance(au, dict) else None
        if not b: continue
        name = (au.get("path") if isinstance(au, dict) else "") or f"ir{row.get('id')}"
        x, sr = sf.read(io.BytesIO(b), dtype="float32")
        if x.ndim > 1: x = x.mean(axis=1)
        irs.append({"name": name, "x": x, "sr": sr})
    return irs

def measure_ir(h, sr):
    """Schroeder 反向积分 T60 (-5..-25dB 拟合) + DRR (峰值±2.5ms)"""
    h2 = (h.astype(np.float64)) ** 2
    e = np.cumsum(h2[::-1])[::-1]  # 反向积分能量
    if e[0] <= 0: return None
    db = 10 * np.log10(e / e[0] + 1e-20)
    # 找 -5 和 -25 的时刻
    t5 = t25 = None
    for i in range(len(db)):
        if db[i] <= -5 and t5 is None: t5 = i
        if db[i] <= -25: t25 = i; break
    if t5 is None or t25 is None or t25 <= t5: return None
    seg = db[t5:t25+1]
    ts = np.arange(len(seg)) / sr
    k, c = np.polyfit(ts, seg, 1)
    t60 = -60.0 / k if k < 0 else None
    if t60 is None or not (0.05 < t60 < 5.0): return None
    # DRR: 直接声 ±2.5ms
    pk = int(np.argmax(np.abs(h)))
    w = int(0.0025 * sr)
    d = float(np.sum(h2[max(0, pk-w):pk+w]))
    r = float(np.sum(h2) - d)
    drr = 10 * np.log10((d + 1e-20) / (r + 1e-20))
    return {"t60": round(float(t60), 3), "drr_db": round(float(drr), 1)}

def prepare_rirs():
    print("=== MIT IR 测量与选择 ===", flush=True)
    irs = load_mit_irs()
    print(f"IR 总数: {len(irs)}")
    # 降采样到 16k 并测量
    cands = []
    for ir in irs:
        x = ir["x"]
        if ir["sr"] != SR:
            from librosa import resample
            x = resample(x, orig_sr=ir["sr"], target_sr=SR).astype(np.float32)
        if len(x) < SR // 10: continue
        m = measure_ir(x, SR)
        if m is None: continue
        m.update({"name": ir["name"], "h": x})
        cands.append(m)
    print(f"有效测量: {len(cands)}")
    # T60 匹配 0.5s (与合成 rev 一致), 偏好室内对话空间
    PREF = ["Room", "Office", "Kitchen", "Hallway", "Apartment", "Studio", "Classroom",
            "Cafe", "Restaurant", "Library", "Store", "Lab", "Dorm", "Home", "Living"]
    def pref_score(c):
        n = c["name"]
        return (0 if any(p.lower() in n.lower() for p in PREF) else 1, abs(c["t60"] - 0.5))
    # 过滤 T60 范围
    pool = [c for c in cands if 0.3 <= c["t60"] <= 0.75]
    pool.sort(key=pref_score)
    sel = []
    used_loc = set()
    for c in pool:
        loc = c["name"].split("_")[1] if len(c["name"].split("_")) > 1 else c["name"]
        if loc in used_loc: continue  # 空间类型多样化
        sel.append(c); used_loc.add(loc)
        if len(sel) >= 3: break
    for c in sel:
        print(f"  选中: {c['name']}: T60={c['t60']}s DRR={c['drr_db']}dB")
    return sel, cands

# ---------- 2) 真实 babble 声源 ----------
def prepare_babble_sources():
    pool = []  # 文件路径列表 (build_babble 接受路径)
    for f in sorted(glob.glob(f"{D3}/libri_babble_src/enb_*.wav")):
        pool.append(f)
    # 中文 (AISHELL S0002/S0005, 选 20 个 3-10s 存盘)
    zh_files = sorted(glob.glob(f"{D3}/aishell_babble/train/S000*/*.wav"))
    rng = random.Random(20261018)
    rng.shuffle(zh_files)
    os.makedirs(f"{D3}/zh_babble_src", exist_ok=True)
    n_zh = 0
    for f in zh_files:
        if n_zh >= 20: break
        x = load_wav(f)
        if not (3.0 <= len(x)/SR <= 10.0): continue
        if float(np.max(np.abs(x))) < 0.02: continue
        out = f"{D3}/zh_babble_src/zhb_{n_zh+1:02d}.wav"
        save_wav(out, x, SR)
        pool.append(out); n_zh += 1
    print(f"真实 babble 声源: en={len(pool)-n_zh} zh={n_zh} 总={len(pool)}")
    return pool

# ---------- 3) 交通噪声池 ----------
def prepare_transport():
    z = zipfile.ZipFile(f"{D3}/ESC50.zip")
    import csv, io as _io
    rd = list(csv.DictReader(_io.StringIO(z.read("ESC-50-master/meta/esc50.csv").decode())))
    tr = [r["filename"] for r in rd if r["category"] == "train"]
    segs = []
    for fn in tr:
        b = z.read(f"ESC-50-master/audio/{fn}")
        x, sr = sf.read(io.BytesIO(b), dtype="float32")
        if x.ndim > 1: x = x.mean(axis=1)
        if sr != SR:
            from librosa import resample
            x = resample(x, orig_sr=sr, target_sr=SR).astype(np.float32)
        segs.append(x)
    pool = np.concatenate(segs)
    print(f"交通噪声池: {len(tr)} 片段, 总时长 {len(pool)/SR:.0f}s")
    return pool

# ---------- 4) 生成条件 ----------
CONDS = ["clean_r", "revr", "rb5", "rb0", "rbm5", "rn0"]

def gen_all(rir_sel, babble_pool, transport):
    report = {"conditions": CONDS, "n_utts": len(CORPUS), "rir": [
        {"name": c["name"], "t60": c["t60"], "drr_db": c["drr_db"]} for c in rir_sel]}
    os.makedirs(f"{OUT}", exist_ok=True)
    stoi_mod = None
    try:
        from pystoi import stoi as stoi_mod
    except Exception:
        pass
    stois = {c: [] for c in CONDS}
    for cond in CONDS:
        os.makedirs(f"{OUT}/{cond}", exist_ok=True)
        os.makedirs(f"{OUT}/../d3_8k/{cond}", exist_ok=True)
    for n, rec in enumerate(CORPUS):
        sid, lang = rec["id"], rec["lang"]
        x = load_wav(f"{D3}/real_zh/{sid}.wav" if lang == "zh" else f"{D3}/real_en/{sid}.wav")
        clean = x
        for cond in CONDS:
            opath = f"{OUT}/{cond}/{sid}.wav"
            if cond == "clean_r":
                y = x
            elif cond == "revr":
                h = rir_sel[n % 3]["h"]
                y = fftconvolve(x, h)[:len(x)]
                y = (y / (np.max(np.abs(y)) + 1e-9) * (np.max(np.abs(x)) + 1e-9)).astype(np.float32)
            elif cond in ("rb5", "rb0", "rbm5"):
                rng = np.random.RandomState(seed_of(f"{cond}/{sid}"))
                noise = build_babble(babble_pool, len(x)/SR + 0.5, rng)
                snr = {"rb5": 5, "rb0": 0, "rbm5": -5}[cond]
                y = mix_at_snr(x, noise, snr, rng).astype(np.float32)
            else:  # rn0
                rng = np.random.RandomState(seed_of(f"{cond}/{sid}"))
                start = rng.randint(0, max(1, len(transport) - len(x) - 1))
                noise = transport[start:start+len(x)]
                y = mix_at_snr(x, noise, 0, rng).astype(np.float32)
            save_wav(opath, y, SR)
            y8 = resample_poly(y, 1, 2)
            save_wav(f"{OUT}/../d3_8k/{cond}/{sid}.wav", y8, 8000)
            if stoi_mod is not None and cond != "clean_r" and len(y) == len(clean):
                try:
                    s = stoi_mod(clean, y, SR, extended=False)
                    stois[cond].append(float(s))
                except Exception:
                    pass
        if (n+1) % 30 == 0:
            print(f"  {n+1}/{len(CORPUS)}", flush=True)
    report["stoi_mean"] = {c: (round(float(np.mean(v)), 3) if v else None) for c, v in stois.items()}
    return report

if __name__ == "__main__":
    rir_sel, all_irs = prepare_rirs()
    babble_pool = prepare_babble_sources()
    transport = prepare_transport()
    report = gen_all(rir_sel, babble_pool, transport)
    # 全部 IR 的统计摘要 (供论文报告)
    t60s = [c["t60"] for c in all_irs]
    drrs = [c["drr_db"] for c in all_irs]
    report["mit_survey_stats"] = {
        "n_measured": len(all_irs),
        "t60_median": round(float(np.median(t60s)), 2),
        "t60_p25_p75": [round(float(np.percentile(t60s, 25)), 2), round(float(np.percentile(t60s, 75)), 2)],
        "drr_median_db": round(float(np.median(drrs)), 1),
        "drr_p25_p75": [round(float(np.percentile(drrs, 25)), 1), round(float(np.percentile(drrs, 75)), 1)],
    }
    with open(f"{D3}/d3_audio_report.json", "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in report.items() if k != "conditions"}, ensure_ascii=False, indent=1))
    print("完成")
