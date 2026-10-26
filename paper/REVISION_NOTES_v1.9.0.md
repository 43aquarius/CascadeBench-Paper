# Revision Notes — v1.9.0 (Computer Speech & Language transfer)

This round adapts the manuscript from the Applied Acoustics submission
package (v1.8.1) to the **Computer Speech & Language** Guide for Authors,
following the desk decision that the previous venue was not a journal match.
No experimental result, number, figure, or table is changed; every change is
a format/scope adaptation. All 92 numeric self-checks from v1.8.1 still pass
on the converted manuscript.

## Guide-for-Authors differences identified and addressed

| # | CSL requirement | Action |
|---|-----------------|--------|
| 1 | References in **author-year** style: reference list "arranged first alphabetically, then chronologically if necessary", same-author-same-year items distinguished "a, b, c", journal names abbreviated per the List of Title Word Abbreviations | `elsarticle-num` → `elsarticle-harv`; `\documentclass[review,number,sort&compress]` → `[review,authoryear,sort&compress]`; all 51 in-text `\cite` → `\citep` (rendered "(Author, Year)"); 10 journal names in `refs.bib` abbreviated (J. Acoust. Soc. Am.; Speech Commun.; Sov. Phys. Dokl.; Scand. J. Statist.; Proc. Natl. Acad. Sci. U. S. A.; Nat. Methods; IEEE/ACM Trans. Audio Speech Lang. Process.; IEEE Trans. Speech Audio Process.; Adv. Neural Inf. Process. Syst.; Biometrics Bull.) |
| 2 | `\journal{}` footer must name the target journal | `Applied Acoustics` → `Computer Speech & Language` (page-1 footer: "Preprint submitted to Computer Speech & Language") |
| 3 | Keywords: "maximum of 6 keywords, using American spelling and avoiding general and plural terms" | Three plural keywords singularised/made specific: "acoustic channel degradations" → "acoustic channel degradation", "cascaded systems" → "cascaded translation", "cloud APIs" → "cloud speech API" (still 6, all American spelling) |
| 4 | Role of the funding source: state no-funding explicitly | New `Funding` section with the Elsevier standard sentence ("This research did not receive any specific grant from funding agencies in the public, commercial, or not-for-profit sectors.") before CRediT |
| 5 | Repository link must not carry the previous venue's name | GitHub repository renamed `CascadeBench-Paper-AppliedAcoustics` → `CascadeBench-Paper` (GitHub auto-redirects all old URLs, releases and tags intact); manuscript data-availability URL, README, and CITATION.cff updated; the released PDF is renamed `CascadeBench_Paper.pdf` |
| 6 | Vitae: short (≤ 100 words) biography + passport-type photograph in an editable separate file | Template provided (`paper/Vitae_ChangTan_template.txt`) for the author to complete; the photograph must be supplied by the author at the Attach Files step |
| 7 | Suggesting reviewers: "submit the names and institutional e-mail addresses of several potential reviewers" | Noted in the cover letter that reviewer suggestions are provided in the submission system; the author enters them at the Suggest Reviewers step (see SUBMISSION_CHECKLIST) |
| 8 | Single-anonymised review; Highlights 3–5 bullets ≤ 85 chars as a separate editable file; abstract "concise and factual"; ≤ 6 keywords; elsarticle.cls + BibTeX; numbered sections; appendices A, B, …; declarations (competing interests, generative AI, CRediT); continuous line numbering | Already satisfied by the v1.8.1 package and re-verified on the v1.9.0 export: 5 Highlights bullets (max 81 chars), abstract 248 words (no hard CSL limit), 6 keywords, elsarticle review mode with `lineno`, sections 1–5 + Appendices A–D, all four declarations present, supplementary material S1–S14 cited in the main text |

## Verification on the converted manuscript

- **Compile**: main 78 pages (+1 vs v1.8.1, author-year citations are wider
  than bracketed numbers), supplementary 10 pages unchanged.
- **New overfull boxes: none.** The two warnings that appear in the log
  (`results:838` 130.8 pt hbox, `main.tex:74` 26.9 pt vbox) reproduce
  byte-identically when the pristine v1.8.1 source is compiled in the same
  environment, and the Table 6 page renders pixel-identically to the released
  v1.8.1 PDF, so both are pre-existing measurement warnings, not regressions
  of this round. All other overfull boxes are ≤ 7.9 pt, identical to the
  v1.8.1 baseline.
- **Self-check**: 92/92 PASS (`scripts/v18_selfcheck.py`), including the
  analysis-JSON / manuscript number agreement, accounting sums
  (45,288 / 44,398), S-table citations, and Highlights lengths.
- **Citation audit**: no residual bracketed `[n]` citations in the PDF text;
  reference list is alphabetical with correct "et al." handling; the page-1
  footer names Computer Speech & Language.
- **Watermark triple-verification** (text layer / metadata / pixel corners)
  re-run clean on the re-exported PDF.
- Repository rename verified: API reports `43aquarius/CascadeBench-Paper`,
  all seven v1.8.1 assets and every earlier release intact; old URLs
  redirect.

## Files changed

- `paper/latex/main.tex` (document class option, `\journal`, keywords, URL,
  Funding section, bibliography style)
- `paper/latex/sections/{intro,related,methods,results,discussion}.tex`
  (51 × `\cite` → `\citep`)
- `paper/latex/refs.bib` (10 abbreviated journal names)
- `paper/latex/main.pdf`, `paper/latex/supplementary.pdf` (re-exported)
- `paper/CascadeBench_Paper.pdf` (renamed from
  `CascadeBench_Paper_AppliedAcoustics.pdf`, re-exported v1.9.0)
- `paper/CoverLetter_v1.9.txt` (CSL cover letter, scope paragraph rewritten
  for speech and language processing readership)
- `paper/Vitae_ChangTan_template.txt` (new)
- `README.md`, `CITATION.cff` (v1.9.0, new repository URL)
- `scripts/build_anon_snapshot_v190.py` (URL/journal-aware anonymised
  snapshot rebuild), `scripts/csl_convert.py` (the conversion patch itself,
  idempotent, kept for the record)
