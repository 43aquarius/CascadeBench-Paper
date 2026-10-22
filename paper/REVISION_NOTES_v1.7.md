# REVISION NOTES — v1.7 (upgrade item 2: GLM nine-condition backend re-translation)

Base: v1.6 (main e9715a8, 74 pp + 8 pp supplementary)

## Motivation

v1.5/1.6 validated the pass-through relation on a second vendor's translation
engine (GLM) with only three non-clean babble conditions (+5/0/-5 dB), reported
as slopes 0.34 (Mandarin) / 0.55 (English) against 0.38/0.72 for the provider
engine on the same conditions -- explicitly flagged as a three-point fit with
no inferential weight at n=3. Reviewer-facing weakness: the engine-independence
claim rested on a narrow slice.

## What was done (this round)

1. Completed the GLM backend re-translation for all nine real-speech
   conditions (clean, measured-RIR reverb, six-level real babble ladder,
   traffic noise) of the Qwen-Audio (q31) frontend: +727 new GLM translations
   (revr 150, rb10 150, rb25 149, rbm25 128, rn0 150; 61 ASR-empty slots carry
   an empty translation by the same broken-cascade rule as the provider
   backend).
2. n-alignment improvement: the q31 transcription list is authoritative
   (150/condition); GLM-missing slots are scored as empty translations, so both
   backends are compared on identical sentence sets (v1.5 compared n=150 vs
   n=148/114 at 0/-5 dB).
3. Nine-condition per-backend slopes refit (same estimator as the main grid:
   y = clean-BLEU minus condition-BLEU, OLS over the eight non-clean points).
4. Nine-condition backend matrix (2 backends x 2 references x 9 conditions).

## Results (from analysis_v17_glm9.json; slopes pending final data)

- [x] GLM nine-condition slopes (GLM reference): zh 0.323 (r=0.986), en
  0.564 (r=0.992) — the v1.5 three-point estimates (0.34/0.55) were accurate;
  the nine-point fits add the correlation evidence the n=3 fit lacked
  (provider engine nine-condition: 0.426/0.721, reproducing 0.43/0.72)
- [x] gummy nine-condition slopes re-verified under the aligned-n protocol:
  zh 0.426, en 0.721 (paper value 0.43/0.72 — reproduced)
- [x] backend matrix table (nine conditions, all four backend x reference
  cells) — analysis_v17_glm9.json backend_matrix_9, S14
- [x] diagonal advantage under nine conditions (clean: +36.2 qwen, +23.4
  GLM, within the pre-written 23–36 band; off-diagonal differ by 3.9 BLEU)
- [x] accounting: GLM backend re-translations 562 -> 1,289; second-vendor
  total 1,192 -> 1,919; grand total successful API responses 43,046 -> 43,773

## Paper changes (pending numbers)

- main.tex abstract: "three-point re-fit ... same order of magnitude" ->
  nine-condition re-fit wording
- intro.tex: same upgrade
- results.tex 4.7: table expanded to nine conditions; "three observations"
  paragraph rewritten (drop n=3 caveat, report nine-point fit and r)
- discussion.tex (two places): three-point -> nine-condition, numbers updated
- conclusions.tex: same
- methods.tex: protocol sentence (4 conditions -> 9), accounting rows,
  630+562 -> 630+1289
- supplementary: GLM nine-condition full table (new S-section or extended)
- README changelog, CITATION.cff version 1.7.0

## Files

- scripts/glm_translate_v17.mjs (execution, resumable, 429 backoff 45 s)
- scripts/v17_glm9conds.py (analysis, n-aligned)
- results/analysis_v17_glm9.json
