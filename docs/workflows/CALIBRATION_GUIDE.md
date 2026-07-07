# TRACE Calibration Guide

This is the current calibration runbook for TRACE task reviews and solve-rate
acceptance. Older review/planning artifacts are not acceptance inputs.

## Current Model

Use only `qwen25vl7b` for current task acceptance:

| model key | model | endpoint | response cap | max model len |
| --- | --- | --- | ---: | ---: |
| `qwen25vl7b` | `Qwen/Qwen2.5-VL-7B-Instruct` | `http://127.0.0.1:8002/v1` | `2048` | `4096` |

This machine has one calibration GPU. Do not start competing local vLLM
servers for calibration. Use the runner's endpoint lock:

```text
logs/vllm/locks/qwen25vl7b_8002.lock
```

Run calibration with `--probe-backend openai_server --models qwen25vl7b`.

## Review Artifacts

Generate current review artifacts under:

```text
review/task-reviews/<domain>/<scene_id>/<task_id>/
```

The browser review app reads that root by default. Resource review sheets live
under `review/task-reviews/assets/`.

Manual issue threads and audit checkboxes live in:

```text
review/feedback/review_feedback.sqlite
```

The review app UI calls reviewer comments **issues**. The underlying path and
schema retain the `feedback` name for compatibility.

The authoritative calibration status ledger for the current 50x8 pass is:

```text
review/calibration/50x8_qwen25vl3b_prompt_pilot_seed20260703/task_status_records.json
review/calibration/50x8_qwen25vl3b_prompt_pilot_seed20260703/task_status_records.md
```

Use that ledger for claims such as pending task count, accepted task count,
manual acceptance, and live registry coverage. The older top-level files are a
derived compatibility export only:

```text
review/calibration_sweep_status.json
review/calibration_sweep_status.md
```

Do not edit the compatibility export by hand, and do not treat a single
calibration sweep output as global truth. After updating the current
calibration ledger, regenerate the compatibility export with:

```bash
PYTHONPATH=. python scripts/sync_calibration_status_from_task_records.py
```

## Freshness

The current TRACE-owned artifact baseline is `v0`. Task-review manifests,
distribution reports, scene manifests, and solve-rate stats used for
acceptance must carry:

```json
{"calibration_baseline": "v0"}
```

Do not reuse stale artifacts from older roots, renamed tasks, removed tasks,
pre-refactor configs, or files without the matching baseline metadata. If a
task, prompt, renderer, config, verifier, or annotation contract changes, delete
or regenerate that task's current review and solve-rate artifacts before using
them for acceptance.

Calibration dataset manifests also carry a task source fingerprint covering the
task source directory, domain/shared task helpers, global task/core helpers,
domain configs, prompt assets, and rendering assets. The calibration sweep must
rebuild the task parquet whenever that fingerprint differs, even when the user
only requested `--force-models`. Probe output and `calibration_stats.json` must
carry the same fingerprint as the parquet they were run against; otherwise the
model output directory is stale and must be regenerated.

Use `--force-build` or `--force` when intentionally rebuilding a calibration
sample. `--force-models` is only for re-probing a still-current parquet; the
runner will now override stale reuse and rebuild automatically if source files
changed.

## Acceptance Gates

Each task is accepted only on the same `50` sampled task instances with `8`
rollouts per instance.

Required gates for `qwen25vl7b`:

1. `0 / 50` sampled prompts exceed `2048` prompt tokens.
2. Response cap rate is `<= 0.25`.
3. Hard-question fraction is `<= 0.50`, where hard means `0 / 8` successful
   rollouts for that question.
4. Easy-question fraction is `<= 0.25`, where easy means `8 / 8`
   successful rollouts for that question.
5. Mean solve rate is `0.10 <= mean <= 0.80` over all `400` rollouts.
6. Exact calibration parquet answer distribution passes: at least `4` unique
   answers and no answer above `1/3` frequency.

A task that fails prompt length or response cap is blocked until prompt,
rendering, density, or output-format issues are fixed. A task that passes those
but misses hard, easy, or mean gates needs manual tuning.

## Domain Done

A domain is done only when every active task has:

- current browser-visible task-review sidecars under `review/task-reviews`;
- manual audit passing in the web app for prompt, image, annotation,
  distribution, and solve-rate review;
- accepted `qwen25vl7b` solve-rate status;
- current docs and task inventory for the active public task surface.

Excel workbooks are optional static exports. They are not the default review
surface and do not replace browser-app manual audit.
