#!/usr/bin/env python3
"""P1 核验: 六级真实 babble 阶梯上 Qwen3-ASR vs 两个专家系统的交叉位置
数据源: analysis_v15_real.json (从原始 JSONL 重算的持久化结果)"""
import json

import os
d = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "analysis_v15_real.json")))
A = d['asr_real_all']

# 六级 babble 阶梯 (SNR 从高到低)
levels = ['rb10', 'rb25', 'rb5', 'rb0', 'rbm25', 'rbm5']
labels = {'rb10': '+10', 'rb25': '+2.5', 'rb5': '+5', 'rb0': '0', 'rbm25': '-2.5', 'rbm5': '-5'}
order = ['rb10', 'rb5', 'rb25', 'rb0', 'rbm25', 'rbm5']
snr = {'rb10': 10, 'rb5': 5, 'rb25': 2.5, 'rb0': 0, 'rbm25': -2.5, 'rbm5': -5}
order.sort(key=lambda c: -snr[c])

systems = ['q31', 'q3', 'para16k', 'para8k']
names = {'q31': 'Qwen-Audio', 'q3': 'Qwen3-ASR', 'para16k': '16kHz-spec', 'para8k': 'tel-spec'}

for lang in ['zh', 'en']:
    print(f"\n=== {lang}: 六级真实 babble 误差 (%) ===")
    print(f"{'SNR':>6} | " + " | ".join(f"{names[s]:>11}" for s in systems) + " | q3 vs 16k | q3 vs tel")
    for c in order:
        vals = {}
        for s in systems:
            cell = A[s].get(f'{c}/{lang}')
            vals[s] = cell['err'] if cell else None
        v16 = vals['para16k']; vt = vals['para8k']; vq3 = vals['q3']
        c1 = 'q3 BETTER' if vq3 < v16 else 'q3 WORSE'
        c2 = ('q3 BETTER' if vq3 < vt else 'q3 WORSE') if vt is not None else 'n/a'
        fmt = lambda v: f"{v:>11.1f}" if v is not None else f"{'—':>11}"
        print(f"{labels[c]:>6} | " + " | ".join(fmt(vals[s]) for s in systems) + f" | {c1:>9} | {c2:>9}")

# 交叉点确认
print("\n=== 交叉位置确认 ===")
for lang in ['zh', 'en']:
    prev_better_16 = None
    for c in order:
        vq3 = A['q3'][f'{c}/{lang}']['err']; v16 = A['para16k'][f'{c}/{lang}']['err']
        b16 = vq3 < v16
        if prev_better_16 is not None and b16 != prev_better_16:
            print(f"{lang}: q3 vs 16kHz-spec 在 {labels[c]} dB 反转 (q3={vq3:.1f}, 16k={v16:.1f})")
        prev_better_16 = b16
    # 每个水平分别打印对 tel 的比较
    for c in order:
        vq3 = A['q3'][f'{c}/{lang}']['err']
        vt = A['para8k'].get(f'{c}/{lang}', {}).get('err')
        if vt is None:
            print(f"  {lang} {labels[c]:>5}dB: q3={vq3:6.1f}  tel-spec=无数据")
        else:
            print(f"  {lang} {labels[c]:>5}dB: q3={vq3:6.1f}  tel-spec={vt:6.1f}  {'q3 better' if vq3<vt else 'q3 WORSE'}")

# Clean 基线
print("\n=== clean_r / revr / rn0 基线 (供参考) ===")
for c in ['clean_r', 'revr', 'rn0']:
    for lang in ['zh', 'en']:
        row = []
        for s in systems:
            cell = A[s].get(f'{c}/{lang}')
            row.append(f"{names[s]}={cell['err']:.1f}" if cell else f"{names[s]}=无数据")
        print(f"{c}/{lang}: " + ", ".join(row))
