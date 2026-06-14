# `task_three_d__surface_fixture__colored_element_count`

## Summary
- Domain: `three_d`
- Scene id: `surface_fixture`
- Scene package: `surface_fixture`
- Query id: `single`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`

## Program Contract
- `count(filter(surface_fixture_elements, present=true, element_type=target_element_type, color_name=target_color_name)); scene=surface_fixture; scope=colored_element_count`

## Contract
The image shows one projected fixture surface with repeated colored elements.
The prompt asks for the number of elements of the sampled family that have the
requested semantic color.

The answer is the integer count of finalized present cells whose
`element_type == target_element_type` and `color_name == target_color_name`.

## Annotation Contract
Annotation is a `bbox_set` containing one bounding box around each counted
colored surface element. Non-target colors, empty cells, the fixture panel, and
decorative context are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_surface_fixture_v1` under `prompts/three_d/surface_fixture/`.
The trace records scene variant, target element type, target color, explicit
cell metadata, projected element boxes, and the solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized fixture trace.
