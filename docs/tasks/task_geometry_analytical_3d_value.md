# `task_geometry_analytical_3d_value`

## 1) Identity
1. Domain: `geometry`
2. Task group: `analytical_3d`
3. Task id: `task_geometry_analytical_3d_value`
4. Objective: solve one annotated 3D solid problem from a consolidated solid-family scene scaffold.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `rectangular_prism`
   - `triangular_prism`
   - `square_pyramid`
   - `cylinder`
   - `cone`
   - `sphere`
2. Supported `query_variant` values:
   - `volume`
   - `surface_area`
3. Every supported solid scene can pair with both query variants.
4. Evidence stays `label_set`, with each item formatted as `ANNOTATION=VALUE`.
5. Answer types remain legacy-variant-dependent (`integer` or `pi_expression`).

## 3) Prompt contract
1. Bundles remain legacy-generator-backed:
   - `geometry_analytical_volume_v1`
   - `geometry_analytical_surface_area_v1`
2. Consolidated trace metadata records `scene_variant` and `query_variant` while preserving the exact legacy solid variant used to phrase the prompt.

## 4) Evidence + trace contract
1. `label_set` evidence is the public source of truth for annotated givens, with one `ANNOTATION=VALUE` token per required annotation.
2. `execution_trace`, `query_spec.params`, and `scene_ir.relations` record:
   - `scene_variant`
   - `query_variant`
   - `legacy_task_id`
3. Measurement annotations and projected evidence remain delegated to the legacy analytical 3D generator.

## 5) Determinism + constraints
1. Deterministic generation from `instance_seed`.
2. Incompatible scene/query combinations are rejected.
3. Answers and evidence still come from the same finalized solid scene and annotation map.

## 6) Complexity + tests
1. Complexity components stay analytical-family-specific and come from the delegated legacy generator.
2. Determinism/build tests: `tests/test_geometry_consolidated_contracts.py`
3. Behavior/trace tests: `tests/test_geometry_consolidated_tasks.py`
