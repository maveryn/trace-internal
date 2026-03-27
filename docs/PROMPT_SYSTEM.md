# TRACE Prompt System

Prompt text is externalized and deterministic.

## 1) Core contract
1. Task modules must not hardcode user-facing prompt strings.
2. Bundles live under `prompts/<domain>/<task_group>/<bundle_id>.json`.
3. Composition layers:
   - task family,
   - task,
   - optional task variant,
   - output mode (`answer_only`, `answer_and_evidence`).
4. Selection is deterministic from seed namespaces.
5. Each required template list must contain exactly 5 high-quality variants.
6. All active tasks must provide explicit JSON-format instructions in both output modes:
   - `answer_only` uses `{"answer": ...}`
   - `answer_and_evidence` uses `{"evidence": ..., "answer": ...}`
7. Prefer slot-based composition for reusable format rules (for example shared `json_output_contract*` in domain/task-group config, with task-level `evidence_hint`/`answer_hint`/example overrides).
8. For mixed-shape tasks, keep one bundle and switch shape-specific wording via slots (`object_description_*`, `question_text_*`, evidence/answer hint families).
9. When a prompt asks about a named color, include the canonical hex code in the prompt-facing color label using the format `<color_name> [#RRGGBB]`.

## 2) Bundle schema (v1)
Required fields:
1. `bundle_id`
2. `schema_version`
3. `task_family_templates`
4. `task_templates`
5. `answer_or_evidence_templates`
6. `required_slots_by_key`
7. Optional: `task_variant_templates`

## 3) Metadata requirements
Trace `query_spec.prompt_variant` should include:
1. bundle/key identifiers (`task_family_key`, `task_key`, optional `task_variant_key`),
2. selected variant indices,
3. variant counts,
4. slot values for declared required slots,
5. output-mode key/index when mode templates exist.

Train records should store:
1. active `prompt`,
2. all rendered mode variants in `prompt_variants`.

## 4) Shared implementation
1. `trace/core/prompts/assets.py` — bundle loading/cache.
2. `trace/core/prompts/schema.py` — schema validation.
3. `trace/core/prompts/select.py` — deterministic variant selection.
4. `trace/core/prompts/render.py` — strict rendering and composition.
5. `trace/tasks/shared/prompt_variants.py` — task-level dual-mode orchestration.

## 4.1 Prompt-quality policy
1. Prefer 5 strong variants over larger padded lists.
2. Keep stems natural and image-focused; avoid awkward scaffolding such as “single/exactly one object” unless the distinction is semantically necessary.
3. Keep output-mode variants concise and structurally consistent so format requirements stay easy to parse.

## 5) Active bundles/tasks
Bundles:
1. `prompts/geometry/measurement/geometry_angle_measure_v1.json`
2. `prompts/geometry/measurement/geometry_measurement_v1.json`
3. `prompts/geometry/analytical_2d/geometry_analytical_area_v1.json`
4. `prompts/geometry/analytical_2d/geometry_analytical_length_v1.json`
5. `prompts/geometry/analytical_3d/geometry_analytical_volume_v1.json`
6. `prompts/geometry/analytical_3d/geometry_analytical_surface_area_v1.json`
7. `prompts/tile/count/tile_count_v1.json`
8. `prompts/tile/path/tile_path_v1.json`
9. `prompts/tile/pattern/tile_pattern_v1.json`
10. `prompts/tile/reachability/tile_reachability_v1.json`
11. `prompts/tile/relation/tile_relation_v1.json`
12. `prompts/tile/symmetry/tile_symmetry_v1.json`
13. `prompts/tile/transition/tile_transition_v1.json`

Tasks:
1. `task_geometry_measurement_angle` (bundle override: `geometry_angle_measure_v1`)
2. `task_geometry_measurement_area` (bundle: `geometry_measurement_v1`)
3. `task_geometry_measurement_perimeter` (bundle: `geometry_measurement_v1`)
4. `task_geometry_measurement_length` (bundle: `geometry_measurement_v1`)
5. `task_geometry_measurement_slope` (bundle: `geometry_measurement_v1`)
6. `task_geometry_analytical_2d_area` (bundle: `geometry_analytical_area_v1`)
7. `task_geometry_analytical_2d_length` (bundle: `geometry_analytical_length_v1`)
8. `task_geometry_analytical_3d_volume` (bundle: `geometry_analytical_volume_v1`)
9. `task_geometry_analytical_3d_surface_area` (bundle: `geometry_analytical_surface_area_v1`)
10. `task_tile_count_color_count`
11. `task_tile_count_color_components`
12. `task_tile_count_largest_component_size`
13. `task_tile_path_shortest_path`
14. `task_tile_path_reachable_target_count`
15. `task_tile_pattern_match3_run_count`
16. `task_tile_reachability_region_size`
17. `task_tile_relation_min_distance`
18. `task_tile_symmetry_violation_count`
19. `task_tile_transition_gravity_max_drop`
