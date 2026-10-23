# Revision Notes v1.8.1 — Journal-Compliance Pass (Submission Package)

Round 9 applies the Applied Acoustics *Guide for Authors* to the v1.8 manuscript
and assembles the submission package. No scientific content changed; every
change is submission-format or packaging related.

## Guide-for-Authors audit (all confirmed on the re-exported PDF)

| Requirement | Status |
|---|---|
| Abstract ≤ 250 words | 246 words |
| Keywords (max 6, specific, after abstract) | 6 keywords |
| Highlights: 3–5 bullets, ≤ 85 chars incl. spaces | 5 bullets, max 85 chars |
| Reference style | numbered (`elsarticle-num`), matches journal style |
| Review model | single-anonymised: author identity visible, public repo link given directly; anonymised snapshot additionally provided |
| Title page (title, author, affiliation, corresponding author + email) | present; elsarticle footer carries the email |
| Declarations: competing interest / CRediT / data availability / generative-AI use | all present, before the reference list |
| Continuous line numbering | **added this round** (`lineno`, 77-page layout unchanged) |
| Page numbers | present (elsarticle preprint mode) |
| Supplementary material cited in text | S1–S14 all cited (92-check suite) |
| Watermark triple-verification (text / metadata / pixel) | clean on the re-export |

## Changes made

1. **Continuous line numbering** added to `paper/latex/main.tex`
   (`\usepackage{lineno}` + `\linenumbers`, the elsarticle-template method).
   The amsmath patch variant was deliberately NOT used: the widely copied
   snippet errors with `Extra \endcsname` under this class/font setup, and
   the Elsevier template instructions specify the plain form.
2. **Portable CJK sans declaration**: `\IfFontExistsTF{Noto Sans SC}{...}{Noto
   Serif SC}`. CJK sans is not used anywhere in the document (verified by
   scan), so the output is byte-identical; the fallback only guarantees the
   source compiles where fontconfig does not index the variable font.
3. **LaTeX source zip defect fixed**: the v1.7 and v1.8 zips were built from a
   `figures` path that did not exist at the build location, silently producing
   a source-only zip that cannot compile. `latex_source_v1.8.1.zip` now ships
   `latex/` + `figures/` (33 files), and a fresh-extract `tectonic` compile of
   both documents is verified.
4. **Anonymised repository snapshot** built (`anonymised_repository_snapshot_
   v1.8.1.zip`, 205 files): the tree minus `.git`, cover letters, and
   `CITATION.cff`; author block, CRediT name, supplementary author line,
   README citation URL, and self-check identity strings scrubbed; the
   data-availability paragraph reworded for the anonymised copy; both PDFs
   recompiled inside the snapshot; a residual-identity sweep over all text
   files passes.
5. **Self-check suite re-run**: 92/92 PASS on the line-numbered build
   (watermark protocol re-run clean: page-77 corner 0 non-white pixels,
   metadata standard, no AI-generation markers in the text layer).

## Submission package (release v1.8.1)

| File | Editorial Manager item |
|---|---|
| `CascadeBench_Manuscript_v1.8.1.pdf` | Manuscript (line-numbered, 77 pp) |
| `CascadeBench_Supplementary_v1.8.1.pdf` | Supplementary material (10 pp) |
| `Highlights.txt` | Highlights (5 bullets ≤ 85 chars) |
| `CoverLetter_v1.8.1.txt` | Cover letter (paste into Comments field or upload) |
| `latex_source_v1.8.1.zip` | LaTeX source (self-contained, compile-verified) |
| `anonymised_repository_snapshot_v1.8.1.zip` | Additional file / research data |

The v1.8.0 data assets (raw rerun logs, analysis JSONs) remain attached to
release v1.8.0; the snapshot additionally carries the repo tree including
`results/`.
