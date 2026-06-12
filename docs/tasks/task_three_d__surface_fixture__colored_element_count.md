# `task_three_d__surface_fixture__colored_element_count`

## Summary
- Domain: `three_d`
- Scene id: `surface_fixture`
- Scene package: `surface_fixture`
- Query id: `element_color_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Status: pending_v0_review

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
The prompt bundle is `three_d_surface_fixture_v0` under `prompts/three_d/surface_fixture/`.
The trace records scene variant, target element type, target color, explicit
cell metadata, projected element boxes, and the solver count predicate.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b
solve-rate calibration are pending.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized fixture trace.

