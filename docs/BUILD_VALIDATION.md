# TRACE Build and Validation

## Purpose
This document is the source of truth for dataset build lifecycle, pre-finalize validation,
failure handling, cleanup behavior, and CI strict reproducibility checks.

Use this together with:
1. `docs/DSL_BLUEPRINT.md` for architecture and ABI contracts.
2. `docs/TASK_AUTHORING.md` for task-specific authoring guidance.

## Build lifecycle
Builds follow this sequence:
1. Create temp staging directory.
2. Generate `TrainInstance` records and sidecar trace shards.
3. Run required pre-finalize validation.
4. If validation passes, atomically finalize dataset output.
5. If validation fails, do not finalize; persist failure bundle.

## Sidecar trace contract
1. Trace payload storage is sidecar-only.
2. Sidecar trace export is mandatory for every dataset build.
3. Every `TrainInstance` must include `trace_ref`.
4. If any sidecar trace write fails, fail the build (no partial dataset).

## Pre-finalize validation (required)
Before atomic finalize, validate all of:
1. schema validity for every `TrainInstance`.
2. `trace_ref` integrity for every instance.
3. image path/hash integrity for every image entry.
4. per-task accepted-count expectations for current build mode.
5. single `instance_version` consistency across dataset.
6. if configured for a multi-query task, per-task query-type accepted-count expectations.
7. prompt metadata presence for each instance (`trace.query_spec.prompt_variant`).
8. referenced prompt bundle/key existence checks.
9. required prompt-slot metadata conformance checks.
10. unresolved placeholder token checks on rendered prompt text.
11. template-list cardinality checks (10+ variants per required key) and metadata count/index consistency checks.

Validation behavior:
1. collect all detected errors.
2. fail once with summarized output.
3. write `<dataset_root_tmp>/validation_report.json`.
4. print concise console summary.

## Validation report contract
`validation_report.json` is unversioned and must include:
1. top-level summary fields:
- `total_errors`
- `error_counts_by_code`
- `error_counts_by_category`
2. full error list (no sampling cap).
3. per-error fields:
- `error_code`
- human-readable message
- concise context references (for example `instance_id`, `field_path`).
4. deterministic error ordering.
5. build context block:
- `dataset_id`
- temp path
- timestamp

Validation error codes are cataloged in `docs/VALIDATION_ERROR_CODES.md`.

## Failure bundle policy
On failure:
1. final dataset path must remain untouched.
2. persist failure bundle to `<output_root>/failed_builds/<dataset_id>/`.
3. include:
- `validation_report.json`
- resolved build config snapshot
- log path/reference
4. overwrite existing bundle for same `dataset_id` (keep latest).
5. failure-bundle write is best-effort; preserve original failure reason if bundle write also fails.

## Temp directory and cleanup
1. successful builds clean temp staging directory.
2. failed builds keep temp staging directory for debugging.
3. provide manual cleanup command/flag for failed temp dirs and failure bundles.
4. cleanup is all-or-nothing.
5. cleanup defaults to dry-run; requires explicit `--apply` to delete.
6. default cleanup targets both failed temp dirs and `<output_root>/failed_builds/` bundles.

## CI strict reproducibility profile
Default CI reproducibility profile:
1. run `strict_repro` on fixed small regression builds.
2. sample size is task-scaled: `K=5` accepted instances per enabled task.
3. require exact `K` per enabled task.
4. fail immediately if any task exceeds `max_attempts_per_instance_ci=100`.
5. use pinned config under `configs/ci/` (for example `configs/ci/strict_repro.yaml`).
6. pinned CI config must contain explicit enabled task list.
7. fail if any pinned enabled task is missing from registry.
8. compare decompressed canonical sidecar content.
9. ordering mismatches are failures.
10. failure output includes first mismatching `instance_id`, field-level diff, and image hash/byte diff location.
