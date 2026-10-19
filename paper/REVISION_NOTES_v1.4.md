# Revision Notes — v1.4

This revision responds to the reviewer's nine-point feedback on v1.3 and
executes the agreed upgrade items. All numbers cited below are regenerated
from the raw JSONL logs; the repository analysis script
(`scripts/analysis_v14.py`) reproduces every table entry from
`results/*.jsonl` byte-identically.

## Point-by-point response

**1. Fig. 6 was a stale figure.** Redrawn from the current
`analysis_ext.json` (key `cac_v2`): all three cascades are shown (slopes
0.44 / 0.54 / 0.47, annotated with intercepts +0.6 / −1.0 / −0.3, Pearson r
1.000 / 0.995 / 0.994, and sentence-level 95% CIs), each with a 95%
confidence band, the x-axis now extends past 100% (insertion errors), and
mild conditions (error ≤ 40%) are marked as small dots while collapsed
conditions are marked as large crosses — making visible that the fit is
anchored by 3 / 4 / 1 collapsed points respectively. Caption updated
accordingly.

**2. "Relative loss is reference-invariant" overstated the finding.**
All such statements are reworded to *orderings stable across references,
magnitudes not*. Table 5 now carries a third relative-loss column: the GLM
reference (family-disjoint from every system and both other references).
Clean-to-0 dB relative losses across the three references: Qwen-Audio
cascade 18/24/17, Qwen3-ASR cascade 19/30/23, specialist cascade 69/80/73,
omni 33/29/30, LiveTranslate 16/21/17 — the ordering is identical under
all three references while per-system magnitudes roam over a 6–11 point
band. Section 4.6 and the abstract updated; the omni-vs-cascade
relative-loss gap narrowing (≈15 → ≈5 points) is stated explicitly.

**3. "E2E is more fragile" lacked statistical support.** Added: paired
sentence-level bootstrap of the relative-loss difference on synthetic
speech (common subset, +22.2 points [10.9, 32.9] against the primary
reference but +11.2 [−3.4, +24.6] against the oracle reference —
significance is reference-dependent) and on real speech (+7.9 points,
[−0.4, +15.7], spans zero). All "most fragile" claims are now qualified
with "on the point estimate"; the common-subset comparison re-reports the
omni path's clean and 0 dB scores on the same sentences (no n-mixing).

**4. Pass-through wording too strong.** The abstract and conclusions now
state the condition-level 95% intervals directly (0.23–0.45, 0.52–0.66,
heavily right-tailed 0.38–3.9); "calibrated engineering rule" is replaced
by "empirical rule of thumb" everywhere. The 3–20% error-range operating
points and the non-Qwen MT hold-out (see upgrade e) are included.

**5. Fig. 5 (cascade/E2E bar chart) inconsistencies.** The figure now
matches its caption: all three cascades are plotted (caption says so), the
oracle is drawn as a dotted line (caption says dotted line, not hatched),
the legend is placed clear of all bars, and a new lower panel adds the
non-noise conditions (narrowband, Opus, packet loss, clipping, tempo,
synthetic reverb **and the new measured MIT-RIR reverb**) so the
"condition-wise structure" discussion is no longer text-only. The omni
packet-loss/tempo anomaly remains reported as unexplained (quota exhausted
before a re-run was possible).

**6. Small numeric/typographic inconsistencies.** Table 2 subtotals now
use one convention throughout (original-phase subtotal 25,387 unique =
sum of rows; the 24-refusal discrepancy is resolved by counting refusals
as successful calls and unique evaluations, stated in the caption);
bootstrap counts unified at 1,000 (Table 5 note now matches §3.8); all
confidence intervals in Tables 3, E.10, G.13 restored to one decimal (no
more "(0,0)"); the "Appendix Appendix" duplication (elsarticle
auto-prefixes \ref to appendix labels) is gone; Fig. 1 redrawn with larger
fonts and wider boxes.

**7. References.** The explanatory notes that had leaked into [15][16][17]
were already removed in v1.3's bib; this version additionally fixes three
erroneous entries found during the DOI audit: AIR-Bench now cites the
correct arXiv:2402.07729 with the correct author list (Yang, Xu, Liu, Chu,
et al.); VoiceBench now lists the correct authors (Chen, Yue, Zhang, Gao,
Tan, Li); a non-existent "Park et al. robust self-training" citation is
replaced by Pino et al., "Self-training for end-to-end speech translation"
(arXiv:2010.03142). FunASR's author list is corrected. The Qwen3.8-Max
model card is now cited for the reference generator. DOI/page audit of all
38 entries: [12] Bentivogli et al. pp. 2873–2887 verified against the ACL
Anthology; [17] Ruiz & Federico pp. 261–274 verified.

**8. Anonymity.** Verified against the Elsevier Guide for Authors (fetched
October 2026): Applied Acoustics operates **single-anonymised review**
("This journal follows a single anonymized review process"), and its
research-data policy is Option C (deposit in a repository, cite and link).
The public GitHub link and the on-page statement are therefore retained as
is.

**9. Single-vendor structural limitation + upgrades.** The paper keeps the
"single-vendor case study" framing, further tightened in the abstract,
introduction, and conclusions. All five upgrade items were executed:

- **(a) Non-Alibaba ASR (highest value).** Whisper small (int8, CPU, fully
  local) run over the real-speech subset (clean, +5, 0, −5 dB; 600
  inferences). Clean CER/WER 10.1/3.6% (as expected, several times the
  commercial LLM rates), knee beyond +5 dB in Mandarin, and the same
  knee-and-collapse structure with insertion-driven hallucination above
  100% (120.3% at 0 dB, 130.7% at −5 dB) and a gentler
  deletion-dominated English curve. New §4.4 paragraph + Appendix table
  G.4.
- **(b) Human-reference anchor (best-effort).** A family-disjoint GLM
  reference was generated for all 480 synthetic + 150 real clean
  transcripts (the third reference of point 2). A human-translation
  worksheet (150 sentences, CSV) is included in the release so a bilingual
  annotator can produce the true human anchor; the paper states clearly
  that the GLM reference is LLM-generated, not human.
- **(c) Measured RIRs replace the synthetic reverb on the main grid.** A
  new rev-mit condition convolves the full 480-sentence synthetic corpus
  with the same three measured MIT impulse responses used by the
  real-speech validation (T60 ≈ 0.5 s matched; everyday DRRs). All four
  vendor recognisers + cascade MT re-run (3,360 API calls). Result: the
  broadband systems barely move (0.2/1.2 → 0.2/1.1 etc.) while the
  telephone-band specialist improves from 18.2% to 3.4% CER — the
  "synthetic reverb is an extreme-DRR stress case" reading now has a
  measured calibration. New §4.5 paragraph + Appendix table G.5.
- **(d) Denser real-babble ladder.** +10, +2.5, −2.5 dB points added to
  the real-speech babble sweep (all four vendor ASR + cascade MT, 2,025
  calls). Ten-percent crossings are now interpolated between levels at
  most 2.5 dB apart: Qwen-Audio 2.8 dB (zh) / 2.3 (en), Qwen3-ASR 7.0
  (zh), 16 kHz specialist above +10 dB (zh, 12.1%) / 9.8 dB (en). Fig. 4
  (real-validation figure) updated to the six-level ladder including the
  Whisper curve.
- **(e) Non-Qwen MT backend.** The Qwen-Audio frontend's real-speech
  transcripts re-translated by GLM (562 calls), forming a cascade with no
  component in common with the vendor. Clean-to-0 dB relative loss: 33.8%
  (GLM backend, GLM reference), 28.6% (GLM backend, oracle reference),
  33.8% (vendor backend, oracle reference), 32.6% (vendor backend, GLM
  reference) — the frontend-governed degradation band is stable across
  backends and references, directly supporting the "frontend matters more
  than engine" claim.

## Updated accounting

Vendor API total: 41,854 successful responses (37,643 unique evaluations)
+ 1,820 failed attempts. Non-vendor, logged and released: 600 local
Whisper inferences and 1,192 GLM API calls.

## Files changed

- `sections/*`: results (hold-out subsection content in §4.4, reverb
  calibration in §4.5, three-reference analysis in §4.6), methods (§2.7
  protocol, Table 2), discussion (limitations), conclusions, intro,
  appendix (three new tables), main.tex (abstract, author block).
- `figures/`: fig1, fig4, fig6, fig8 redrawn.
- `results/`: revmit_asr_* ×4, revmit_mt_cascade, d3_asr_whisper,
  glm_tasks, updated d3_asr_* (nine-condition), analysis_v14.json.
- `scripts/`: gen_rev_mit, run_revmit, run_whisper_d3, glm_translate2.mjs,
  analysis_v14, redraw_figs_v14, fix_fig1_v14 (+ path fixes in two older
  scripts).
