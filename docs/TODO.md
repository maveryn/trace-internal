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
1. Add strict reproducibility checker:
- run identical configs twice,
- compare canonical `TrainInstance` records,
- compare decompressed sidecar trace content,
- compare image bytes/hashes,
- fail with first mismatch summary.
2. Implement task-level global sampling policy in builder:
- equal task weight default,
- configurable task weights,
- derived domain/task-group probabilities in reporting.
3. Implement per-task query-type sampling:
- default uniform within task,
- optional task-level query-weight override,
- emit selected `query_type` in trace metadata and build report summaries.
4. Add query-type count validation hooks for multi-query tasks.

## Next (P1)
1. Implement `geometry_angle_value_query` task with variants:
- `min`, `max`, `median`,
- `kth_smallest`, `kth_largest`,
- `closest_to_x`,
- `smallest_above_x`, `largest_below_x`,
- `difference_max_min`.
2. Enforce uniqueness-by-construction for all angle query variants (hard reject/resample on ties).
3. Add prompt variation framework:
- template packs with deterministic variant selection by seed namespace,
- task/query-specific slot filling with consistent contracts.
4. Add shared query helper module(s) for order-stat and threshold queries where reusable.

## Later (P2)
1. Add additional geometry/chart task families using the same answer+evidence pattern.
2. Add verifier scaffolding for structural answer/evidence checks (no reward tolerance tuning yet).
3. Expand failure-path tests:
- failure-bundle persistence,
- validation-report error-code coverage,
- cleanup command behavior (`dry-run` vs `--apply`).
4. Add richer build telemetry dashboards/reports.

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
