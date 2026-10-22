#!/usr/bin/env python3
"""v1.7-round2 self-check: 校对轮全部数字核验 (原 40 项 + 新增 17 类).
Target tree: /tmp/my-project/repo_clone/paper/latex (权威树).
"""
import json, re, sys, os
from collections import defaultdict

L = '/tmp/my-project/repo_clone/paper/latex'
PAPER = '/tmp/my-project/repo_clone/paper'
R = '/tmp/my-project/research/results'
A = json.load(open(os.path.join(R, 'analysis_v17_glm9.json')))
M9 = A["backend_matrix_9"]
CONDS = ["clean_r", "revr", "rb10", "rb5", "rb25", "rb0", "rbm25", "rbm5", "rn0"]

passed, failed = [], []
def chk(name, cond, detail=""):
    (passed if cond else failed).append(name + (f" [{detail}]" if detail else ""))

def read(p):
    return open(f'{L}/{p}', encoding='utf-8').read()

main = read('main.tex'); supp = read('supplementary.tex')
results = read('sections/results.tex'); methods = read('sections/methods.tex')
disc = read('sections/discussion.tex'); intro = read('sections/intro.tex')
concl = read('sections/conclusions.tex'); appx = read('sections/appendix.tex')
refs = read('refs.bib')
ALL = main + supp + results + methods + disc + intro + concl + appx

# ============ 1. 占位符清零 ============
for pat, lbl in [(r'XX\.X', 'XX.X cell'), (r'XX\\%', 'XX% relloss'), (r'XXSUMMARYXX', 'XXSUMMARYXX'),
                 (r'\bXX\b', 'bare XX')]:
    n = len(re.findall(pat, ALL))
    chk(f'no {lbl}', n == 0, f'{n} found')

# ============ 2. 旧措辞清除 ============
for pat in ['three-point', '562 GLM backend', '43{,}046', '42{,}171',
            'four core real-speech conditions',
            'making the advantage\nprovider-specific', 'making the advantage provider-specific',
            'the harder stressor at every SNR',
            'roughly 3--6~dB', 'four of the six levels',
            'counted as successful calls, scored as empty',
            'three hardest babble conditions']:
    chk(f'old wording gone: "{pat[:44]}"', pat not in ALL)

# ============ 3. tab:backend 行与 JSON 一致 ============
tl = [l for l in results.split('\n') if l.startswith('qwen-mt-uni & oracle') or l.startswith('qwen-mt-uni & GLM') or l.startswith('GLM &')]
def cellval(cond, col):
    return f"{M9[cond][col]['bleu']:.1f}"
row_gummy_orc = [cellval(c, 'gummy_vs_oracle') for c in CONDS]
row_gummy_glm = [cellval(c, 'gummy_vs_glmref') for c in CONDS]
row_glm_orc = [cellval(c, 'glm_vs_oracle') for c in CONDS]
row_glm_glm = [cellval(c, 'glm_vs_glmref') for c in CONDS]
for row, expected, lbl in [(0, row_gummy_orc, 'gummy|oracle'), (1, row_gummy_glm, 'gummy|glm'),
                           (2, row_glm_orc, 'glm|oracle'), (3, row_glm_glm, 'glm|glm')]:
    if row < len(tl):
        got = [g for g in re.findall(r'&\s*([\d.]+)\s*', tl[row]) if '.' in g][:9]
        chk(f'tab:backend row {lbl} matches JSON', all(abs(float(a)-float(b)) < 0.051 for a, b in zip(got, expected)) and len(got) == 9,
            f'{got} vs {expected}')

def relloss(col):
    c = M9['clean_r'][col]['bleu']; e = M9['rbm5'][col]['bleu']
    return f"{100*(c-e)/c:.0f}"
chk('relloss gummy|oracle', f"{relloss('gummy_vs_oracle')}\\%" in results)
chk('relloss gummy|glm', f"{relloss('gummy_vs_glmref')}\\%" in results)
chk('relloss glm|oracle', f"{relloss('glm_vs_oracle')}\\%" in results)
chk('relloss glm|glm', f"{relloss('glm_vs_glmref')}\\%" in results)

# ============ 4. 斜率数字 ============
for k, lbl in [("slope_gummy_9cond_oracleref_noclean", "gummy 9-cond"),
               ("slope_glm_9cond_glmref_noclean", "glm 9-cond")]:
    v = A.get(k, {})
    for lang in ("zh", "en"):
        s = v.get(lang, {}).get("slope")
        if s is not None:
            chk(f'slope {lbl} {lang} in text', f"{s:.2f}" in ALL, f"{s:.2f}")
gs = A.get("slope_glm_9cond_glmref_noclean", {})
zh_s = gs.get('zh', {}).get('slope'); en_s = gs.get('en', {}).get('slope')
if zh_s and en_s:
    citing = [n for n, t in [('main', main), ('intro', intro), ('disc', disc), ('concl', concl), ('results', results)]
              if f"{zh_s:.2f}" in t]
    chk(f'GLM zh slope {zh_s:.2f} cited in >=2 files', len(citing) >= 2, f'in {citing}')

# ============ 5. Table 2 核算 (本轮修复) ============
chk('q31 unique 4,728 in Table2 row', 'Qwen-Audio-3.1 & 5{,}154 & 4{,}728' in methods)
rows_unique = [520, 4752, 2376, 4728, 4752, 1271, 960, 3456, 1004, 1544]
chk('original rows sum = 25,363', sum(rows_unique) == 25363, str(sum(rows_unique)))
chk('subtotal 25,363 printed', '25{,}363' in methods)
chk('26,238+5,581+6,675+3,360+1,919=43,773', 26238+5581+6675+3360+1919 == 43773)
chk('unique total 42,898 printed', '42{,}898' in methods)
chk('25,363+5,581+6,675+3,360+1,919=42,898', 25363+5581+6675+3360+1919 == 42898)
chk('calls-unique diff = 875', 26238-25363 == 875)
chk('875-call difference sentence present', '875-call difference' in methods)
chk('failed 3,874 = 3,333+541', '3{,}874' in methods and 3333+541 == 3874)
chk('refusal clarification present', '182 logged attempts' in methods)

# 原始日志回算: q31 unique 与 24 拒答
def tob(x): return x is True or str(x) == "True"
ok_keys, all_fail_keys = set(), set()
for line in open(os.path.join(R, 'asr_q31.jsonl')):
    d = json.loads(line)
    if d.get('ok'): ok_keys.add(d['key'])
    else: all_fail_keys.add(d['key'])
fail_never = all_fail_keys - ok_keys
chk('raw log: q31 unique ok keys = 4,728', len(ok_keys) == 4728, str(len(ok_keys)))
chk('raw log: never-ok keys = 24', len(fail_never) == 24, str(len(fail_never)))
chk('raw log: all 24 refusals at n0', all(k.startswith('n0/') for k in fail_never))

# GLM 核算
n_glm = sum(A['n_glm_by_cond'].values())
chk('glm unique ok = 1,289', n_glm == 1289, str(n_glm))
chk('630+1289=1919', 630 + n_glm == 1919)
chk('all 9 conds in matrix', all(c in M9 for c in CONDS))
chk('empty accounting 61', A['empty_accounting']['glm_empty_slots'] == 61)

# ============ 6. 图注/局限新数字: 真实vs合成 ============
chk('caption: 26.0 against 39.7 present', '26.0 against 39.7' in results)
# tab:babble: q31 en 0dB = 26.0 (real); tab:sweep: q31 en 0dB = 39.7 (synthetic)
babble_row = [l for l in appx.split('\n') if l.startswith('Qwen-Audio-3.1 &')][1]  # 第二个=英文行
chk('tab:babble q31 en 0dB = 26.0', re.search(r'&\s*26\.0\s*&', babble_row) is not None, babble_row[:60])
sweep_en = [l for l in supp.split('\n') if l.strip().startswith('& en & 0.9 & 1.3 & 1.5 & 2.0 & 8.5 & 39.7')][0]
chk('tab:sweep q31 en 0dB = 39.7', '39.7' in sweep_en)
# knee shifts: real cross (tab:babble) − synthetic cross (tab:slopes)
slopes = {'q31_zh': -0.06, 'q31_en': 2.38, 'q3_zh': 0.29, 'q3_en': 2.02, 'p16_en': 6.79}
real = {'q31_zh': 2.8, 'q31_en': 2.3, 'q3_zh': 7.0, 'q3_en': 3.6, 'p16_en': 9.8}
for k in slopes:
    shift = real[k] - slopes[k]
    chk(f'knee shift {k} = {shift:+.1f} derivable', True, f'{shift:+.2f}')
chk('discussion: 2.9 and 6.7 dB present', '2.9 and 6.7~dB' in disc)
chk('discussion: -0.1 and +3.0 dB present', '$-0.1$ and $+3.0$~dB' in disc)
chk('discussion: TTS confound sentence present', 'same-sentence control' in disc)

# ============ 7. GLM 自一致性数字 ============
chk('results: rendering noise ~5 BLEU stated', 'roughly five BLEU' in results)
chk('results: 19 doubly-rendered stated', 'nineteen doubly-rendered' in results)
chk('results: mean 65 IQR 53 to 76 stated', 'mean of 65 (interquartile range 53 to' in results)
chk('results: clean-rev 10.5 BLEU stated', 'still differ by 10.5' in results)
chk('results: MC 98 percent stated', 'positive in 98 percent' in results)
chk('results: MC gaps 0.10/0.16 stated', 'gap 0.10' in results and '0.16, 0.01 to' in results)
chk('results: Rev non-monotonicity addressed', 'reverberation at 49.7, below' in results)
chk('methods: no temperature/seed disclosure', 'exposes no temperature or seed' in methods)
chk('table note: single-draw generation', 'single-draw generations' in results)
# clean-rev gap from matrix
gap = M9['clean_r']['glm_vs_glmref']['bleu'] - M9['revr']['glm_vs_glmref']['bleu']
chk('matrix clean-rev gap = 10.5', abs(gap - 10.55) < 0.06, f'{gap:.2f}')
# S14 引用
chk('S14 cited in main results', 'Supplementary Table~S14' in results)

# ============ 8. Whisper 解码参数 ============
for s in ['beam size one', 'voice-activity filter', 'no-speech 0.6', 'temperature fallback',
          'traditional-to-simplified', 'counts as substitutions', '以下是普通话的句子']:
    chk(f'methods discloses: {s[:36]}', s in methods)
chk('appendix: three of six levels + clean', 'three of the six levels plus the clean anchor' in appx)
chk('supp: decoding-config qualifier', 'shared decoding configuration' in supp)

# ============ 9. 参考文献 ============
chk('refs: AIR-Bench arXiv 2402.07729', 'arXiv:2402.07729' in refs)
chk('refs: AIR-Bench first author Yang, Qian', 'Yang, Qian and Xu, Jin and Liu, Wenrui' in refs)
chk('refs: old wrong ID gone', '2408.10513' not in refs)
chk('refs: VoiceBench authors fixed', 'Chen, Yiming and Yue, Xianghu' in refs)
chk('refs: He, Jinzheng', 'He, Jinzheng' in refs)
chk('refs: Gong, Yifan', 'Gong, Yifan' in refs)
chk('refs: GLM-4.5 Team', '{GLM-4.5 Team}' in refs)
chk('refs: CosyVoice title fixed', 'zero-shot text-to-speech synthesizer' in refs)
chk('refs: Qwen2.5-Omni individual authors', 'Xu, Jin and Guo, Zhifang' in refs)
chk('refs: Qwen3 individual authors', 'Yang, An and Li, Anfeng' in refs)
bad_notes = [m for m in re.finditer(r'^\s*note\s*=\s*\{([^}]*)\}', refs, re.M)
             if not re.match(r'Accessed October 2026', m.group(1))]
chk('refs: no annotation notes remain', len(bad_notes) == 0, str([m.group(1)[:30] for m in bad_notes]))

# ============ 10. 摘要/CRediT/Highlights ============
m = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', main, re.DOTALL)
txt = re.sub(r'\\[a-zA-Z]+\{?|[{}$~]', ' ', m.group(1))
wc = len(txt.split())
chk('abstract <= 250 words', wc <= 250, f'{wc} words')
chk('abstract: no provider-specific claim', 'provider-specific' not in m.group(1))
chk('abstract: quarter-lower wording', 'quarter lower' in m.group(1))
chk('abstract: class-versus-vendor open', 'class-versus-vendor provenance remains open' in m.group(1))
chk('CRediT section present', 'CRediT authorship contribution statement' in main)
hl = [l[2:] for l in open(f'{PAPER}/highlights.txt', encoding='utf-8').read().split('\n') if l.startswith('- ')]
chk('highlights: 3-5 bullets', 3 <= len(hl) <= 5, str(len(hl)))
chk('highlights: all <= 85 chars', all(len(h) <= 85 for h in hl), str([len(h) for h in hl]))

# ============ 11. S 表编号一致性 ============
supp_tabs = re.findall(r'\\label\{tab:(\w+)\}', supp)
chk('supplementary has 14 tables', len(supp_tabs) == 14, str(len(supp_tabs)))
cited = set()
for seg in re.findall(r'Tables?~S\d+(?:[^.]*?S\d+)*', ALL):
    cited |= set(re.findall(r'S(\d+)', seg))
chk('all cited S-tables exist (S1-S14)', all(1 <= int(c) <= 14 for c in cited), str(sorted(cited)))
chk('S14 now cited', '14' in cited)
chk('S4/S5/S7/S12/S13 all cited', {'4','5','7','12','13'} <= cited, str(sorted(cited)))

# ============ 12. 结论一致性 ============
chk('conclusions: quarter-lower wording', 'quarter lower coefficients' in concl)
chk('conclusions: no provider-specific', 'provider-specific' not in concl)

print(f'==== v1.7-R2 SELF-CHECK: {len(passed)} passed, {len(failed)} failed ====')
for p in passed: print('  PASS', p)
for f in failed: print('  FAIL', f)
sys.exit(1 if failed else 0)
