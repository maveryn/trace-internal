# TRACE TODO

## Now (P0)
1. Extend pre-finalize validation with prompt checks:
- prompt bundle metadata presence on each instance,
- bundle/key existence checks,
- required-slot/cardinality conformance checks.
2. Expand tests for failure paths:
- geometry-angle edge conditions (invalid threshold, tie rejection),
- query-weight edge cases in builder,
- validation error-code coverage.
3. Add shared scene/background-style variation presets by task group (deterministic + recorded in trace).
4. Regenerate full review samples (default 50) for tasks after logic/prompt/render updates.

## Next (P1)
1. Add additional measurement-style tasks (for example geometry area value query) reusing value-query and prompt infrastructure.
2. Add additional tile/path-adjacent task(s) that require grounded evidence.
3. Expand build diagnostics and reporting for easier dataset QA.

## Later (P2)
1. Add split-artifact generation with deterministic split policy metadata.
2. Add richer dataset inspection tooling around trace shards and build reports.

## Deferred
1. Reward/tolerance policy tuning for RLVR scoring.
- Dataset ABI stores exact float evidence values; tolerance strategy is deferred to training/reward stage.

## Done (high level)
1. Core deterministic build/ABI/trace pipeline and strict-repro framework.
2. Validation/reporting baseline and error-code catalog.
3. External prompt-bundle system and migration of active tasks.
4. Task-group config loader and deterministic post-image noise infrastructure.
5. Initial grounded tasks:
- `tile_shortest_path`
- `geometry_angle_value_query`
6. Sample-generation CLI with per-task artifacts and combined Excel.
