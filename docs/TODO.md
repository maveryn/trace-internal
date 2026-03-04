# TRACE TODO

## Purpose
This is the working backlog for TRACE implementation.
Use it to track what is actively being built, what is next, and what is intentionally deferred.

## Update rules
1. Update this file whenever scope, priorities, or implementation status changes.
2. Move completed items to the `Done` section in the same change that lands implementation.
3. Keep items concrete and testable; avoid vague reminders.
4. If a decision is deferred, note why and where it will be handled later.

## Now (P0)
1. Add more tests for geometry-angle failure paths:
- forced tie/invalid-threshold generation behavior,
- query-weight edge-case coverage in builder.
2. Generate and review representative sample images for the new geometry-angle task.
3. Add shared scene/background style variation infrastructure (graph-paper families, tile-style families) with task-family defaults.

## Next (P1)
1. Add additional geometry/chart task families using the same answer+evidence pattern.
2. Add verifier scaffolding for structural answer/evidence checks (no reward tolerance tuning yet).
3. Expand failure-path tests:
- failure-bundle persistence,
- validation-report error-code coverage,
- cleanup command behavior (`dry-run` vs `--apply`).
4. Add richer build telemetry dashboards/reports.

## Later (P2)
1. Add split-artifact generation with deterministic split policies and metadata.
2. Add richer dataset inspection/diagnostics tooling around build reports and trace manifests.

## Deferred decisions
1. Verifier tolerance presets and reward design:
- deferred until RLVR scoring phase,
- dataset ABI continues storing exact float evidence values.

## Done
1. Core vertical slice implemented:
- ABI models, canonical hashing, seed derivation,
- sidecar trace I/O, dataset builder, validation core,
- `tile_shortest_path` task,
- CLI scripts and initial regression tests.
2. Core architecture/reuse docs added:
- `SYSTEM_ARCHITECTURE.md`,
- `SHARED_UTILITIES.md`.
3. Sampling policy documented:
- task-level global sampling,
- per-task internal query sampling.
4. P0 builder/runtime upgrades completed:
- strict reproducibility checker with first-mismatch summaries,
- weighted task-level global sampler (with `num_instances` mode),
- per-task query-type sampling (uniform default, optional weights),
- query-type accepted-count validation hooks.
5. Taxonomy decision locked:
- keep `task_group` broad by reasoning style,
- use `task_group = measurement` for geometry value-style tasks,
- keep most variation in per-task `query_type`.
6. Implemented `geometry_angle_value_query` under `geometry/measurement` with query variants:
- `min`, `max`, `median`, `closest_to_x`, `smallest_above_x`, `largest_below_x`, `difference_max_min`,
- unique-answer-by-construction enforcement,
- evidence as vertex points (`point_set` or ordered `point_path`).
7. Added shared query utility module for reusable value-query semantics:
- `trace/tasks/geometry/shared/value_queries.py` (with backward-compatible shim at `trace/tasks/shared/value_queries.py`).
8. Prompt system design and documentation plan added:
- `docs/PROMPT_SYSTEM.md`,
- task-doc template and requirements under `docs/tasks/`.
9. Implemented deterministic post-image noise infrastructure with task-family defaults:
- shared module `trace/core/visual/noise.py`,
- integrated into `geometry_angle_value_query` and `tile_shortest_path`,
- trace metadata emission under `render_spec.post_image_noise`,
- defaults: `geometry/measurement apply_prob=0.75`, `tile/path apply_prob=0.0`.
10. Implemented external prompt bundle system and migrated active tasks:
- added shared prompt modules under `trace/core/prompts/` (assets/schema/select/render),
- added external prompt bundles under `prompts/geometry/measurement/` and `prompts/tile/path/`,
- migrated `geometry_angle_value_query` and `tile_shortest_path` to deterministic bundle-based prompt rendering,
- prompt variant metadata now emitted in `trace_payload.query_spec.prompt_variant`.
