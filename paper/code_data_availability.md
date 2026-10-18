# CascadeBench: Code and Data Availability

## Repository structure (to be released upon acceptance)

```
cascadebench/
├── corpus/
│   ├── corpus.jsonl            # 480 sentences: id, lang, domain, length, text, voice
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
│   └── figures.py              # all publication figures
├── results/                    # per-sentence JSONL logs for every system call
│   ├── tts_log.jsonl
│   ├── asr_{system}.jsonl      # transcripts + latency per call
│   ├── mt_oracle.jsonl         # text MT on clean transcripts
│   ├── mt_refmax.jsonl         # independent LLM reference translations
│   ├── mt_cascade.jsonl        # cascade translations (2 frontends x 12 conditions)
│   ├── mt_e2e_omni.jsonl       # end-to-end translations (omni path)
│   └── mt_e2e_lt.jsonl         # end-to-end translations (streaming path)
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

All systems were accessed through the Alibaba Cloud Model Studio
(DashScope) API, Beijing region, during October 2026, in their default
configurations: paraformer-realtime-v2, paraformer-realtime-8k-v2,
qwen-audio-3.1-asr-flash, qwen3-asr-flash, qwen3.8-omni-flash,
qwen3.8-livetranslate-flash-realtime, qwen-mt-uni, qwen3.8-max, and Sambert
voices sambert-zhida-v1, sambert-zhixiao-v1, sambert-brian-v1,
sambert-beth-v1 for synthesis, with six additional voices for babble noise
sources.

## Dependencies

Python 3.12; dashscope, requests, websocket-client, numpy, scipy, soundfile,
librosa, sacrebleu, cn2an, word2number, matplotlib, pandas; ffmpeg for codec
and tempo operations.
