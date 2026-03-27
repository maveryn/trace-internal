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
10. For reference-panel tasks, keep the task-family layer responsible for establishing the panel layout so task-layer wording can focus on the matching rule itself.

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
1. `prompts/geometry/comparison/geometry_comparison_v1.json`
2. `prompts/geometry/counting/geometry_counting_v1.json`
3. `prompts/geometry/measurement/geometry_angle_measure_v1.json`
4. `prompts/geometry/measurement/geometry_measurement_v1.json`
5. `prompts/geometry/analytical_2d/geometry_analytical_area_v1.json`
6. `prompts/geometry/analytical_2d/geometry_analytical_composite_area_v1.json`
7. `prompts/geometry/analytical_2d/geometry_analytical_length_v1.json`
8. `prompts/geometry/analytical_2d/geometry_analytical_perimeter_v1.json`
9. `prompts/geometry/analytical_3d/geometry_analytical_volume_v1.json`
10. `prompts/geometry/analytical_3d/geometry_analytical_surface_area_v1.json`
11. `prompts/icons/counting/icons_counting_v1.json`
12. `prompts/icons/relation/icons_relation_v1.json`
13. `prompts/icons/sequence/icons_sequence_v1.json`
14. `prompts/icons/transformation/icons_transformation_v1.json`
15. `prompts/tile/count/tile_count_v1.json`
16. `prompts/tile/path/tile_path_v1.json`
17. `prompts/tile/pattern/tile_pattern_v1.json`
18. `prompts/tile/reachability/tile_reachability_v1.json`
19. `prompts/tile/relation/tile_relation_v1.json`
20. `prompts/tile/symmetry/tile_symmetry_v1.json`
21. `prompts/tile/transition/tile_transition_v1.json`

Tasks:
1. `task_geometry_comparison_angle` (bundle: `geometry_comparison_v1`)
2. `task_geometry_comparison_area` (bundle: `geometry_comparison_v1`)
3. `task_geometry_comparison_length` (bundle: `geometry_comparison_v1`)
4. `task_geometry_comparison_perimeter` (bundle: `geometry_comparison_v1`)
5. `task_geometry_counting_angle` (bundle: `geometry_counting_v1`)
6. `task_geometry_counting_triangle` (bundle: `geometry_counting_v1`)
7. `task_geometry_counting_quadrilateral` (bundle: `geometry_counting_v1`)
8. `task_geometry_counting_shape_type` (bundle: `geometry_counting_v1`)
9. `task_geometry_counting_convexity` (bundle: `geometry_counting_v1`)
10. `task_geometry_measurement_angle` (bundle override: `geometry_angle_measure_v1`)
11. `task_geometry_measurement_area` (bundle: `geometry_measurement_v1`)
12. `task_geometry_measurement_perimeter` (bundle: `geometry_measurement_v1`)
13. `task_geometry_measurement_length` (bundle: `geometry_measurement_v1`)
14. `task_geometry_measurement_slope` (bundle: `geometry_measurement_v1`)
15. `task_geometry_analytical_2d_area` (bundle: `geometry_analytical_area_v1`)
16. `task_geometry_analytical_2d_composite_area` (bundle: `geometry_analytical_composite_area_v1`)
17. `task_geometry_analytical_2d_length` (bundle: `geometry_analytical_length_v1`)
18. `task_geometry_analytical_2d_perimeter` (bundle: `geometry_analytical_perimeter_v1`)
19. `task_geometry_analytical_3d_volume` (bundle: `geometry_analytical_volume_v1`)
20. `task_geometry_analytical_3d_surface_area` (bundle: `geometry_analytical_surface_area_v1`)
21. `task_icons_counting_type` (bundle: `icons_counting_v1`)
22. `task_icons_counting_orientation` (bundle: `icons_counting_v1`)
23. `task_icons_counting_color` (bundle: `icons_counting_v1`)
24. `task_icons_counting_size_relation` (bundle: `icons_counting_v1`)
25. `task_icons_relation_relative_position_type` (bundle: `icons_relation_v1`)
26. `task_icons_relation_occlusion_order` (bundle: `icons_relation_v1`)
27. `task_icons_sequence_missing_count` (bundle: `icons_sequence_v1`)
28. `task_icons_transformation_pair_count` (bundle: `icons_transformation_v1`)
29. `task_tile_count_color_count` (bundle: `tile_count_v1`)
30. `task_tile_count_color_components` (bundle: `tile_count_v1`)
31. `task_tile_count_largest_component_size` (bundle: `tile_count_v1`)
32. `task_tile_path_shortest_path` (bundle: `tile_path_v1`)
33. `task_tile_path_reachable_target_count` (bundle: `tile_path_v1`)
34. `task_tile_pattern_match3_run_count` (bundle: `tile_pattern_v1`)
35. `task_tile_reachability_region_size` (bundle: `tile_reachability_v1`)
36. `task_tile_relation_min_distance` (bundle: `tile_relation_v1`)
37. `task_tile_symmetry_violation_count` (bundle: `tile_symmetry_v1`)
38. `task_tile_transition_gravity_max_drop` (bundle: `tile_transition_v1`)
