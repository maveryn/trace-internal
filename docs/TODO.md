# TRACE TODO

## Now (P0)
1. No immediate P0 cleanup blockers; keep follow-up review findings flowing into docs/tests as new task families land.

## Next (P1)
1. Extend objective-first measurement pattern to additional domains.
2. Add cross-domain `scene_variant` + role-binding spec in architecture/ABI docs.
3. Improve dataset QA diagnostics/report summaries.
4. Extend analytical geometry to additional objectives beyond `task_geometry_analytical_2d_area` / `task_geometry_analytical_3d_surface_area` (`perimeter`, composite/shaded-region area, additional 3D objectives).

## Later (P2)
1. Add split-artifact generation with deterministic split policy metadata.
2. Add richer dataset inspection tooling around trace shards and build reports.
3. Keep future tile task groups aligned with `configs/domains/tile/base.yaml` shared defaults.
4. Expand geometry analytical task suite with multi-step composite-region and shaded-area reasoning.
5. Add geometry `estimate` task track for non-exact quantitative reasoning (for example count graph squares, count angles `< 90°`).

## Deferred
1. Reward/tolerance policy tuning for RLVR scoring.
- Dataset ABI stores exact evidence values; tolerance policy remains training/reward-stage configurable.
2. Polygon measurement variants not in current scope:
- polygon diameter
- polygon min-side / max-side

## Done (high level)
1. Core deterministic build/ABI/trace pipeline and strict-repro framework.
2. Validation/reporting baseline and error-code catalog.
3. External prompt-bundle system and migration of active tasks.
4. Domain/task-group config loader and deterministic visual-variation infrastructure.
5. Initial grounded tasks:
- `task_tile_path_shortest_path`
- `task_geometry_measurement_angle`
- `task_geometry_measurement_area`
- `task_geometry_measurement_perimeter`
- `task_geometry_measurement_length`
- `task_geometry_measurement_slope`
- `task_geometry_analytical_2d_area`
- `task_geometry_analytical_2d_length`
- `task_geometry_analytical_3d_volume`
- `task_geometry_analytical_3d_surface_area`
6. Task-review/sample-generation tooling with per-task artifacts and inspection workbooks.
7. Pre-finalize prompt validation checks (metadata/bundle/key/placeholder/cardinality).
