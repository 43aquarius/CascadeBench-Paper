# CascadeBench Experiment Scripts

All scripts are deterministic (fixed seeds) and checkpointed: every runner
appends to a JSONL log and skips work that is already present, so any
interrupted phase resumes where it stopped.

## Pipeline order

| Step | Script | Output | Approx. cost |
|------|--------|--------|--------------|
| 1 | `corpus_build.py` | `corpus/corpus.jsonl`, `corpus/babble_sources.jsonl` | seconds, free |
| 2 | `run_tts.py` | `audio/tts/*.wav` + `results/tts_log.jsonl` | 520 calls, Sambert free tier |
| 3 | `perturb.py` | `audio/perturbed/{cond}/*.wav` + `audio/perturbed_8k/...` | local CPU, ~15 min |
| 4 | `run_asr.py <system>` | `results/asr_<system>.jsonl` | see quota table below |
| 5 | `run_mt.py oracle` / `refmax` / `cascade` / `e2e_omni` | `results/mt_*.jsonl` | see quota table |
| 6 | `run_lt_shard.py <shard>` | `results/mt_e2e_lt.jsonl` | LiveTranslate, single connection |
| 7 | `analysis.py` | `results/analysis_results.json` | local CPU, ~2 min |
| 8 | `figures.py` | `figures/fig*.pdf` + `.png` (300 dpi) | local CPU |

`run_chunk.sh <seconds> <task...>` is a convenience orchestrator that runs
several phases in parallel inside one shell invocation and stops cleanly at a
time budget (useful under sandbox wall-clock limits).

`check_progress.py` prints a per-phase completion summary.

## API key

Set the DashScope (Alibaba Cloud Model Studio) key either via the
environment variable `DASHSCOPE_API_KEY` or by creating `apikey.txt` at the
repository root. The study consumed only complimentary quotas:

| System | Model id | Free quota shape |
|--------|----------|------------------|
| Streaming ASR | `paraformer-realtime-v2`, `paraformer-realtime-8k-v2` | ~36 k s audio / month |
| LLM-ASR | `qwen-audio-3.1-asr-flash`, `qwen3-asr-flash` | ~1 M tokens / month |
| E2E / translate | `qwen3.8-omni-flash`, `qwen3.8-livetranslate-flash-realtime` | ~1 M tokens / month |
| Text MT / refs | `qwen-mt-uni`, `qwen3.8-max` | per-character free tier |
| TTS | Sambert voices (`sambert-zhida-v1`, ...) | ~30 k calls / month / voice |


## Second-vendor GLM backend (v1.5 / v1.7)

The second-backend validation re-translates the Qwen-Audio (q31) recognition
outputs with the GLM engine of a second vendor (Z.ai):

| Script | Output | Notes |
|--------|--------|-------|
| `glm_translate2.mjs` | `results/glm_tasks.jsonl` | v1.4/v1.5 rounds: references + 4-condition backend (batched, 8 sentences/call) |
| `glm_translate_v17.mjs` | `results/glm_tasks.jsonl` (appended) | v1.7 round: backend re-translation extended to all nine real-speech conditions (same batch protocol, resumable) |
| `v17_glm9conds.py` | `results/analysis_v17_glm9.json` | n-aligned nine-condition backend matrix + per-backend pass-through slopes |
| `v17_table.py` | stdout | main-paper Table (tab:backend) rows, cross-checked against the JSON |
| `v17_suptable.py` | `paper/latex/supp_tables/tab_s14_glm9.tex` | Supplementary Table S14 |

Both `.mjs` runners import the Z.ai SDK from `scripts/zai-sdk/dist/index.js`
(not committed; place a copy of `z-ai-web-dev-sdk` there, or edit the `SDK`
path). They are resumable: completed sentences are skipped on re-run, and a
429 rate-limit exits with code 3 so a driver loop (`glm_drive.sh`) can retry
after a cool-down.

Protocol notes:

- Translation prompt: one sentence per call in v1.4, batched
  `N||translation` lines in v1.5/v1.7; the batch mode was verified
  sentence-level consistent with the per-sentence mode before adoption.
- n-alignment: the q31 transcription list is authoritative (150 per
  condition); the 61 slots where the frontend returned no transcription
  carry an empty translation under both backends, so every matrix cell
  covers the same sentences.
- The 429 penalty period on the Z.ai gateway can last hours; the driver
  script probes with one lightweight call before each block.

## Operational notes discovered the hard way

- `qwen3.8-livetranslate-flash-realtime` refuses concurrent websocket
  connections: run `run_lt_shard.py` with a single worker. Use voice
  `Tina`. Its intermittent disconnects surface as `JSONDecodeError`, which
  is treated as retryable in `apis.py`.
- `qwen-audio-3.1-asr-flash` requires the `input_audio` payload format and
  `parameters.format` set per audio encoding.
- `qwen-mt-uni` takes `input.source_texts` + `input.target_lang`, not the
  plain messages format.
- `paraformer-realtime-8k-v2` (telephony model) hallucinates fluent but
  wrong English transcripts, so it is evaluated on Mandarin only; this is
  stated in the paper.
- `qwen3.8-omni-flash` free quota was exhausted near the end of the study,
  so the omni end-to-end path covers a subset of the grid (documented in
  the paper's limitations).
- Empty transcripts (`NO_WORDS`) from qwen systems are scored as 100 %
  recognition error for that sentence, per the paper's protocol.

## Reproducing the paper numbers

```bash
pip install -r requirements.txt
python3 analysis.py     # regenerates results/analysis_results.json (verified identical)
python3 figures.py      # regenerates all 7 figures at 300 dpi
```

The committed `results/analysis_results.json` was verified to be regenerated
byte-identically by `analysis.py` from the committed raw logs.
