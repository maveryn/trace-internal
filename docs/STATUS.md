# TRACE Status

Date: 2026-03-05

## Implemented
1. Deterministic build pipeline with sidecar trace shards and atomic finalize.
2. Typed train-instance ABI with mandatory `trace_ref`.
3. Pre-finalize validation + structured error codes.
4. Strict reproducibility comparison mode.
5. External prompt-bundle system with dual output modes.
6. Deterministic background/noise visual variation helpers.
7. Domain + task-group default config loading with section-level `shared` + `task_overrides` composition.
8. Shared helper layers for value queries, layout constraints, graph adapters, prompt variants, and output metadata.
9. Query-weight default fallback chain (`build override -> task-group sampling defaults -> uniform`).

## Active tasks
1. `tile_shortest_path` (`domain=tile`, `task_group=path`)
2. `geometry_angle_value_query` (`domain=geometry`, `task_group=measurement`)

## Current quality baseline
1. Tests currently pass (`27 passed`).
2. Sample tooling supports per-task artifacts, per-query distribution reports, and combined Excel output.

## Next priorities
1. Add another geometry measurement task (for example area value query).
2. Add another tile/path-adjacent task to stress shared abstractions.
3. Continue trimming duplication as new task families arrive.
