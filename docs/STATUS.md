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
- prompt metadata/bundle/key/placeholder/cardinality validation,
- validation reports with cataloged error codes,
- strict reproducibility mode comparing records, traces, and images.
3. Prompt infrastructure:
- external prompt bundles under `prompts/`,
- deterministic task/query template variant selection,
- deterministic output-mode prompt variant selection (`answer_only`, `answer_and_evidence`) with per-instance storage of both prompt forms,
- strict placeholder rendering,
- prompt variant metadata emission in task trace payloads.
4. Visual variation foundation:
- deterministic post-image noise helper (`trace/core/visual/noise.py`),
- deterministic task-group background-style helper (`trace/core/visual/background.py`),
- task-group defaults loaded from `configs/task_groups/<domain>/<task_group>.yaml`.
5. Implemented tasks:
- `tile_shortest_path` (`domain=tile`, `task_group=path`),
- `geometry_angle_value_query` (`domain=geometry`, `task_group=measurement`).
  - geometry measurement value queries now use feasible-uniform answer-conditioned sampling per `query_type` to reduce answer-shape bias.
  - geometry angle layouts enforce explicit non-overlap/touch clearance (>= one graph-paper square) via shared layout-constraint helpers.
6. Task/sample tooling:
- sample generation CLI (`scripts/generate_task_samples.py`) with images, per-sample JSON, per-task summaries, per-task distribution reports, per-task Excel files (embedded preview image, max side 384 px), and combined Excel output (one sheet per task).
7. Test baseline:
- repository tests currently pass (`24 passed`).

## Not yet implemented
1. Additional domain/task coverage beyond the first two tasks.
2. Verifier-specific structural reward checks beyond schema/consistency validation.

## Immediate next steps
1. Add one more geometry measurement task (for example area value query) using existing value-query + prompt infrastructure.
2. Add one more tile path/measurement task to stress shared abstractions and reduce task-local code.
3. Refresh task samples to full review sets (default 50 per changed task) after each task logic/prompt/render change.

## Keep in sync
If architecture or contracts change, update this file together with:
1. `BLUEPRINT.md`,
2. `SYSTEM_ARCHITECTURE.md`,
3. `TASK_AUTHORING.md`,
4. `CODE_DOCUMENTATION.md`,
5. `PROMPT_SYSTEM.md`,
6. `TODO.md`.
