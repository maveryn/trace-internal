# `task_three_d__surface_fixture__scoped_colored_element_count`

## Summary
- Domain: `three_d`
- Scene id: `surface_fixture`
- Scene package: `surface_fixture`
- Query ids: `row_scoped_color_count`, `column_scoped_color_count`
- Answer type: `integer`
- Annotation type: unordered `point_set`

## Program Contract
- `count(filter(surface_fixture_elements, present=true, scope_axis=scope_axis, scope_index=scope_index, color_name=target_color_name)); scene=surface_fixture; scope=scoped_colored_element_count`

## Contract
The image shows one projected fixture surface arranged in rows and columns with
repeated colored elements. The prompt asks for the number of elements of the
requested color within one sampled row or column.
Generated named-color instances use readout-safe fixture variants and avoid
near-color distractors for the requested semantic color.

The answer is the integer count of finalized present cells matching both the
requested scope and `color_name == target_color_name`.
The `row_scoped_color_count` query binds `scope_axis=row`; the
`column_scoped_color_count` query binds `scope_axis=column`.

## Annotation Contract
Annotation is a `point_set` containing one center point for each counted colored
surface element in the requested row or column. Same-color elements outside the
scope, other colors, the fixture panel, and decorative context are not
annotation.

## Prompt And Trace
The prompt bundle is `three_d_surface_fixture_v1` under `prompts/three_d/surface_fixture/`.
The trace records scene variant, target element type, target color, scope axis,
scope index, explicit cell metadata, projected element centers, and the solver
count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized fixture trace.
