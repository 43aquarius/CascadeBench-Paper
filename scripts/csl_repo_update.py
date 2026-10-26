#!/usr/bin/env python3
"""Update README.md and CITATION.cff for the v1.9.0 CSL transfer + rename PDFs."""
import pathlib, sys, subprocess

R = pathlib.Path("/tmp/my-project/repo_clone")
fails = []

# ---------- README.md ----------
rd = R / "README.md"
txt = rd.read_text()

subs = [
    # journal line
    ("> — prepared for submission to **Applied Acoustics** (Elsevier).",
     "> — prepared for submission to **Computer Speech & Language** (Elsevier)."),
    # preprint pointer line
    ("Preprint PDF: [`paper/CascadeBench_Paper_AppliedAcoustics.pdf`](paper/CascadeBench_Paper_AppliedAcoustics.pdf) (v1.8.1, 8 figures, supplementary material with 14 tables, 77 pages + 10 pages, continuously line-numbered).",
     "Preprint PDF: [`paper/CascadeBench_Paper.pdf`](paper/CascadeBench_Paper.pdf) (v1.9.0, 8 figures, supplementary material with 14 tables, 78 pages + 10 pages, continuously line-numbered, author-year reference style)."),
    # new v1.9.0 entry inserted before the v1.8.1 entry
    ("> **v1.8.1 (ninth round, journal-compliance pass for submission)**",
     """> **v1.9.0 (tenth round, Computer Speech & Language transfer)** — following the desk decision that the previous venue was not a journal match, the manuscript is adapted to the **Computer Speech & Language** Guide for Authors with no change to any result, number, figure, or table: the reference style moves from numbered to **author-year** (`elsarticle-harv`, 51 in-text citations re-rendered "(Author, Year)", reference list now alphabetical, ten journal names abbreviated per the List of Title Word Abbreviations); the page-1 footer now reads "Preprint submitted to Computer Speech & Language"; three plural keywords are singularised ("acoustic channel degradation", "cascaded translation", "cloud speech API"); an Elsevier-standard no-funding **Funding** section is added before CRediT; the GitHub repository is renamed to the journal-neutral **`CascadeBench-Paper`** (all old URLs redirect, every release intact) with the manuscript data-availability URL, README, and CITATION.cff updated; and a Vitae template and a CSL cover letter are added. Verification: 78 + 10 pages compile with **zero new overfull boxes** (the two log warnings reproduce byte-identically on the pristine v1.8.1 source in the same environment and the Table 6 page is pixel-identical to the released v1.8.1 PDF), the **92-check suite passes unchanged**, the abstract is 248 words (CSL sets no hard limit), 6 keywords and 5 Highlights bullets ≤ 81 chars are re-confirmed, no bracketed `[n]` citations remain, and the watermark text/metadata/pixel triple-verification is clean. See `paper/REVISION_NOTES_v1.9.0.md`.

> **v1.8.1 (ninth round, journal-compliance pass for submission)**"""),
    # bibtex block at the tail
    ("            Applied Acoustics},\n  url    = {https://github.com/43aquarius/CascadeBench-Paper-AppliedAcoustics}",
     "            Computer Speech \\& Language},\n  url    = {https://github.com/43aquarius/CascadeBench-Paper}"),
]
for old, new in subs:
    if old not in txt:
        fails.append(f"README pattern not found: {old[:60]!r}")
    else:
        txt = txt.replace(old, new, 1)
rd.write_text(txt)

# ---------- CITATION.cff ----------
cf = R / "CITATION.cff"
txt = cf.read_text()
subs = [
    ('repository-code: "https://github.com/43aquarius/CascadeBench-Paper-AppliedAcoustics"',
     'repository-code: "https://github.com/43aquarius/CascadeBench-Paper"'),
    ("version: 1.8.1", "version: 1.9.0"),
    ('date-released: "2026-10-23"', 'date-released: "2026-10-26"'),
]
for old, new in subs:
    if old not in txt:
        fails.append(f"CITATION pattern not found: {old[:60]!r}")
    else:
        txt = txt.replace(old, new, 1)
cf.write_text(txt)

# ---------- PDF renames (git mv keeps history) ----------
moves = [
    ("paper/CascadeBench_Paper_AppliedAcoustics.pdf", "paper/CascadeBench_Paper.pdf"),
    ("paper/CascadeBench_Paper_AppliedAcoustics_supplementary.pdf",
     "paper/CascadeBench_Paper_supplementary.pdf"),
]
for src, dst in moves:
    sp, dp = R / src, R / dst
    if sp.exists():
        # refresh content from the freshly compiled latex output
        if "supplementary" in src:
            sp.write_bytes((R / "paper/latex/supplementary.pdf").read_bytes())
        else:
            sp.write_bytes((R / "paper/latex/main.pdf").read_bytes())
        subprocess.run(["git", "-C", str(R), "mv", src, dst], check=True)
        print(f"git mv {src} -> {dst} (content refreshed from new build)")
    elif dp.exists():
        print(f"already renamed: {dst}")

if fails:
    print("\n".join(fails)); sys.exit(1)
print("README + CITATION + PDF renames OK")
