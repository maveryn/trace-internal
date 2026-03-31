# `task_geometry_analytical_2d_value`

## 1) Identity
1. Domain: `geometry`
2. Task group: `analytical_2d`
3. Task id: `task_geometry_analytical_2d_value`
4. Objective: solve one annotated 2D geometry problem from a consolidated shape-based scene family.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `rectangle`
   - `triangle`
   - `parallelogram`
   - `trapezoid`
   - `rhombus`
   - `circle`
   - `ellipse`
   - `composite_region`
2. Supported `query_variant` values:
   - `area`
   - `length`
   - `perimeter`
   - `composite_area`
3. Supported pairings:
   - `rectangle|triangle|parallelogram|trapezoid|rhombus|circle|ellipse` with `area`
   - `triangle|rectangle|rhombus|trapezoid|circle` with `length`
   - `triangle|rectangle|rhombus|trapezoid|circle` with `perimeter`
   - `composite_region` with `composite_area`
4. Evidence stays `label_set` across all pairings, with each item formatted as `ANNOTATION=VALUE`.
5. Answer types remain legacy-variant-dependent (`integer`, `decimal`, or `pi_expression`).

## 3) Prompt contract
1. Bundles remain legacy-generator-backed:
   - `geometry_analytical_area_v1`
   - `geometry_analytical_length_v1`
   - `geometry_analytical_perimeter_v1`
   - `geometry_analytical_composite_area_v1`
2. Consolidated trace metadata records `scene_variant` and `query_variant` while preserving the legacy prompt variant that actually produced the question wording.

## 4) Evidence + trace contract
1. `label_set` evidence remains the public source of truth for all annotated givens, with one `ANNOTATION=VALUE` token per required annotation.
2. `execution_trace`, `query_spec.params`, and `scene_ir.relations` record:
   - `scene_variant`
   - `query_variant`
   - `legacy_task_id`
3. Legacy derivation-specific details remain in trace for review and verifier alignment.

## 5) Determinism + constraints
1. Deterministic generation from `instance_seed`.
2. Incompatible scene/query combinations are rejected.
3. The consolidated task keeps the underlying analytical reasoning contracts unchanged; it only refactors taxonomy and variant sampling.

## 6) Complexity + tests
1. Complexity components stay analytical-family-specific and come from the delegated legacy generator.
2. Determinism/build tests: `tests/test_geometry_consolidated_contracts.py`
3. Behavior/trace tests: `tests/test_geometry_consolidated_tasks.py`
