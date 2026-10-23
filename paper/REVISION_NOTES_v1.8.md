# Revision Notes v1.8 (pre-submission proofreading round 2)

Seven review points from the second pre-submission read-through. All changes
verified by a 92-check self-check suite (`scripts/v18_selfcheck.py`) against
the raw logs; main.pdf re-exported and verified watermark-free at the text,
metadata, and pixel level.

## 1. PDF "AI-generated" mark on the last page

The v1.7 PDF was re-exported (tectonic, xdvipdfmx) and verified clean at
three levels: no AI-generation string in the text layer of any page
(pdftotext), no custom metadata / XMP / JavaScript / annotations (pdfinfo +
structure scan), and a pixel-level scan of the bottom-right corner of pages
1, 40, and 77 showing zero non-white pixels on content pages (page 1's
corner is the standard Elsevier preprint footer). The mark seen by the
reviewer originates in the PDF viewer / download layer, not in the file. The
existing generative-AI declaration in the manuscript is retained unchanged.

## 2. Whisper Mandarin script-mismatch sensitivity (OpenCC t2s)

The disclosed but unhandled methodological issue: the released scoring
applies no traditional-to-simplified conversion, so traditional characters
in a small share of Mandarin outputs count as substitutions. New analysis
(`scripts/v18_t2s_sensitivity.py`, OpenCC t2s applied to every Mandarin
hypothesis before scoring):

- Corrected disclosure: the traditional share is **6 of 300** Whisper small
  sentences (2.0%) and **2 of 525** large-v3-turbo sentences (0.4%) — the
  v1.7 text's "about ten / thirteen percent" overstated the share (it was
  based on a looser detection criterion; both counts re-verified under two
  independent criteria: TSCharacters key membership and any t2s change).
- Sensitivity: after conversion no sentence remains traditional, no
  condition mean moves by more than 0.2 points (small clean 10.1 -> 10.0;
  turbo +10 dB 14.9 -> 14.7, CI 11.5-18.6 -> 11.2-18.4), and **no
  ten-percent crossing changes** (both models remain above-highest /
  > +10 dB in Mandarin).
- Conclusion unchanged: the non-vendor knee placement in the specialist
  band is not an artefact of script mismatch. Methods section now reports
  both the corrected share and the sensitivity result; the Appendix D
  table caption points to it. Table D.10 numbers are unchanged (released
  no-conversion convention), with the sensitivity quantified in text.

## 3. GLM generation noise measured directly (replaces the indirect estimate)

The v1.7 noise treatment rested on one 10.5-BLEU observation and 19
doubly-rendered sentences, and its own Monte Carlo showed unstable gaps.
Three new measurement campaigns (1,515 GLM regenerations, all released):

- **Reference self-consistency**: the 150-sentence real-corpus GLM reference
  regenerated 4 additional times under the identical batch protocol (600
  calls) -> 10 pairwise corpus self-consistency scores, mean 65.0 BLEU,
  **sd 1.4** macro (2.5 zh2en, 1.5 en2zh). This is the measured two-sided
  noise of a Table 6 GLM|GLM cell — an order below the v1.7 assumption of
  ~5 BLEU.
- **Candidate-side cell rerenders**: the GLM candidate translations of the
  three mild cells (reverberation, +10, +5 dB) re-rendered twice each (915
  calls, 900 unique) -> the released reverberation cell at 49.7 sits 6.0
  points below the mild babble cells, but its rerenders score 55.2 / 55.3;
  after 3-generation averaging the deficit shrinks to 1.9 / 1.1 points.
  The mild-condition non-monotonicity is **a single-draw artefact** — now
  shown directly, not inferred.
- **Noise-calibrated Monte Carlo** (2000 draws, measured sigma):
  GLM slope 95% intervals 0.29-0.36 (Mandarin) / 0.53-0.60 (English);
  vendor-minus-GLM gap 0.10 [0.07, 0.14] / 0.16 [0.13, 0.19], positive in
  **100%** of draws (v1.7: 98%, interval lower bounds near zero). Both the
  direction and the magnitude of the gap are now stable under generation
  noise. Averaging the reference over its five generations refits the
  slopes at 0.34 / 0.52.

Paper updates: methods protocol (regeneration campaign), Table 6 footnote
(measured noise), Section 4.7 caveat paragraph rewritten around the measured
numbers, discussion (two places) and conclusions carry the slope intervals,
abstract adds "noise-sensitive in magnitude" (kept at 250 words).

## 4. Table 2 measured-RIR cascade row

The row (1,680 calls, 4 frontends) is real but under-explained: it comprises
the three full-bandwidth cascades (480 sentences each) plus the 8 kHz
specialist cascade on the Mandarin half (240), the latter reported only in
Supplementary Table S8 and the released logs. The Coverage column now reads
"3x480 + 240 zh 8 kHz" and the table caption states the split and where the
8 kHz cascade is reported. Totals and subtotals are unchanged by this fix.

## 5. Call accounting extended (integrity of "total successful responses")

The 1,515 new GLM regeneration calls are API responses and are now counted:
new Table 2 row "GLM noise-measurement reruns 1,515 / 1,500", second-vendor
subtotal 1,919 -> 3,434 / 3,419, grand totals **43,773 / 42,898 -> 45,288 /
44,398**, with the abstract, data-availability statement, methods narrative,
README, and CITATION.cff all updated. Arithmetic re-verified:
26,238 + 5,581 + 6,675 + 3,360 + 3,434 = 45,288.

## 6. Section 4.7 / discussion qualifiers aligned with abstract and conclusions

The two remaining "reproduces the relation" statements (Section 4.6 closing
sentence, discussion pass-through caveat) now carry the same qualifiers as
the abstract and conclusions: linear form retained, coefficients roughly a
quarter lower, measured-noise intervals given, single frontend tested.

## 7. Structural positioning and upgrade path (no text change required)

The single-vendor case-study positioning, the 2023-24 encoder-decoder
characterisation of Whisper, the int8 CPU disclosure, the one-frontend
second-backend coverage, and the machine-reference-only translation scoring
remain as stated in the limitations; no generalisation language was added
back anywhere. The ranked upgrade path (non-Alibaba open audio LLM such as
Voxtral Mini / Phi-4-multimodal at +5/0 dB; GPU unquantified large-v3; 100-
150 bilingual human references; GLM backend on the other two frontends;
same-sentence TTS-vs-recorded babble contrast) is documented in the
repository notes for the revision stage.

## Verification

- `scripts/v18_selfcheck.py`: 92/92 PASS (text-vs-JSON for every new number,
  superseded-claim removal, accounting sums, abstract 250 words, watermark
  scans, S-table cross-references, Highlights bullets <= 85 chars).
- main.pdf 77 pp + supplementary 10 pp recompiled clean; figures unchanged
  (Fig. 5/6 print-size legibility carried over from the v1.5.1 fix).
- New released artifacts: `glm_selfcons.jsonl` (600), `glm_mtre2.jsonl`
  (915), `analysis_v18_selfcons.json`, `analysis_v18_mtre2.json`,
  `analysis_v18_whisper_t2s.json`, and scripts `glm_selfcons.mjs`,
  `glm_mtre2.mjs`, `v18_selfcons.py`, `v18_mtre2_cells.py`,
  `v18_t2s_sensitivity.py`.
