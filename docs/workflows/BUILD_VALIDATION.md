# TRACE Build and Validation

Operational policy for build lifecycle and pre-finalize validation.

## 1) Build lifecycle
1. Build to staging directory.
2. Generate train instances + sidecar traces.
3. Run pre-finalize validation.
4. Optional strict-repro second pass and compare.
5. Write reports.
6. Atomic finalize on success; failure bundle on error.

## 2) Mandatory trace contract
1. Sidecar trace export is required.
2. Every `TrainInstance` must include `trace_ref`.
3. Trace write failures are hard build failures.

## 3) Required pre-finalize checks
1. Train-instance schema validity.
2. `trace_ref` existence/hash/index integrity.
3. Image path/hash integrity.
4. Task count expectations.
5. Single `instance_version` consistency.
6. Prompt metadata/bundle/key validity.
7. Required slot conformance and unresolved placeholder checks.
8. Prompt variant-count/index consistency.
9. Task-doc consistency: every registered task has `docs/tasks/<task_id>.md`, and `docs/tasks/README.md` links match active tasks.

## 4) Task-review and distribution policy
For new or distribution-changing task logic:
1. Run the task-review workflow on affected tasks:
   - full review: `PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode full`
   - distribution only: `PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode distribution`
   - inspection only (skip distribution analysis): `PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode inspection`
   - by default review scripts use all visible CPUs via `--workers`; override it explicitly when you need a smaller review footprint
2. Required review scope:
   - random sample review: 100 samples per task (`random_review_100.json`)
   - per-variant distribution review: 100 samples per task variant when variants exist (`distribution_review.json`)
   - manual inspection workbook: 25 samples per task variant in `task-reviews/<domain>/<task_id>/<task_id>.xlsx` (one sheet per task variant)
   - review artifacts live under `task-reviews/<domain>/<task_id>/` so the review root stays grouped by domain as task count grows
3. Required gating checks (computed from answer values only):
   - `unique_answers >= 5`
   - `max_answer_frequency < 25%`
   - apply checks per task variant; task-level pass requires every variant to pass.
   - zero collected samples for a task/variant review is a hard fail (`no_samples_collected`).
4. Numeric answer-distribution summaries still report `max_five_bin_frequency` and the 5 equal-width bin counts over the observed numeric range, but these are informational review metrics rather than hard pass/fail gates.
5. For quick distribution-only runs (without workbook generation), the dedicated checker remains available:
   - `PYTHONPATH=. python scripts/check_task_answer_distribution.py --tasks <task_id>`

## 5) Reports and failure artifacts
Always emit in staging:
1. `validation_report.json`
2. `build_report.json`

On failure, keep:
1. staging directory (for debugging),
2. failure bundle under `failed_builds/<dataset_id>/`.

## 6) CI strict-repro profile
Run CI with a pinned strict-repro config and fail on:
1. record mismatches,
2. trace mismatches,
3. image-byte/hash mismatches,
4. missing pinned tasks or attempt-limit exhaustion.

## 7) Test-scaling policy
1. Keep shared invariants in family-level contract tests.
2. Keep per-task tests focused on task-specific constraints and edge cases.
3. Avoid duplicating the same determinism/build smoke assertions across every task file.
4. For config-loading tests, validate merge/wiring/schema behavior (for example `shared` vs `task_overrides`) instead of asserting every literal default value per task.
