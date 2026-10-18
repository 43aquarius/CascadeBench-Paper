# -*- coding: utf-8 -*-
"""拉取 LibriSpeech dev-other 2 个行组 → 真实英文 babble 声源 (存 wav)"""
import io, os, time, json, random
import numpy as np
import soundfile as sf
import pyarrow.parquet as pq
import fsspec
from aiohttp import ClientTimeout

random.seed(42)
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D3 = os.path.join(ROOT, "d3_data")
URL = "https://hf-mirror.com/datasets/openslr/librispeech_asr/resolve/main/other/validation/0000.parquet"
OUT = f"{D3}/libri_babble_src"
os.makedirs(OUT, exist_ok=True)

def open_pf(url, tries=10):
    last = None
    for i in range(tries):
        try:
            fs = fsspec.filesystem("http", block_size=1024*1024,
                                   client_kwargs={"timeout": ClientTimeout(total=120, connect=20)})
            return pq.ParquetFile(fs.open(url, "rb"))
        except Exception as e:
            last = e; print(f"  open retry {i+1}: {str(e)[:90]}", flush=True); time.sleep(3+i*2)
    raise last

cands = []
for g in [0, 3, 6, 9, 12, 15, 18]:
    for attempt in range(5):
        try:
            pf = open_pf(URL)
            if g >= pf.metadata.num_row_groups:
                continue
            tbl = pf.read_row_group(g)
            n0 = len(cands)
            for i in range(tbl.num_rows):
                au = tbl.column("audio")[i].as_py()
                if not (isinstance(au, dict) and au.get("bytes")): continue
                spk = str(tbl.column("speaker_id")[i].as_py())
                cands.append({"b": au["bytes"], "spk": spk})
            print(f"组{g}: +{len(cands)-n0}", flush=True)
            break
        except Exception as e:
            print(f"  组{g} retry {attempt+1}: {str(e)[:90]}", flush=True); time.sleep(4)

print("候选:", len(cands))
# 挑 20 个不同说话人的 3-10s 片段
sel = []
seen = []
for c in cands:
    if len(sel) >= 20: break
    if seen.count(c["spk"]) >= 3: continue
    try:
        x, sr = sf.read(io.BytesIO(c["b"]), dtype="float32")
    except Exception:
        continue
    if x.ndim > 1: x = x.mean(axis=1)
    d = len(x)/sr
    if not (3.0 <= d <= 10.0): continue
    if abs(float(np.max(np.abs(x)))) < 1e-3: continue
    seen.append(c["spk"])
    sel.append((c["spk"], x, sr))
    sf.write(f"{OUT}/enb_{len(sel):02d}_spk{c['spk']}.wav", x, sr, subtype="PCM_16")
print(f"已存 {len(sel)} 个英文真实声源, 说话人分布:", __import__("collections").Counter(seen))
