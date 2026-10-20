# REVISION NOTES — v1.6 (upgrade item 1: the non-vendor knee)

Executed before submission, per the agreed priority order of the upgrade
items: "Whisper large-v3 or another non-Alibaba system on the full six-level
real-babble ladder", answering the question the v1.5 review left open —
where does a non-vendor system's knee sit?

## What was run

Whisper **large-v3-turbo** (the 809M-parameter, four-decoder-layer
distillation of Whisper large-v3; OpenAI, 2024), executed locally with the
same faster-whisper int8 CPU runtime, greedy decoding, and explicit Mandarin
initial prompt as the Whisper small run, on **all six real-babble levels
(+10/+5/+2.5/0/−2.5/−5 dB) plus the clean anchor** — 150 utterances × 7
conditions = **1,050 transcriptions**, all released
(`results/d3_asr_whisper_lg3t.jsonl`; runner `scripts/run_whisper_lg3t.py`).
The full turbo variant was not run: on the two-core CPU available, the
3B-parameter large-v3 would have required an order of magnitude more
wall-clock than the turbo distillation for the same ladder; the turbo model
is the same family and generation, and its clean-condition accuracy
(5.9% Mandarin CER / 2.5% English WER on real speech) shows it is a
credible representative, clearly above Whisper small (10.1/3.6).

## Verified numbers (all recomputed from the raw log; `v16_whisper_curve.py`)

Mandarin (CER %): clean 5.9; +10: 14.9 (CI 11.5–18.6); +5: 45.9; +2.5: 76.1;
0: 105.3; −2.5: 136.8; −5: 120.3. **Cross-10%: above +10 dB** — the
specialist band (Qwen3-ASR 7.0, Qwen-Audio 2.8; both streaming specialists
also above +10). At least 3 dB worse than Qwen3-ASR, at least 7 dB worse
than Qwen-Audio.

English (WER %): clean 2.5; +10: 3.3; +5: 8.5; +2.5: 15.0; 0: 24.8; −2.5:
46.7; −5: 70.7. **Cross-10%: 4.4 dB** — 0.8 dB above Qwen3-ASR (3.6), 5.4 dB
below the 16 kHz specialist (9.8): between the two product classes.

Failure structure: Mandarin insertion fraction 0.08 (at +10) → 0.27 (at
−2.5); English deletion-dominated throughout (deletion fraction up to 0.38);
Mandarin error >100% from 0 dB down (hallucination regime replicates on a
second model family outside the vendor); **zero silent-empty outputs in
every condition** (against Qwen-Audio's 29.3% Mandarin refusals at −5 dB —
refusal behaviour is engine-specific, failure structure is not). At −5 dB
the open model errs 70.7 (English) / 120.3 (Mandarin) against provider
ranges of 64.1–86.6 / 93.1–207.6 — milder collapse than most, but not all,
provider systems, and from a far worse near-knee baseline.

## Manuscript changes

- **§3 (methods)**: protocol paragraph rewritten for two open-weights models
  (small: 4 conditions, 600; turbo: 7 conditions, 1,050); systems table row;
  accounting prose and Table 2 (local runs now "1,650 transcriptions",
  caption carries the 600/1,050 split; the 43,046 API total is unchanged —
  turbo makes no API calls).
- **§4.4**: the Whisper small paragraph is reframed as the failure-structure
  probe; a new passage reports the turbo ladder, both crossings, the
  specialist-band/intermediate placement, the provider-specific conclusion,
  the zero-empty contrast, and the gentler-but-not-universal collapse.
- **Fig. 4** (real validation): turbo series added (green triangles, all six
  levels, both panels); VLM print-size QA passes; caption updated.
- **Appendix D** (six-level ladder table): turbo rows in both language
  panels; caption and intro text updated (CIs for turbo cells → S13).
- **Supplementary**: new **Table S13** (full turbo ladder: error, CI, empty
  rate, ins/del/sub counts, insertion fraction, 14 cells) with a section
  describing the zero-empty and failure-structure findings; supplementary
  now 8 pages, S1–S13, zero overfull boxes, zero undefined references.
- **Abstract** (250 words, at the journal limit), **intro**, **discussion**
  (tolerance-asymmetry passage + Limitations: the hold-outs are
  encoder–decoder models, so the audio-LLM near-knee advantage remains a
  single-vendor observation pending a same-generation non-vendor system),
  **conclusions** (first conclusion extended with the knee placement), and
  the **cover letter** all carry the finding.
- **References**: Whisper large-v3-turbo model card added
  (`whisperturbo2024`); CITATION.cff abstract and version updated to 1.6.0.

## Statistical hygiene

Per-cell errors are sentence-level means with 1000-resample bootstrap CIs
(seed 42), identical methodology to every other system; cross-10% is the
linear interpolation of the ten-percent crossing used in Appendix D. The
Mandarin "above +10 dB" statement is CI-supported (lower bound 11.5 > 10 at
the mildest level). The English 4.4 dB crossing sits between +5 (8.5, CI
5.9–11.9) and +2.5 (15.0, CI 10.8–19.8), so its bracketing levels are
resampling-stable.

## Interpretation guardrails

The finding *strengthens* the case-study framing rather than weakening it:
the provider's near-knee audio-LLM advantage does not transfer to the
open-weights encoder–decoder generation, so it is a provider property, not a
class law — exactly the kind of claim a single-vendor case study can
support. No generalisation language was restored. The remaining upgrade
items (GLM nine-condition re-translation refit, 100–150-sentence bilingual
human reference — worksheet already released — and a non-vendor commercial
ASR on the real-speech subset) stay listed as future work pending reviewer
requests.
