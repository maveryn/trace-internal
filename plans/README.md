# TRACE Active Planning Workspace

This directory now keeps only current active-task audit and manual calibration
tracking files at the top level.

Live files and folders:

- `CALIBRATION_PLAN.md`
- `DOMAIN_REFACTOR_AGENT_BRIEF.md`
- `MERGE_SPLIT_REFACTOR_REFERENCE.md`
- `PROGRESS.md`
- `PROGRESS_SUMMARY.md`
- `SHARED_VISUAL_STYLE_REFACTOR_NOTE.md`
- `PUZZLE_STYLE_PACK_WORKFLOW.md`
- `calibration-status/`
- `active_task_audit.md`
- `active_task_audit.json`
- `task-reviews/`

Non-current one-off calibration artifacts have been removed from
this workspace; current active-task inventory should come from the generated
audit files and source-of-truth docs.

Current manual task-review workbooks belong under:

`plans/task-reviews/<public_domain>/<scene_id>/<task_id>/`

Scoped per-task or exploratory calibration status summaries belong under:

`plans/calibration-status/`

Keep only the aggregate calibration sweep status files at the `plans/` root.

Solve-rate artifacts will be regenerated later and should not be inferred from
non-current files unless the current progress summary explicitly says so.

The current calibration and TRACE-owned version baseline is `v0`. Regenerated
task-review, distribution, solve-rate, and scene-review artifacts must carry
`calibration_baseline: "v0"`; prompt bundles, TRACE schema/version fields,
taxonomy version wording, instance versions, and reward contracts should also
use `v0`. Artifacts without the current baseline metadata are stale for current
acceptance and should be deleted or regenerated for the relevant task/scene
before use.

## Current Calibration Runbook

Use `plans/CALIBRATION_PLAN.md` as the only current source of truth for task
calibration. Non-current calibration notes and smoke files are not acceptance
inputs.

Current rules:

- Run only `qwen25vl7b` for all future task calibration.
- Use `100` task samples and `24` rollouts per sample.
- Generate fresh `v0` artifacts from current code/config. Do not reuse old
  review or solve-rate files that lack the current baseline metadata.
- Before any solve-rate run, the answer-distribution gate must pass using the
  same sampler as dataset generation. Check the original `100` calibration rows
  first; if needed, validate cumulative same-sampler shards up to `500` rows.
  Review workbooks and solve-rate probing still use the original `100` rows.
  If distribution still fails after `500`, report the task as blocked or
  distribution-failed instead of changing config or sampling inside the run.
- Qwen2.5 server: `Qwen/Qwen2.5-VL-7B-Instruct` at
  `http://127.0.0.1:8002/v1`, response cap `2048`, vLLM
  `--max-model-len 4096`.
- On the one-GPU machine, shared calibration and external benchmark runs should
  use `http://127.0.0.1:8002/v1` and hold
  `logs/vllm/locks/qwen25vl7b_8002.lock` while sending requests. Agents should
  wait on that lock instead of starting a competing model server.
- Existing Qwen3-4B comparison results are not part of future acceptance
  decisions.
- A task is accepted only if `qwen25vl7b` passes: no prompt over `2048`,
  response cap rate `<= 0.25`, `hard_frac < 0.30` for `0 / 24` solved,
  `easy_frac < 0.20` for `> 18 / 24` solved, and
  `0.15 <= mean_solve_rate <= 0.75`.
