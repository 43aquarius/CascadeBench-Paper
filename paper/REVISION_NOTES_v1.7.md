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

## Results (from analysis_v17_glm9.json)

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

## Paper changes

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

## Proofreading round (same-day refresh of the v1.7.0 tag)

External proofreading against the released tables and raw logs surfaced nine
issues; all text-level fixes, no re-measurement:

1. Fig. 4 caption + limitations: "Real babble is the harder stressor at every
   SNR" held in Mandarin only. Split by language: Mandarin real babble is
   harsher at every level (knee +2.9/+6.7 dB for the two audio-LLM systems);
   English profiles cross (real harsher at +10 to +2.5 dB, synthetic from
   0 dB down; knee shifts -0.1/+1.6/+3.0 dB). Added the confound note
   (synthetic curves on the authored TTS corpus, real curves on recorded
   corpora with different sentence sets) and the same-sentence TTS control
   as future work.
2. Abstract: "making the advantage provider-specific" -> "not reproduced on
   an open encoder-decoder; class-versus-vendor provenance remains open"
   (consistent with the limitations framing); same fix in the cover letter.
3. Whisper decoding configuration fully disclosed (faster-whisper, greedy
   beam-1, VAD off, condition_on_previous_text off, timestamps off, default
   thresholds, simplified-script initial prompt); refusal-behaviour
   conclusion qualified as decoding-configuration-specific (main text +
   S13); traditional-character incidence disclosed (10%/13% of Mandarin
   outputs, no traditional-to-simplified conversion before CER). Also fixed
   "three hardest babble conditions" -> "original three-level babble ladder
   (+5/0/-5 dB)".
4. Table 2: Qwen-Audio unique evaluations corrected 4,752 -> 4,728 (raw-log
   recount; the 24 refusal triples at 0 dB babble carry no successful
   response and are absent from the unique column). Subtotal 25,363 and
   total 42,898 now equal the row sum; the methods sentence rewritten
   (refusal attempts are among the 541 API failures, not successful calls).
5. Appendix D: "Whisper small on four of the six levels" -> "three of the
   six levels plus the clean anchor".
6. References: AIR-Bench corrected (Q. Yang, J. Xu, W. Liu, Y. Chu et al.;
   arXiv 2402.07729, not 2408.10513); VoiceBench author list corrected
   (Y. Chen, X. Yue, C. Zhang, X. Gao, R. T. Tan, H. Li); Qwen2-Audio
   He, Jinzheng; CosyVoice title and authors corrected; GLM-4.5 Team;
   Gong, Yifan; Qwen2.5-Omni and Qwen3 reports cited with individual first
   authors; all annotation-style notes removed (fixes the glued
   arXiv-ID+note renderings and the lowercased "aPI documentation").
7. GLM generation-noise treatment (new in Sec. 4.7 + methods): the gateway
   exposes no temperature or seed controls; nineteen doubly-rendered
   sentences give a sentence-level self-BLEU of 65 (IQR 53-76); the clean
   and reverberation cells (near-identical ASR inputs) differ by 10.5 BLEU,
   a direct corpus-level rendering-noise floor of about five BLEU, within
   which the Rev non-monotonicity sits; a Monte Carlo re-fit under this
   floor keeps the provider-minus-GLM slope gap positive in 98% of draws
   (Mandarin 0.10 [0.01, 0.19]; English 0.16 [0.01, 0.32]). Abstract and
   conclusions slope wording tightened to "quarter lower coefficients".
8. Abstract trimmed to 248 words (journal limit 250); CRediT authorship
   statement added; S14 now cited from the main text; Highlights verified
   at <=85 characters; figure print-size legibility re-verified (7.5-11 pt
   effective); no AI-generated markers in either compiled PDF.
9. Self-check suite extended to 101 checks (scripts/v17b_selfcheck.py),
   including raw-log recounts of Table 2 and of every number added in items
   1-7.
