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
