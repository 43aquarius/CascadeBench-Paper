#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""升级项c: 主网格合成语音 × MIT实测RIR (rev_mit 条件)
与 D3 revr 完全相同协议: 3房间轮换, fftconvolve截断, peak保持, 8k版同步生成
输出: research/audio/perturbed/rev_mit/ + perturbed_8k/rev_mit/"""
import os, sys, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import soundfile as sf
import io
from scipy.signal import fftconvolve, resample_poly

SR = 16000
D3 = os.path.join(ROOT, "d3_data")
TTS = os.path.join(ROOT, "audio", "tts")
OUT = os.path.join(ROOT, "audio", "perturbed", "rev_mit")
OUT8 = os.path.join(ROOT, "audio", "perturbed_8k", "rev_mit")
CORPUS = [json.loads(l) for l in open(os.path.join(ROOT, "corpus", "corpus.jsonl"))]

SEL = ["h201_DramaRoom_MITCampus_1txts.wav", "h202_Diningroom_1txts.wav", "h104_Classroom_2txts.wav"]

def load_sel_rirs():
    import pyarrow.parquet as pq
    tbl = pq.read_table(f"{D3}/mit_ir.parquet")
    out = {}
    for i in range(tbl.num_rows):
        row = {c: tbl.column(c)[i].as_py() for c in tbl.column_names}
        au = row["audio"]
        b = au["bytes"] if isinstance(au, dict) else None
        if not b: continue
        name = (au.get("path") if isinstance(au, dict) else "") or ""
        if name not in SEL: continue
        x, sr = sf.read(io.BytesIO(b), dtype="float32")
        if x.ndim > 1: x = x.mean(axis=1)
        if sr != SR:
            if abs(sr / SR - 2.0) < 0.01:
                x = resample_poly(x, 1, 2).astype(np.float32)
            elif abs(sr / SR - 4.0) < 0.01:
                x = resample_poly(x, 1, 4).astype(np.float32)
            else:
                x = resample_poly(x, 1, int(round(sr / SR))).astype(np.float32)
        out[name] = x
        print(f"loaded {name}: {len(x)/SR:.2f}s @16k")
    assert len(out) == 3, f"expected 3 RIRs, got {list(out)}"
    return [out[n] for n in SEL]  # 与 SEL 顺序一致

def main():
    os.makedirs(OUT, exist_ok=True); os.makedirs(OUT8, exist_ok=True)
    rirs = load_sel_rirs()
    n_done = 0
    for n, rec in enumerate(CORPUS):
        sid = rec["id"]
        op = f"{OUT}/{sid}.wav"; op8 = f"{OUT8}/{sid}.wav"
        if os.path.exists(op) and os.path.exists(op8):
            n_done += 1; continue
        x, sr = sf.read(f"{TTS}/{sid}.wav", dtype="float32")
        assert sr == SR
        h = rirs[n % 3]
        y = fftconvolve(x, h)[:len(x)]
        y = (y / (np.max(np.abs(y)) + 1e-9) * (np.max(np.abs(x)) + 1e-9)).astype(np.float32)
        sf.write(op, y, SR)
        y8 = resample_poly(y, 1, 2)
        sf.write(op8, y8, 8000)
        n_done += 1
        if n_done % 60 == 0:
            print(f"  {n_done}/{len(CORPUS)}", flush=True)
    print(f"rev_mit generated: {n_done} utts")
    # 报告
    from scipy.io import wavfile
    rep = {"n": n_done, "rir_rotation": [{"name": n, "t60": t, "drr_db": d} for n, t, d in
            [("h201_DramaRoom_MITCampus_1txts.wav", 0.5, -0.9),
             ("h202_Diningroom_1txts.wav", 0.499, 1.3),
             ("h104_Classroom_2txts.wav", 0.495, 13.1)]]}
    json.dump(rep, open(f"{OUT}/_report.json", "w"), indent=1)
    print(json.dumps(rep, indent=1))

if __name__ == "__main__":
    main()
