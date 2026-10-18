# CascadeBench

**A black-box benchmark of acoustic channel degradation in commercial speech intelligence APIs — recognition and cascade/end-to-end translation error propagation.**

This repository accompanies the manuscript

> *Error Propagation in Cascaded Speech Translation under Acoustic Channel Degradations: A Black-Box Benchmark of Commercial Speech Intelligence APIs*
> — prepared for submission to **Applied Acoustics** (Elsevier).

Preprint PDF: [`paper/CascadeBench_Paper_AppliedAcoustics.pdf`](paper/CascadeBench_Paper_AppliedAcoustics.pdf) (revision round, 7 figures, 45 references).

> **v1.1 (revision round)** — extended the noise sweep to eight levels (20 … −10 dB incl. 2.5 dB), added a third cascade (Qwen3-ASR + MT), repetition runs for run-to-run variance, an exact call-accounting table, refusal/empty-transcript tables for all systems, knee-threshold (logistic) severity analysis replacing single-range slopes, a pass-through regression with intercept + bootstrap CIs + leave-one-out + leverage checks, STOI analysis with the dissociation finding, measured MT latency, normalisation sensitivity analysis, CJK-correct PDF rendering, and reference corrections.

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
- **15 degradation conditions**: multi-talker babble at SNR 20/15/10/5/2.5/0/−5/−10 dB (active-speech calibration), reverberation (measured T60 0.51 s, C50 +4.9 dB, DRR −27.6 dB), telephone narrowbanding, 8 kbps Opus coding, packet loss, clipping, and tempo distortion.
- **6 recognition systems** spanning three product classes of one provider: specialised streaming (paraformer-realtime-v2, paraformer-realtime-8k-v2), audio LLM (qwen-audio-3.1-asr-flash, qwen3-asr-flash), and omni-modal (qwen3.8-omni-flash).
- **5 translation paths**: three cascades (ASR → qwen-mt-uni) and two end-to-end (qwen3.8-omni-flash, qwen3.8-livetranslate-flash-realtime), scored against both an LLM reference (qwen3.8-max) and the oracle transcript translation.
- **33,847 successful API calls** (original + revision extension), fully seeded and checkpointed, at zero cost on complimentary quotas.

## Key findings

1. **Knee-shaped noise response.** Audio-LLM recognisers cross 10 % error 2.4–2.9 dB later (Mandarin) and 4.4–4.8 dB later (English) than the specialised streaming system, then collapse more sharply; the telephone specialist needs 8.8 dB.
2. **Hallucination below 0 dB.** LLM-ASR systems fail by insertion-heavy hallucination (CER 127–143 %), while streaming systems return silence/fragments; refusal rates reach 42–58 % at −5 dB.
3. **A calibrated pass-through regression.** Cascade BLEU loss = 0.44–0.54 × recognition error rate (bootstrap 95 % CI ±0.04, intercept ≈ 0, stable under leave-one-out) across 15 conditions and 3 frontends.
4. **End-to-end is not automatically more robust.** At 0 dB the omni path loses 33 % of its clean BLEU versus 18–19 % for well-frontended cascades; the streaming translation service is the most resilient (16 %) and fastest.
5. **Two empty-output mechanisms.** Qwen-Audio refuses at protocol level (5.0 % at 0 dB); Paraformer returns silent empties (8.8 %) — an operationally meaningful distinction. Machine-reference scoring bias can invert rankings; STOI does not predict ASR error across degradation families.

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
python3 scripts/analysis.py       # regenerates results/analysis_results.json from the main logs
python3 scripts/analysis_ext.py   # regenerates results/analysis_ext.json (revision-round analyses)
python3 scripts/figures_v2.py     # regenerates all figures at 300 dpi
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
