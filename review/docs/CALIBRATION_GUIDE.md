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

Manual feedback and audit checkboxes live in:

```text
review/feedback/review_feedback.sqlite
```

Aggregate solve-rate status defaults to:

```text
review/calibration_sweep_status.json
review/calibration_sweep_status.md
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
task, prompt, renderer, config, verifier, or evidence contract changes, delete
or regenerate that task's current review and solve-rate artifacts before using
them for acceptance.

## Acceptance Gates

Each task is accepted only on the same `100` sampled task instances with `24`
rollouts per instance.

Required gates for `qwen25vl7b`:

1. `0 / 100` sampled prompts exceed `2048` prompt tokens.
2. Response cap rate is `<= 0.25`.
3. Hard-question fraction is `< 0.30`, where hard means `0 / 24` successful
   rollouts for that question.
4. Easy-question fraction is `< 0.20`, where easy means `> 18 / 24`
   successful rollouts for that question.
5. Mean solve rate is `0.15 <= mean <= 0.75` over all `2400` rollouts.

A task that fails prompt length or response cap is blocked until prompt,
rendering, density, or output-format issues are fixed. A task that passes those
but misses hard, easy, or mean gates needs manual tuning.

## Domain Done

A domain is done only when every active task has:

- current browser-visible task-review sidecars under `review/task-reviews`;
- manual audit passing in the web app for prompt, image, evidence,
  distribution, and solve-rate review;
- accepted `qwen25vl7b` solve-rate status;
- current docs and task inventory for the active public task surface.

Excel workbooks are optional static exports. They are not the default review
surface and do not replace browser-app manual audit.
