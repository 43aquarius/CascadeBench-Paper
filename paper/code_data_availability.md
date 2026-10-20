# CascadeBench: Code and Data Availability

## Repository structure (publicly released)

```
cascadebench/
├── corpus/
│   ├── corpus.jsonl            # 480 sentences: id, lang, domain, length, text, voice
│   ├── d3_corpus.jsonl         # 150 real-speech validation utterances (AISHELL-1 + LibriSpeech)
│   ├── sweep_ids.json          # 144-sentence SNR severity sweep subset
│   └── babble_sources.jsonl    # 40 noise-source sentences (disjoint voices)
├── scripts/
│   ├── corpus_build.py         # corpus construction (deterministic, seeded)
│   ├── perturb.py              # 8 degradations + SNR ladder (seeded, calibrated)
│   ├── apis.py                 # unified API wrappers (retry, backoff, latency logging)
│   ├── run_tts.py              # TTS synthesis (Sambert voices, 2 per language)
│   ├── run_asr.py              # recognition experiment runner (checkpointed)
│   ├── run_mt.py               # oracle/reference/cascade/E2E translation runners
│   ├── metrics.py              # normalisation, CER/WER, BLEU/chrF, statistics
│   ├── analysis.py             # aggregate results, slopes, tests, CAC
│   ├── v15_accounting.py       # unified call accounting (43,046 successful responses)
│   ├── v15_table5.py           # three-reference Table 5 + paired bootstraps
│   ├── v15_real.py / v15_real2.py   # real-speech ladder, slopes, GLM backend matrix, measured-RIR bridge
│   ├── v15_whisper.py          # Whisper small errors + insertion/deletion decomposition
│   ├── run_whisper_lg3t.py     # Whisper large-v3-turbo runner (six-level ladder + clean)
│   ├── v16_whisper_curve.py    # turbo ladder, crossings, decomposition
│   ├── v16_suptable.py         # S13 table rows from the analysis JSON
│   ├── v16_selfcheck.py        # v1.6 round self-check (45 items)
│   ├── v151_babble_ladder.py   # six-level babble ladder verification (v1.5.1)
│   ├── v151_reallloss.py       # real-speech relative losses, paired bootstrap (v1.5.1)
│   ├── v15_figures.py          # publication figures (v1.5)
│   ├── v15_supptables.py       # supplementary table bodies (S5-S12)
│   └── v15_selfcheck.py        # 68-item numeric/wording consistency check
│       (plus v151_selfcheck.py, 54 items, v1.5.1)
├── results/                    # per-sentence JSONL logs for every system call
│   ├── tts_log.jsonl
│   ├── asr_{system}.jsonl      # transcripts + latency per call
│   ├── mt_oracle.jsonl         # text MT on clean transcripts
│   ├── mt_refmax.jsonl         # independent LLM reference translations
│   ├── mt_cascade.jsonl        # cascade translations (2 frontends x 12 conditions)
│   ├── mt_e2e_omni.jsonl       # end-to-end translations (omni path)
│   ├── mt_e2e_lt.jsonl         # end-to-end translations (streaming path)
│   ├── d3_asr_*.jsonl          # real-speech recognition (4 vendor systems, 9 conditions)
│   ├── d3_asr_whisper.jsonl    # real-speech recognition (Whisper small, local, 4 conditions)
│   ├── d3_asr_whisper_lg3t.jsonl # real-speech recognition (large-v3-turbo, local, 7 conditions)
│   ├── analysis_v16_whisper_curve.json # turbo ladder + cross-10% + decomposition
│   ├── d3_mt_*.jsonl           # real-speech cascade/oracle/end-to-end translations
│   ├── revmit_asr_*.jsonl      # measured-RIR bridge condition, recognition (4 systems)
│   ├── revmit_mt_cascade.jsonl # measured-RIR bridge condition, cascades (4 frontends)
│   ├── glm_tasks.jsonl         # second-vendor GLM references + backend re-translations
│   └── analysis_v1[45]_*.json  # released analysis outputs for every reported number
├── figures/                    # PDF + PNG, 300 dpi
└── paper/                      # LaTeX source
```

## Reproduction

1. Obtain a DashScope API key (Alibaba Cloud Model Studio) with free-tier
   quotas enabled and the stop-on-exhaustion option active. The study
   consumed only complimentary quotas; approximate consumption: 36k seconds
   per streaming recogniser, 1M tokens per LLM-ASR system, and under 0.4M
   tokens for each translation system.
2. `python3 scripts/corpus_build.py` regenerates the corpus deterministically.
3. `python3 scripts/run_tts.py` synthesises the audio (approximately 15
   minutes).
4. `python3 scripts/perturb.py` generates all degraded variants with fixed
   per-sentence seeds (approximately 15 minutes).
5. `python3 scripts/run_asr.py <system>` for each system; `python3
   scripts/run_mt.py <phase>` for each translation phase. All runners are
   checkpointed and resume automatically.
6. `python3 scripts/analysis.py` and `python3 scripts/figures.py` reproduce
   every number and figure in the paper.

## System versions

The main-grid systems were accessed through the Alibaba Cloud Model Studio
(DashScope) API, Beijing region, during October 2026, in their default
configurations: paraformer-realtime-v2, paraformer-realtime-8k-v2,
qwen-audio-3.1-asr-flash, qwen3-asr-flash, qwen3.8-omni-flash,
qwen3.8-livetranslate-flash-realtime, qwen-mt-uni, qwen3.8-max, and Sambert
voices sambert-zhida-v1, sambert-zhixiao-v1, sambert-brian-v1,
sambert-beth-v1 for synthesis, with six additional voices for babble noise
sources. The validation components are Whisper small and Whisper
large-v3-turbo (open weights, executed locally with greedy decoding) and
GLM (Zhipu AI / Z.ai,
public text API, accessed October 2026), used as a family-disjoint
reference generator and as an alternative cascade backend. In total
43,046 successful API responses, 1,650 local Whisper transcriptions
(600 small + 1,050 large-v3-turbo), and
3,874 failed attempts (3,333 LiveTranslate websocket drops plus 541
API-level failures) are logged.

## Dependencies

Python 3.12; dashscope, requests, websocket-client, numpy, scipy, soundfile,
librosa, sacrebleu, cn2an, word2number, matplotlib, pandas; ffmpeg for codec
and tempo operations.
