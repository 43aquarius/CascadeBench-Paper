#!/usr/bin/env python3
"""Convert the CascadeBench manuscript from Applied Acoustics (numbered refs)
to Computer Speech & Language (author-year refs) per the CSL Guide for Authors.

Idempotent: each replacement is guarded, safe to re-run.
"""
import re, sys, pathlib

L = pathlib.Path("/tmp/my-project/repo_clone/paper/latex")

def patch(path, subs, label):
    """subs: list of (old, new, required). Returns list of failures."""
    txt = path.read_text()
    fails = []
    for old, new, required in subs:
        if new in txt and old not in txt:
            continue  # already applied
        if old not in txt:
            if required:
                fails.append(f"{label}: pattern not found: {old[:70]!r}")
            continue
        txt = txt.replace(old, new)
    path.write_text(txt)
    return fails

fails = []

# ---------- 1. main.tex ----------
main = L / "main.tex"
fails += patch(main, [
    ("\\documentclass[review,number,sort&compress]{elsarticle}",
     "\\documentclass[review,authoryear,sort&compress]{elsarticle}", True),
    ("\\journal{Applied Acoustics}",
     "\\journal{Computer Speech \\& Language}", True),
    # keywords: singularise per CSL 'avoid plural terms' rule, keep 6 concepts
    ("acoustic channel degradations \\sep cascaded systems \\sep cloud APIs",
     "acoustic channel degradation \\sep cascaded translation \\sep cloud speech API", True),
    # repository URL points at the renamed (journal-neutral) repository
    ("https://github.com/43aquarius/CascadeBench-Paper-AppliedAcoustics}",
     "https://github.com/43aquarius/CascadeBench-Paper}", True),
    # funding statement: Elsevier standard no-funding sentence (CSL GfA)
    ("\\section*{CRediT authorship contribution statement}",
     "\\section*{Funding}\nThis research did not receive any specific grant from funding agencies in\n"
     "the public, commercial, or not-for-profit sectors.\n\n"
     "\\section*{CRediT authorship contribution statement}", True),
    ("\\bibliographystyle{elsarticle-num}",
     "\\bibliographystyle{elsarticle-harv}", True),
], "main.tex")

# ---------- 2. sections: \cite -> \citep (numbered-mode writing becomes paren authoryear) ----------
n_cited = 0
for sec in ["intro", "related", "methods", "results", "discussion", "conclusions", "appendix"]:
    p = L / "sections" / f"{sec}.tex"
    if not p.exists():
        continue
    txt = p.read_text()
    new, n = re.subn(r"\\cite\{", r"\\citep{", txt)
    # guard: do not double-convert \citep already there (regex cannot match \citep{ twice)
    if n:
        p.write_text(new)
        n_cited += n
        print(f"  {sec}.tex: {n} \\cite -> \\citep")
print(f"total cites converted: {n_cited}")

# ---------- 3. refs.bib: LTWA journal-name abbreviations ----------
bib = L / "refs.bib"
JOURNAL_ABBR = [
    ("The Journal of the Acoustical Society of America", "J. Acoust. Soc. Am."),
    ("Speech Communication", "Speech Commun."),
    ("Soviet Physics Doklady", "Sov. Phys. Dokl."),
    ("Scandinavian Journal of Statistics", "Scand. J. Statist."),
    ("Proceedings of the National Academy of Sciences", "Proc. Natl. Acad. Sci. U. S. A."),
    ("Nature Methods", "Nat. Methods"),
    ("IEEE/ACM Transactions on Audio, Speech, and Language Processing",
     "IEEE/ACM Trans. Audio Speech Lang. Process."),
    ("IEEE Transactions on Speech and Audio Processing", "IEEE Trans. Speech Audio Process."),
    ("Advances in Neural Information Processing Systems", "Adv. Neural Inf. Process. Syst."),
    ("Biometrics Bulletin", "Biometrics Bull."),
]
txt = bib.read_text()
for full, abbr in JOURNAL_ABBR:
    # only inside journal={...} fields
    pat = re.compile(r"(journal\s*=\s*\{)" + re.escape(full) + r"(\})")
    txt, n = pat.subn(r"\g<1>" + abbr.replace("\\", "\\\\") + r"\g<2>", txt)
    print(f"  journal abbr: {full[:45]:47s} -> {abbr:38s} ({n} fields)")
bib.write_text(txt)

if fails:
    print("\n".join(fails))
    sys.exit(1)
print("ALL PATCHES APPLIED OK")
