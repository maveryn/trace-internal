# TRACE Status

Date: 2026-03-04

## Current scope
TRACE is a deterministic grounded visual reasoning data-generation environment with sidecar traces for replay/debug and lightweight train records for model training.

## Implemented
1. Core ABI and dataset build pipeline:
- `TrainInstance` + `TraceInstance` contracts,
- sidecar trace shards with `trace_ref`,
- deterministic identity/hash/seed utilities,
- atomic finalize + failure bundle behavior.
2. Validation and reproducibility foundations:
- schema/trace/image/count/version/identity validation,
- validation reports with cataloged error codes,
- strict reproducibility mode comparing records, traces, and images.
3. Prompt infrastructure:
- external prompt bundles under `prompts/`,
- deterministic task/query template variant selection,
- strict placeholder rendering,
- prompt variant metadata emission in task trace payloads.
4. Visual variation foundation:
- deterministic post-image noise helper (`trace/core/visual/noise.py`),
- task-group defaults loaded from `configs/task_groups/<domain>/<task_group>.yaml`.
5. Implemented tasks:
- `tile_shortest_path` (`domain=tile`, `task_group=path`),
- `geometry_angle_value_query` (`domain=geometry`, `task_group=measurement`).
6. Task/sample tooling:
- sample generation CLI (`scripts/generate_task_samples.py`) with images, per-sample JSON, summaries, and combined Excel output.
7. Test baseline:
- repository tests currently pass (`18 passed`).

## Not yet implemented
1. Prompt-bundle checks in pre-finalize validation:
- prompt bundle existence and key checks,
- required placeholder conformance checks at dataset validation stage,
- enforced template-cardinality checks at dataset validation stage.
2. Additional domain/task coverage beyond the first two tasks.
3. Shared scene/background-style variation families (for example graph-paper variants).
4. Verifier-specific structural reward checks beyond schema/consistency validation.

## Immediate next steps
1. Add validation pass extensions for prompt metadata and prompt asset conformance.
2. Add one more geometry measurement task (for example area value query) using existing value-query + prompt infrastructure.
3. Add one more tile path/measurement task to stress shared abstractions and reduce task-local code.
4. Expand failure-path tests:
- ambiguity rejection coverage,
- query-weight edge cases in builder,
- validation error-code coverage.
5. Refresh task samples to full review sets (default 50 per changed task) after each task logic/prompt/render change.

## Keep in sync
If architecture or contracts change, update this file together with:
1. `DSL_BLUEPRINT.md`,
2. `SYSTEM_ARCHITECTURE.md`,
3. `TASK_AUTHORING.md`,
4. `PROMPT_SYSTEM.md`,
5. `TODO.md`.
