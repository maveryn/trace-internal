# `task_geometry_comparison_value`

## 1) Identity
1. Domain: `geometry`
2. Task group: `comparison`
3. Task id: `task_geometry_comparison_value`
4. Objective: choose the labeled object that wins a requested geometry comparison.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `angle`
   - `segment`
   - `rectangle`
2. Supported `query_variant` values:
   - `largest_angle`
   - `smallest_angle`
   - `largest_length`
   - `smallest_length`
   - `largest_area`
   - `smallest_area`
   - `largest_perimeter`
   - `smallest_perimeter`
3. Supported pairings:
   - `angle` with `largest_angle|smallest_angle`
   - `segment` with `largest_length|smallest_length`
   - `rectangle` with `largest_area|smallest_area|largest_perimeter|smallest_perimeter`
4. `answer_gt.type`: `option_letter`
5. Evidence remains winner-specific geometry evidence from the delegated comparison scene.

## 3) Prompt contract
1. Bundle: `geometry_comparison_v1`
2. Prompt wording remains delegated to the legacy comparison prompts.
3. Consolidated metadata records `scene_variant` and `query_variant` even though legacy prompts still phrase the question in object-specific terms.

## 4) Evidence + trace contract
1. `execution_trace`, `query_spec.params`, and `scene_ir.relations` record:
   - `scene_variant`
   - `query_variant`
   - `legacy_task_id`
2. `legacy_scene_variant` / `legacy_query_variant` are preserved when they differ from the consolidated axes.
3. Winner evidence stays in the original geometry-grounded format (for example point sets for the winning segment, angle, or rectangle).

## 5) Determinism + constraints
1. Deterministic generation from `instance_seed`.
2. Incompatible scene/query combinations are rejected.
3. Winner uniqueness is still guaranteed by the delegated legacy comparison task.

## 6) Complexity + tests
1. Complexity components stay comparison-family-specific and come from the delegated legacy generator.
2. Determinism/build tests: `tests/test_geometry_consolidated_contracts.py`
3. Behavior/trace tests: `tests/test_geometry_consolidated_tasks.py`
