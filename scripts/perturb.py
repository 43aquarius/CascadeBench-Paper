# -*- coding: utf-8 -*-
"""CascadeBench 扰动注入模块: 8类声学信道退化 + SNR梯度
C0 clean | C1 babble@10dB | C2 babble@0dB | C3 reverb RT60=0.5s | C4 narrowband 8k
C5 opus 8kbps | C6 packet loss 15% | C7 clipping 0.3 | C8 tempo 1.15x
+ SNR扫描: n20/n15/n5 (10/0在主网格)
所有随机性固定种子, 完全可复现"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import os, subprocess, tempfile
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly, fftconvolve

SR = 16000

def load_wav(path):
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1: x = x.mean(axis=1)
    if sr != SR:
        from librosa import resample
        x = resample(x, orig_sr=sr, target_sr=SR)
    return x.astype(np.float32)

def save_wav(path, x, sr=SR):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sf.write(path, x.astype(np.float32), sr, subtype="PCM_16")

# ---------- 语音活动检测(能量法, 用于SNR计算) ----------
def active_rms(x, sr=SR, frame=0.025):
    """返回语音活跃帧的RMS(标量)"""
    fl = int(sr*frame)
    n = max(1, len(x)//fl)
    e = np.array([np.mean(x[i*fl:(i+1)*fl]**2) for i in range(n)])
    thr = np.percentile(e, 60) * 0.5
    act = e[e > thr]
    if len(act) == 0: act = e
    return float(np.sqrt(np.mean(act)))

def mix_at_snr(speech, noise, snr_db, rng):
    """把噪声缩放后叠加到语音, SNR基于语音活跃段能量"""
    noise = noise[:len(speech)]
    if len(noise) < len(speech):
        noise = np.pad(noise, (0, len(speech)-len(noise)))
    p_s = active_rms(speech) ** 2
    p_n = float(np.mean(noise**2)) + 1e-12
    target = p_s / (10 ** (snr_db/10))
    scale = float(np.sqrt(target / p_n))
    return speech + noise * scale

# ---------- Babble噪声构造 ----------
def build_babble(babble_wavs, dur_s, rng, sr=SR):
    """从多个babble源音频随机拼接混合成dur_s长度的babble"""
    need = int(dur_s*sr) + sr
    streams = []
    for w in babble_wavs:
        x = load_wav(w)
        if len(x) < sr: continue
        streams.append(x)
    # 3路叠加, 每路独立随机拼接
    mix = np.zeros(need, np.float32)
    for _ in range(3):
        pos = 0
        while pos < need:
            src = streams[rng.randint(len(streams))]
            start = rng.randint(0, max(1, len(src)-sr//2))
            seg = src[start:start+rng.randint(sr//2, sr)]
            end = min(pos+len(seg), need)
            mix[pos:end] += seg[:end-pos]
            pos += len(seg)
    return mix / (np.max(np.abs(mix)) + 1e-9)

# ---------- 各扰动 ----------
def p_reverb(x, rt60=0.5, sr=SR, seed=0):
    rng = np.random.RandomState(seed)
    n_taps = int(sr*rt60)
    h = rng.randn(n_taps) * np.exp(-6.9*np.arange(n_taps)/(sr*rt60))
    h[0] = 1.0  # 直达声
    h = h / np.sqrt(np.sum(h**2))
    y = fftconvolve(x, h)[:len(x)]
    return (y / (np.max(np.abs(y))+1e-9) * (np.max(np.abs(x))+1e-9)).astype(np.float32)

def p_narrowband(x, sr=SR):
    y = resample_poly(x, 1, 2)      # 16k → 8k
    y = resample_poly(y, 2, 1)      # 8k → 16k
    return y.astype(np.float32)

def p_opus(x, sr=SR, bitrate="8k"):
    with tempfile.TemporaryDirectory() as td:
        wi, wo = os.path.join(td,"in.wav"), os.path.join(td,"out.opus")
        save_wav(wi, x, sr)
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",wi,"-c:a","libopus","-b:a",bitrate,"-ar","16000","-ac","1",wo], check=True)
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",wo,"-ar","16000","-ac","1",os.path.join(td,"dec.wav")], check=True)
        y, _ = sf.read(os.path.join(td,"dec.wav"), dtype="float32")
    return y.astype(np.float32)

def p_packet_loss(x, rate=0.15, sr=SR, seed=0, frame=0.02):
    rng = np.random.RandomState(seed)
    fl = int(sr*frame)
    n = int(np.ceil(len(x)/fl))
    y = x.copy()
    for i in range(n):
        if rng.rand() < rate:
            y[i*fl:(i+1)*fl] = 0
    return y

def p_clip(x, thresh=0.3):
    return np.clip(x, -thresh, thresh).astype(np.float32)

def p_tempo(x, speed=1.15, sr=SR):
    with tempfile.TemporaryDirectory() as td:
        wi = os.path.join(td,"in.wav")
        save_wav(wi, x, sr)
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",wi,"-filter:a",f"atempo={speed}","-ar","16000","-ac","1",os.path.join(td,"out.wav")], check=True)
        y, _ = sf.read(os.path.join(td,"out.wav"), dtype="float32")
    return y.astype(np.float32)

# ---------- 批处理入口 ----------
CONDITIONS = {
    "clean": None,
    "n10":   {"type":"babble","snr":10},
    "n0":    {"type":"babble","snr":0},
    "rev":   {"type":"reverb"},
    "nb":    {"type":"narrowband"},
    "opus":  {"type":"opus"},
    "pl":    {"type":"pl"},
    "clip":  {"type":"clip"},
    "tempo": {"type":"tempo"},
    # SNR扫描 (额外)
    "n20":   {"type":"babble","snr":20},
    "n15":   {"type":"babble","snr":15},
    "n5":    {"type":"babble","snr":5},
}

def apply_condition(x, cond, babble_wavs, seed, sr=SR):
    cfg = CONDITIONS[cond]
    if cfg is None: return x
    t = cfg["type"]
    if t == "babble":
        rng = np.random.RandomState(seed)
        noise = build_babble(babble_wavs, len(x)/sr, rng, sr)
        return mix_at_snr(x, noise, cfg["snr"], rng)
    if t == "reverb": return p_reverb(x, seed=seed, sr=sr)
    if t == "narrowband": return p_narrowband(x, sr)
    if t == "opus": return p_opus(x, sr)
    if t == "pl": return p_packet_loss(x, seed=seed, sr=sr)
    if t == "clip": return p_clip(x)
    if t == "tempo": return p_tempo(x, sr=sr)
    raise ValueError(t)

if __name__ == "__main__":
    import json, glob, sys
    BASE = os.path.join(ROOT, "audio")
    corpus = [json.loads(l) for l in open(os.path.join(ROOT, "corpus", "corpus.jsonl"))]
    sweep_ids = set(json.load(open(os.path.join(ROOT, "corpus", "sweep_ids.json"))))
    babble_wavs = sorted(glob.glob(f"{BASE}/tts/babble_*.wav"))
    assert len(babble_wavs) >= 10, "需先运行TTS生成babble源"
    main_conds = ["clean","n10","n0","rev","nb","opus","pl","clip","tempo"]
    sweep_conds = ["n20","n15","n5"]
    count = 0
    for rec in corpus:
        sid = rec["id"]
        src = f"{BASE}/tts/{sid}.wav"
        if not os.path.exists(src): print("MISS", sid); continue
        x = load_wav(src)
        conds = main_conds + (sweep_conds if sid in sweep_ids else [])
        for cond in conds:
            out16 = f"{BASE}/perturbed/{cond}/{sid}.wav"
            if os.path.exists(out16): continue
            seed = hash(sid+cond) % (2**31)
            try:
                y = apply_condition(x, cond, babble_wavs, seed)
                save_wav(out16, y)
                # 8k版本 (供paraformer-8k)
                y8 = resample_poly(y, 1, 2)
                save_wav(f"{BASE}/perturbed_8k/{cond}/{sid}.wav", y8, 8000)
                count += 1
            except Exception as e:
                print("ERR", sid, cond, repr(e)[:100])
    print(f"perturbation done, generated {count} files")
