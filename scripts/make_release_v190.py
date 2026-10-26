#!/usr/bin/env python3
"""v1.9.0 Release: the Computer Speech & Language submission package (7 assets).
Token: GITHUB_TOKEN env > /home/z/my-project/upload/gh_token.txt.
Idempotent + retry (flaky network)."""
import json, os, sys, time

def tok():
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"].strip()
    p = "/home/z/my-project/upload/gh_token.txt"
    if os.path.exists(p):
        return open(p).read().strip()
    sys.exit("no token")

T = tok()
REPO = "43aquarius/CascadeBench-Paper"
TAG = "v1.9.0"
NAME = "v1.9.0 — Computer Speech & Language submission package (author-year references, journal-neutral repository)"
BODY = """## Submission-ready package (journal transfer: Applied Acoustics -> Computer Speech & Language)

v1.9.0 adapts the v1.8.1 manuscript to the **Computer Speech & Language Guide for Authors** after the
previous venue's desk decision (journal mismatch). **No scientific content changed** — every number,
figure, and table is identical to v1.8.1; all 92 numeric self-checks pass unchanged.

**Compliance items addressed for CSL**
- **Reference style: author-year** (`elsarticle-harv` instead of `elsarticle-num`): all 51 in-text citations re-render as "(Author, Year)", the reference list is now alphabetical with same-author-same-year a/b/c disambiguation, and ten journal names are abbreviated per the List of Title Word Abbreviations (J. Acoust. Soc. Am., Speech Commun., IEEE/ACM Trans. Audio Speech Lang. Process., ...).
- Page-1 footer reads "Preprint submitted to Computer Speech & Language"; `\journal{}` updated.
- Keywords: three plural keywords singularised/made specific per the "avoid general and plural terms" rule — "acoustic channel degradation", "cascaded translation", "cloud speech API" (still 6, American spelling).
- **Funding**: Elsevier-standard no-funding statement added as its own section before CRediT.
- Repository renamed to the journal-neutral **`CascadeBench-Paper`** (old URLs redirect; all releases intact); manuscript data-availability URL, README, and CITATION.cff synced; released PDFs renamed `CascadeBench_Paper*.pdf`.
- Vitae requirement: an editable author-biography template is included (`Vitae_ChangTan_template.txt`, for the author to complete with a passport-type photograph).

**Verification on the converted manuscript**
- 78 + 10 pages compile with **zero new overfull boxes**: the two warnings present in the log reproduce byte-identically when the pristine v1.8.1 source is compiled in the same environment, and the Table 6 page renders pixel-identically to the released v1.8.1 PDF.
- Abstract **248 words** (CSL sets no hard limit) · **6** keywords · **5** Highlights bullets, longest **81** characters.
- No residual bracketed `[n]` citations; single-anonymised review handling unchanged (public link + anonymised snapshot).
- Watermark triple-verification (text layer / metadata / pixel corners incl. the new final page) clean.

## Upload guide (Editorial Manager — https://www.editorialmanager.com/csl/)

| File in this release | EM item |
|---|---|
| `CascadeBench_Manuscript_v1.9.0.pdf` | Manuscript |
| `Highlights.txt` | Highlights |
| `CascadeBench_Supplementary_v1.9.0.pdf` | Supplementary material |
| `latex_source_v1.9.0.zip` | LaTeX source files (fresh-extract compile verified) |
| `anonymised_repository_snapshot_v1.9.0.zip` | Additional file / research data |
| `CoverLetter_v1.9.txt` | Cover letter (paste into Comments or upload) |
| `REVISION_NOTES_v1.9.0.md` | for the record (not uploaded) |

Also prepare before submission (not in this release): the completed author **vitae + passport-type
photograph** (template included in the repo under `paper/`), and **reviewer suggestions** (names +
institutional e-mail addresses) for the Suggest Reviewers step.

The v1.8.1 release keeps the Applied Acoustics package; v1.8.0 keeps the raw noise-measurement logs.
"""

import urllib.request, urllib.error

def api(path, raw=False, data=None, method=None, ctype="application/json", retries=3):
    host = "uploads.github.com" if raw else "api.github.com"
    url = f"https://{host}/repos/{REPO}/{path}"
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, method=method or ("POST" if data is not None else "GET"))
            req.add_header("Authorization", f"token {T}")
            req.add_header("Accept", "application/vnd.github+json")
            req.add_header("User-Agent", "cascade-release-script")
            body = None
            if data is not None:
                if isinstance(data, (dict, list)):
                    body = json.dumps(data).encode()
                    req.add_header("Content-Type", "application/json")
                else:
                    body = data
                    req.add_header("Content-Type", ctype)
            with urllib.request.urlopen(req, data=body, timeout=240) as r:
                resp = r.read()
                return r.status, (json.loads(resp) if resp and r.headers.get("Content-Type", "").startswith("application/json") else resp)
        except Exception as e:
            last = e
            print(f"    api {path.split('?')[0]} attempt {attempt+1} failed: {e}")
            time.sleep(8 * (attempt + 1))
    raise last

S = "/tmp/my-project/download/CascadeBench_Submission_CSL"
ASSETS = [
    (f"{S}/CascadeBench_Manuscript_v1.9.0.pdf", "application/pdf"),
    (f"{S}/Highlights.txt", "text/plain"),
    (f"{S}/CascadeBench_Supplementary_v1.9.0.pdf", "application/pdf"),
    (f"{S}/latex_source_v1.9.0.zip", "application/zip"),
    (f"{S}/anonymised_repository_snapshot_v1.9.0.zip", "application/zip"),
    (f"{S}/CoverLetter_v1.9.txt", "text/plain"),
    ("/tmp/my-project/repo_clone/paper/REVISION_NOTES_v1.9.0.md", "text/markdown"),
]

# 1. find or create release
try:
    st, rel = api(f"releases/tags/{TAG}")
    rid = rel["id"]
    print(f"reusing release {rid} ({rel['html_url']})")
except urllib.error.HTTPError:
    st, rel = api("releases", data={"tag_name": TAG, "name": NAME, "body": BODY})
    rid = rel["id"]
    print(f"created release {rid} ({rel['html_url']})")

api(f"releases/{rid}", method="PATCH", data={"name": NAME, "body": BODY, "draft": False, "prerelease": False})

# 2. assets (delete + reupload on size mismatch)
st, existing = api(f"releases/{rid}/assets")
have = {a["name"]: a for a in existing}

for path, ctype in ASSETS:
    name = os.path.basename(path)
    size = os.path.getsize(path)
    if name in have:
        a = have[name]
        if a["size"] == size:
            print(f"  {name}: already uploaded, size matches ({size})")
            continue
        api(f"releases/assets/{a['id']}", method="DELETE")
        print(f"  {name}: deleted stale ({a['size']} != {size})")
    st, up = api(f"releases/{rid}/assets?name={name}", raw=True, data=open(path, "rb").read(), ctype=ctype)
    print(f"  {name}: uploaded {up['size']} bytes (local {size})")

# 3. verify
st, final = api(f"releases/{rid}/assets")
print("\nfinal asset list:")
allok = True
for a in final:
    local = [p for p, _ in ASSETS if os.path.basename(p) == a["name"]]
    if not local:
        print(f"  {a['name']:55s} {a['size']:>9,} B  (not in manifest)")
        continue
    ok = a["size"] == os.path.getsize(local[0])
    allok &= ok
    print(f"  {a['name']:55s} {a['size']:>9,} B  {'OK' if ok else 'MISMATCH'}")
st, rel2 = api(f"releases/{rid}")
print(f"\nrelease: {rel2['html_url']}  draft={rel2['draft']} prerelease={rel2['prerelease']} assets={len(final)}")
sys.exit(0 if allok else 1)
