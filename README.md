# CascadeBench

**A black-box benchmark of acoustic channel degradation in commercial speech intelligence APIs — recognition and cascade/end-to-end translation error propagation.**

This repository accompanies the manuscript

> *Error Propagation in Cascaded Speech Translation under Acoustic Channel Degradations: A Black-Box Benchmark of Commercial Speech Intelligence APIs*
> — prepared for submission to **Applied Acoustics** (Elsevier).

Preprint PDF: [`paper/CascadeBench_Paper_AppliedAcoustics.pdf`](paper/CascadeBench_Paper_AppliedAcoustics.pdf) (45-page review format, ~12,000 words, 7 figures, 41 references).

---

## Why this benchmark exists

Speech recognition (ASR) and speech translation are increasingly consumed as
cloud services assembled from black-box APIs. The acoustic channels feeding
those services are rarely clean, yet vendors publish almost no evidence about
how their systems behave under controlled degradation. CascadeBench measures
exactly that, end to end, on free-tier commercial APIs — and quantifies how
recognition errors induced by the acoustic channel propagate into downstream
translation quality.

## What was measured

- **480-sentence bilingual corpus** (Mandarin ⇄ English, 4 domains × 3 lengths × 20 sentences, symmetric across languages), synthesised with 4 Sambert voices; 40 additional sentences from disjoint voices serve as multi-talker babble sources.
- **12 degradation conditions**: multi-talker babble at SNR 20/15/10/5/0 dB (calibrated to < 0.1 dB error), reverberation, telephone narrowbanding, 8 kbps Opus coding, packet loss, clipping, and tempo distortion.
- **6 recognition systems** spanning three architectural families: specialised streaming (paraformer-realtime-v2, paraformer-realtime-8k-v2), audio LLM (qwen-audio-3.1-asr-flash, qwen3-asr-flash), and omni-modal (qwen3.8-omni-flash).
- **4 translation paths**: two cascades (ASR → qwen-mt-uni) and two end-to-end (qwen3.8-omni-flash, qwen3.8-livetranslate-flash-realtime), scored against both an independent LLM reference (qwen3.8-max) and the oracle transcript translation.
- **26,238 successful API calls**, fully seeded and checkpointed, at zero cost on complimentary quotas.

## Key findings

1. **Family-level robustness gap.** Audio-LLM recognisers degrade at 0.34–0.44 percentage points per dB (Mandarin) versus 1.70 for the specialised streaming system; at 0 dB babble the error-rate gap reaches 2–6×.
2. **A linear error pass-through rule.** Cascade BLEU loss = 0.47–0.66 × recognition error rate (Pearson r > 0.98 across all 12 conditions) — a directly usable engineering estimation rule.
3. **End-to-end is not automatically more robust.** At 0 dB, the end-to-end omni path loses 33 % of its clean BLEU versus 18 % for the strongest cascade frontend; the dedicated streaming translation service is the most stable (16 %).
4. **Machine-reference scoring bias.** Scoring against a machine reference from the same model family can invert system rankings; a dual-reference protocol (independent LLM reference + oracle-transcript reference) exposes and controls this bias.
5. **Behavioural failure modes.** qwen-audio returns empty transcripts for 5.2 % of 0 dB inputs (all other systems always emit text); the telephony-band expert model hallucinates fluent English and is evaluated on Mandarin only.

## Repository structure

```
├── corpus/                  # benchmark corpus + babble sources + SNR sweep subset
├── scripts/                 # full pipeline: corpus → TTS → perturb → ASR → MT → analysis → figures
├── results/                 # per-sentence JSONL logs (26,238 calls) + analysis_results.json
├── figures/                 # 7 publication figures, PDF (vector) + PNG (300 dpi)
└── paper/                   # manuscript PDF, LaTeX source, submission materials
```

## Quick start

```bash
pip install -r scripts/requirements.txt
python3 scripts/analysis.py   # regenerates results/analysis_results.json from raw logs
python3 scripts/figures.py    # regenerates all figures at 300 dpi
```

`results/analysis_results.json` committed here was verified to be regenerated
**byte-identically** by `analysis.py` from the committed raw logs. To re-run
the API experiments themselves, see [`scripts/README.md`](scripts/README.md)
for pipeline order, quota shapes, and operational caveats.

## Figures

| | |
|---|---|
| Fig 1 — benchmark architecture | Fig 5 — sentence-level error distributions |
| Fig 2 — error-rate heatmap (system × condition, per language) | Fig 6 — cascade error pass-through regression (CAC) |
| Fig 3 — SNR degradation curves with 95 % CIs | Fig 7 — API latency comparison |
| Fig 4 — cascade vs end-to-end translation quality | |

All figures are in [`figures/`](figures/) as vector PDF and 300 dpi PNG.

## Data records

Each JSONL log line is one API call with model id, condition, sentence id,
input reference, system output, latency, token usage, and retry count:

- `results/asr_*.jsonl` — recognition transcripts for 5 systems (+ omni internal ASR)
- `results/mt_oracle.jsonl` / `mt_refmax.jsonl` — reference translations
- `results/mt_cascade.jsonl` — cascade translations (2 frontends × 12 conditions)
- `results/mt_e2e_omni.jsonl` / `mt_e2e_lt.jsonl` — end-to-end translations
- `results/tts_log.jsonl` — synthesis records (voice, duration, latency)

## Reproducibility statement

Every phase is seeded and checkpointed. Audio is regenerated deterministically
by `scripts/perturb.py` from `audio/tts/` (the 866 MB WAV tree is not
committed but is fully reproducible via `scripts/run_tts.py` +
`scripts/perturb.py`). All systems were accessed through the Alibaba Cloud
Model Studio (DashScope) API, Beijing region, in October 2026, default
configurations; exact model ids and versions are listed in the paper's
Code and Data Availability section.

## Citation

```bibtex
@misc{cascadebench2026,
  title  = {Error Propagation in Cascaded Speech Translation under Acoustic
            Channel Degradations: A Black-Box Benchmark of Commercial
            Speech Intelligence APIs},
  author = {CascadeBench Authors},
  year   = {2026},
  note   = {Benchmark and dataset accompanying the manuscript submitted to
            Applied Acoustics},
  url    = {https://github.com/43aquarius/CascadeBench-Paper-AppliedAcoustics}
}
```

(Author list will be completed upon publication.)

## License

- **Code** (`scripts/`): MIT License — see [LICENSE](LICENSE).
- **Corpus, logs, and figures**: released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **Manuscript**: the preprint PDF is provided for review; copyright transfers to the publisher upon acceptance.

## Acknowledgements

All experiments ran on the complimentary quotas of the Alibaba Cloud Model
Studio free tier. No financial relationship with any vendor; all systems were
accessed as ordinary black-box API customers.
