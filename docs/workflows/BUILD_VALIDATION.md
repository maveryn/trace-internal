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
4. Every generated trace payload must include the full mandatory sidecar surface before finalize:
   - `scene_ir`
   - `query_spec`
   - `render_spec`
   - `render_map`
   - `execution_trace`
   - `witness_symbolic`
   - `projected_annotation`

## 3) Required pre-finalize checks
1. Train-instance schema validity.
2. `trace_ref` existence/hash/index integrity.
3. Image path/hash integrity.
4. Public taxonomy fields (`domain`, `scene_id`, `task`) plus source `task_group`.
5. Task count expectations.
6. Single `instance_version` consistency.
7. Prompt metadata/bundle/key validity.
8. Required slot conformance and unresolved placeholder checks.
9. Prompt variant-count/index consistency.
10. `reward_contract` schema validity plus train/trace reward-contract consistency.
11. Task-doc consistency: every registered task has `docs/tasks/<task_id>.md`, and `docs/tasks/README.md` links match active tasks.
12. Active inventory consistency: `docs/ACTIVE_TASK_INVENTORY.md` matches the live registry/taxonomy generator.

## 4) Task-review and distribution policy
For new or distribution-changing task logic:
1. Run the task-review workflow on affected tasks:
   - full review: `PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode full --out-root review/task-reviews`
   - distribution only: `PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode distribution --out-root review/task-reviews`
   - inspection only (skip distribution analysis): `PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode inspection --out-root review/task-reviews`
   - by default review scripts use all visible CPUs via `--workers`; override it explicitly when you need a smaller review footprint
2. Required review scope:
   - random sample review: 100 samples per task (`random_review_100.json`)
   - per-query-id distribution review: 100 samples per query id when variants exist (`distribution_review.json`)
     - per-query-id collection uses the same task sampler as dataset generation, with only explicit public variant/query overrides when needed for coverage
   - browser inspection sidecars: images, JSON data, prompt/answer/annotation payloads, and manifests under `review/task-reviews/<domain>/<scene_id>/<task_id>/`
     - pass `--balanced-inspection-by-query` only for a deliberately balanced per-query visual audit; calibration reviews should use the default 100 total task samples
   - review artifacts live under `review/task-reviews/<domain>/<scene_id>/<task_id>/` so the review root stays grouped by domain and scene as task count grows
   - current calibration artifacts must carry `calibration_baseline: "v0"` in manifests or stats files; artifacts without that metadata are stale for current acceptance
   - after regenerating review artifacts, reload the browser review app index with **Reload Index** or `POST /api/reload` before inspection; if app code/templates/CSS/JS/indexer/resource/feedback logic changed, restart the app instead of only reloading; inspect the current artifacts in the app, verify the affected page reflects the updated local files, and save sample-specific issues there; Excel exports are optional static snapshots, not the required review surface. The app UI and browser route say "issue" and `/issues`; internal APIs/storage still use `feedback`.
3. Required gating checks (computed from answer values only):
   - `unique_answers >= 5`
   - `max_answer_frequency < 1/3`
   - apply checks per query id; task-level pass requires every variant to pass.
   - zero collected samples for a task/variant review is a hard fail (`no_samples_collected`).
4. Solve-rate calibration must also gate the exact exported calibration parquet,
   not only a separately sampled review stream. `scripts/run_task_calibration_sweep.py`
   runs `scripts/check_rlvr_probe_distribution.py` on the realized `100` rows
   first; if the answer-frequency gate fails, it may generate up to four
   additional same-sampler validation shards of 100 rows each and validate the
   cumulative distribution. Browser review samples and solve-rate runs still use the
   original 100-row shard. Any remaining validation failure blocks the task until the
   sampler is fixed.
5. Numeric answer-distribution summaries still report `max_five_bin_frequency` and the 5 equal-width bin counts over the observed numeric range, but these are informational review metrics rather than hard pass/fail gates.
6. For quick distribution-only runs (without inspection sidecar generation), the dedicated checker remains available:
   - `PYTHONPATH=. python scripts/check_task_answer_distribution.py --tasks <task_id>`
   For exact exported RLVR probes, use:
   - `PYTHONPATH=. python scripts/check_rlvr_probe_distribution.py --parquet <probe.parquet> --dataset-root <trace_dataset_root>`

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

## 8) Large-build canary policy
Before launching a large all-task build for training:
1. run a one-sample-per-task canary build first,
2. confirm every active task survives builder finalization with the mandatory trace payload keys above,
3. only then scale to the full target row count and RLVR export.
