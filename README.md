# CascadeBench

**A black-box benchmark of acoustic channel degradation in commercial speech intelligence APIs — recognition and cascade/end-to-end translation error propagation.**

This repository accompanies the manuscript

> *Error Propagation in Cascaded Speech Translation under Acoustic Channel Degradations: A Black-Box Case Study of Commercial Speech Intelligence APIs*
> — prepared for submission to **Applied Acoustics** (Elsevier).

Preprint PDF: [`paper/CascadeBench_Paper_AppliedAcoustics.pdf`](paper/CascadeBench_Paper_AppliedAcoustics.pdf) (v1.8.1, 8 figures, supplementary material with 14 tables, 77 pages + 10 pages, continuously line-numbered).

> **v1.8.1 (ninth round, journal-compliance pass for submission)** — the manuscript is brought to the final Applied Acoustics submission format: continuous line numbering is added (`lineno`, the Elsevier review requirement; the 77-page layout is unchanged and all 92 numeric self-checks still pass), the CJK sans declaration is made portable with an `\IfFontExistsTF` fallback, **the LaTeX source zip is fixed to actually include the figures directory** (the v1.7/v1.8 zips silently omitted it; a fresh-extract compile of both documents is now verified), and the **anonymised repository snapshot** promised in the data-availability statement is built and released (author-identifying strings scrubbed from the tex/README/self-check sources, CITATION.cff and cover letters excluded, anonymised manuscript + supplementary recompiled inside the snapshot). Guide-for-Authors audit on the re-exported PDF: abstract 246/250 words, 6 keywords, 5 Highlights bullets at ≤ 85 characters each, numbered reference style, single-anonymised-review handling, generative-AI declaration, CRediT, competing-interest and data-availability statements, and the text/metadata/pixel watermark triple-verification all confirmed. The complete journal submission package (manuscript, supplementary, Highlights, cover letter, LaTeX source, anonymised snapshot) is collected in release v1.8.1. See `paper/REVISION_NOTES_v1.8.1.md`.

> **v1.8 (eighth revision round, pre-submission proofreading 2)** — GLM generation noise is now measured directly instead of estimated: the 150-sentence real-corpus reference regenerated 4x under the identical protocol (pairwise corpus self-consistency sd **1.4 BLEU** macro, 2.5 zh2en / 1.5 en2zh, mean 65.0) and the three mild-condition candidate cells re-rendered 2x each (the released reverberation cell at 49.7 is a single-draw low — its rerenders score 55.2/55.3, and 3-generation averaging closes the apparent deficit to 1.9/1.1 points, so the mild-condition non-monotonicity is an artefact, shown directly); a noise-calibrated Monte Carlo puts 95% intervals of 0.29–0.36 / 0.53–0.60 around the GLM slopes and keeps the vendor-minus-GLM gap positive in **100%** of draws (0.10 [0.07, 0.14] / 0.16 [0.13, 0.19]); reference-averaged slopes 0.34/0.52. Whisper Mandarin script-mismatch sensitivity added (OpenCC t2s before scoring): the traditional share is corrected to 6/300 small and 2/525 turbo sentences (the v1.7 "10%/13%" overstated it), conversion moves no condition by more than 0.2 points and changes no ten-percent crossing, so the non-vendor knee placement is robust to script mismatch. Table 2's measured-RIR cascade row now states its composition (3 full-bandwidth cascades x480 + the 8 kHz specialist on the Mandarin half, x240, reported in Supplementary Table S8), and the 1,515 noise-measurement regeneration calls are counted in the accounting (new row; second-vendor subtotal 1,919 -> 3,434; grand totals **45,288 / 44,398**, with abstract / data-availability / methods / cover letter updated). Section 4.6's closing sentence and the two discussion mentions of the second-backend fit now carry the same qualifiers as the abstract and conclusions (linear form retained, quarter-lower coefficients, measured-noise intervals, single frontend tested). Abstract 250 words; Highlights bullet 3 shortened to 81 chars; 92-check self-check suite; PDF re-exported and verified watermark-free (text / metadata / pixel). See `paper/REVISION_NOTES_v1.8.md`.

> **v1.7 (seventh revision round, upgrade item 2)** — the second-backend validation is extended from three to all nine real-speech conditions: the Qwen-Audio recognition outputs of the clean anchor, measured-RIR reverb, the full six-level real-babble ladder and traffic noise are re-translated by the second vendor's engine (GLM), +727 new translations for a backend total of 1,289 (630 reference + 1,289 backend = 1,919 second-vendor calls; grand total 43,773 successful API responses). n-alignment: the frontend's transcription list is authoritative at 150 utterances per condition, and the 61 slots where it returned no transcription carry an empty translation under both backends, so the two engines are compared on identical sentence sets (v1.5 compared n=150 vs 148/114). Nine-condition backend matrix (2 backends × 2 references × 9 conditions, new Supplementary Table S14); the GLM pass-through refit on the eight non-clean points gives 0.32 (Mandarin, $r=0.99$) and 0.56 (English, $r=0.99$) against 0.43/0.72 for the provider engine on the same conditions, with the same-engine diagonal advantage and the flatter GLM degradation profile now measured across the full ladder. The engine-independence caveat is retained: the validation isolates the translation-engine contribution on one recognition frontend, it is not a vendor-independent cascade. Main-paper updates: abstract / intro / methods protocol + accounting / §4.7 table expanded to nine conditions with the observations paragraph rewritten (the n=3 no-inferential-weight caveat retired) / discussion ×2 / conclusions.  Same-day proofreading refresh: Fig. 4 caption and the limitations now split the real-vs-synthetic babble comparison by language (Mandarin real-harsher everywhere, knee +2.9/+6.7 dB; English profiles cross, shifts −0.1 to +3.0 dB) with the TTS-vs-recorded-material confound stated; the abstract's "provider-specific" overclaim replaced by "not reproduced on an open encoder–decoder, class-versus-vendor provenance open"; the Whisper decoding configuration fully disclosed and the refusal conclusion qualified to it; Table 2's Qwen-Audio unique count corrected to 4,728 by raw-log recount (24 refusal triples carry no successful response); AIR-Bench/VoiceBench/CosyVoice/Qwen-report reference entries corrected and annotation notes removed; GLM single-draw generation noise quantified (self-BLEU 65, corpus floor ≈5 BLEU, slope-gap MC 98% positive); abstract at 248 words, CRediT statement added; 101-check self-check suite. See `paper/REVISION_NOTES_v1.7.md`.

> **v1.6 (sixth revision round, upgrade item 1)** — the non-vendor knee is localised: Whisper large-v3-turbo (809M-param distillation of large-v3, int8 CPU, greedy, same Mandarin prompt) run on the full six-level real-babble ladder plus the clean anchor (1,050 local transcriptions, all released). Mandarin: 14.9% CER already at +10 dB (CI 11.5–18.6), so the ten-percent crossing lies above the mildest tested level — the specialist band, ≥3 dB worse than Qwen3-ASR (7.0) and ≥7 dB worse than Qwen-Audio (2.8); English: crossing at 4.4 dB, 0.8 dB above Qwen3-ASR and 5.4 dB below the 16 kHz specialist — between the two product classes. The provider's near-knee audio-LLM advantage is therefore not a generic property of current large speech models. The failure structure replicates on the second model family (Mandarin insertion fraction 0.08→0.27 as noise deepens, English deletion-dominated up to 0.38, Mandarin CER >100% from 0 dB down) with zero silent empties anywhere (refusal behaviour is engine-specific, failure structure is not); at −5 dB the open model collapses milder than most but not all provider systems. Main-paper updates: methods protocol + systems table + accounting (600 small + 1,050 turbo local runs; API total unchanged at 43,046), §4.4 rewritten with the full curve, Fig. 4 gains the turbo series (VLM QA pass), Appendix D gains both turbo rows, new Supplementary Table S13, abstract (250 words) / intro / discussion / conclusions carry the provider-specific finding with the explicit caveat that the Whisper hold-outs are encoder–decoder models rather than same-generation audio-LLMs. See `paper/REVISION_NOTES_v1.6.md`.

> **v1.5.1 (fifth revision round, pre-submission polish)** — §4.4's "Qwen3-ASR better than both specialists at every tested babble level" corrected to the verified level- and language-dependent ordering (in Mandarin: behind the telephone-band specialist already at +2.5 dB and behind both specialists from 0 dB down; in English below the 16 kHz specialist at all six levels); the real-speech end-to-end-vs-cascade relative-loss comparison now carries a paired bootstrap under both references (same-engine 41.6% vs 33.7%, difference +7.9, CI −1.5 to +16.7; family-disjoint GLM 32.6% vs 32.7%, difference −0.1, CI −9.0 to +9.0 — both cross zero, so the fragility claim is qualified to point estimate, new Supplementary Table S12); the GLM-backend pass-through uniformly restated as "reproduced at the same order of magnitude by a three-point fit" with the engine-independence caveat in the abstract and conclusions; Table 4's SNR@10% column at two decimals matching the released analysis JSON (Mandarin gap 2.19–2.54 dB, so the text's 2.2–2.5 is table-verifiable); duplicate "Appendix Appendix C" references fixed; the six-level real-babble ladder restored to the main paper as Appendix D; print-size figure legibility fixed (Figs. 4–8 effective fonts from 4.3–5.9 pt to 7.4–7.8 pt via reduced canvases, VLM-verified); abstract at 245 words (journal limit 250); Highlights file added; corresponding-author block completed. A post-round consistency pass re-compiled the released PDF from the final figure set (the latency figure in the previously committed PDF predated the round-2 figure regeneration), synchronised `paper/figures/` with the root `figures/` directory, removed stale v1.5-era manuscript copies (`paper/main.tex`, `paper/sections_v13/`, `paper/refs.bib`, `paper/submission_materials.md`), and re-aligned `CITATION.cff` with the case-study title and the 43,046-call accounting. See `paper/REVISION_NOTES_v1.5.1.md`.

> **v1.4 (third revision round)** — all five upgrade items executed: an open-source non-vendor recogniser (Whisper small, int8, CPU) replicates the knee-and-collapse and hallucination structure on the real-speech subset; a family-disjoint GLM third reference and a GLM-translation backend hold-out show the relative-loss ordering stable across three references and two backends; a measured MIT-RIR reverb condition calibrates the synthetic extreme-DRR stress case (telephone-band specialist 18.2% -> 3.4% CER); the real-babble ladder densified to six levels (+10/+5/+2.5/0/-2.5/-5 dB, crossings at 1 dB resolution); Fig. 6 redrawn with three cascades, CIs, and mild/collapsed markers; Fig. 5 gains a non-noise-conditions panel; three erroneous reference entries corrected (AIR-Bench arXiv id and authors, VoiceBench authors, a non-existent citation replaced); total 41,854 vendor API responses plus 1,192 GLM calls and 600 local Whisper inferences, all released. See `paper/REVISION_NOTES_v1.4.md`.

> **v1.5 (fourth revision round)** — unified call accounting at **43,046 successful API responses** (the v1.4 manuscript's two counts, 38,494 and 41,854, both omitted the 1,192 second-vendor GLM calls); the omni path's fragility restated with scope ("most fragile of the end-to-end paths, degrades more than the LLM-frontend cascades in point estimate, reference-dependent margin") plus new paired bootstraps of the relative-loss difference that cross zero under the oracle reference (+11.7 [−5.6, +25.8] vs the Qwen-Audio cascade; +4.4 [−9.2, +18.4] vs Qwen3-ASR); the three-reference ranking stated as stable except for a sub-point omni/Qwen3-ASR inversion under the same-engine reference (29.0 vs 29.5 percent); vendor-independence wording corrected (the GLM validation isolates the engine contribution and is not a vendor-independent cascade); Whisper small's role limited to the failure-structure finding (Mandarin insertion-dominated vs English deletion-dominated hallucination, tolerance asymmetry reversed relative to the LLM systems, knee position not localisable in the tested range); real-babble ladder extended from three to six SNR levels (+10/+5/+2.5/0/−2.5/−5 dB; crossings measured rather than interpolated); measured-RIR bridge condition on the synthetic corpus (telephone-band specialist 18.2 → 3.4 percent under survey room responses); real-speech pass-through refit over nine conditions (0.43 Mandarin / 0.72 English); second-backend validation showing the pass-through survives a translation-engine swap (GLM slopes 0.34/0.55 vs 0.38/0.72 on shared conditions); references corrected (the self-training citation replaced with Pino et al., Interspeech 2020, doi:10.21437/Interspeech.2020-2938; FunASR author list and pages fixed per the ISCA record); revision-process language removed; abstract at 256 words; appendices D–G moved to a separate supplementary document (S1–S12). See `paper/REVISION_NOTES_v1.5.md` for the item-by-item response.

> **v1.3 (second revision round)** — full re-verification of every contested number against the raw logs, plus: corrected OLS slopes for the two LLM systems on the English sweep (−1.31/−1.06, replacing −2.79/−2.64) with a new observed-segment-slope column and an explicit caveat that the fitted logistic knees fall in the unobserved 0…−5 dB interval; unified knee-threshold gaps (2.2–2.5 dB zh, 8.5–8.9 dB vs the 8 kHz specialist, 4.4–4.8 dB en); the pass-through relation restated as an empirical rule with condition-level bootstrap intervals (0.23–0.45 / 0.52–0.66 / 0.38–3.9) replacing the "±0.04" sentence-level claim; the real-speech E2E-vs-cascade comparison restated in reference-invariant relative-loss terms with the same-engine reference bias quantified (ASR matches the human transcript on 133/150 clean sentences, engine self-BLEU 100); the LLM noise-tolerance claim bounded to the near-knee regime with the Qwen3-ASR hallucination-regime reversal documented; the telephone-band reverberation fragility downgraded to a property of the synthetic extreme-DRR response; insertion/deletion/substitution decomposition of the hallucination regime (a Mandarin phenomenon); Table 5 gains bootstrap CIs and an omni-subset paired comparison (n0 gap not significant on common sentences); the call accounting rebuilt in two counting conventions summing exactly to 36,469 successful responses; terminology fixed (7 families / 14 degradation conditions / 15 operating points); STOI tempo example removed as metric misuse with ESTOI added; figure fixes (dangling arrow, legend size); 9 reference corrections; abstract compressed to ~250 words. See `paper/REVISION_NOTES_v1.3.md` for the item-by-item response.

> **v1.2 (real-speech validation)** — 150 human-recorded utterances (AISHELL-1 + LibriSpeech test-clean), three measured MIT impulse responses at matched T60, real multi-talker babble at +5/0/−5 dB, ESC-50 transport noise; 4,650 additional API calls; confirms knee structure, hallucination regime, and pass-through on real speech; calibrates synthetic reverb as an extreme-DRR stress case.

> **v1.1 (revision round)** — extended the noise sweep to eight levels (20 … −10 dB incl. 2.5 dB), added a third cascade (Qwen3-ASR + MT), repetition runs for run-to-run variance, an exact call-accounting table, refusal/empty-transcript tables for all systems, knee-threshold severity analysis, a pass-through regression with intercept + bootstrap CIs + leave-one-out + leverage checks, STOI analysis with the dissociation finding, measured MT latency, normalisation sensitivity analysis, CJK-correct PDF rendering, and reference corrections.

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
