#!/usr/bin/env python3
"""Build the anonymised repository snapshot for the Computer Speech & Language
submission (v1.9.0).

Copies the repo (minus .git / cover letters / vitae / CITATION.cff / zips),
scrubs author-identifying strings from text sources, swaps the
data-availability wording to the anonymised variant, compiles both PDFs, and
zips the tree. Run from anywhere; builds under /tmp/anonbuild.
"""
import os, re, shutil, subprocess, sys

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DST = os.environ.get("ANON_DST", "/tmp/anonbuild")
OUT_ZIP = os.environ.get("ANON_OUT", "/tmp/anonymised_repository_snapshot_v1.9.0.zip")

EXCLUDE_DIRS = {".git", "__pycache__"}
EXCLUDE_FILES = {
    "CITATION.cff",                       # author-identifying metadata
    "CoverLetter_v1.6.txt", "CoverLetter_v1.7.txt", "CoverLetter_v1.8.txt",
    "CoverLetter_v1.8.1.txt", "CoverLetter_v1.9.txt",
    "Vitae_ChangTan_template.txt",        # author-named vitae template
    "latex_source.zip",                   # stale in-tree zip; rebuilt separately
    "build_anon_snapshot_v181.py",        # build tool whose scrub sources carry ids
    "build_anon_snapshot_v190.py",
}

# ---------------------------------------------------------------- copy tree
if os.path.exists(DST):
    shutil.rmtree(DST)
n_files = 0
for root, dirs, files in os.walk(SRC):
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    rel = os.path.relpath(root, SRC)
    for f in files:
        if f in EXCLUDE_FILES:
            continue
        s = os.path.join(root, f)
        d = os.path.join(DST, rel, f) if rel != "." else os.path.join(DST, f)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(s, d)
        n_files += 1
print(f"copied {n_files} files")

# ---------------------------------------------------------------- scrubbing
def scrub(path, pairs):
    t = open(path, encoding="utf-8").read()
    for a, b in pairs:
        t = t.replace(a, b)
    open(path, "w", encoding="utf-8").write(t)

URL = "https://github.com/43aquarius/CascadeBench-Paper"

# main.tex: author block + anonymised data statement
main_p = f"{DST}/paper/latex/main.tex"
t = open(main_p, encoding="utf-8").read()
t = t.replace(r"\author[addr1]{Chang Tan\corref{cor1}}" + "\n"
              + r"\ead{aquars43@foxmail.com}" + "\n"
              + r"\cortext[cor1]{Corresponding author.}" + "\n"
              + r"\address[addr1]{Dalian University of Technology, Dalian, China}",
              r"\author[addr1]{Anonymous}" + "\n"
              + r"\address[addr1]{Anonymised institution}")
# CRediT statement also carries the name
t = t.replace(r"\textbf{Chang Tan:} Conceptualization",
              r"\textbf{Anonymous:} Conceptualization")
assert "Chang Tan" not in t, "author scrub failed"
# data statement for the anonymised variant
t = t.replace(
    "The complete benchmark is publicly released at\n"
    "\\url{" + URL + "}:\n"
    "the sentence corpus",
    "The complete benchmark is publicly released (corpus")
t = t.replace(
    "Because the\njournal operates single-anonymised review, in which author identity is\n"
    "visible to reviewers, the public link is given directly; an anonymised\n"
    "snapshot is additionally provided with the submission.",
    "Because this copy is anonymised, the public repository link is provided\n"
    "with the submission rather than printed here; this snapshot itself\n"
    "contains the corpus, scripts, and released logs.")
assert "43aquarius" not in t and "aquars43" not in t, "url/email scrub failed"
open(main_p, "w", encoding="utf-8").write(t)

# supplementary.tex author line
sup_p = f"{DST}/paper/latex/supplementary.tex"
scrub(sup_p, [(r"\author{Chang Tan\thanks{Dalian University of Technology, Dalian, China.}}",
               r"\author{Anonymous}")])

# README: URL mention(s) in citation block
readme_p = f"{DST}/README.md"
scrub(readme_p, [(URL, "[public repository link removed for anonymisation]")])

# revision notes for this round mention the author-named vitae file and the
# renamed repository owner
notes_p = f"{DST}/paper/REVISION_NOTES_v1.9.0.md"
if os.path.exists(notes_p):
    scrub(notes_p, [("Vitae_ChangTan_template.txt", "author vitae template"),
                    ("43aquarius/CascadeBench-Paper", "the public repository")])

# self-check scripts mention the author strings
for s in ("v15_selfcheck.py", "v151_selfcheck.py"):
    p = f"{DST}/scripts/{s}"
    scrub(p, [('"Chang Tan"', '"Anonymous"'),
              ('"aquars43@foxmail.com"', '"anonymised"'),
              ('"Dalian University of Technology"', '"Anonymised institution"')])

# sweep: any residual identity strings in text files under the tree?
bad = []
for root, dirs, files in os.walk(DST):
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    for f in files:
        if f.endswith((".tex", ".py", ".md", ".txt", ".bib", ".cff", ".json")):
            p = os.path.join(root, f)
            try:
                t = open(p, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            if re.search(r"Chang\s*Tan|43aquarius|aquars43|ChangTan|Dalian", t):
                bad.append(p)
if bad:
    print("RESIDUAL IDENTITY STRINGS:", bad); sys.exit(1)
print("identity scrub: clean")

# ---------------------------------------------------------------- compile
for doc in ("main", "supplementary"):
    r = subprocess.run(["tectonic", f"{doc}.tex"], cwd=f"{DST}/paper/latex",
                       capture_output=True, text=True)
    ok = os.path.exists(f"{DST}/paper/latex/{doc}.pdf")
    print(f"tectonic {doc}: exit={r.returncode} pdf={ok}")
    if not ok:
        print(r.stdout[-1500:]); sys.exit(1)

# copy canonical PDF copies (journal-neutral filenames, v1.9.0)
shutil.copy2(f"{DST}/paper/latex/main.pdf", f"{DST}/paper/CascadeBench_Paper.pdf")
shutil.copy2(f"{DST}/paper/latex/supplementary.pdf",
             f"{DST}/paper/CascadeBench_Paper_supplementary.pdf")
# remove old-named copies if the source tree still carried them
for old in ("CascadeBench_Paper_AppliedAcoustics.pdf",
            "CascadeBench_Paper_AppliedAcoustics_supplementary.pdf"):
    p = f"{DST}/paper/{old}"
    if os.path.exists(p):
        os.remove(p)

# ---------------------------------------------------------------- zip
if os.path.exists(OUT_ZIP):
    os.remove(OUT_ZIP)
r = subprocess.run(["zip", "-q", "-r", OUT_ZIP, "."], cwd=DST)
print("zip exit", r.returncode)
print(subprocess.run(["unzip", "-l", OUT_ZIP], capture_output=True, text=True).stdout.splitlines()[-1])
