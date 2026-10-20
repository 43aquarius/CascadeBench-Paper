# REVISION NOTES — v1.5.1 (pre-submission polish round)

Responses to the seven-point external evaluation of v1.5.1 (2026-10-20).
All numerical changes were re-verified against the released raw logs before
editing; the verification scripts are `scripts/v151_babble_ladder.py`,
`scripts/v151_reallloss.py`, and `scripts/v151_selfcheck.py` (54/54 checks;
the v1.5 self-check still passes 68/68).

## Point 1 — §4.4 self-contradiction on Qwen3-ASR vs the specialists

**Claim under review.** "Qwen3-ASR is better than both specialists at every
tested babble level" contradicted the same subsection's 0 dB numbers
(117.5% vs 102.6% for the 16 kHz specialist; 207.6% vs 164.4% at −5 dB).

**Verification.** From `analysis_v15_real.json` (= raw JSONL, matches
Supplementary Table S5 cell by cell): in Mandarin, Qwen3-ASR is below both
specialists at +10 and +5 dB, already above the telephone-band specialist at
+2.5 dB (62.3 vs 60.2), and above both from 0 dB down (117.5/173.0/207.6 vs
102.6/131.3/164.4 and 78.7/86.8/93.1). In English it stays below the 16 kHz
specialist at all six levels (2.8→64.1 vs 9.5→86.1).

**Fix.** §4.4 now states the level- and language-dependent ordering
explicitly with those numbers; the later 0 dB sentence no longer carries the
reversal as a surprise ("already worse" removed). Abstract, Conclusions, and
§5.1 were re-checked: all three already bound the LLM advantage to the
near-knee regime and say "disappearing and for one LLM system reversing" —
no "everywhere better" claim existed there; no change needed.

## Point 2 — "AI生成" marker on page 70

**Finding.** Pixel-level scan of our tectonic-compiled v1.5 PDF page 70:
zero dark pixels in the bottom-right quadrant (only the centred page number).
The marker was added by the platform used to view/export the reviewed PDF,
not by our toolchain. The manuscript was recompiled locally (tectonic) and
the final export re-verified clean. The Elsevier generative-AI declaration
remains in the manuscript before the reference list, as the journal requires.

## Point 3 — statistical support for "E2E more fragile" on real speech

**Verification.** `v151_reallloss.py` recomputed both paths' relative losses
(clean → 0 dB real babble) on the common 150-sentence subset under both
references, with a paired sentence-level bootstrap (1000 resamples, seed 42,
per Methods §3.8):

| Reference | LiveTranslate | Cascade | Difference | 95% CI |
|---|---|---|---|---|
| same-engine (oracle) | 41.6% (42.0→24.5) | 33.7% (69.1→45.8) | +7.9 | −1.5 to +16.7 (crosses 0) |
| family-disjoint (GLM) | 32.6% (37.3→25.1) | 32.7% (32.9→22.1) | −0.1 | −9.0 to +9.0 (crosses 0) |

Both point estimates reproduce the published 41.6/33.7 exactly.

**Fix.** The old sentence also claimed the within-path relative losses are
"stable across reference choices" — refuted by the GLM column (LiveTranslate
41.6→32.6). §4.4 now reports both references with CIs and concludes the
streaming E2E path is more fragile "in point estimate under the same-engine
reference" but not established at sentence level; §5.3 ("reference-sensitive,
consistent with, without establishing") and Conclusions were aligned. A new
Supplementary Table S12 carries the numbers; the analysis JSON
(`analysis_v151_reallloss.json`) is released.

## Point 4 — GLM-backend pass-through wording

**Fix.** All five sites (abstract, intro, §4.7, §5.1 twice incl. worked
example, conclusions) now say the relation is *reproduced at the same order
of magnitude by a three-point fit* (slopes 0.34/0.55 vs 0.38/0.72 on the
shared conditions — the English coefficient about a quarter shallower), with
$n=3$ carrying no inferential weight. The abstract and conclusions now carry
the explicit caveat that engine-independence of the coefficient is not
established. The relative-loss-trajectory claim (89% vs 87% at −5 dB), which
is supported by four conditions, is retained separately. The full
nine-condition GLM re-translation remains an upgrade item (see Point 7).

## Point 5 — small issues

- **"Appendix Appendix C" ×2**: both `Appendix~\ref{app:normalisation}` sites
  fixed (elsarticle's appendix counter already prints "Appendix C"). One
  further instance introduced by this round's own new appendix reference was
  caught by the extended self-check and fixed.
- **Table 4 precision**: SNR@10% column now two decimals (2.48 / 8.82 /
  −0.06 / 0.29 / 6.79 / 2.38 / 2.02), exactly matching the released
  `analysis_ext.json`, so the text's "2.2 to 2.5 dB" Mandarin gap is now
  verifiable from the table (2.19–2.54). §4.3 prose quotes the same
  precision; the stray "streaming generalist" is now "streaming specialist".
- **Six-level babble table back in the main paper**: new Appendix D
  (`tab:babble`) with the full Mandarin+English ladder and Cross-10% column;
  §4.4 points to it; CIs and extra conditions stay in Supplementary S5.
- **Supplementary table numbering**: S1–S12 verified in order; the only
  hard-coded main-text references (S4 ×3) match the compiled supplementary;
  the new S12 is referenced from §4.4. S5 was rotated to landscape (was
  102 pt overwide), S11 font fixed (was 32 pt overwide) — supplementary now
  compiles with zero overfull boxes.

## Point 6 — pre-submission wrap-up

- **Number re-verification**: extended self-check `v151_selfcheck.py`
  (54 items) + original `v15_selfcheck.py` (68 items) all pass: 43,046 total,
  subtotals, slopes (0.43/0.72; 0.34/0.55), thresholds, relative losses,
  paired CIs, appendix/table cross-references.
- **Figures at print size**: measured effective font sizes in the compiled
  PDF were 4.3–5.9 pt for Figs. 4–8 (wide canvases × narrow review text
  block, 343 pt). All affected figures regenerated on reduced canvases;
  effective minimum is now 7.4–7.8 pt. In-panel annotations that collided
  with bars were removed (the caption already explains the oracle line);
  Fig. 6 legend/stats labels shortened; VLM print-size QA passes on all
  figures. Fig. 6 in-document width 0.6→0.8\textwidth, latency figure
  0.5→0.68\textwidth.
- **Journal requirements** (Applied Acoustics Guide for Authors, verified
  2026-10-20): single-anonymized review confirmed (author identity and
  real-name repository link may stay); abstract ≤250 words → now 248;
  Highlights file added (5 bullets, all ≤85 characters); keywords 6 (limit
  1–7); data availability statement present (Option C: data deposited in the
  public repository, cited and linked in the manuscript); generative-AI
  declaration present before the reference list; supplementary material
  cited in text and submitted simultaneously.
- **Cover letter**: added (`CoverLetter_v1.5.1.txt`), states the three
  non-vendor validations and fit to the journal in under a page.

## Point 7 — structural positioning and upgrade items

The manuscript keeps the single-vendor case-study framing in the title,
abstract, and conclusions; no generalisation language was restored. Upgrade
items (in the agreed priority order) remain future work pending reviewer
requests: (1) full six-level real-babble curve for a non-vendor large ASR
(Whisper large-v3 or SenseVoice) on the knee axis; (2) GLM-backend
re-translation of all nine real-speech conditions for a cross-engine slope
refit; (3) 100–150-sentence bilingual human reference (worksheet already
released); (4) a non-vendor commercial ASR on the real-speech subset.
